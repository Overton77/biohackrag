# mcp_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="BiohackAgent", stateless_http=True)  

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Simple dynamic resource."""
    return f"Hello, {name}!"