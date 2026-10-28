@echo off
rem Mode demo (Windows): build produksi frontend lalu jalankan server standalone.
rem Jalankan jalankan.bat sekali dulu untuk menyiapkan lingkungan dan .env.
rem Build butuh internet (Google Fonts) saat pertama kali dijalankan.
setlocal
cd /d "%~dp0"

if not exist agent-backend\.venv\Scripts\activate.bat (
  echo Jalankan jalankan.bat sekali dulu untuk menyiapkan lingkungan dan .env.
  pause & exit /b 1
)
if not exist agent-backend\.env (
  echo Jalankan jalankan.bat sekali dulu untuk menyiapkan lingkungan dan .env.
  pause & exit /b 1
)

echo == Build frontend produksi
pushd agent-frontend
if not exist node_modules call npm install --no-audit --no-fund
call npm run build || (popd & pause & exit /b 1)
popd

if not exist agent-frontend\.next\standalone\.next mkdir agent-frontend\.next\standalone\.next
xcopy /e /i /y agent-frontend\.next\static agent-frontend\.next\standalone\.next\static >nul
xcopy /e /i /y agent-frontend\public agent-frontend\.next\standalone\public >nul

echo == Menjalankan backend dan frontend produksi
start "Capy Backend" cmd /k "cd /d %~dp0agent-backend && call .venv\Scripts\activate.bat && python app.py"
start "Capy Frontend (demo)" cmd /k "cd /d %~dp0agent-frontend\.next\standalone && set PORT=3000 && set HOSTNAME=0.0.0.0 && node server.js"
timeout /t 8 /nobreak >nul
start "" http://localhost:3000/beranda
echo Server demo berjalan di jendela terpisah. Tutup jendela itu untuk berhenti.
pause
