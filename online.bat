@echo off
setlocal
cd /d "%~dp0"

where cloudflared >nul 2>nul || (
  echo cloudflared belum terpasang.
  echo Pasang dengan: winget install --id Cloudflare.cloudflared -e
  pause
  exit /b 1
)

curl.exe --fail --silent --output NUL http://localhost:3000/beranda || (
  echo Aplikasi lokal belum berjalan. Jalankan jalankan.bat terlebih dahulu.
  pause
  exit /b 1
)

set "ALLOW_ARGS="
:parse_emails
if "%~1"=="" goto start_tunnel
set "ALLOW_ARGS=%ALLOW_ARGS% --allowed-mail %~1"
shift
goto parse_emails

:start_tunnel
echo Membuat URL demo sementara. Bagikan URL yang muncul di bawah.
echo Tekan Ctrl+C untuk menghentikan akses publik.
cloudflared tunnel --url http://localhost:3000 %ALLOW_ARGS%