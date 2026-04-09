"""Tests for Security Scanner MCP Server."""
import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from servers.security.scanner import SecurityScanner
from orchestrator.security import validate_url, validate_hostname, validate_ports_list


@pytest.fixture
def scanner():
    return SecurityScanner()


class TestSSRFProtection:
    def test_blocks_localhost(self):
        with pytest.raises(ValueError, match="internal"):
            validate_url("http://127.0.0.1/admin")

    def test_blocks_private_ip(self):
        with pytest.raises(ValueError, match="internal"):
            validate_url("http://192.168.1.1")

    def test_blocks_cloud_metadata(self):
        with pytest.raises(ValueError, match="internal"):
            validate_url("http://169.254.169.254/metadata")

    def test_blocks_file_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("file:///etc/passwd")

    def test_blocks_ftp_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("ftp://evil.com/file")

    def test_allows_public_url(self):
        result = validate_url("https://google.com")
        assert result == "https://google.com"

    def test_blocks_empty_hostname(self):
        with pytest.raises(ValueError):
            validate_url("http://")


class TestPortValidation:
    def test_valid_ports(self):
        result = validate_ports_list([80, 443, 22])
        assert result == [22, 80, 443]

    def test_deduplicates(self):
        result = validate_ports_list([80, 80, 80, 443])
        assert result == [80, 443]

    def test_caps_at_max(self):
        result = validate_ports_list(list(range(1, 200)), max_count=5)
        assert len(result) == 5

    def test_rejects_invalid_port(self):
        with pytest.raises(ValueError, match="Invalid port"):
            validate_ports_list([99999])

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="Invalid port"):
            validate_ports_list([0])

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="Invalid port"):
            validate_ports_list([-1])


class TestSSLChecker:
    @pytest.mark.asyncio
    async def test_valid_ssl(self, scanner):
        result = await scanner.check_ssl("google.com")
        assert result["valid"] is True
        assert result["issuer"] != ""
        assert result["days_until_expiry"] > 0
        assert result["protocol"].startswith("TLS")

    @pytest.mark.asyncio
    async def test_invalid_hostname(self, scanner):
        result = await scanner.check_ssl("this-does-not-exist-12345.com")
        assert result["valid"] is False


class TestHeaderChecker:
    @pytest.mark.asyncio
    async def test_check_headers(self, scanner):
        result = await scanner.check_headers("https://google.com")
        assert "present" in result
        assert "missing" in result
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_detects_missing_headers(self, scanner):
        result = await scanner.check_headers("https://httpbin.org/get")
        assert len(result["missing"]) > 0


class TestSecurityScore:
    @pytest.mark.asyncio
    async def test_score_range(self, scanner):
        result = await scanner.get_security_score("https://google.com")
        assert 0 <= result["score"] <= 100
        assert result["grade"] in ("A", "B", "C", "D", "F")

    @pytest.mark.asyncio
    async def test_good_site_scores_high(self, scanner):
        result = await scanner.get_security_score("https://google.com")
        assert result["score"] >= 60
