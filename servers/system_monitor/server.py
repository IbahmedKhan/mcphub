"""System Monitor MCP Server — Infrastructure health monitoring via MCP."""
from fastmcp import FastMCP

from .monitor import SystemMonitor

mcp = FastMCP(
    "mcphub-system-monitor",
    description="Server and infrastructure health monitoring. Tracks CPU, memory, disk, "
                "network, and processes with health status alerts.",
)

monitor = SystemMonitor()


@mcp.tool()
async def get_system_info() -> dict:
    """Get comprehensive system information — OS, CPU, memory, uptime, boot time."""
    return await monitor.get_system_info()


@mcp.tool()
async def get_cpu_usage(per_core: bool = False) -> dict:
    """Get current CPU usage with health status assessment.

    Args:
        per_core: If True, returns usage per individual CPU core (default: False)
    """
    return await monitor.get_cpu_usage(per_core)


@mcp.tool()
async def get_memory_usage() -> dict:
    """Get RAM and swap memory usage with health alerts."""
    return await monitor.get_memory_usage()


@mcp.tool()
async def get_disk_usage() -> dict:
    """Get disk usage for all mounted partitions with capacity alerts."""
    return await monitor.get_disk_usage()


@mcp.tool()
async def list_processes(sort_by: str = "memory", limit: int = 20) -> dict:
    """List top processes sorted by resource usage.

    Args:
        sort_by: Sort criteria — 'memory' or 'cpu' (default: 'memory')
        limit: Number of processes to return (default: 20)
    """
    return await monitor.list_processes(sort_by, limit)


@mcp.tool()
async def get_network_stats() -> dict:
    """Get network interface statistics — bytes sent/received, active connections, errors."""
    return await monitor.get_network_stats()


if __name__ == "__main__":
    mcp.run()
