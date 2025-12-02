
import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .ai_reporter import ai_generate_report

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def run_mobsfscan(apk_path: str) -> List[Dict[str, Any]]:
    """Run mobsfscan and return findings list (best-effort)."""
    try:
        result = subprocess.run(
            ["mobsfscan", "-o", "-", apk_path],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if not output:
            return []

        try:
            data = json.loads(output)
            findings = data.get("findings", [])
            return findings
        except json.JSONDecodeError:
            print("[scanner] mobsfscan output not JSON, skipping detailed parse.")
            return []
    except Exception as e:
        print("[scanner] mobsfscan failed:", e)
        return []


def aggregate_by_severity(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    severities = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for item in findings:
        sev = str(item.get("severity", "info")).lower()
        if sev not in severities:
            sev = "info"
        severities[sev] += 1
    return severities


def build_basic_report(apk_name: str, findings: List[Dict[str, Any]], sev_counts: Dict[str, int]) -> str:
    lines: List[str] = []
    lines.append(f"# {apk_name} – Android Security Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    total = sum(sev_counts.values())
    lines.append(f"- Total issues: **{total}**")
    lines.append(f"- Critical: {sev_counts['critical']}")
    lines.append(f"- High: {sev_counts['high']}")
    lines.append(f"- Medium: {sev_counts['medium']}")
    lines.append(f"- Low: {sev_counts['low']}")
    lines.append(f"- Info: {sev_counts['info']}")
    lines.append("")

    if not findings:
        lines.append("_No findings were reported by the static scanner. This does not guarantee the app is secure._")
        return "\n".join(lines)

    lines.append("## Findings")
    lines.append("")
    for f in findings:
        sev = str(f.get("severity", "info")).title()
        desc = f.get("description", "No description")
        tool = f.get("tool", "mobsfscan")
        lines.append(f"### {sev} – {desc}")
        lines.append("")
        lines.append(f"- Tool: `{tool}`")
        lines.append("")
    return "\n".join(lines)


def scan_apk(apk_path: str, app_id: str = None, mode: str = "safe", ai: bool = False) -> Dict[str, Any]:
    apk_path_obj = Path(apk_path)
    apk_name = apk_path_obj.name

    print(f"[+] Scanning {apk_name}")

    findings: List[Dict[str, Any]] = []

    # Static analysis via mobsfscan (simple, robust base)
    findings.extend(run_mobsfscan(str(apk_path_obj)))

    # Save findings JSON
    findings_file = REPORTS_DIR / f"{apk_name}.findings.json"
    findings_file.write_text(json.dumps(findings, indent=2))

    severity_counts = aggregate_by_severity(findings)
    total_findings = len(findings)

    # Base Markdown report (non-AI)
    report_file = REPORTS_DIR / f"{apk_name}.report.md"
    report_file.write_text(build_basic_report(apk_name, findings, severity_counts))

    ai_report_file = None
    if ai:
        try:
            print("[scanner] Generating AI bug bounty report via OpenRouter...")
            report_md = ai_generate_report(apk_name, findings)
            ai_report_file = REPORTS_DIR / f"{apk_name}.ai_report.md"
            ai_report_file.write_text(report_md)
        except Exception as e:
            print("[scanner] AI report failed:", e)

    print("[+] Scan complete")

    return {
        "apk_name": apk_name,
        "findings": findings,
        "severity_counts": severity_counts,
        "total_findings": total_findings,
        "findings_file": findings_file.name,
        "report_file": report_file.name,
        "ai_report_file": ai_report_file.name if ai_report_file else None,
        "screenshots_file": None,
    }


def main():
    parser = argparse.ArgumentParser(description="Scan an APK file with RedHawk.")
    parser.add_argument("apk_path", help="Path to APK file")
    parser.add_argument("--ai", action="store_true", help="Enable AI bug bounty report")
    args = parser.parse_args()
    scan_apk(args.apk_path, ai=args.ai)


if __name__ == "__main__":
    main()
