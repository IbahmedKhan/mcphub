"""Security Scanner MCP Server — Exposes security scanning tools via MCP protocol."""
from fastmcp import FastMCP

from .scanner import SecurityScanner

mcp = FastMCP(
    "mcphub-security-scanner",
    description="Website security vulnerability scanner — port scanning, SSL analysis, "
                "security headers check, technology detection, and security scoring.",
)

scanner = SecurityScanner()


@mcp.tool()
async def scan_website(url: str) -> dict:
    """Perform a full security scan on a website. Returns security score, vulnerabilities,
    SSL status, security headers, open ports, and technology detection.

    Args:
        url: The website URL to scan (e.g., 'example.com' or 'https://example.com')
    """
    return await scanner.scan_website(url)


@mcp.tool()
async def check_ssl(hostname: str) -> dict:
    """Check SSL/TLS certificate details for a hostname. Returns validity, expiry date,
    issuer, protocol version, cipher strength, and Subject Alternative Names.

    Args:
        hostname: The hostname to check (e.g., 'example.com')
    """
    return await scanner.check_ssl(hostname)


@mcp.tool()
async def check_headers(url: str) -> dict:
    """Analyze HTTP security headers of a website. Checks for HSTS, CSP, X-Frame-Options,
    X-Content-Type-Options, and other security headers. Also detects server technology.

    Args:
        url: The full URL to check (e.g., 'https://example.com')
    """
    return await scanner.check_headers(url)


@mcp.tool()
async def scan_ports(hostname: str, ports: list[int] = None) -> dict:
    """Scan for open ports on a hostname. Checks common service ports (HTTP, SSH, FTP,
    database ports, etc.) and identifies potentially dangerous exposed services.

    Args:
        hostname: The hostname or IP to scan
        ports: Optional list of specific ports to scan. Defaults to top 22 common ports.
    """
    return await scanner.scan_ports(hostname, ports)


@mcp.tool()
async def get_security_score(url: str) -> dict:
    """Get a quick security score (0-100) and grade (A-F) for a website.
    Performs SSL, header, and port checks to calculate the score.

    Args:
        url: The website URL to score
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    from urllib.parse import urlparse
    hostname = urlparse(url).hostname
    ssl_data = await scanner.check_ssl(hostname)
    headers_data = await scanner.check_headers(url)
    ports_data = await scanner.scan_ports(hostname)
    return await scanner.get_security_score(url, ssl_data, headers_data, ports_data)


if __name__ == "__main__":
    mcp.run()
