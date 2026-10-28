# Panduan hosting Caby Organizer (VPS + Docker + HTTPS)

Panduan ini untuk satu VPS Ubuntu dengan satu domain. Semua berjalan di Docker: backend, frontend, cadangan harian, dan Caby (Caddy) untuk HTTPS otomatis.

## 0. Yang disiapkan sebelum mulai
- VPS Ubuntu 22.04 atau 24.04, RAM minimal 1 GB.
- Domain, misalnya `caby.contoh.ac.id`.
- Kunci API Ollama Cloud baru (buat di akun Ollama, dan cabut kunci lama).

## 1. Arahkan domain ke VPS
Di pengelola DNS, buat **A record** `caby` (atau `@`) yang mengarah ke IP publik VPS. Tunggu sampai berlaku (biasanya beberapa menit).

## 2. Buka port dan amankan server
```
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```
Port 3000 dan 5000 sengaja tidak dibuka. Hanya Caddy yang menerima koneksi dari luar.

## 3. Pasang Docker
```
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER      # lalu logout dan login lagi
```

## 4. Unggah aplikasi
Salin `harus-v28.zip` ke server (misalnya dengan `scp` atau SFTP), lalu:
```
sudo apt install -y unzip
unzip harus-v28.zip -d ~/caby
cd ~/caby/harus
```

## 5. Buat file konfigurasi
Salin contoh env, lalu isi:
```
cp agent-backend/.env.example agent-backend/.env
nano agent-backend/.env
```
Isi minimal:
- `SECRET_KEY`: buat dengan `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `CORS_ORIGINS=https://caby.contoh.ac.id` (domainmu)
- `CAPY_PRODUKSI=1`, `COOKIE_SECURE=1`, `TRUST_PROXY=1`
- `OLLAMA_API_KEY`: kunci Ollama Cloud baru
- `OLLAMA_MODEL`, `CAPY_MODEL_OBROLAN`, `CAPY_MODEL_ACARA`: nama model yang tersedia di akunmu

Lalu buat file `.env` di folder utama (untuk nama domain, dibaca Docker Compose):
```
echo "DOMAIN=caby.contoh.ac.id" > .env
```

## 6. Jalankan
```
docker compose up -d --build
```
Build pertama memakan beberapa menit. Font diunduh dari Google saat build, jadi server perlu internet.

Cek status:
```
docker compose ps
docker compose logs -f backend      # Ctrl+C untuk keluar
```
Semua layanan harus `running`. Caddy akan mengurus sertifikat HTTPS otomatis; log-nya ada di `docker compose logs caddy`.

## 7. Buat admin pertama
Dua cara:

**A. Otomatis (disarankan):** sebelum langkah 6, isi di `agent-backend/.env`:
```
ADMIN_AWAL_USERNAME=nama_admin
ADMIN_AWAL_PASSWORD=password_minimal_8_karakter
```
Admin dibuat saat pertama kali aplikasi jalan. Setelah itu **hapus kedua baris ini** dari `.env`, lalu jalankan `docker compose up -d` lagi agar perubahan terbaca.

**B. Lewat terminal:**
```
docker compose exec backend python buat_admin.py NAMA_ADMIN --nama "Nama Lengkap" --baru
```

Setelah itu masuk di `https://DOMAINMU/login`. Menu **Admin** akan muncul.

## 8. Uji alur utama (checklist)
Lakukan di browser, dan centang satu per satu:
- [ ] `https://DOMAINMU` terbuka dengan gembok HTTPS.
- [ ] Daftar akun baru. Kode pemulihan tampil, simpan.
- [ ] Masuk, lalu halaman pindah ke dashboard.
- [ ] Buat acara dengan template Pemilihan.
- [ ] Dari akun kedua: gabung acara dengan password, lalu masuk ke acara.
- [ ] Bagikan tugas ke akun kedua, lalu akun kedua menerima tugas.
- [ ] Lupa password: pakai kode pemulihan di halaman Lupa password.
- [ ] Capy: tanya sesuatu di dashboard (ngobrol) dan di dalam acara (kerja).
- [ ] Halaman admin terbuka untuk admin, dan ditolak untuk akun biasa.
- [ ] Coba tampilan di HP.

