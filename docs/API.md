# Referensi API

Semua endpoint berawalan `/api`. Kecuali yang disebut publik, semua membutuhkan login (cookie sesi). Akses ke data acara mengikuti keanggotaan dan peran di acara tersebut.

| Metode | Path | Keterangan |
|---|---|---|
| GET | `/api/admin/acara` | Semua acara dengan pembuat dan jumlah peserta. Hanya admin. |
| GET | `/api/admin/acara-tanpa-ketua` | Acara lama tanpa pembuat. Hanya admin; dipakai untuk mengklaim acara lama. |
| POST | `/api/admin/angkat` | Admin menjadikan akun lain admin, atau mencabut statusnya. |
| GET | `/api/admin/audit` | Catatan aksi tulis terbaru (hanya dibaca, tidak bisa diubah). Hanya admin. |
| GET | `/api/admin/pengguna` | Daftar akun. Hanya admin. Kode pemulihan dan password tidak pernah ditampilkan. |
| POST | `/api/admin/reset-password` | Admin mengatur ulang password akun yang lupa password. Password baru diberikan admin lewat jalur lain. |
| GET | `/api/admin/ringkasan` | Angka utama untuk halaman admin. |
| POST | `/api/agen/chat` | Capy: membaca data acara, membuka halaman, dan mengusulkan perubahan. Riwayat disimpan per acara. |
| POST | `/api/agen/jalankan` | Pengguna menekan Jalankan pada usulan dari Capy. |
| DELETE | `/api/agen/riwayat` | Mulai baru: hapus percakapan saya di satu acara (atau 'umum'). Percakapan orang lain tidak tersentuh. |
| GET | `/api/agen/riwayat` | Percakapan saya di satu acara (atau 'umum'). Tidak pernah menampilkan percakapan orang lain. |
| POST | `/api/auth/daftar` | Daftar akun user: nama, username, password. Tanpa acara dan tanpa role. |
| GET | `/api/auth/events` | Daftar acara untuk halaman login. Hanya nama dan tanggal, tanpa data tugas. |
| POST | `/api/auth/login` | - |
| POST | `/api/auth/logout` | - |
| POST | `/api/auth/lupa-password` | Atur ulang password dengan kode pemulihan. Kode lama langsung hangus dan kode baru diberikan sekali. |
| GET | `/api/auth/me` | - |
| GET | `/api/beranda` | Data beranda publik: pengaturan tampilan, angka dari data asli, dan kabar kerja yang diizinkan tampil. |
| PUT | `/api/beranda` | - |
| GET | `/api/events` | - |
| POST | `/api/events` | Buat acara. Pembuatnya otomatis menjadi Ketua acara itu dan langsung masuk ke acara tersebut. |
| DELETE | `/api/events/<event_id>` | - |
| GET | `/api/events/<event_id>` | - |
| POST | `/api/events/<event_id>/buka` | - |
| GET | `/api/events/<event_id>/calendar.ics` | - |
| GET | `/api/events/<event_id>/dashboard` | - |
| GET | `/api/events/<event_id>/dokumen/laporan.pdf` | Laporan acara dalam PDF: data acara, ringkasan tugas per seksi, log, daftar tamu, dan notulen. |
| GET | `/api/events/<event_id>/keputusan` | - |
| POST | `/api/events/<event_id>/keputusan` | - |
| POST | `/api/events/<event_id>/klaim` | Acara lama yang dibuat sebelum ada pembuat: hanya admin yang bisa menetapkan dirinya sebagai Ketua. |
| PUT | `/api/events/<event_id>/password` | Ketua mengatur password pendaftaran acara. Kosongkan untuk menutup pendaftaran lewat password. |
| GET | `/api/events/<event_id>/peran` | - |
| POST | `/api/events/<event_id>/peran` | - |
| DELETE | `/api/events/<event_id>/peran/<peran_id>` | - |
| PUT | `/api/events/<event_id>/peran/<peran_id>` | Ketua menurunkan jabatan, menaikkan, atau memindahkan anggota ke seksi lain. |
| POST | `/api/events/<event_id>/pesan` | - |
| POST | `/api/events/<event_id>/seksi/<seksi>/pakai-default` | Ganti tugas seksi di acara ini dengan tugas default. Menghapus tugas yang sudah ada, jadi wajib konfirmasi. |
| POST | `/api/events/<event_id>/serahkan-ketua` | Ketua menyerahkan kepemimpinan acara kepada peserta lain. Ketua lama menjadi anggota. |
| GET | `/api/events/<event_id>/struktur` | - |
| PUT | `/api/events/<event_id>/struktur` | - |
| GET | `/api/events/<event_id>/tindak-lanjut` | Daftar yang harus ditindaklanjuti Ketua: belum dibagi, belum dikonfirmasi lebih dari 24 jam, |
| POST | `/api/events/<event_id>/tutup` | Tutup acara: semua peran kembali ke default (anggota, seksi tetap), dan peran tidak bisa diubah sampai acara dibuka lagi. |
| GET | `/api/kabar` | - |
| POST | `/api/kabar` | - |
| DELETE | `/api/kabar/<kabar_id>` | - |
| GET | `/api/kerja` | Ruang kerja seksi: tugas yang menjadi tanggung jawab seksi ini, dikelompokkan per acara. |
| POST | `/api/lampiran` | - |
| DELETE | `/api/lampiran/<lampiran_id>` | - |
| GET | `/api/lampiran/<lampiran_id>` | - |
| GET | `/api/me/acara` | Acara yang diikuti user ini, beserta perannya. |
| POST | `/api/me/acara/<event_id>/gabung` | Gabung ke acara dengan password pendaftaran dari Ketua. Peran yang bisa dipilih: anggota atau pj. |
| POST | `/api/me/acara/<event_id>/masuk` | Masuk ke dashboard acara tempat user terdaftar. Peran diambil dari penugasan di acara itu. |
| POST | `/api/me/keluar-acara` | Keluar dari acara aktif dan kembali ke dashboard user. |
| POST | `/api/me/kode-pemulihan` | Buat kode pemulihan baru (kode lama hangus). Dipakai oleh akun yang dibuat sebelum fitur ini ada. |
| GET | `/api/me/pengingat` | Tugas yang perlu diperhatikan saya: tenggat dalam 3 hari atau sudah lewat, di semua acara yang saya ikuti. |
| GET | `/api/orang` | Daftar akun pribadi. Hanya Ketua. |
| POST | `/api/orang` | Buat akun pribadi. Hanya Ketua (sementara; admin terpisah menyusul di Tahap 1b). |
| GET | `/api/pesan` | - |
| POST | `/api/pesan` | - |
| DELETE | `/api/pesan/<pesan_id>` | Tarik pesan yang sudah terkirim. Pesan yang ditarik hilang dari kotak masuk semua penerima. |
| PATCH | `/api/pesan/<pesan_id>` | Pengirim atau Ketua bisa memperbaiki isi atau tingkat pesan yang sudah terkirim. |
| POST | `/api/pesan/<pesan_id>/baca` | - |
| POST | `/api/pesan/otomatis` | Ketua mengirim peringatan ke setiap seksi yang punya tugas lewat deadline. |
| GET | `/api/riwayat` | Apa yang bisa dibatalkan dan diulang oleh user ini di acara itu. |
| POST | `/api/riwayat/batal` | - |
| POST | `/api/riwayat/ulang` | - |
| GET | `/api/seksi/hasil` | Hasil kerja tiap anggota di seksi yang dikoordinasi (atau semua seksi untuk Ketua). |
| GET | `/api/tasks` | - |
| POST | `/api/tasks` | - |
| DELETE | `/api/tasks/<task_id>` | - |
| PATCH | `/api/tasks/<task_id>` | - |
| GET | `/api/tasks/<task_id>/komentar` | - |
| POST | `/api/tasks/<task_id>/komentar` | - |
| POST | `/api/tasks/<task_id>/konfirmasi` | Penerima tugas menerima atau menolak tugas yang dibagikan kepadanya. |
| POST | `/api/tasks/<task_id>/tugaskan` | Ketua atau koordinator seksi membagi tugas ke satu akun user yang terdaftar di acara ini. |
| GET | `/api/tasks/stats` | - |
| GET | `/api/team/stats` | Rekap per divisi untuk monitoring organizer. Sie hanya melihat rekap seksinya sendiri. |
