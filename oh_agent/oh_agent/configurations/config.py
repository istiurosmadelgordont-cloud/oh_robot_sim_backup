import os
from typing import Optional
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str = Field(..., description="Model provider: anthropic, openai, deepseek")
    model_name: str = Field(..., description="Model identifier")
    api_key: str = Field(..., description="API key")
    base_url: Optional[str] = Field(None, description="Custom base URL for API")
    max_tokens: int = Field(4096, description="Maximum tokens for completion")
    temperature: float = Field(0.7, description="Sampling temperature")


class MCPServerConfig(BaseModel):
    name: str = Field(..., description="MCP server name")
    command: str = Field(..., description="Command to start server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")


class AgentConfig(BaseModel):
    database_url: str = Field("sqlite:///./agent.db", description="Database connection URL")
    log_level: str = Field("INFO", description="Logging level")
    models: list[ModelConfig] = Field(default_factory=list, description="Available models")
    default_model: str = Field(..., description="Default model provider")
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list, description="MCP servers")
    max_conversation_history: int = Field(50, description="Max messages to keep in context")


def load_config() -> AgentConfig:
    """Load configuration from environment or defaults"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    robot_mcp_server_path = os.path.join(current_dir, "..", "robot_mcp_server.py")
    return AgentConfig(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./agent.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        default_model=os.getenv("DEFAULT_MODEL", "anthropic"),
        models=[
            # ModelConfig(
            #     provider="anthropic",
            #     model_name=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            #     api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            # ),
            # ModelConfig(
            #     provider="openai",
            #     model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
            #     api_key=os.getenv("OPENAI_API_KEY", ""),
            # ),
            ModelConfig(
                provider="qwen",
                model_name=os.getenv("QWEN_MODEL", "qwen3-4b"),
                api_key=os.getenv("QWEN_API_KEY", "sk-dwjeifjiewrpijepwjiw"),
                base_url=os.getenv("QWEN_BASE_URL", "http://localhost:17100"),
            ),
            # ModelConfig(
            #     provider="deepseek",
            #     model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            #     api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            #     base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            # ),
        ],
        mcp_servers=[
            MCPServerConfig(
                name="robot-simulator",
                command="python",
                args=[robot_mcp_server_path, "--transport", "stdio"],
                env={
                    "ROBOT_GRPC_HOST": os.getenv("ROBOT_GRPC_HOST", "localhost"),
                    "ROBOT_GRPC_PORT": os.getenv("ROBOT_GRPC_PORT", "50051"),
                },
            )
        ],
    )
