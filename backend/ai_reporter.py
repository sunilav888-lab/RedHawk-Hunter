
"""
AI report generator for RedHawk Android Hunter.

Uses OpenRouter (OpenAI-compatible) Chat Completions API
to generate Bugcrowd / HackerOne style Markdown reports.

Environment:
  OPENROUTER_API_KEY   - your OpenRouter key (sk-or-v1-...)
  (fallback) OPENAI_API_KEY - if you want to reuse your OpenAI-style env var
"""

import os
from typing import Any, Dict, List

from openai import OpenAI

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")


def _get_client() -> OpenAI:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY (or OPENAI_API_KEY) is not set")

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    return client


def build_ai_prompt(app_name: str, findings: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("You are a senior Android application security researcher.")
    lines.append(
        f"Generate a complete HackerOne/Bugcrowd-style vulnerability report for "
        f"the Android APK: `{app_name}`."
    )
    lines.append("")
    lines.append("Normalized findings from scanners:")
    if not findings:
        lines.append("- No explicit static tool findings. Provide a generic risk assessment template.")
    else:
        for f in findings:
            title = f.get("title") or f.get("description") or "Unnamed issue"
            sev = f.get("severity", "info")
            tool = f.get("tool", "mobsfscan")
            lines.append(f"- [{sev}] {title} (tool: {tool})")

    lines.append(
        "\nWrite the report in Markdown with these sections:\n"
        "## Executive Summary\n"
        "- High-level overview of the app's security posture.\n"
        "\n"
        "## Findings Overview\n"
        "- Table-like summary grouped by severity.\n"
        "\n"
        "## Detailed Findings\n"
        "For each vulnerability, include:\n"
        "- Title\n"
        "- Severity\n"
        "- Affected components / permissions / endpoints\n"
        "- Description\n"
        "- Risk / Impact\n"
        "- Steps to Reproduce\n"
        "- Recommendations / Remediation\n"
        "\n"
        "## Conclusion\n"
        "- Overall risk and recommended next steps.\n"
    )
    return "\n".join(lines)


def ai_generate_report(app_name: str, findings: List[Dict[str, Any]]) -> str:
    """Call OpenRouter to produce a Markdown bug bounty report."""
    client = _get_client()
    prompt = build_ai_prompt(app_name, findings)

    resp = client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional Android penetration tester. "
                    "Generate clear, concise, well-structured vulnerability reports."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
    )
    return resp.choices[0].message.content
