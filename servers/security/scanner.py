"""Security Scanner Engine — Port scanning, SSL analysis, header checks, scoring."""
import ssl
import socket
import asyncio
import time
import warnings
from typing import Any
from urllib.parse import urlparse

import requests
import urllib3

# Suppress InsecureRequestWarning for intentional unverified scans
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from orchestrator.security import validate_hostname, validate_url, validate_ports_list


class SecurityScanner:
    """Core security scanning engine used by both MCP server and REST API."""

    COMMON_PORTS = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
        3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
        6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
    }

    SECURITY_HEADERS = {
        "Strict-Transport-Security": {"severity": "high", "description": "HSTS prevents downgrade attacks and cookie hijacking"},
        "Content-Security-Policy": {"severity": "high", "description": "CSP prevents XSS and injection attacks"},
        "X-Content-Type-Options": {"severity": "medium", "description": "Prevents MIME type sniffing"},
        "X-Frame-Options": {"severity": "medium", "description": "Prevents clickjacking attacks"},
        "X-XSS-Protection": {"severity": "low", "description": "Legacy XSS filter (modern browsers use CSP)"},
        "Referrer-Policy": {"severity": "low", "description": "Controls referrer information leakage"},
        "Permissions-Policy": {"severity": "medium", "description": "Controls browser feature access"},
    }

    async def dispatch(self, tool: str, params: dict) -> Any:
        methods = {
            "scan_website": self.scan_website,
            "check_ssl": self.check_ssl,
            "check_headers": self.check_headers,
            "scan_ports": self.scan_ports,
            "get_security_score": self.get_security_score,
        }
        if tool not in methods:
            raise ValueError(f"Unknown tool: {tool}")
        return await methods[tool](**params)

    async def scan_website(self, url: str) -> dict:
        """Full security scan of a website."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        validate_url(url)
        parsed = urlparse(url)
        hostname = parsed.hostname
        validate_hostname(hostname)
        start = time.time()

        ssl_result = await self.check_ssl(hostname=hostname)
        headers_result = await self.check_headers(url=url)
        ports_result = await self.scan_ports(hostname=hostname)
        score_result = await self.get_security_score(
            url=url, ssl_data=ssl_result, headers_data=headers_result, ports_data=ports_result
        )

        elapsed = round(time.time() - start, 2)

        vulnerabilities = []
        # SSL vulnerabilities
        if not ssl_result.get("valid"):
            vulnerabilities.append({
                "severity": "critical",
                "category": "SSL/TLS",
                "title": "SSL Certificate Invalid",
                "description": ssl_result.get("error", "Certificate validation failed"),
                "fix": "Install a valid SSL certificate from Let's Encrypt (free) or your CA.",
            })
        if ssl_result.get("days_until_expiry") is not None and ssl_result["days_until_expiry"] < 30:
            vulnerabilities.append({
                "severity": "high",
                "category": "SSL/TLS",
                "title": f"SSL Certificate Expires in {ssl_result['days_until_expiry']} Days",
                "description": "Your SSL certificate is expiring soon.",
                "fix": "Renew your SSL certificate immediately.",
            })

        # Header vulnerabilities
        for header, info in self.SECURITY_HEADERS.items():
            if header not in headers_result.get("present", {}):
                vulnerabilities.append({
                    "severity": info["severity"],
                    "category": "Security Headers",
                    "title": f"Missing {header}",
                    "description": info["description"],
                    "fix": f"Add the {header} header to your server configuration.",
                })

        # Port vulnerabilities
        for port_info in ports_result.get("open_ports", []):
            port = port_info["port"]
            if port in (21, 23, 3389, 5900, 27017, 6379):
                vulnerabilities.append({
                    "severity": "critical" if port in (23, 27017, 6379) else "high",
                    "category": "Open Ports",
                    "title": f"Dangerous Port Open: {port} ({port_info['service']})",
                    "description": f"Port {port} ({port_info['service']}) is exposed to the internet.",
                    "fix": f"Close port {port} or restrict access via firewall.",
                })

        critical = sum(1 for v in vulnerabilities if v["severity"] == "critical")
        high = sum(1 for v in vulnerabilities if v["severity"] == "high")
        medium = sum(1 for v in vulnerabilities if v["severity"] == "medium")
        low = sum(1 for v in vulnerabilities if v["severity"] == "low")

        return {
            "url": url,
            "hostname": hostname,
            "scan_time_seconds": elapsed,
            "security_score": score_result["score"],
            "grade": score_result["grade"],
            "summary": score_result["summary"],
            "vulnerabilities": {
                "critical": critical, "high": high, "medium": medium, "low": low,
                "total": len(vulnerabilities),
                "details": vulnerabilities,
            },
            "ssl": ssl_result,
            "headers": headers_result,
            "ports": ports_result,
            "technology": headers_result.get("technology", {}),
        }

    async def check_ssl(self, hostname: str) -> dict:
        """Analyze SSL/TLS certificate of a host."""
        validate_hostname(hostname)
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    protocol = ssock.version()

            import datetime
            not_after = ssl.cert_time_to_seconds(cert["notAfter"])
            not_before = ssl.cert_time_to_seconds(cert["notBefore"])
            days_left = (not_after - time.time()) / 86400

            subject = dict(x[0] for x in cert.get("subject", []))
            issuer = dict(x[0] for x in cert.get("issuer", []))
            san = [entry[1] for entry in cert.get("subjectAltName", [])]

            return {
                "valid": True,
                "hostname": hostname,
                "subject": subject.get("commonName", ""),
                "issuer": issuer.get("organizationName", ""),
                "issuer_cn": issuer.get("commonName", ""),
                "not_before": time.strftime("%Y-%m-%d", time.localtime(not_before)),
                "not_after": time.strftime("%Y-%m-%d", time.localtime(not_after)),
                "days_until_expiry": round(days_left),
                "protocol": protocol,
                "cipher": cipher[0] if cipher else "",
                "cipher_bits": cipher[2] if cipher else 0,
                "san": san[:10],
            }
        except Exception as e:
            return {"valid": False, "hostname": hostname, "error": str(e)}

    async def check_headers(self, url: str) -> dict:
        """Check HTTP security headers and detect technology."""
        validate_url(url)
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True,
                                headers={"User-Agent": "MCPHub Security Scanner/1.0"},
                                verify=False)
            headers = dict(resp.headers)
            present = {}
            missing = []

            for header, info in self.SECURITY_HEADERS.items():
                if header.lower() in {k.lower(): k for k in headers}:
                    actual_key = next(k for k in headers if k.lower() == header.lower())
                    present[header] = headers[actual_key]
                else:
                    missing.append({"header": header, "severity": info["severity"],
                                    "description": info["description"]})

            # Technology detection
            server = headers.get("Server", headers.get("server", ""))
            powered_by = headers.get("X-Powered-By", headers.get("x-powered-by", ""))
            technology = {"server": server, "powered_by": powered_by}

            if "wp-" in resp.text[:5000].lower() or "wordpress" in resp.text[:5000].lower():
                technology["cms"] = "WordPress"
            elif "joomla" in resp.text[:5000].lower():
                technology["cms"] = "Joomla"
            elif "drupal" in resp.text[:5000].lower():
                technology["cms"] = "Drupal"

            return {
                "url": url,
                "status_code": resp.status_code,
                "present": present,
                "missing": missing,
                "total_headers": len(headers),
                "security_headers_found": len(present),
                "security_headers_missing": len(missing),
                "technology": technology,
                "cookies_secure": all(
                    "secure" in str(c).lower() for c in resp.cookies
                ) if resp.cookies else True,
            }
        except Exception as e:
            return {"url": url, "error": str(e)}

    async def scan_ports(self, hostname: str, ports: list = None) -> dict:
        """Scan common ports on a host."""
        validate_hostname(hostname)
        if ports:
            ports = validate_ports_list(ports, max_count=100)
        target_ports = ports or list(self.COMMON_PORTS.keys())
        open_ports = []
        closed_ports = []

        async def check_port(port):
            try:
                loop = asyncio.get_event_loop()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = await loop.run_in_executor(None, lambda: sock.connect_ex((hostname, port)))
                sock.close()
                if result == 0:
                    open_ports.append({
                        "port": port,
                        "service": self.COMMON_PORTS.get(port, "unknown"),
                        "state": "open",
                    })
                else:
                    closed_ports.append(port)
            except Exception:
                closed_ports.append(port)

        await asyncio.gather(*[check_port(p) for p in target_ports])
        open_ports.sort(key=lambda x: x["port"])

        return {
            "hostname": hostname,
            "ports_scanned": len(target_ports),
            "open_ports": open_ports,
            "open_count": len(open_ports),
            "closed_count": len(closed_ports),
        }

    async def get_security_score(self, url: str = None, ssl_data: dict = None,
                                  headers_data: dict = None, ports_data: dict = None) -> dict:
        """Calculate overall security score (0-100)."""
        score = 100
        issues = []

        # SSL scoring (30 points max deduction)
        if ssl_data:
            if not ssl_data.get("valid"):
                score -= 30
                issues.append("No valid SSL certificate (-30)")
            elif ssl_data.get("days_until_expiry", 999) < 7:
                score -= 15
                issues.append("SSL expires within 7 days (-15)")
            elif ssl_data.get("days_until_expiry", 999) < 30:
                score -= 8
                issues.append("SSL expires within 30 days (-8)")
            if ssl_data.get("protocol") in ("TLSv1", "TLSv1.1"):
                score -= 10
                issues.append(f"Outdated TLS protocol: {ssl_data['protocol']} (-10)")

        # Headers scoring (35 points max deduction)
        if headers_data:
            for missing in headers_data.get("missing", []):
                if missing["severity"] == "high":
                    score -= 8
                elif missing["severity"] == "medium":
                    score -= 5
                else:
                    score -= 2
                issues.append(f"Missing {missing['header']} (-{'8' if missing['severity']=='high' else '5' if missing['severity']=='medium' else '2'})")

        # Ports scoring (35 points max deduction)
        if ports_data:
            for port_info in ports_data.get("open_ports", []):
                port = port_info["port"]
                if port in (23, 27017, 6379):
                    score -= 15
                    issues.append(f"Critical port {port} open (-15)")
                elif port in (21, 3389, 5900):
                    score -= 8
                    issues.append(f"Risky port {port} open (-8)")
                elif port not in (80, 443, 22):
                    score -= 3
                    issues.append(f"Unnecessary port {port} open (-3)")

        score = max(0, min(100, score))
        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"

        summary = f"Security score: {score}/100 (Grade {grade}). "
        if score >= 90:
            summary += "Excellent security posture."
        elif score >= 75:
            summary += "Good security with minor improvements needed."
        elif score >= 60:
            summary += "Fair security. Several issues should be addressed."
        elif score >= 40:
            summary += "Poor security. Critical issues need immediate attention."
        else:
            summary += "Critical security failures detected. Immediate action required."

        return {"score": score, "grade": grade, "summary": summary,
                "issues": issues, "max_score": 100}
