import logging
from contextlib import asynccontextmanager
from typing import List, AsyncGenerator, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from common.models import *

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str):
        # Convert sqlite:/// to sqlite+aiosqlite:///
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database schema"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for database sessions"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_conversation(self, title: Optional[str] = None, metadata: dict = None) -> Conversation:
        """Create a new conversation"""
        async with self.session() as session:
            conv = Conversation(title=title, meta=metadata or {})
            session.add(conv)
            await session.flush()
            await session.refresh(conv)
            return conv

    async def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID"""
        async with self.session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            return result.scalar_one_or_none()

    async def list_conversations(self, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List all conversations"""
        async with self.session() as session:
            result = await session.execute(
                select(Conversation)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def add_message(
            self,
            conversation_id: int,
            role: str,
            content: str | list[dict] | None,
            model: Optional[str] = None
    ) -> Message:
        """Add a message to a conversation"""
        async with self.session() as session:
            # Update conversation timestamp
            conv = await session.get(Conversation, conversation_id)
            if conv:
                conv.updated_at = datetime.utcnow()

            # Handle content types
            content_text = None
            content_json = None
            if isinstance(content, str):
                content_text = content
            elif isinstance(content, list):
                content_json = content

            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content_text,
                content_json=content_json,
                model=model
            )
            session.add(msg)
            await session.flush()
            await session.refresh(msg)
            return msg

    async def get_messages(
            self,
            conversation_id: int,
            limit: Optional[int] = None
    ) -> List[Message]:
        """Get messages for a conversation"""
        async with self.session() as session:
            query = select(Message).where(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at)

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def add_tool_call(
            self,
            conversation_id: int,
            tool_name: str,
            tool_input: dict,
            message_id: Optional[int] = None
    ) -> ToolCall:
        """Record a tool call"""
        async with self.session() as session:
            tool_call = ToolCall(
                conversation_id=conversation_id,
                message_id=message_id,
                tool_name=tool_name,
                tool_input=tool_input,
                status=ToolCallStatus.PENDING.value
            )
            session.add(tool_call)
            await session.flush()
            await session.refresh(tool_call)
            return tool_call

    async def update_tool_call(
            self,
            tool_call_id: int,
            status: str,
            tool_output: Optional[dict] = None,
            error: Optional[str] = None
    ) -> ToolCall:
        """Update tool call status and result"""
        async with self.session() as session:
            tool_call = await session.get(ToolCall, tool_call_id)
            if tool_call:
                tool_call.status = status
                tool_call.tool_output = tool_output
                tool_call.error = error
                tool_call.completed_at = datetime.utcnow()
                await session.flush()
                await session.refresh(tool_call)
            return tool_call

    async def get_tool_calls(self, conversation_id: int) -> List[ToolCall]:
        """Get all tool calls for a conversation"""
        async with self.session() as session:
            result = await session.execute(
                select(ToolCall)
                .where(ToolCall.conversation_id == conversation_id)
                .order_by(ToolCall.started_at)
            )
            return list(result.scalars().all())
