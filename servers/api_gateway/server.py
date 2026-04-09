"""API Gateway MCP Server — Universal REST API connector via MCP."""
from fastmcp import FastMCP

from .gateway import APIGateway

mcp = FastMCP(
    "mcphub-api-gateway",
    description="Universal REST API connector for AI. Register any API, call endpoints, "
                "chain multi-step workflows, and test connectivity — all through MCP.",
)

gateway = APIGateway()


@mcp.tool()
async def register_api(name: str, base_url: str, description: str = "",
                        auth_type: str = "none", auth_value: str = "") -> dict:
    """Register an external API for AI to use.

    Args:
        name: Friendly name for this API (e.g., 'github', 'stripe')
        base_url: Base URL of the API (e.g., 'https://api.github.com')
        description: What this API does
        auth_type: Authentication type — 'none', 'bearer', 'api_key' (default: 'none')
        auth_value: Auth token or API key value
    """
    return await gateway.register_api(name, base_url, description, auth_type, auth_value)


@mcp.tool()
async def call_api(name: str = None, url: str = None, method: str = "GET",
                    path: str = "", params: dict = None, body: dict = None) -> dict:
    """Call a registered API or any URL directly. Returns status code, response body, headers.

    Args:
        name: Name of a registered API (use register_api first)
        url: Direct URL to call (alternative to name)
        method: HTTP method — GET, POST, PUT, DELETE, PATCH (default: GET)
        path: API path to append to base URL (e.g., '/users/123')
        params: Query parameters as key-value pairs
        body: Request body for POST/PUT/PATCH requests
    """
    return await gateway.call_api(name, url, method, path, params, body)


@mcp.tool()
async def list_apis() -> dict:
    """List all registered APIs with their base URLs and call counts."""
    return await gateway.list_apis()


@mcp.tool()
async def test_endpoint(url: str, method: str = "GET") -> dict:
    """Test if an API endpoint is reachable. Returns response time, status code, content type.

    Args:
        url: Full URL to test
        method: HTTP method (default: GET)
    """
    return await gateway.test_endpoint(url, method)


@mcp.tool()
async def create_workflow(name: str, steps: list[dict]) -> dict:
    """Create and execute a multi-step API workflow. Chain multiple API calls where
    results from previous steps can feed into later steps.

    Args:
        name: Workflow name for logging
        steps: List of step objects, each with: api, method, path, params, body.
               Use {{step_name.field}} to reference previous step results.
    """
    return await gateway.create_workflow(name, steps)


if __name__ == "__main__":
    mcp.run()
