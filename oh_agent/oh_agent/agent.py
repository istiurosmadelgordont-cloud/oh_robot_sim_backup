import json
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator

from configurations.config import AgentConfig
from configurations.prompts import SYS_PROMPT
from common.database import Database
from common.mcp_client import MCPManager
from common.models import ChatMessage, MessageRole, ToolCallStatus
from common.llm_adapters import LLMAdapter, create_adapter

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
            self,
            config: AgentConfig,
            database: Database,
            mcp_manager: MCPManager,
    ):
        self.config = config
        self.db = database
        self.mcp_manager = mcp_manager
        self.adapters: Dict[str, LLMAdapter] = {}

        # Initialize adapters
        for model_config in config.models:
            self.adapters[model_config.provider] = create_adapter(model_config)

    def get_adapter(self, provider: Optional[str] = None) -> LLMAdapter:
        """Get LLM adapter for specified provider"""
        provider = provider or self.config.default_model
        if provider not in self.adapters:
            raise ValueError(f"Provider '{provider}' not configured")
        return self.adapters[provider]

    async def chat(
            self,
            messages: List[ChatMessage],
            model: str,
            conversation_id: Optional[int] = None,
            stream: bool = False,
            **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """Main chat method supporting human-in-the-loop"""

        # Create or get conversation
        if conversation_id is None:
            conv = await self.db.create_conversation()
            conversation_id = conv.id
        else:
            conv = await self.db.get_conversation(conversation_id)
            if not conv:
                raise ValueError(f"Conversation {conversation_id} not found")

        # Store user messages
        for msg in messages:
            if msg.role == MessageRole.USER:
                await self.db.add_message(
                    conversation_id=conversation_id,
                    role=msg.role.value,
                    content=msg.content
                )

        # Get conversation history
        history = await self._build_context(conversation_id)

        # Add new messages to history
        for msg in messages:
            history.append({"role": msg.role.value, "content": msg.content})

        # Get tools
        tools = self.mcp_manager.get_all_tools()

        # Determine provider from model
        provider = self._get_provider_from_model(model)
        adapter = self.get_adapter(provider)

        if stream:
            return self._stream_chat(
                adapter, history, tools, conversation_id, model, **kwargs
            )
        else:
            return await self._complete_chat(
                adapter, history, tools, conversation_id, model, **kwargs
            )

    async def _complete_chat(
            self,
            adapter: LLMAdapter,
            history: List[Dict[str, Any]],
            tools: List[Dict[str, Any]],
            conversation_id: int,
            model: str,
            **kwargs
    ) -> Dict[str, Any]:
        """Non-streaming chat completion with tool execution loop"""

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Get completion from LLM
            response = await adapter.complete(history, tools=tools, stream=False, **kwargs)

            # Store assistant message
            assistant_content = response.get("content", "")
            if isinstance(assistant_content, list):
                assistant_content = assistant_content

            await self.db.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
                model=model
            )

            # Check for tool calls
            tool_calls = adapter.extract_tool_calls(response)

            if not tool_calls:
                # No more tool calls, return final response
                return {
                    "conversation_id": conversation_id,
                    "response": response,
                    "iterations": iteration
                }

            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_call_id = tool_call.get("id", "")

                # Record tool call in database
                db_tool_call = await self.db.add_tool_call(
                    conversation_id=conversation_id,
                    tool_name=tool_name,
                    tool_input=tool_input
                )

                try:
                    # Execute tool
                    logger.info(f"Executing tool: {tool_name}")
                    result = await self.mcp_manager.call_tool(tool_name, tool_input)
                    tool_result_dict = Agent._serialize_mcp_result(result)
                    tool_result_content: str = tool_result_dict["content"] if hasattr(result, 'content') \
                        else tool_result_dict["result"]

                    # Update tool call status
                    await self.db.update_tool_call(
                        tool_call_id=db_tool_call.id,
                        status=ToolCallStatus.SUCCESS.value,
                        tool_output=tool_result_dict
                    )

                    # Format result for LLM
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": tool_result_content
                    })

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    await self.db.update_tool_call(
                        tool_call_id=db_tool_call.id,
                        status=ToolCallStatus.FAILED.value,
                        error=str(e)
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    })

            # Add tool results to history
            history.append({"role": "assistant", "content": response.get("content", "")})
            history.append({"role": "tool", "content": tool_results})

        return {
            "conversation_id": conversation_id,
            "response": {"content": "Max iterations reached"},
            "iterations": iteration
        }

    async def _stream_chat(
            self,
            adapter: LLMAdapter,
            history: List[Dict[str, Any]],
            tools: List[Dict[str, Any]],
            conversation_id: int,
            model: str,
            **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming chat with tool execution"""

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            final_message: dict | None = None

            # Stream completion
            async for chunk in await adapter.complete(history, tools=tools, stream=True, **kwargs):
                if chunk["type"] == "content":
                    yield {
                        "type": "content",
                        "content": chunk["content"],
                        "conversation_id": conversation_id
                    }
                elif chunk["type"] == "done":
                    logger.info(f"finally done: {chunk}")
                    final_message = chunk["message"]

            # Ensure we have a final message
            if not final_message:
                yield {
                    "type": "error",
                    "message": "No response received from model",
                    "conversation_id": conversation_id
                }
                return

            # Store assistant message
            assistant_content = final_message.get("content", "")
            # tool call is a list[dict]
            if final_message.get("tool_calls"):
                # Store content with tool calls metadata
                content_with_tools: list[dict] = [{"type": "text", "text": assistant_content}]
                content_with_tools += (list[dict])(final_message["tool_calls"])
                await self.db.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=content_with_tools,
                    model=model
                )
            else:
                await self.db.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    model=model
                )

            # Check for tool calls
            tool_calls = adapter.extract_tool_calls(final_message)

            if not tool_calls:
                yield {
                    "type": "done",
                    "conversation_id": conversation_id,
                    "iterations": iteration
                }
                return

            # Execute tools
            yield {
                "type": "tool_calls",
                "tool_calls": tool_calls,
                "conversation_id": conversation_id
            }

            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_call_id = tool_call.get("id", "")

                db_tool_call = await self.db.add_tool_call(
                    conversation_id=conversation_id,
                    tool_name=tool_name,
                    tool_input=tool_input
                )

                try:
                    result = await self.mcp_manager.call_tool(tool_name, tool_input)
                    tool_result_dict = Agent._serialize_mcp_result(result)
                    tool_result_content: str = tool_result_dict["content"] if hasattr(result, 'content') \
                        else tool_result_dict["result"]

                    await self.db.update_tool_call(
                        tool_call_id=db_tool_call.id,
                        status=ToolCallStatus.SUCCESS.value,
                        tool_output=tool_result_dict
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_call_id": tool_call_id,
                        "content": tool_result_content
                    })

                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": tool_result_content,
                        "tool_call_id": tool_call_id,
                        "conversation_id": conversation_id
                    }

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    await self.db.update_tool_call(
                        tool_call_id=db_tool_call.id,
                        status=ToolCallStatus.FAILED.value,
                        error=str(e)
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_call_id": tool_call_id,
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    })

            # Update history for next iteration
            # Add assistant message with proper content structure
            history.append({
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["input"])
                        }
                    } for tc in tool_calls
                ]
            })

            # Add tool results
            for tool_call, result in zip(tool_calls, tool_results):
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(Agent._serialize_mcp_result(result))
                })

        yield {
            "type": "error",
            "message": "Max iterations reached",
            "conversation_id": conversation_id
        }

    async def _build_context(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Build conversation context from history"""
        messages = await self.db.get_messages(
            conversation_id,
            limit=self.config.max_conversation_history
        )

        context = [{"role": "system", "content": SYS_PROMPT}]
        for msg in messages:
            content = msg.content_json if msg.content_json is not None else msg.content
            context.append({
                "role": msg.role,
                "content": content
            })

        return context

    def _get_provider_from_model(self, model: str) -> str:
        """Extract provider from model string"""
        for provider in self.adapters.keys():
            if provider in model.lower():
                return provider
        return self.config.default_model

    @staticmethod
    def _serialize_mcp_result(result) -> dict:
        """Convert MCP result to JSON-serializable format"""
        if hasattr(result, 'content'):
            # Handle list of TextContent objects
            if isinstance(result.content, list):
                return {
                    "content": [
                        {"type": item.type, "text": item.text}
                        if hasattr(item, 'text') else str(item)
                        for item in result.content
                    ]
                }
            return {"content": str(result.content)}
        return {"result": str(result)}
