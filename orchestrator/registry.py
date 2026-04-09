"""Server Registry — Tracks all MCP servers, their status, and health."""
import time
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("mcphub.registry")


class ServerStatus(str, Enum):
    REGISTERED = "registered"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class ServerInfo:
    name: str
    description: str
    version: str = "1.0.0"
    status: ServerStatus = ServerStatus.REGISTERED
    tools_count: int = 0
    tools: list = field(default_factory=list)
    last_heartbeat: float = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_ms: float = 0
    started_at: Optional[float] = None

    @property
    def uptime_seconds(self) -> float:
        if self.started_at:
            return time.time() - self.started_at
        return 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "tools_count": self.tools_count,
            "tools": self.tools,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 2),
            "avg_response_ms": round(self.avg_response_ms, 2),
        }


class ServerRegistry:
    """Central registry for all MCP servers in the MCPHub ecosystem."""

    def __init__(self):
        self._servers: dict[str, ServerInfo] = {}
        self._lock = asyncio.Lock()

    async def register(self, name: str, description: str, version: str = "1.0.0",
                       tools: list = None) -> ServerInfo:
        async with self._lock:
            info = ServerInfo(
                name=name,
                description=description,
                version=version,
                tools=tools or [],
                tools_count=len(tools) if tools else 0,
                status=ServerStatus.RUNNING,
                started_at=time.time(),
                last_heartbeat=time.time(),
            )
            self._servers[name] = info
            logger.info(f"Registered server: {name} ({len(info.tools)} tools)")
            return info

    async def unregister(self, name: str):
        async with self._lock:
            if name in self._servers:
                self._servers[name].status = ServerStatus.STOPPED
                logger.info(f"Unregistered server: {name}")

    async def heartbeat(self, name: str):
        if name in self._servers:
            self._servers[name].last_heartbeat = time.time()
            self._servers[name].status = ServerStatus.RUNNING

    async def record_request(self, name: str, success: bool, response_ms: float):
        if name in self._servers:
            srv = self._servers[name]
            srv.total_requests += 1
            if not success:
                srv.failed_requests += 1
            # Running average
            n = srv.total_requests
            srv.avg_response_ms = srv.avg_response_ms + (response_ms - srv.avg_response_ms) / n

    def get_server(self, name: str) -> Optional[ServerInfo]:
        return self._servers.get(name)

    def list_servers(self) -> list[dict]:
        return [srv.to_dict() for srv in self._servers.values()]

    def get_status_summary(self) -> dict:
        total = len(self._servers)
        running = sum(1 for s in self._servers.values() if s.status == ServerStatus.RUNNING)
        return {
            "total_servers": total,
            "running": running,
            "stopped": total - running,
            "servers": self.list_servers(),
        }
