"""System Monitor — Server health, CPU, memory, disk, network, and process monitoring."""
import platform
import time
from typing import Any

import psutil


class SystemMonitor:
    """Monitors system health — CPU, memory, disk, network, and processes."""

    async def dispatch(self, tool: str, params: dict) -> Any:
        methods = {
            "get_system_info": self.get_system_info,
            "get_cpu_usage": self.get_cpu_usage,
            "get_memory_usage": self.get_memory_usage,
            "get_disk_usage": self.get_disk_usage,
            "list_processes": self.list_processes,
            "get_network_stats": self.get_network_stats,
        }
        if tool not in methods:
            raise ValueError(f"Unknown tool: {tool}")
        return await methods[tool](**params)

    async def get_system_info(self) -> dict:
        """Get comprehensive system information."""
        uname = platform.uname()
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "hostname": uname.node,
            "os": f"{uname.system} {uname.release}",
            "os_version": uname.version,
            "architecture": uname.machine,
            "processor": uname.processor or platform.processor(),
            "python_version": platform.python_version(),
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "frequency_mhz": round(cpu_freq.current, 2) if cpu_freq else None,
                "usage_percent": psutil.cpu_percent(interval=1),
            },
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_percent": mem.percent,
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_percent": swap.percent,
            },
            "uptime": {
                "seconds": round(uptime_seconds),
                "hours": round(uptime_seconds / 3600, 1),
                "days": round(uptime_seconds / 86400, 1),
            },
            "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time)),
        }

    async def get_cpu_usage(self, per_core: bool = False) -> dict:
        """Get current CPU usage statistics."""
        overall = psutil.cpu_percent(interval=1)
        result = {
            "overall_percent": overall,
            "load_average": None,
            "core_count": psutil.cpu_count(logical=True),
        }

        try:
            result["load_average"] = [round(x, 2) for x in psutil.getloadavg()]
        except (AttributeError, OSError):
            pass

        if per_core:
            per_cpu = psutil.cpu_percent(interval=1, percpu=True)
            result["per_core"] = [{"core": i, "percent": p} for i, p in enumerate(per_cpu)]

        # Status assessment
        if overall > 90:
            result["status"] = "critical"
            result["alert"] = f"CPU usage is critically high at {overall}%"
        elif overall > 70:
            result["status"] = "warning"
            result["alert"] = f"CPU usage is elevated at {overall}%"
        else:
            result["status"] = "healthy"

        return result

    async def get_memory_usage(self) -> dict:
        """Get memory and swap usage statistics."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        result = {
            "ram": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "used_percent": mem.percent,
                "cached_gb": round(getattr(mem, 'cached', 0) / (1024**3), 2),
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "used_percent": swap.percent,
            },
        }

        if mem.percent > 90:
            result["status"] = "critical"
            result["alert"] = f"Memory usage critically high at {mem.percent}%"
        elif mem.percent > 75:
            result["status"] = "warning"
            result["alert"] = f"Memory usage elevated at {mem.percent}%"
        else:
            result["status"] = "healthy"

        return result

    async def get_disk_usage(self) -> dict:
        """Get disk usage for all mounted partitions."""
        partitions = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "filesystem": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "used_percent": round(usage.percent, 1),
                })
            except (PermissionError, OSError):
                continue

        alerts = []
        for p in partitions:
            if p["used_percent"] > 90:
                alerts.append(f"Critical: {p['mountpoint']} is {p['used_percent']}% full")
            elif p["used_percent"] > 80:
                alerts.append(f"Warning: {p['mountpoint']} is {p['used_percent']}% full")

        return {
            "partitions": partitions,
            "partition_count": len(partitions),
            "alerts": alerts,
            "status": "critical" if any(p["used_percent"] > 90 for p in partitions) else
                      "warning" if any(p["used_percent"] > 80 for p in partitions) else "healthy",
        }

    async def list_processes(self, sort_by: str = "memory", limit: int = 20) -> dict:
        """List top processes sorted by CPU or memory usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent',
                                          'status', 'create_time', 'username']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": round(info.get('cpu_percent', 0) or 0, 1),
                    "memory_percent": round(info.get('memory_percent', 0) or 0, 1),
                    "status": info.get('status', ''),
                    "user": info.get('username', ''),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if sort_by == "cpu":
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        else:
            processes.sort(key=lambda x: x["memory_percent"], reverse=True)

        return {
            "processes": processes[:limit],
            "total_processes": len(processes),
            "sort_by": sort_by,
        }

    async def get_network_stats(self) -> dict:
        """Get network interface statistics and active connections."""
        net_io = psutil.net_io_counters()
        interfaces = {}
        for name, addrs in psutil.net_if_addrs().items():
            ips = []
            for addr in addrs:
                if addr.family.name == "AF_INET":
                    ips.append(addr.address)
            if ips:
                interfaces[name] = {"ipv4": ips}

        # Connection summary
        connections = psutil.net_connections(kind='inet')
        conn_summary = {"ESTABLISHED": 0, "LISTEN": 0, "TIME_WAIT": 0, "OTHER": 0}
        for conn in connections:
            status = conn.status
            if status in conn_summary:
                conn_summary[status] += 1
            else:
                conn_summary["OTHER"] += 1

        return {
            "io_counters": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errors_in": net_io.errin,
                "errors_out": net_io.errout,
            },
            "interfaces": interfaces,
            "connections": conn_summary,
            "total_connections": sum(conn_summary.values()),
        }