Cara melihat error jika ada yang gagal:
```
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
```

## 9. Uji model Ollama Cloud
Ini bagian yang belum pernah diuji dengan kunci asli. Di komputermu (bukan server), jalankan `uji-ollama.zip` dengan:
```
export OLLAMA_URL=https://ollama.com/api/chat
export OLLAMA_API_KEY=KUNCI_BARU_KAMU
export OLLAMA_MODEL=NAMA_MODEL
python uji_ollama.py
```
Di Windows gunakan `$env:OLLAMA_API_KEY="..."` di PowerShell. Kirim `hasil_uji_*.md` untuk dianalisis. Kalau model acara tidak mendukung alat, Capy tetap menjawab, tetapi tidak bisa membaca data atau mengusulkan perubahan.

## 10. Cadangan
Cadangan otomatis dibuat setiap 24 jam di volume `capy-data` (folder `backups/` di dalamnya). Salin ke tempat lain secara berkala:
```
docker compose exec cadangan ls /app/instance/backups
docker compose cp cadangan:/app/instance/backups ./cadangan-$(date +%F)
```
Simpan salinan di luar server, misalnya di komputer atau penyimpanan cloud. Cadangan di server yang sama tidak melindungi dari kerusakan disk.

## 11. Memperbarui aplikasi
Ganti isi folder dengan versi baru (tanpa `.env`), lalu:
```
docker compose up -d --build
```
Data di volume `capy-data` tetap aman. Sebelum memperbarui, salin cadangan terbaru seperti di langkah 10.

## 12. Masalah yang sering terjadi
- **Login gagal atau tidak tersimpan:** pastikan domain di browser sama dengan `CORS_ORIGINS`, dan `COOKIE_SECURE=1` hanya dipakai lewat HTTPS.
- **Halaman 502 Bad Gateway:** frontend belum siap. Tunggu sebentar, lalu cek `docker compose ps` dan `docker compose logs frontend`.
- **Capy mengatakan Ollama tidak bisa dihubungi:** cek `OLLAMA_URL`, `OLLAMA_API_KEY`, dan nama model. Dari server, jalankan `docker compose exec backend python -c "import requests,os;print(requests.get('https://ollama.com').status_code)"`.
- **Banyak pengguna di satu jaringan terkena batas login:** batas dihitung per alamat dan nama pengguna. Jika tetap terasa terlalu ketat, naikkan batas di kode atau pastikan `TRUST_PROXY=1` aktif.
- **Ingin mengulang dari awal (hapus semua data uji):** `docker compose down -v` menghapus volume. Lakukan hanya jika benar-benar ingin menghapus data.

## Keamanan yang disarankan
- Login SSH dengan kunci saja, nonaktifkan login password.
- Jalankan `sudo apt update && sudo apt upgrade` secara berkala.
- Cabut semua kunci lama yang sempat terlihat di percakapan, termasuk `SECRET_KEY` dan kunci Ollama sebelumnya.

## Cek alamat asli pengguna di balik proxy
Batas login dan kuota dihitung per alamat. Di belakang Caddy, pastikan alamat itu alamat pengguna, bukan alamat container:
1. Dari HP (jaringan seluler) lakukan 6 kali login dengan password salah memakai username acak.
2. Dari laptop (jaringan lain) coba login dengan password yang benar.
3. Jika laptop **tidak** ikut terkunci, batas per alamat bekerja dengan benar. Jika ikut terkunci, `TRUST_PROXY=1` belum meneruskan alamat asli: cek `docker compose logs backend` dan kabari kami.

## Build dan font
Build Docker mengunduh font Zilla Slab dan Inter dari Google, jadi server (atau mesin tempat build) harus punya internet. Jika server tidak bisa mengakses Google, lakukan build di komputer lain yang punya internet, lalu pindahkan image-nya dengan `docker save` dan `docker load`.
