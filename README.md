# Caby Organizer

Aplikasi untuk panitia acara kampus: membagi tugas dengan jelas, mengingatkan tenggat, dan mengurangi koordinasi lewat WhatsApp. Dibuat untuk satu acara dengan puluhan orang, bukan untuk banyak organisasi sekaligus.

## Alur pemakaian

1. **Daftar akun** dengan nama, username, dan password. Akun tidak punya peran sampai bergabung ke sebuah acara.
2. **Masuk**, lalu buka dashboard. Di sana ada daftar acara yang diikuti, tombol Buat acara, dan Gabung acara.
3. **Buat acara**: isi nama, tanggal, dan password pendaftaran. Pembuat otomatis menjadi Ketua acara itu. Bisa mulai dari template Pemilihan, Seminar, atau Bakti sosial yang sudah berisi tugas awal per seksi.
4. **Gabung acara**: pilih acara, pilih peran Anggota atau PJ, lalu masukkan password acara. Langsung terdaftar tanpa persetujuan.
5. **Ketua mengatur acara**:
   - menetapkan atau mengubah password pendaftaran,
   - menurunkan jabatan, memindah seksi, atau mengeluarkan anggota (Ketua sendiri tidak bisa dikeluarkan),
   - membagikan tugas ke orang tertentu dan melihat yang perlu ditindaklanjuti,
   - mencatat keputusan rapat,
   - membagikan undangan dan teks pengingat tenggat ke WhatsApp,
   - mengunduh laporan PDF dan menambahkan tenggat ke kalender.
6. **Anggota** melihat tugasnya, menerima atau menolak tugas yang dibagikan (penolakan wajib disertai alasan), dan melihat catatan keputusan.
7. **Tutup acara** membekukan perubahan. Peserta selain Ketua hanya bisa membaca.

## Tanya Capy (asisten, mode demo)

Panel **Tanya Capy** ada di dashboard dan di halaman acara. Asisten ini masih **mode demo**: ia menjawab dengan model lokal lewat **Ollama**, sehingga gratis dan tidak butuh kunci API. Batasannya:

- Jawaban bisa kurang tepat. Periksa lagi sebelum dipakai untuk keputusan penting.
- Belum bisa mencari di internet.
- Hanya memberi informasi. Capy tidak mengubah data acara.

Cara menyiapkan Ollama:

```bash
# pasang Ollama dari https://ollama.com, lalu:
ollama pull llama3.1
ollama serve        # biasanya sudah berjalan otomatis setelah dipasang
```

Pengaturan di `agent-backend/.env` (opsional, ini default-nya):

| Variabel | Default | Fungsi |
|---|---|---|
| `OLLAMA_URL` | Lokal tanpa API key; `https://ollama.com/api/chat` jika `OLLAMA_API_KEY` diisi | Alamat Ollama. Nilai eksplisit di `.env` selalu dipakai. |
| `OLLAMA_MODEL` | `llama3.1` lokal; `gpt-oss:20b-cloud` untuk Cloud | Model default yang dipakai untuk ngobrol dan kerja acara. Mode bisa dioverride terpisah jika diperlukan. |
| `OLLAMA_API_KEY` | kosong | Kunci Ollama Cloud. Backend perlu dijalankan ulang setelah `.env` diubah. |

Saat dijalankan lokal, backend membaca `agent-backend/.env` terlebih dahulu lalu `.env` di folder utama sebagai fallback. Nilai environment yang diberikan langsung ke proses tetap memiliki prioritas tertinggi. Docker Compose menggunakan `agent-backend/.env`.

Setiap user dibatasi 10 pertanyaan per menit. Jika Ollama tidak berjalan, panel menampilkan petunjuk untuk menyalakannya.

**Untuk produksi** (pengembangan berikutnya): ganti dengan layanan model yang stabil dan berbayar, tambahkan pencarian web dengan sumber yang bisa diperiksa, dan atur batas pemakaian per hari.

## Capy sebagai agen

Capy bisa membaca data acara yang boleh kamu lihat, membuka halaman, dan mengusulkan perubahan. **Setiap perubahan ditanyakan dulu**: Capy menampilkan usulan, dan baru berjalan setelah kamu menekan **Jalankan**. Tindakan berbahaya (hapus tugas, keluarkan peserta, tutup acara) meminta konfirmasi tambahan.

