#!/bin/bash
# RedHawk Android Hunter launcher

cd "$(dirname "$0")" || exit 1

if [ ! -d "venv" ]; then
  echo "[*] Creating virtualenv..."
  python3 -m venv venv || exit 1
fi

source venv/bin/activate

echo "[*] Installing requirements..."
pip install -r requirements.txt

mkdir -p uploads backend/reports

echo "[*] Killing anything on 9000/8080..."
fuser -k 9000/tcp >/dev/null 2>&1 || true
fuser -k 8080/tcp >/dev/null 2>&1 || true

echo "[*] Starting backend on 9000..."
uvicorn backend.app:app --host 0.0.0.0 --port 9000 &

sleep 2

echo "[*] Starting frontend on 8080..."
cd frontend
python3 -m http.server 8080 &

sleep 2

echo "[*] Open http://127.0.0.1:8080/ in your browser."
