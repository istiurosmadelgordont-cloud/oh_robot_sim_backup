import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
import anthropic
import openai
import logging

from configurations.config import ModelConfig

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters"""

    @abstractmethod
    async def complete(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            stream: bool = False,
            **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """Generate completion"""
        pass

    @abstractmethod
    def format_message(self, role: str, content: Any) -> Dict[str, Any]:
        """Format message for the specific provider"""
        pass

    @abstractmethod
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from response"""
        pass


class AnthropicAdapter(LLMAdapter):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = anthropic.AsyncAnthropic(api_key=config.api_key)

    async def complete(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            stream: bool = False,
            **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        # Separate system messages
        system_messages = [m for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]

        system_content = "\n".join([m["content"] for m in system_messages]) if system_messages else None

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in other_messages:
            anthropic_messages.append(self.format_message(msg["role"], msg["content"]))

        params = {
            "model": self.config.model_name,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "messages": anthropic_messages,
        }

        if system_content:
            params["system"] = system_content

        if tools:
            params["tools"] = tools

        if stream:
            return self._stream_complete(params)
        else:
            response = await self.client.messages.create(**params)
            return self._format_response(response)

    async def _stream_complete(self, params: dict) -> AsyncGenerator[Dict[str, Any], None]:
        async with self.client.messages.stream(**params) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield {
                                "type": "content",
                                "content": event.delta.text
                            }
                    elif event.type == "message_stop":
                        message = await stream.get_final_message()
                        yield {
                            "type": "done",
                            "message": self._format_response(message)
                        }

    def _format_response(self, response) -> Dict[str, Any]:
        content_blocks = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
                content_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return {
            "id": response.id,
            "model": response.model,
            "role": "assistant",
            "content": content_blocks,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }

    def format_message(self, role: str, content: Any) -> Dict[str, Any]:
        # Handle tool results
        if role == "tool":
            return {
                "role": "user",
                "content": content if isinstance(content, list) else [content]
            }

        # Handle regular messages
        if isinstance(content, str):
            return {"role": role, "content": content}
        elif isinstance(content, list):
            # Handle multimodal content
            formatted_content = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        formatted_content.append(item)
                    elif item.get("type") == "image_url":
                        # Convert image URL to Anthropic format
                        image_url = item["image_url"]["url"]
                        if image_url.startswith("data:"):
                            # Extract media type and base64 data
                            header, data = image_url.split(",", 1)
                            media_type = header.split(";")[0].split(":")[1]
                            formatted_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": data
                                }
                            })
                    else:
                        formatted_content.append(item)
            return {"role": role, "content": formatted_content}

        return {"role": role, "content": str(content)}

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("tool_calls", [])


class OpenAIAdapter(LLMAdapter):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )

    async def complete(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            stream: bool = False,
            **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        # Convert messages to OpenAI format
        openai_messages = []
        for m in messages:
            formatted = self.format_message(m["role"], m["content"])
            
            # Preserve tool_call_id for tool messages
            if m["role"] == "tool" and "tool_call_id" in m:
                formatted["tool_call_id"] = m["tool_call_id"]
            
            # Preserve tool_calls for assistant messages
            if m["role"] == "assistant" and "tool_calls" in m:
                formatted["tool_calls"] = m["tool_calls"]
            
            openai_messages.append(formatted)

        params = {
            "model": self.config.model_name,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "messages": openai_messages,
        }

        if tools:
            # Convert tools to OpenAI format
            params["tools"] = [self._convert_tool_schema(t) for t in tools]

        if stream:
            return self._stream_complete(params)
        else:
            response = await self.client.chat.completions.create(**params)
            return self._format_response(response)

    async def _stream_complete(self, params: dict) -> AsyncGenerator[Dict[str, Any], None]:
        stream = await self.client.chat.completions.create(**params, stream=True)
        collected_content = []
        collected_tool_calls = {}
        finish_reason = None
        response_id = None
        response_model = None

        async for chunk in stream:
            if not response_id:
                response_id = chunk.id
                response_model = chunk.model

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason or finish_reason

            # Collect content
            if delta.content:
                yield {
                    "type": "content",
                    "content": delta.content
                }
                collected_content.append(delta.content)

            # Collect tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in collected_tool_calls:
                        collected_tool_calls[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }

                    if tc_delta.id:
                        collected_tool_calls[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            collected_tool_calls[idx]["function"]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            collected_tool_calls[idx]["function"]["arguments"] += tc_delta.function.arguments

            if finish_reason:
                # Build complete message
                tool_calls_list = []
                for idx in sorted(collected_tool_calls.keys()):
                    tc = collected_tool_calls[idx]
                    tool_calls_list.append({
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    })

                yield {
                    "type": "done",
                    "message": {
                        "id": response_id,
                        "model": response_model,
                        "role": "assistant",
                        "content": "".join(collected_content) if collected_content else "",
                        "tool_calls": tool_calls_list,
                        "stop_reason": finish_reason
                    }
                }

    def _format_response(self, response) -> Dict[str, Any]:
        choice = response.choices[0]
        message = choice.message

        content = message.content or ""
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments)
                })

        return {
            "id": response.id,
            "model": response.model,
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": choice.finish_reason,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        }

    def _convert_tool_schema(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MCP tool schema to OpenAI format"""
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
            }
        }

    def format_message(self, role: str, content: Any) -> Dict[str, Any]:
        if role == "tool":
            # OpenAI expects tool responses in a specific format
            if isinstance(content, str):
                # Simple string content
                return {
                    "role": "tool",
                    "content": content
                }
            elif isinstance(content, dict):
                # Single tool result
                return {
                    "role": "tool",
                    "tool_call_id": content.get("tool_use_id", content.get("tool_call_id", "")),
                    "content": json.dumps(content.get("content", content))
                }
            elif isinstance(content, list):
                # Multiple tool results - return first one, others will be added separately
                if len(content) > 0:
                    first = content[0]
                    return {
                        "role": "tool",
                        "tool_call_id": first.get("tool_use_id", first.get("tool_call_id", "")),
                        "content": json.dumps(first.get("content", first))
                    }

        return {"role": role, "content": content}

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("tool_calls", [])


class DeepseekAdapter(OpenAIAdapter):
    """Deepseek uses OpenAI-compatible API"""
    pass


class QwenAdapter(OpenAIAdapter):
    """Deepseek uses OpenAI-compatible API"""
    pass


def create_adapter(config: ModelConfig) -> LLMAdapter:
    """Factory function to create appropriate adapter"""
    adapters = {
        # "anthropic": AnthropicAdapter,
        # "openai": OpenAIAdapter,
        # "deepseek": DeepseekAdapter,
        "qwen": QwenAdapter,
    }

    adapter_class = adapters.get(config.provider)
    if not adapter_class:
        raise ValueError(f"Unsupported provider: {config.provider}")

    return adapter_class(config)
