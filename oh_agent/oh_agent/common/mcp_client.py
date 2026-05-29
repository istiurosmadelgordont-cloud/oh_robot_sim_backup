import logging
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from configurations.config import MCPServerConfig


logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self.session: Optional[ClientSession] = None
        self._stdio_context = None
        self._read = None
        self._write = None
        self.tools: Dict[str, Any] = {}

    async def connect(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env or None
        )

        self._stdio_context = stdio_client(server_params)
        self._read, self._write = await self._stdio_context.__aenter__()
        self.session = ClientSession(self._read, self._write)
        await self.session.__aenter__()

        # Initialize and get tools
        await self.session.initialize()
        tools_list = await self.session.list_tools()
        self.tools = {tool.name: tool for tool in tools_list.tools}

        logger.info(f"Connected to MCP server '{self.config.name}' with {len(self.tools)} tools")

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._stdio_context:
            await self._stdio_context.__aexit__(None, None, None)
        logger.info(f"Disconnected from MCP server '{self.config.name}'")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected")

        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        result = await self.session.call_tool(tool_name, arguments)
        return result

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas in a format suitable for LLM APIs"""
        schemas = []
        for tool in self.tools.values():
            schema = {
                "name": tool.name,
                "description": tool.description or "",
            }

            if tool.inputSchema:
                schema["input_schema"] = tool.inputSchema

            schemas.append(schema)

        return schemas


class MCPManager:
    def __init__(self, server_configs: List[MCPServerConfig]):
        self.clients: Dict[str, MCPClient] = {}
        self.server_configs = server_configs

    async def connect_all(self):
        """Connect to all MCP servers"""
        for config in self.server_configs:
            client = MCPClient(config)
            await client.connect()
            self.clients[config.name] = client
        logger.info(f"Connected to {len(self.clients)} MCP servers")

    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tool schemas from all servers"""
        all_tools = []
        for client in self.clients.values():
            all_tools.extend(client.get_tool_schemas())
        return all_tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on any connected server"""
        for client in self.clients.values():
            if tool_name in client.tools:
                return await client.call_tool(tool_name, arguments)

        raise ValueError(f"Tool '{tool_name}' not found on any connected server")
