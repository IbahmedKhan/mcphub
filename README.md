# MCPHub — Enterprise AI Integration Framework

> Connect AI to your entire business infrastructure through a unified MCP server orchestrator.

MCPHub is a production-ready framework that lets AI assistants (Claude, GPT, etc.) interact with multiple business systems simultaneously through **Model Context Protocol (MCP)**.

## The Problem

Companies want AI that can **actually do things** — query databases, scan security, send alerts, monitor infrastructure. But connecting AI to real systems is hard, fragmented, and insecure.

## The Solution

MCPHub provides a **unified orchestration layer** with 6 built-in MCP servers, a central management dashboard, and a REST API gateway.

```
AI Assistant --> MCPHub Orchestrator --> Multiple MCP Servers --> Your Systems
```

One conversation with AI can now:
- Scan your website for vulnerabilities
- Query your database for affected users
- Generate an incident report
- Send alerts via WhatsApp, Email, and Slack
- Monitor your server infrastructure

All through natural language.

## Built-in MCP Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **Security Scanner** | 5 | Vulnerability detection, SSL analysis, port scanning, security headers, scoring |
| **Database Query** | 5 | Safe read-only SQL access with injection prevention and query validation |
| **Notification Hub** | 5 | Multi-channel alerts via Email (SMTP), Slack, WhatsApp, Webhooks |
| **Document Analyzer** | 5 | PDF extraction, CSV parsing with statistics, text analysis, table detection |
| **API Gateway** | 5 | Universal REST API connector with workflow chaining and auth management |
| **System Monitor** | 6 | CPU, memory, disk, network, process monitoring with health alerts |

**Total: 31 tools across 6 servers**

## Architecture

```
+-----------------------------------------------------------+
|                    MCPHub Framework                         |
|                                                            |
|  +------------------------------------------------------+  |
|  |              Orchestrator Layer                        |  |
|  |  [Auth]  [Router]  [Rate Limiter]  [SSRF Protection] |  |
|  |  [Audit Logger]  [Registry]  [Health Monitor]         |  |
|  +------------------------------------------------------+  |
|                          |                                  |
|  +----------+ +----------+ +----------+ +----------+       |
|  | Security | | Database | | Notif    | | Document |       |
|  | Scanner  | | Query    | | Hub      | | Analyzer |       |
|  |   MCP    | |   MCP    | |   MCP    | |   MCP    |       |
|  +----------+ +----------+ +----------+ +----------+       |
|  +----------+ +----------+                                  |
|  |   API    | | System   |                                  |
|  | Gateway  | | Monitor  |                                  |
|  |   MCP    | |   MCP    |                                  |
|  +----------+ +----------+                                  |
+-----------------------------------------------------------+
```

## Quick Start

### Installation

```bash
git clone https://github.com/IbahmedKhan/mcphub.git
cd mcphub
pip install -r requirements.txt
```

### Start the Dashboard

```bash
python -m uvicorn orchestrator.main:app --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000` — interactive dashboard with all 6 servers.

### Use Individual MCP Servers Standalone

Each server runs independently via MCP protocol:

```bash
# Security Scanner
python -m servers.security.server

# Database Query
python -m servers.database.server

# Notification Hub
python -m servers.notifications.server

# Document Analyzer
python -m servers.documents.server

# API Gateway
python -m servers.api_gateway.server

# System Monitor
python -m servers.system_monitor.server
```

### Use with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcphub-security": {
      "command": "python",
      "args": ["-m", "servers.security.server"],
      "cwd": "/path/to/mcphub"
    },
    "mcphub-database": {
      "command": "python",
      "args": ["-m", "servers.database.server"],
      "cwd": "/path/to/mcphub"
    },
    "mcphub-system": {
      "command": "python",
      "args": ["-m", "servers.system_monitor.server"],
      "cwd": "/path/to/mcphub"
    },
    "mcphub-notifications": {
      "command": "python",
      "args": ["-m", "servers.notifications.server"],
      "cwd": "/path/to/mcphub"
    },
    "mcphub-documents": {
      "command": "python",
      "args": ["-m", "servers.documents.server"],
      "cwd": "/path/to/mcphub"
    },
    "mcphub-api-gateway": {
      "command": "python",
      "args": ["-m", "servers.api_gateway.server"],
      "cwd": "/path/to/mcphub"
    }
  }
}
```

### REST API

All tools are also accessible via REST API:

```bash
# Scan a website
curl -X POST http://localhost:8000/api/servers/security-scanner/invoke/scan_website \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Get system info
curl -X POST http://localhost:8000/api/servers/system-monitor/invoke/get_system_info \
  -H "Content-Type: application/json" \
  -d '{}'

