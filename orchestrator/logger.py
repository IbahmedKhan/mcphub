"""Audit Logger — Tracks all MCP tool calls for compliance and debugging."""
import json
import time
import logging
from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger("mcphub.audit")


@dataclass
class AuditEntry:
    timestamp: float
    server: str
    tool: str
    user: Optional[str]
    parameters: dict
    success: bool
    response_ms: float
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)),
            "server": self.server,
            "tool": self.tool,
            "user": self.user,
            "parameters": self.parameters,
            "success": self.success,
            "response_ms": round(self.response_ms, 2),
            "error": self.error,
        }


class AuditLogger:
    """Logs all MCP tool invocations for audit trail and analytics."""

    def __init__(self, log_dir: str = "logs"):
        self._entries: list[AuditEntry] = []
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)
        self._max_memory_entries = 10000

    def log(self, server: str, tool: str, parameters: dict,
            success: bool, response_ms: float, user: str = None,
            error: str = None):
        entry = AuditEntry(
            timestamp=time.time(),
            server=server,
            tool=tool,
            user=user,
            parameters=self._sanitize_params(parameters),
            success=success,
            response_ms=response_ms,
            error=error,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_memory_entries:
            self._entries = self._entries[-self._max_memory_entries:]

        level = logging.INFO if success else logging.ERROR
        logger.log(level, f"[{server}] {tool} | {'OK' if success else 'FAIL'} | {response_ms:.0f}ms")

        # Append to daily log file
        date_str = time.strftime("%Y-%m-%d")
        log_file = self._log_dir / f"audit_{date_str}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def _sanitize_params(self, params: dict) -> dict:
        """Remove sensitive values from parameters before logging (recursive)."""
        sensitive_keys = {"password", "token", "secret", "api_key", "key", "credential",
                          "auth", "authorization"}
        sanitized = {}
        for k, v in params.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_params(v)
            else:
                sanitized[k] = v
        return sanitized

    def get_recent(self, limit: int = 50, server: str = None) -> list[dict]:
        entries = self._entries
        if server:
            entries = [e for e in entries if e.server == server]
        return [e.to_dict() for e in entries[-limit:]]

    def get_stats(self) -> dict:
        if not self._entries:
            return {"total_calls": 0, "success_rate": 100, "avg_response_ms": 0}
        total = len(self._entries)
        successes = sum(1 for e in self._entries if e.success)
        avg_ms = sum(e.response_ms for e in self._entries) / total
        # Per-server breakdown
        by_server = {}
        for e in self._entries:
            if e.server not in by_server:
                by_server[e.server] = {"calls": 0, "failures": 0}
            by_server[e.server]["calls"] += 1
            if not e.success:
                by_server[e.server]["failures"] += 1
        return {
            "total_calls": total,
            "success_rate": round((successes / total) * 100, 2),
            "avg_response_ms": round(avg_ms, 2),
            "by_server": by_server,
        }
