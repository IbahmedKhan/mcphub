"""Tests for System Monitor MCP Server."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from servers.system_monitor.monitor import SystemMonitor


@pytest.fixture
def monitor():
    return SystemMonitor()


class TestSystemInfo:
    @pytest.mark.asyncio
    async def test_returns_system_info(self, monitor):
        result = await monitor.get_system_info()
        assert "hostname" in result
        assert "os" in result
        assert "cpu" in result
        assert "memory" in result
        assert "uptime" in result
        assert result["cpu"]["logical_cores"] > 0
        assert result["memory"]["total_gb"] > 0


class TestCPU:
    @pytest.mark.asyncio
    async def test_cpu_usage(self, monitor):
        result = await monitor.get_cpu_usage()
        assert 0 <= result["overall_percent"] <= 100
        assert result["status"] in ("healthy", "warning", "critical")

    @pytest.mark.asyncio
    async def test_per_core(self, monitor):
        result = await monitor.get_cpu_usage(per_core=True)
        assert "per_core" in result
        assert len(result["per_core"]) > 0


class TestMemory:
    @pytest.mark.asyncio
    async def test_memory_usage(self, monitor):
        result = await monitor.get_memory_usage()
        assert result["ram"]["total_gb"] > 0
        assert 0 <= result["ram"]["used_percent"] <= 100
        assert result["status"] in ("healthy", "warning", "critical")


class TestDisk:
    @pytest.mark.asyncio
    async def test_disk_usage(self, monitor):
        result = await monitor.get_disk_usage()
        assert result["partition_count"] > 0
        assert result["partitions"][0]["total_gb"] > 0


class TestProcesses:
    @pytest.mark.asyncio
    async def test_list_processes(self, monitor):
        result = await monitor.list_processes("memory", 5)
        assert result["total_processes"] > 0
        assert len(result["processes"]) <= 5

    @pytest.mark.asyncio
    async def test_sort_by_cpu(self, monitor):
        result = await monitor.list_processes("cpu", 3)
        assert result["sort_by"] == "cpu"


class TestNetwork:
    @pytest.mark.asyncio
    async def test_network_stats(self, monitor):
        result = await monitor.get_network_stats()
        assert result["io_counters"]["bytes_sent"] >= 0
        assert result["io_counters"]["bytes_recv"] >= 0
        assert "interfaces" in result
