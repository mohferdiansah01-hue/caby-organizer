#!/usr/bin/env bash
# Mode demo: build produksi frontend lalu jalankan server standalone (lebih cepat dibuka daripada npm run dev).
# Pakai ./jalankan.sh dulu sekali agar lingkungan Python dan .env sudah siap.
# Build butuh internet (Google Fonts) saat pertama kali dijalankan.
set -e
cd "$(dirname "$0")"

if [ ! -d agent-backend/.venv ] || [ ! -f agent-backend/.env ]; then
  echo "Jalankan ./jalankan.sh sekali dulu untuk menyiapkan lingkungan dan .env."; exit 1
fi

echo "== Build frontend produksi"
(cd agent-frontend && npm install --no-audit --no-fund >/dev/null 2>&1 || true && npm run build)
mkdir -p agent-frontend/.next/standalone/.next
cp -r agent-frontend/.next/static agent-frontend/.next/standalone/.next/static
rm -rf agent-frontend/.next/standalone/public && cp -r agent-frontend/public agent-frontend/.next/standalone/public

echo "== Menjalankan backend"
(cd agent-backend && . .venv/bin/activate && python app.py) > backend.log 2>&1 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT

echo "== Menjalankan frontend (produksi)"
(cd agent-frontend/.next/standalone && PORT=3000 HOSTNAME=0.0.0.0 node server.js) > frontend.log 2>&1 &
FRONTEND_PID=$!

for i in $(seq 1 60); do
  if curl -s -o /dev/null http://localhost:3000/beranda; then break; fi
  sleep 1
done
echo "Buka http://localhost:3000/beranda di browser. Tekan Ctrl+C untuk berhenti."
wait
