"""Notification Hub — Multi-channel alert dispatcher (Email, Slack, WhatsApp, Webhook)."""
import json
import smtplib
import time
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from orchestrator.security import validate_url


class NotificationHub:
    """Sends notifications through multiple channels — Email, Slack, WhatsApp, Webhooks."""

    def __init__(self):
        self._history: list[dict] = []
        self._max_history = 1000

    async def dispatch(self, tool: str, params: dict) -> Any:
        methods = {
            "send_email": self.send_email,
            "send_slack": self.send_slack,
            "send_whatsapp": self.send_whatsapp,
            "send_webhook": self.send_webhook,
            "list_channels": self.list_channels,
        }
        if tool not in methods:
            raise ValueError(f"Unknown tool: {tool}")
        return await methods[tool](**params)

    async def send_email(self, to: str, subject: str, body: str,
                          html: bool = False, smtp_host: str = "",
                          smtp_port: int = 587, smtp_user: str = "",
                          smtp_pass: str = "") -> dict:
        """Send an email notification."""
        if not smtp_host:
            return {"status": "error",
                    "error": "SMTP not configured. Set smtp_host, smtp_user, smtp_pass.",
                    "demo_mode": True,
                    "message": f"Would send email to {to}: {subject}"}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            entry = {"channel": "email", "to": to, "subject": subject,
                     "status": "sent", "timestamp": time.time()}
            self._history.append(entry)
            return {"status": "sent", "channel": "email", "to": to, "subject": subject}
        except Exception as e:
            return {"status": "error", "channel": "email", "error": str(e)}

    async def send_slack(self, webhook_url: str, message: str,
                          channel: str = None, username: str = "MCPHub") -> dict:
        """Send a Slack notification via webhook."""
        if webhook_url:
            validate_url(webhook_url)
        if not webhook_url:
            return {"status": "error",
                    "error": "No Slack webhook URL provided.",
                    "demo_mode": True,
                    "message": f"Would send to Slack: {message[:100]}"}
        try:
            payload = {"text": message, "username": username}
            if channel:
                payload["channel"] = channel
            resp = requests.post(webhook_url, json=payload, timeout=10)
            success = resp.status_code == 200
            entry = {"channel": "slack", "status": "sent" if success else "failed",
                     "timestamp": time.time()}
            self._history.append(entry)
            return {"status": "sent" if success else "failed", "channel": "slack",
                    "http_status": resp.status_code}
        except Exception as e:
            return {"status": "error", "channel": "slack", "error": str(e)}

    async def send_whatsapp(self, phone: str, message: str, api_key: str = "") -> dict:
        """Send a WhatsApp message via WhatsApp Business API."""
        if not api_key:
            return {"status": "demo_mode",
                    "message": f"Would send WhatsApp to {phone}: {message[:100]}",
                    "note": "Configure WhatsApp Business API key for live messages."}
        try:
            # WhatsApp Business API (Meta Cloud API)
            resp = requests.post(
                "https://graph.facebook.com/v18.0/FROM_PHONE_ID/messages",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": message},
                },
                timeout=10,
            )
            entry = {"channel": "whatsapp", "to": phone, "status": "sent",
                     "timestamp": time.time()}
            self._history.append(entry)
            return {"status": "sent", "channel": "whatsapp", "to": phone,
                    "api_response": resp.status_code}
        except Exception as e:
            return {"status": "error", "channel": "whatsapp", "error": str(e)}

    async def send_webhook(self, url: str, payload: dict, method: str = "POST",
                            headers: dict = None) -> dict:
        """Send a custom webhook notification to any URL."""
        validate_url(url)
        try:
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            if method.upper() == "POST":
                resp = requests.post(url, json=payload, headers=req_headers, timeout=10)
            else:
                resp = requests.get(url, params=payload, headers=req_headers, timeout=10)

            entry = {"channel": "webhook", "url": url, "status": resp.status_code,
                     "timestamp": time.time()}
            self._history.append(entry)
            return {"status": "sent", "channel": "webhook", "url": url,
                    "http_status": resp.status_code, "response": resp.text[:500]}
        except Exception as e:
            return {"status": "error", "channel": "webhook", "error": str(e)}

    async def list_channels(self) -> dict:
        """List available notification channels and recent send history."""
        return {
            "channels": [
                {"name": "email", "type": "SMTP", "requires": "SMTP credentials"},
                {"name": "slack", "type": "Webhook", "requires": "Slack webhook URL"},
                {"name": "whatsapp", "type": "API", "requires": "WhatsApp Business API key"},
                {"name": "webhook", "type": "HTTP", "requires": "Any URL endpoint"},
            ],
            "recent_history": self._history[-20:],
            "total_sent": len(self._history),
        }
