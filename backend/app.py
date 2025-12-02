
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware

from .scanner import scan_apk, aggregate_by_severity

# Optional Telegram notifications
try:
    from .notifications import send_telegram_alert, format_scan_summary
except Exception:  # notifications.py not present - make no-op stubs
    def send_telegram_alert(*args, **kwargs):
        return None

    def format_scan_summary(scan: Dict[str, Any]) -> str:
        return ""


BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BACKEND_DIR / "reports"

UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
REPORTS_DIR.mkdir(exist_ok=True, parents=True)

# Optional dashboard API keys (comma-separated)
API_KEYS: List[str] = [
    k.strip() for k in os.getenv("DASHBOARD_API_KEYS", "").split(",") if k.strip()
]

app = FastAPI(title="RedHawk Android Hunter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # relax for local dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory scan registry
SCANS: Dict[str, Dict[str, Any]] = {}


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """If API_KEYS is configured, enforce it. Otherwise accept all."""
    if not API_KEYS:
        return
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/api/status")
def api_status() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "RedHawk Android Hunter API"}


@app.get("/api/scans")
def list_scans(x_api_key: Optional[str] = Header(None)) -> List[Dict[str, Any]]:
    require_api_key(x_api_key)
    scans = list(SCANS.values())
    scans.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return scans


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: str, x_api_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    scan = SCANS.get(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@app.get("/api/reports/{scan_id}/ai_report")
def get_ai_report(scan_id: str, x_api_key: Optional[str] = Header(None)) -> str:
    require_api_key(x_api_key)
    scan = SCANS.get(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    ai_file = scan.get("ai_report_file")
    report_file = scan.get("report_file")

    path: Optional[Path] = None
    if ai_file:
        candidate = REPORTS_DIR / ai_file
        if candidate.exists():
            path = candidate
    if path is None and report_file:
        candidate = REPORTS_DIR / report_file
        if candidate.exists():
            path = candidate

    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    return path.read_text(encoding="utf-8")


@app.post("/api/scan")
async def start_scan(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    app_id: str = Form(""),
    device_id: str = Form(""),
    platform: str = Form("hackerone"),
    ai: str = Form("true"),
    mode: str = Form("safe"),
    x_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Upload an APK and enqueue a scan."""
    require_api_key(x_api_key)

    if not file.filename.lower().endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are supported")

    scan_id = str(uuid.uuid4())
    apk_name = f"{scan_id}_{file.filename}"
    apk_path = UPLOAD_DIR / apk_name

    data = await file.read()
    apk_path.write_bytes(data)

    scan: Dict[str, Any] = {
        "id": scan_id,
        "apk_name": file.filename,
        "stored_apk": apk_name,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "app_id": app_id or "",
        "device_id": device_id or "",
        "platform": platform or "hackerone",
        "mode": mode or "safe",
        "total_findings": 0,
        "severity_counts": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        },
        "findings_file": None,
        "report_file": None,
        "ai_report_file": None,
        "screenshots_file": None,
        "error": None,
    }
    SCANS[scan_id] = scan

    background_tasks.add_task(
        run_scan_job,
        scan_id=scan_id,
        apk_path=str(apk_path),
        app_id=app_id,
        mode=mode,
        ai=(ai.lower() == "true"),
    )

    return {"id": scan_id, "status": "queued"}


def run_scan_job(scan_id: str, apk_path: str, app_id: str, mode: str, ai: bool) -> None:
    """Background worker that calls scanner and updates SCANS."""
    scan = SCANS.get(scan_id)
    if not scan:
        return

    scan["status"] = "running"
    SCANS[scan_id] = scan

    try:
        result = scan_apk(
            apk_path=apk_path,
            app_id=app_id or None,
            mode=mode or "safe",
            ai=ai,
        )

        findings: List[Dict[str, Any]] = result.get("findings", [])
        apk_name = result.get("apk_name", Path(apk_path).name)

        sev_counts = result.get("severity_counts")
        if not sev_counts:
            sev_counts = aggregate_by_severity(findings)

        total_findings = result.get("total_findings", len(findings))

        findings_file = result.get("findings_file") or f"{apk_name}.findings.json"
        report_file = result.get("report_file") or f"{apk_name}.report.md"
        ai_report_file = result.get("ai_report_file")
        screenshots_file = result.get("screenshots_file")

        scan.update(
            {
                "status": "completed",
                "apk_name": apk_name,
                "findings_file": findings_file,
                "report_file": report_file,
                "ai_report_file": ai_report_file,
                "screenshots_file": screenshots_file,
                "total_findings": total_findings,
                "severity_counts": sev_counts,
            }
        )
        SCANS[scan_id] = scan

        try:
            summary = format_scan_summary(scan)
            if summary:
                send_telegram_alert("✅ RedHawk Scan Completed", summary)
        except Exception:
            pass

    except Exception as e:
        scan["status"] = "error"
        scan["error"] = str(e)
        SCANS[scan_id] = scan

        try:
            send_telegram_alert(
                "❌ RedHawk Scan Failed",
                f"APK: `{scan.get('apk_name','unknown.apk')}`\nError: `{e}`",
            )
        except Exception:
            pass
