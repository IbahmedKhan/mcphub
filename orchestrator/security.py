"""MCPHub Security Utilities — Shared validation, sanitization, and protection."""
import ipaddress
import socket
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# --- API Key Authentication ---

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: Optional[str] = Security(api_key_header)) -> str:
    """Verify API key from X-API-Key header."""
    import os
    expected = os.getenv("MCPHUB_API_KEY", "")
    if not expected:
        # No API key configured — allow access (dev mode)
        return "dev-mode"
    if not key or key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


# --- SSRF Protection ---

BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


def validate_url(url: str, allow_internal: bool = False) -> str:
    """Validate a URL is safe to request — blocks SSRF attacks against internal networks.

    Args:
        url: The URL to validate
        allow_internal: If True, skip private IP checks (for local scanning tools)

    Returns:
        The validated URL

    Raises:
        ValueError: If the URL is unsafe
    """
    parsed = urlparse(url)

    # Block non-HTTP schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked: scheme '{parsed.scheme}' not allowed. Use http or https.")

    if not parsed.hostname:
        raise ValueError("Blocked: no hostname in URL")

    if allow_internal:
        return url

    # Check if hostname is a direct IP
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        _check_ip_blocked(ip, parsed.hostname)
    except ValueError:
        pass  # Not an IP — it's a hostname, resolve it below

    # Resolve hostname and check all IPs
    try:
        resolved = socket.getaddrinfo(parsed.hostname, None, socket.AF_UNSPEC)
        for _, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            _check_ip_blocked(ip, parsed.hostname)
    except socket.gaierror:
        raise ValueError(f"Blocked: cannot resolve hostname '{parsed.hostname}'")

    return url


def _check_ip_blocked(ip: ipaddress._BaseAddress, hostname: str):
    """Check if an IP address falls within blocked ranges."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise ValueError(f"Blocked: '{hostname}' resolves to internal/private address")
    for network in BLOCKED_IP_RANGES:
        if ip in network:
            raise ValueError(f"Blocked: '{hostname}' resolves to restricted network range")


def validate_hostname(hostname: str, allow_internal: bool = False) -> str:
    """Validate a hostname is safe to connect to.

    Args:
        hostname: The hostname to validate
        allow_internal: If True, allow private/internal IPs

    Returns:
        The validated hostname
    """
    if not hostname or not isinstance(hostname, str):
        raise ValueError("Invalid hostname")

    # Basic format check
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$', hostname):
        # Could be an IP
        try:
            ip = ipaddress.ip_address(hostname)
            if not allow_internal:
                _check_ip_blocked(ip, hostname)
            return hostname
        except ValueError:
            raise ValueError(f"Invalid hostname format: '{hostname}'")

    if not allow_internal:
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            for _, _, _, _, sockaddr in resolved:
                ip = ipaddress.ip_address(sockaddr[0])
                _check_ip_blocked(ip, hostname)
        except socket.gaierror:
            raise ValueError(f"Cannot resolve hostname: '{hostname}'")

    return hostname


# --- Path Traversal Protection ---

ALLOWED_DOCUMENT_DIRS: list[Path] = []


def set_allowed_document_dirs(dirs: list[str]):
    """Configure allowed directories for document access."""
    global ALLOWED_DOCUMENT_DIRS
    ALLOWED_DOCUMENT_DIRS = [Path(d).resolve() for d in dirs]


def validate_file_path(file_path: str) -> Path:
    """Validate a file path is within allowed directories — prevents path traversal.

    Args:
        file_path: The file path to validate

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is outside allowed directories or contains traversal
    """
    path = Path(file_path).resolve()

    # Block obvious traversal patterns
    if ".." in str(file_path):
        raise ValueError("Path traversal detected: '..' not allowed")

    # If allowed dirs are configured, enforce them
    if ALLOWED_DOCUMENT_DIRS:
        if not any(path.is_relative_to(allowed) for allowed in ALLOWED_DOCUMENT_DIRS):
            raise ValueError(
                f"Access denied: path outside allowed directories. "
                f"Allowed: {[str(d) for d in ALLOWED_DOCUMENT_DIRS]}"
            )

    # Block sensitive system paths
    sensitive_patterns = [
        "/etc/shadow", "/etc/passwd", "\\system32\\config",
        ".env", ".git/config", "id_rsa", ".ssh/",
    ]
    path_lower = str(path).lower().replace("\\", "/")
    for pattern in sensitive_patterns:
        if pattern.lower() in path_lower:
            raise ValueError(f"Access denied: sensitive system path")

    return path


# --- Input Sanitization ---

def sanitize_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


def validate_port(port: int) -> int:
    """Validate a port number is within valid range."""
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError(f"Invalid port: {port}. Must be between 1 and 65535.")
    return port


def validate_ports_list(ports: list[int], max_count: int = 100) -> list[int]:
    """Validate and deduplicate a list of ports."""
    if not ports:
        return ports
    validated = list(set(ports))[:max_count]
    for p in validated:
        validate_port(p)
    return sorted(validated)


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp an integer to a range."""
    return max(minimum, min(maximum, value))
