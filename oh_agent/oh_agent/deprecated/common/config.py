from langchain_openai import ChatOpenAI
from mcp import StdioServerParameters

# ────────────────────────────────────────────────────────────────────────────
# Configurations
# ────────────────────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    # model_name="gpt-4o-mini",
    # temperature=0.3,
    # base_url="http://localhost:17100",
    # api_key="sk-dwjeifjiewrpijepwjiw")
    model_name="doubao-1.5-lite-32k-250115",
    temperature=0.3,
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="b6ffe756-a533-431e-b6ad-1d9270350c52")
vlm = ChatOpenAI(
    model_name="doubao-1-5-vision-lite-250315",
    temperature=0.3,
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="b6ffe756-a533-431e-b6ad-1d9270350c52")
server_params = StdioServerParameters(
    command="python",
    args=["servers/robot_mcp_server.py", "--stdio", "--grpc-host", "172.17.0.3"],
    env={"PYTHONPATH": "."},
    # args=["robot_mcp_server.py", "--stdio"]
)
