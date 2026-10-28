#!/usr/bin/env bash
# Menyiapkan dan menjalankan Capy Organizer (Linux dan macOS).
# Cara pakai: ./jalankan.sh     (pertama kali membuat agent-backend/.env dengan SECRET_KEY acak)
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Python 3 belum terpasang. Unduh di https://www.python.org"; exit 1; }
command -v node >/dev/null || { echo "Node.js belum terpasang. Unduh versi LTS di https://nodejs.org"; exit 1; }

echo "== Backend: lingkungan Python dan dependency"
if [ ! -d agent-backend/.venv ]; then python3 -m venv agent-backend/.venv; fi
. agent-backend/.venv/bin/activate
pip install -q -r agent-backend/requirements.txt

echo "== Pengaturan (.env)"
if [ ! -f agent-backend/.env ]; then
  KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  printf "SECRET_KEY=%s\nCORS_ORIGINS=http://localhost:3000\n" "$KEY" > agent-backend/.env
  echo "agent-backend/.env dibuat."
fi

echo "== Menyiapkan akun dan acara demo juri"
python agent-backend/buat_demo.py

echo "== Frontend: dependency"
if [ ! -d agent-frontend/node_modules ]; then (cd agent-frontend && npm install --no-audit --no-fund); fi

echo "== Menjalankan"
(cd agent-backend && python app.py) > backend.log 2>&1 &
BACKEND_PID=$!
(cd agent-frontend && CAPY_DEMO_MODE=1 npm run dev) > frontend.log 2>&1 &
FRONTEND_PID=$!
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT

echo "Menunggu server siap..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null http://localhost:3000/beranda; then break; fi
  sleep 1
done
echo "Buka http://localhost:3000/beranda di browser."
echo "Tekan Ctrl+C untuk menghentikan. Log: backend.log dan frontend.log"
wait