Yang bisa diusulkan: membuat, mengubah, dan menghapus tugas; membagikan tugas; mencatat keputusan; mengubah peran peserta; mengeluarkan peserta; menutup acara; membatalkan atau mengulangi perubahan terakhir; membuka laporan PDF.

**Batalkan dan ulangi** tersedia di halaman acara. Yang dibatalkan hanya perubahanmu sendiri di acara itu, untuk: tugas (tambah, ubah, hapus, bagikan), peran peserta, keluarkan peserta, serta tutup dan buka acara. Catatan keputusan, gabung acara, dan perubahan password tidak bisa dibatalkan. Setelah ada perubahan baru, riwayat "ulangi" dikosongkan. Saat acara ditutup, hanya penutupan dan pembukaan yang bisa dibatalkan.

## Yang sengaja tidak ada

- **Pembayaran.** Tidak ada transaksi di aplikasi.
- **Persetujuan berjenjang.** Gabung dengan password langsung berlaku.
- **Capy mengubah data.** Capy hanya menjawab. Perubahan tetap dilakukan manual.
- **Pengiriman WhatsApp atau email otomatis.** Aplikasi menyiapkan teks, lalu Ketua memilih grup atau kontak di WhatsApp sendiri. Nomor telepon anggota tidak disimpan.
- **Lupa password.** Hubungi admin untuk mengatur ulang lewat database.

## Menjalankan

Cara termudah (Windows): klik dua kali `jalankan.bat`. Linux dan macOS: `./jalankan.sh`. Skrip membuat `agent-backend/.env` jika belum ada, menyiapkan data demo juri secara idempotent, lalu menyalakan backend di port 5000 dan frontend di port 3000. Buka http://localhost:3000/beranda.

Data demo berisi acara **Gebyar HUT Organisasi 2027** dengan tanggal 135 hari dari saat seed dijalankan, 30 tugas pada 10 seksi, akun ketua/koordinator/anggota/admin, serta contoh kabar, keputusan, pesan, dan komentar. Seed hanya berjalan di mode lokal; script menolak `CAPY_PRODUKSI=1` dan tidak menghapus data lain.

Kredensial login demo:

| Peran | Username | Password |
|---|---|---|
| Ketua acara | `juri.ketua` | `GebyarJuri2027!` |
| Koordinator Acara | `juri.acara` | `GebyarJuri2027!` |
| Koordinator PDD | `juri.pdd` | `GebyarJuri2027!` |
| Koordinator Humas | `juri.humas` | `GebyarJuri2027!` |
| Koordinator Konsumsi | `juri.konsumsi` | `GebyarJuri2027!` |
| Anggota | `juri.anggota` | `GebyarJuri2027!` |
| Admin juri | `juri.admin` | `AdminJuri2027!` |

Untuk mengulang seed secara manual: `cd agent-backend && python buat_demo.py`. Password pendaftaran acara demo: `GebyarGabung2027!`. Mode lokal menampilkan kredensial di halaman login; Docker/produksi sengaja tidak menampilkannya.

Mode produksi lokal: jalankan `jalankan.sh` sekali, lalu `demo.sh` (atau `demo.bat`). Build butuh internet karena font diunduh dari Google.

Manual:

```bash
cd agent-backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py

cd ../agent-frontend
npm install
FLASK_BACKEND_URL=http://localhost:5000 npm run dev
```

## Konfigurasi (`agent-backend/.env`)

| Variabel | Fungsi |
|---|---|
| `SECRET_KEY` | Kunci sesi. Wajib diisi agar login tidak hilang saat server restart. |
| `DATABASE_URL` | Default `sqlite:///capy.db`. |
| `CORS_ORIGINS` | Asal frontend yang diizinkan, default `http://localhost:3000`. |
| `COOKIE_SECURE` | Isi `1` jika dijalankan lewat HTTPS. |

Frontend membaca `FLASK_BACKEND_URL` (default `http://localhost:5000`) untuk meneruskan `/api` ke backend.

## Admin

Admin tidak punya antarmuka. Untuk menjadikan akun sebagai admin, jalankan dari folder `agent-backend`:

```bash
python -c "from app import app, db, Orang; \
with app.app_context(): o=Orang.query.filter_by(username='NAMA_USER').first(); o.admin=True; db.session.commit()"
```

