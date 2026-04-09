"""MCPHub Orchestrator — Central API that manages all MCP servers."""
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .registry import ServerRegistry
from .logger import AuditLogger
from .security import verify_api_key, sanitize_html, clamp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("mcphub")

registry = ServerRegistry()
audit = AuditLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MCPHub Orchestrator starting...")
    # Register all built-in servers
    await registry.register(
        "security-scanner", "Website security vulnerability scanner",
        tools=["scan_website", "check_ssl", "check_headers", "scan_ports", "get_security_score"]
    )
    await registry.register(
        "database-query", "Safe AI-powered database query engine",
        tools=["connect_database", "query", "list_tables", "describe_table", "export_results"]
    )
    await registry.register(
        "notification-hub", "Multi-channel notification dispatcher",
        tools=["send_email", "send_slack", "send_whatsapp", "send_webhook", "list_channels"]
    )
    await registry.register(
        "document-analyzer", "AI-powered document analysis and extraction",
        tools=["analyze_pdf", "analyze_csv", "extract_text", "summarize_document", "extract_tables"]
    )
    await registry.register(
        "api-gateway", "Universal REST API connector for AI",
        tools=["call_api", "register_api", "list_apis", "test_endpoint", "create_workflow"]
    )
    await registry.register(
        "system-monitor", "Server and infrastructure health monitoring",
        tools=["get_system_info", "get_cpu_usage", "get_memory_usage", "get_disk_usage",
               "list_processes", "get_network_stats"]
    )
    logger.info(f"Registered {len(registry.list_servers())} MCP servers")
    yield
    logger.info("MCPHub Orchestrator shutting down...")


app = FastAPI(
    title="MCPHub",
    description="Enterprise AI Integration Framework — Unified MCP Server Orchestrator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — restrict to known origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("MCPHUB_CORS_ORIGIN", "http://localhost:8000")],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)


# Request size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:  # 1MB max
        raise HTTPException(413, "Request body too large (max 1MB)")
    return await call_next(request)


# --- API Routes ---

@app.get("/health")
async def health():
    """Lightweight health check for load balancers."""
    return {"status": "ok"}


@app.get("/api/status")
async def get_status(_=Depends(verify_api_key)):
    """Get overall MCPHub status and all server states."""
    return {
        "status": "operational",
        "uptime": time.time(),
        "servers": registry.get_status_summary(),
        "audit": audit.get_stats(),
    }


@app.get("/api/servers")
async def list_servers(_=Depends(verify_api_key)):
    """List all registered MCP servers and their tools."""
    return {"servers": registry.list_servers()}


@app.get("/api/servers/{server_name}")
async def get_server(server_name: str, _=Depends(verify_api_key)):
    """Get detailed info about a specific MCP server."""
    server = registry.get_server(server_name)
    if not server:
        raise HTTPException(404, "Server not found")
    return server.to_dict()


@app.get("/api/audit")
async def get_audit_log(limit: int = 50, server: str = None, _=Depends(verify_api_key)):
    """Get recent audit log entries."""
    limit = clamp(limit, 1, 500)
    return {
        "entries": audit.get_recent(limit=limit, server=server),
        "stats": audit.get_stats(),
    }


@app.post("/api/servers/{server_name}/invoke/{tool_name}")
async def invoke_tool(server_name: str, tool_name: str, params: dict = None,
                      _=Depends(verify_api_key)):
    """Invoke a tool on a specific MCP server (REST API gateway)."""
    server = registry.get_server(server_name)
    if not server:
        raise HTTPException(404, "Server not found")
    if tool_name not in server.tools:
        raise HTTPException(404, "Tool not found")

    start = time.time()
    try:
        result = await _dispatch_tool(server_name, tool_name, params or {})
        elapsed = (time.time() - start) * 1000
        # Check for error-dict responses from tools
        success = not (isinstance(result, dict) and "error" in result)
        audit.log(server_name, tool_name, params or {}, success, elapsed)
        await registry.record_request(server_name, success, elapsed)
        return {"success": success, "result": result, "response_ms": round(elapsed, 2)}
    except ValueError as e:
        elapsed = (time.time() - start) * 1000
        audit.log(server_name, tool_name, params or {}, False, elapsed, error=str(e))
        await registry.record_request(server_name, False, elapsed)
        raise HTTPException(400, str(e))
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.exception(f"Tool invocation failed: {server_name}/{tool_name}")
        audit.log(server_name, tool_name, params or {}, False, elapsed, error=str(e))
        await registry.record_request(server_name, False, elapsed)
        raise HTTPException(500, "Internal server error")


async def _dispatch_tool(server_name: str, tool_name: str, params: dict):
    """Route tool calls to the correct server module."""
    if server_name == "security-scanner":
        from servers.security.scanner import SecurityScanner
        scanner = SecurityScanner()
        return await scanner.dispatch(tool_name, params)
    elif server_name == "database-query":
        from servers.database.engine import DatabaseEngine
        engine = DatabaseEngine()
        return await engine.dispatch(tool_name, params)
    elif server_name == "notification-hub":
        from servers.notifications.hub import NotificationHub
        hub = NotificationHub()
        return await hub.dispatch(tool_name, params)
    elif server_name == "document-analyzer":
        from servers.documents.analyzer import DocumentAnalyzer
        analyzer = DocumentAnalyzer()
        return await analyzer.dispatch(tool_name, params)
    elif server_name == "api-gateway":
        from servers.api_gateway.gateway import APIGateway
        gw = APIGateway()
        return await gw.dispatch(tool_name, params)
    elif server_name == "system-monitor":
        from servers.system_monitor.monitor import SystemMonitor
        monitor = SystemMonitor()
        return await monitor.dispatch(tool_name, params)
    else:
        raise ValueError(f"Unknown server: {server_name}")


# --- Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """MCPHub Dashboard — Web UI for managing all servers."""
    return DASHBOARD_HTML


DASHBOARD_HTML = open(
    os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html"), "r"
).read() if os.path.exists(
    os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")
) else "<h1>Dashboard not found</h1>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator.main:app", host="127.0.0.1", port=8000, reload=True)
