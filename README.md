# 🦅 RedHawk Android Hunter

**AI-powered Android APK vulnerability scanner with web dashboard and OpenRouter integration.**

RedHawk Android Hunter analyzes Android APK files using static analysis (MobSFScan) and generates professional Bugcrowd / HackerOne style Markdown reports using AI (via OpenRouter).

> For **legal security testing only**: your own apps or explicitly authorized bug bounty scopes.

---

## ✨ Features

- 🔍 Static APK scanning with **MobSFScan**
- 🤖 AI-generated bug bounty reports via **OpenRouter** (`openai/gpt-4.1-mini`)
- 🌐 Web dashboard (upload, start scan, view history, read reports)
- 🧾 Markdown reports stored on disk (ready to paste into Bugcrowd/HackerOne)
- 📡 Optional Telegram alerts when scans finish
- 🧪 REST API for CI/CD pipelines
- 🐚 CLI scanner for quick local usage

---

## 🧱 Requirements

Tested on:

- Kali Linux 2024+
- Ubuntu 22.04+

System packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl xdg-utils
```

Python tools (installed via `requirements.txt`):

- fastapi
- uvicorn
- python-multipart
- mobsfscan
- openai (used with OpenRouter)
- requests

---

## 📦 Installation (Dev mode in your home dir)

```bash
cd ~/Downloads
unzip RedHawk-Android-Hunter.zip
cd RedHawk-Android-Hunter

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

mkdir -p uploads backend/reports
```

---

## 📂 Recommended System Install Path: `/opt`

For a system-wide install that works with `systemd` auto-start:

```bash
cd ~/Downloads
unzip RedHawk-Android-Hunter.zip

sudo mkdir -p /opt
sudo cp -r RedHawk-Android-Hunter /opt/
sudo chown -R kali:kali /opt/RedHawk-Android-Hunter

cd /opt/RedHawk-Android-Hunter
```

If your username is not `kali`, replace it with your actual username.

Then you can run:

```bash
cd /opt/RedHawk-Android-Hunter
./start.sh
```

---

## 🔑 Configure OpenRouter (AI)

RedHawk uses **OpenRouter** (https://openrouter.ai) to talk to models like `openai/gpt-4.1-mini`.

1. Create an account at OpenRouter.
2. Get an API key (looks like `sk-or-v1-...`).
3. Export it in your shell config:

```bash
echo 'export OPENROUTER_API_KEY="sk-or-v1-...YOUR_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

Verify it:

```bash
echo $OPENROUTER_API_KEY
```

If not set, AI report generation will fail and only the basic report will be created.

---

## (Optional) Telegram Notifications

If you want scan-complete alerts via Telegram:

1. Talk to `@BotFather` → `/newbot` → get BOT token
2. Send a message to your new bot
3. Get your chat ID (via `getUpdates` or any bot inspector)

Then set:

```bash
echo 'export TELEGRAM_BOT_TOKEN="123456:ABC-Your-Bot-Token"' >> ~/.bashrc
echo 'export TELEGRAM_CHAT_ID="123456789"' >> ~/.bashrc
source ~/.bashrc
```

If unset, notifications are simply skipped.

---

## ▶️ Running the Backend

From project root:

```bash
cd /opt/RedHawk-Android-Hunter   # or your cloned path
source venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 9000
```

Check status:

```bash
curl http://127.0.0.1:9000/api/status
# -> {"status":"ok"}
```

---

## 🌐 Running the Web Dashboard

In another terminal:

```bash
cd /opt/RedHawk-Android-Hunter/frontend
python3 -m http.server 8080
```

Then open:

- Dashboard: http://127.0.0.1:8080/
- Backend docs: http://127.0.0.1:9000/docs

---

## 💻 Using the Dashboard

1. Open http://127.0.0.1:8080/
2. (Optional) Enter API Key if you configured `DASHBOARD_API_KEYS`
3. Choose an APK file
4. Choose mode (Safe / Red Team – informational)
5. Click **Start Scan**

Right card:

- Shows scan history (APK, status, severity, total findings, mode)
- Click a **completed** scan row → loads AI bug bounty report
- Use **Copy report** → clipboard → paste into HackerOne/Bugcrowd

---

## 🧪 CLI Usage

You can also run scans directly from terminal:

```bash
cd /opt/RedHawk-Android-Hunter
source venv/bin/activate

python3 -m backend.scanner uploads/your_app.apk --ai
```

This will:

- Run **MobSFScan** on the APK
- Save findings to `backend/reports/your_app.apk.findings.json`
- Generate Markdown report in `backend/reports/your_app.apk.report.md`
- If `--ai` and `OPENROUTER_API_KEY` are set → generate `your_app.apk.ai_report.md`

---

## 📂 Output Files

By default:

- Uploads: `uploads/`
- Reports: `backend/reports/`

For each `<apk_name>`:

- `<apk_name>.findings.json` — raw normalized scanner findings
- `<apk_name>.report.md` — basic report (no AI)
- `<apk_name>.ai_report.md` — AI-enriched bug bounty report (if enabled)

---

## ⚙️ REST API Quick Reference

Base URL: `http://127.0.0.1:9000`

### Health

```bash
curl http://127.0.0.1:9000/api/status
```

### List all scans

```bash
curl http://127.0.0.1:9000/api/scans
```

### Get single scan by ID

```bash
curl http://127.0.0.1:9000/api/scans/<scan_id>
```

### Start a scan (upload APK)

```bash
curl -X POST http://127.0.0.1:9000/api/scan   -F "file=@uploads/app.apk"   -F "app_id=com.example.app"   -F "mode=safe"   -F "ai=true"
```

### Get AI report text for a scan

```bash
curl http://127.0.0.1:9000/api/reports/<scan_id>/ai_report
```

---

## 🧰 Requirements File

`requirements.txt` contains:

```txt
fastapi
uvicorn
python-multipart
mobsfscan
openai>=1.0.0
requests
```

Install with:

```bash
pip install -r requirements.txt
```

---

## 🐞 Troubleshooting

**1. `address already in use` on port 9000 or 8080**

Another process is using the port.

```bash
fuser -k 9000/tcp
fuser -k 8080/tcp
```

Then restart backend/frontend.

---

**2. Dashboard says backend unreachable**

- Ensure `uvicorn backend.app:app --host 0.0.0.0 --port 9000` is running
- Test with `curl http://127.0.0.1:9000/api/status`

---

**3. AI report failed / OPENROUTER_API_KEY not set**

- Double-check: `echo $OPENROUTER_API_KEY`
- Restart your shell and backend
- Ensure your OpenRouter key is valid and has quota

---

**4. No findings but app is clearly vulnerable**

This is a **static analysis helper**, not a guarantee of security.  
Use it as one step in a broader manual pentest.

---

## ⚠️ Legal Disclaimer

RedHawk Android Hunter is provided for:

- Educational use
- Security testing of applications you own
- Security testing of applications where you have **explicit written authorization** (e.g., bug bounty programs)

Using this tool against targets **without permission** is illegal.  
The authors and contributors are **not responsible** for misuse.

> 🛡️ Be ethical. Respect scopes and laws.

---

## 🧩 Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Scanner:** MobSFScan (static)
- **AI:** OpenRouter (OpenAI-compatible Chat Completions)
- **Frontend:** Vanilla HTML + JS (Neon Dark UI)
- **Notifications:** Telegram Bot API

---

🦅 Happy Hunting — responsibly.