Admin dipakai untuk mengklaim acara lama yang belum punya Ketua, lewat dashboard.

## Tes

```bash
cd agent-backend
python -m pytest -q tests
```

Frontend: `cd agent-frontend && npx tsc --noEmit` dan `npx eslint app`.

## Struktur

- `agent-backend/app.py`: semua endpoint Flask dan aturan akses.
- `agent-backend/database.py`: model SQLAlchemy dan migrasi kolom.
- `agent-backend/peran.py`: aturan peran (satu Ketua per acara, koordinator wajib seksi).
- `agent-frontend/app/`: halaman Next.js (beranda, login, daftar, dashboard, acara, ruang kerja).
- `docs/API.md`: daftar endpoint.

## Menjalankan untuk produksi (hosting)

1. Isi `agent-backend/.env` dengan `SECRET_KEY` yang panjang dan acak. Mode produksi menolak berjalan tanpa itu.
2. Jalankan dengan Docker: `docker compose up -d --build`. Layanan:
   - `backend`: gunicorn dengan **satu proses dan delapan thread**. Harus satu proses, karena database SQLite dan batas pemakaian disimpan di memori proses.
   - `frontend`: Next.js standalone di port 3000.
   - `cadangan`: menyalin database setiap 24 jam ke folder `backups/` di volume `capy-data`.
3. Taruh di belakang HTTPS (misalnya reverse proxy). Cookie sesi hanya dikirim lewat HTTPS saat `CAPY_PRODUKSI=1`.
4. Untuk Capy, pasang Ollama di host dan atur `OLLAMA_URL` ke alamatnya, atau biarkan asisten nonaktif jika tidak diperlukan.

## Deploy demo gratis ke Render

Repo ini menyediakan `render.yaml` untuk membuat frontend Next.js dan backend Flask sebagai dua Web Service gratis di region Singapore. Di Render, pilih **New + > Blueprint** lalu hubungkan repo GitHub ini. Saat diminta, masukkan `OLLAMA_API_KEY` yang baru dari akun Ollama; jangan masukkan key ke file atau commit.

Blueprint menyalakan akun demo juri dan mengisi ulang acara contoh saat backend start. Ini hanya untuk demonstrasi: layanan gratis dapat tidur setelah idle dan filesystem-nya sementara, sehingga perubahan/data uji dapat hilang saat restart atau deploy. Jangan gunakan setup ini untuk data acara nyata. Akun demo admin juga sengaja dapat dilihat publik selama demo.

Cadangan juga bisa dijalankan manual dengan `python cadangan_db.py`. Salin folder `backups/` ke tempat lain secara berkala.

## Admin (pusat admin)

Admin pertama dibuat dari terminal, di folder `agent-backend`:
```
python buat_admin.py <username>                          # akun sudah ada: jadikan admin
python buat_admin.py <username> --nama "Nama" --baru     # buat akun baru, password diminta lewat prompt
python buat_admin.py <username> --cabut                  # cabut status admin
```
Setelah itu masuk seperti biasa. Menu **Admin** muncul di navigasi, berisi ringkasan, daftar akun (jadikan/cabut admin, atur ulang password), dan daftar acara. Halaman ini tidak bisa dibuka akun biasa.

## Tes

Tiga lapisan tes:

1. **Backend (pytest):** dari `agent-backend`, jalankan `python -m pytest -q tests`. Mencakup izin, alur acara, riwayat, pemulihan password, dan kuota Capy.
2. **Komponen frontend (Vitest):** dari `agent-frontend`, jalankan `npm test`. Mencakup form masuk dan daftar, kabar, tugas menunggu, lipat, dan dialog konfirmasi.
3. **End-to-end (Playwright):** dari folder utama, jalankan:
   ```
   pip install playwright requests
   python -m playwright install chromium
   python e2e/alur_utama.py
   ```
   Skrip ini menyalakan backend dan frontend sendiri dengan database sementara, lalu menguji alur utama di browser: daftar, buat acara, gabung dari HP, tugas, kabar, lupa password, dan reset password admin. Semua server dimatikan dan database sementara dihapus setelah selesai.

Uji model Ollama tidak termasuk di sini. Lihat `PANDUAN_HOSTING.md` bagian 9.
