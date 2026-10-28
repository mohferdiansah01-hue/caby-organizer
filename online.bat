@echo off
setlocal
cd /d "%~dp0"

where cloudflared >nul 2>nul
if not errorlevel 1 (
  set "CLOUDFLARED=cloudflared"
) else (
  set "CLOUDFLARED=%LOCALAPPDATA%\Programs\cloudflared\cloudflared.exe"
  if not exist "%LOCALAPPDATA%\Programs\cloudflared\cloudflared.exe" (
    echo Mengunduh cloudflared resmi ke folder pengguna...
    if not exist "%LOCALAPPDATA%\Programs\cloudflared" mkdir "%LOCALAPPDATA%\Programs\cloudflared"
    curl.exe --fail --location --silent --show-error --output "%LOCALAPPDATA%\Programs\cloudflared\cloudflared.exe" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" || (
      echo Unduhan gagal. Periksa koneksi internet atau unduh manual dari dokumentasi Cloudflare.
      pause
      exit /b 1
    )
  )
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
"%CLOUDFLARED%" tunnel --url http://localhost:3000 %ALLOW_ARGS%