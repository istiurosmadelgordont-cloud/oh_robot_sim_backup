from datetime import datetime
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    title = Column(String(255), nullable=True)
    meta = Column(JSON, default=dict)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    message_id = Column(Integer, nullable=True)
    tool_name = Column(String(255), nullable=False)
    tool_input = Column(JSON, nullable=False)
    tool_output = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default=ToolCallStatus.PENDING.value)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="tool_calls")


# API Models
class ChatMessage(BaseModel):
    role: MessageRole
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model to use")
    messages: list[ChatMessage]
    stream: bool = Field(False, description="Enable streaming")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    temperature: Optional[float] = Field(None, description="Temperature")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID")


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: Optional[dict[str, int]] = None


class ConversationResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    title: Optional[str]
    message_count: int


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str | list[dict[str, Any]] | None
    created_at: datetime
    model: Optional[str]


class ToolCallResponse(BaseModel):
    id: int
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Optional[dict[str, Any]]
    status: str
    error: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]