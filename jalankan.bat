@echo off
rem Menyiapkan dan menjalankan Capy Organizer (Windows).
rem Cara pakai: klik dua kali jalankan.bat. Pertama kali membuat agent-backend\.env dengan SECRET_KEY acak.
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python belum terpasang. Unduh di https://www.python.org lalu centang "Add Python to PATH". & pause & exit /b 1)
where node >nul 2>nul || (echo Node.js belum terpasang. Unduh versi LTS di https://nodejs.org & pause & exit /b 1)

echo == Backend: lingkungan Python dan dependency
if not exist agent-backend\.venv python -m venv agent-backend\.venv
call agent-backend\.venv\Scripts\activate.bat
pip install -q -r agent-backend\requirements.txt || (pause & exit /b 1)

echo == Pengaturan (.env)
if not exist agent-backend\.env (
  for /f %%K in ('python -c "import secrets; print(secrets.token_hex(32))"') do (
    echo SECRET_KEY=%%K> agent-backend\.env
    echo CORS_ORIGINS=http://localhost:3000>> agent-backend\.env
  )
  echo agent-backend\.env dibuat.
)

echo == Menyiapkan akun dan acara demo juri
python agent-backend\buat_demo.py || (echo Gagal menyiapkan data demo. & pause & exit /b 1)

echo == Frontend: dependency
if not exist agent-frontend\node_modules (
  pushd agent-frontend
  call npm install --no-audit --no-fund || (popd & pause & exit /b 1)
  popd
)

echo == Menjalankan server
start "Capy Backend" cmd /k "cd /d %~dp0agent-backend && call .venv\Scripts\activate.bat && python app.py"
start "Capy Frontend" cmd /k "cd /d %~dp0agent-frontend && set CAPY_DEMO_MODE=1 && npm run dev"
timeout /t 10 /nobreak >nul
start "" http://localhost:3000/beranda
echo Server berjalan di jendela terpisah. Tutup jendela itu untuk menghentikan.
pause