# Query a database
curl -X POST http://localhost:8000/api/servers/database-query/invoke/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users", "alias": "default"}'
```

## Example Workflows

### Security Incident Response
```
User: "Scan example.com, find all vulnerabilities,
       and email the report to the security team"

MCPHub:
  1. Security MCP -> scans example.com (ports, SSL, headers)
  2. Security MCP -> generates vulnerability report
  3. Notification MCP -> emails report to security@company.com
```

### Database-Powered Customer Support
```
User: "Find all orders from customer #1234 that
       haven't shipped yet and notify them via WhatsApp"

MCPHub:
  1. Database MCP -> queries orders table
  2. Database MCP -> filters unshipped orders
  3. Notification MCP -> sends WhatsApp update
```

### Multi-API Workflow
```
User: "Get the latest GitHub issues, check if our
       API is healthy, and post a summary to Slack"

MCPHub:
  1. API Gateway -> calls GitHub API
  2. API Gateway -> health checks internal API
  3. Notification MCP -> posts summary to Slack
```

## Security

MCPHub is built with security-first principles:

- **SSRF Protection** — blocks requests to internal/private IP ranges and cloud metadata endpoints
- **Path Traversal Prevention** — validates all file paths against allowed directories
- **SQL Injection Prevention** — database-level read-only enforcement (`PRAGMA query_only`) plus keyword filtering
- **API Authentication** — API key-based auth on all endpoints via `X-API-Key` header
- **XSS Prevention** — all dynamic content is HTML-escaped in the dashboard
- **CORS Protection** — restrictive cross-origin policy
- **Request Size Limits** — 1MB max request body
- **Audit Logging** — every tool invocation is logged with timestamps, parameters (sensitive values redacted), and response times
- **Input Validation** — port ranges, URL schemes, hostname formats all validated

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `MCPHUB_API_KEY` | For production | API key for authenticating requests |
| `SMTP_HOST` | For email | SMTP server hostname |
| `SMTP_USER` | For email | SMTP username |
| `SMTP_PASS` | For email | SMTP password |
| `SLACK_WEBHOOK_URL` | For Slack | Slack incoming webhook URL |
| `WHATSAPP_API_KEY` | For WhatsApp | Meta WhatsApp Business API key |
| `DATABASE_URL` | Optional | Database connection string (default: SQLite) |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, FastMCP
- **Protocol**: Model Context Protocol (MCP) with JSON-RPC 2.0
- **Database**: SQLAlchemy + SQLite (PostgreSQL-ready)
- **Scanning**: Scapy, pyOpenSSL, dnspython
- **Monitoring**: psutil
- **Dashboard**: HTML5, Vanilla JS
- **Security**: Custom SSRF/traversal/injection prevention layer

## Project Structure

```
mcphub/
├── orchestrator/
│   ├── main.py              # FastAPI app + dashboard
│   ├── registry.py          # Server registry + health tracking
│   ├── logger.py            # Audit logging with file output
│   └── security.py          # SSRF, path traversal, input validation
├── servers/
│   ├── security/
│   │   ├── scanner.py       # Port scan, SSL, headers, scoring engine
│   │   └── server.py        # MCP server (5 tools)
│   ├── database/
│   │   ├── engine.py        # Safe read-only SQL engine
│   │   └── server.py        # MCP server (5 tools)
│   ├── notifications/
│   │   ├── hub.py           # Email, Slack, WhatsApp, webhook sender
│   │   └── server.py        # MCP server (5 tools)
│   ├── documents/
│   │   ├── analyzer.py      # PDF, CSV, text analysis engine
│   │   └── server.py        # MCP server (5 tools)
│   ├── api_gateway/
│   │   ├── gateway.py       # Universal REST API connector
│   │   └── server.py        # MCP server (5 tools)
│   └── system_monitor/
│       ├── monitor.py       # CPU, memory, disk, network, processes
│       └── server.py        # MCP server (6 tools)
├── dashboard/
│   └── index.html           # Interactive web dashboard
├── test_all_servers.py      # Integration test for all 31 tools
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

## Load Test Results

Tested with 1000 concurrent API calls across all 6 servers:

| Metric | Value |
|--------|-------|
| Total Calls | 1,000 |
| Success Rate | 97.6% |
| Avg Response | 814ms |
| Servers | 6/6 running |
| Internal Success | 100% |

Failures were exclusively from external API timeouts (GitHub rate limits, network latency), not from MCPHub itself.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-server`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

**Ibrar Ahmed** — AI Integration & MCP Expert

- LinkedIn: [linkedin.com/in/ibahmedkhan1](https://linkedin.com/in/ibahmedkhan1)
- GitHub: [github.com/IbahmedKhan](https://github.com/IbahmedKhan)
