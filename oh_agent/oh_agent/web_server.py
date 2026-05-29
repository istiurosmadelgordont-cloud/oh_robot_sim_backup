import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import json
import uvicorn

from configurations.config import AgentConfig
from common.database import Database
from common.mcp_client import MCPManager
from common.models import ChatCompletionRequest, ChatCompletionResponse, ConversationResponse, MessageResponse, ToolCallResponse
from agent import Agent

logger = logging.getLogger(__name__)


class WebServer:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.db: Optional[Database] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.agent: Optional[Agent] = None

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.startup()
            yield
            # Shutdown
            await self.shutdown()

        self.app = FastAPI(
            title="Robot Agent API",
            description="Multi-model agent with MCP integration",
            version="1.0.0",
            lifespan=lifespan
        )

        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._setup_routes()

    async def startup(self):
        """Initialize components"""
        logger.info("Starting up web server...")

        # Initialize database
        self.db = Database(self.config.database_url)
        await self.db.init_db()

        # Initialize MCP manager
        self.mcp_manager = MCPManager(self.config.mcp_servers)
        await self.mcp_manager.connect_all()

        # Initialize agent
        self.agent = Agent(self.config, self.db, self.mcp_manager)

        logger.info("Web server started successfully")

    async def shutdown(self):
        """Cleanup components"""
        logger.info("Shutting down web server...")
        if self.mcp_manager:
            await self.mcp_manager.disconnect_all()

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/health")
        async def health_check():
            return {"status": "ok"}

        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatCompletionRequest):
            """OpenAI-compatible chat completions endpoint"""
            try:
                if request.stream:
                    return StreamingResponse(
                        self._stream_response(request),
                        media_type="text/event-stream"
                    )
                else:
                    result = await self.agent.chat(
                        messages=request.messages,
                        model=request.model,
                        conversation_id=request.conversation_id,
                        stream=False,
                        max_tokens=request.max_tokens,
                        temperature=request.temperature
                    )
                    response = result["response"]
                    return ChatCompletionResponse(
                        id=response.get("id", ""),
                        created=int(time.time()),
                        model=request.model,
                        choices=[{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response.get("content", "")
                            },
                            "finish_reason": response.get("stop_reason", "stop")
                        }],
                        usage=response.get("usage")
                    )
            except Exception as e:
                logger.error(f"Chat completion error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/conversations")
        async def list_conversations(limit: int = 100, offset: int = 0):
            """List all conversations"""
            try:
                convs = await self.db.list_conversations(limit, offset)

                results = []
                for conv in convs:
                    msg_count = len(await self.db.get_messages(conv.id))
                    results.append(ConversationResponse(
                        id=conv.id,
                        created_at=conv.created_at,
                        updated_at=conv.updated_at,
                        title=conv.title,
                        message_count=msg_count
                    ))

                return results

            except Exception as e:
                logger.error(f"List conversations error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/conversations/{conversation_id}")
        async def get_conversation(conversation_id: int):
            """Get conversation details"""
            try:
                conv = await self.db.get_conversation(conversation_id)
                if not conv:
                    raise HTTPException(status_code=404, detail="Conversation not found")

                msg_count = len(await self.db.get_messages(conv.id))

                return ConversationResponse(
                    id=conv.id,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    title=conv.title,
                    message_count=msg_count
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Get conversation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/conversations/{conversation_id}/messages")
        async def get_messages(conversation_id: int, limit: Optional[int] = None):
            """Get messages for a conversation"""
            try:
                messages = await self.db.get_messages(conversation_id, limit)

                results = []
                for msg in messages:
                    content = msg.content_json if msg.content_json is not None else msg.content
                    results.append(MessageResponse(
                        id=msg.id,
                        role=msg.role,
                        content=content,
                        created_at=msg.created_at,
                        model=msg.model
                    ))

                return results

            except Exception as e:
                logger.error(f"Get messages error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/conversations/{conversation_id}/tool_calls")
        async def get_tool_calls(conversation_id: int):
            """Get tool calls for a conversation"""
            try:
                tool_calls = await self.db.get_tool_calls(conversation_id)

                results = []
                for tc in tool_calls:
                    results.append(ToolCallResponse(
                        id=tc.id,
                        tool_name=tc.tool_name,
                        tool_input=tc.tool_input,
                        tool_output=tc.tool_output,
                        status=tc.status,
                        error=tc.error,
                        started_at=tc.started_at,
                        completed_at=tc.completed_at
                    ))

                return results

            except Exception as e:
                logger.error(f"Get tool calls error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/tools")
        async def list_tools():
            """List all available MCP tools"""
            try:
                return self.mcp_manager.get_all_tools()
            except Exception as e:
                logger.error(f"List tools error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _stream_response(self, request: ChatCompletionRequest):
        """Stream chat responses in SSE format"""
        try:
            async_generator = await self.agent.chat(
                messages=request.messages,
                model=request.model,
                conversation_id=request.conversation_id,
                stream=True,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            async for chunk in async_generator:
                if chunk["type"] == "content":
                    data = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk["content"]},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                elif chunk["type"] == "done":
                    data = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the web server"""
        uvicorn.run(self.app, host=host, port=port)
