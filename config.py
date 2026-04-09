"""MCPHub Configuration"""
import os
from dataclasses import dataclass, field


@dataclass
class OrchestratorConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    secret_key: str = ""  # Must be set via MCPHUB_SECRET_KEY env var in production
    log_level: str = "INFO"
    max_concurrent_scans: int = 10
    rate_limit_per_minute: int = 60


@dataclass
class DatabaseConfig:
    url: str = "sqlite:///mcphub.db"
    echo: bool = False


@dataclass
class SecurityScannerConfig:
    timeout: int = 30
    max_ports: int = 100
    user_agent: str = "MCPHub Security Scanner/1.0"


@dataclass
class NotificationConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    slack_webhook: str = ""
    whatsapp_api_key: str = ""


@dataclass
class MCPHubConfig:
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityScannerConfig = field(default_factory=SecurityScannerConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    anthropic_api_key: str = ""

    @classmethod
    def from_env(cls) -> "MCPHubConfig":
        config = cls()
        config.orchestrator.host = os.getenv("MCPHUB_HOST", "0.0.0.0")
        config.orchestrator.port = int(os.getenv("MCPHUB_PORT", "8000"))
        config.orchestrator.secret_key = os.getenv("MCPHUB_SECRET_KEY", config.orchestrator.secret_key)
        config.database.url = os.getenv("DATABASE_URL", config.database.url)
        config.security.timeout = int(os.getenv("SCAN_TIMEOUT", "30"))
        config.notifications.smtp_host = os.getenv("SMTP_HOST", "")
        config.notifications.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        config.notifications.smtp_user = os.getenv("SMTP_USER", "")
        config.notifications.smtp_pass = os.getenv("SMTP_PASS", "")
        config.notifications.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        config.notifications.whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "")
        config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        return config
