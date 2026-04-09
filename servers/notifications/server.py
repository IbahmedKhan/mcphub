"""Notification Hub MCP Server — Multi-channel alerts via MCP."""
from fastmcp import FastMCP

from .hub import NotificationHub

mcp = FastMCP(
    "mcphub-notification-hub",
    description="Multi-channel notification dispatcher. Send alerts via Email (SMTP), "
                "Slack (webhooks), WhatsApp (Business API), and custom webhooks.",
)

hub = NotificationHub()


@mcp.tool()
async def send_email(to: str, subject: str, body: str, html: bool = False) -> dict:
    """Send an email notification.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        html: If True, body is treated as HTML (default: False)
    """
    return await hub.send_email(to, subject, body, html)


@mcp.tool()
async def send_slack(webhook_url: str, message: str, channel: str = None) -> dict:
    """Send a Slack notification via webhook.

    Args:
        webhook_url: Slack incoming webhook URL
        message: Message text (supports Slack markdown)
        channel: Override channel (optional)
    """
    return await hub.send_slack(webhook_url, message, channel)


@mcp.tool()
async def send_whatsapp(phone: str, message: str) -> dict:
    """Send a WhatsApp message via WhatsApp Business API.

    Args:
        phone: Phone number with country code (e.g., '+923001234567')
        message: Message text
    """
    return await hub.send_whatsapp(phone, message)


@mcp.tool()
async def send_webhook(url: str, payload: dict, method: str = "POST") -> dict:
    """Send a custom webhook notification to any URL.

    Args:
        url: The webhook endpoint URL
        payload: JSON payload to send
        method: HTTP method — 'POST' or 'GET' (default: 'POST')
    """
    return await hub.send_webhook(url, payload, method)


@mcp.tool()
async def list_channels() -> dict:
    """List available notification channels and recent send history."""
    return await hub.list_channels()


if __name__ == "__main__":
    mcp.run()
