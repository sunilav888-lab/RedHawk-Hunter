
import os
import requests
from typing import Any, Dict

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_alert(title: str, message: str) -> None:
    """Send a simple Markdown Telegram alert. If not configured, no-op."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    text = f"*{title}*\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        # Never break scan on notification failure
        pass


def format_scan_summary(scan: Dict[str, Any]) -> str:
    sev = scan.get("severity_counts") or {}
    return (
        f"APK: `{scan.get('apk_name', 'unknown.apk')}`\n"
        f"Status: *{scan.get('status','?').upper()}*\n"
        f"Findings: {scan.get('total_findings', 0)}\n"
        f"Severity: "
        f"C:{sev.get('critical',0)} "
        f"H:{sev.get('high',0)} "
        f"M:{sev.get('medium',0)} "
        f"L:{sev.get('low',0)} "
        f"I:{sev.get('info',0)}"
    )
