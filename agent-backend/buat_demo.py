from datetime import date, datetime, timedelta
import json
import os

from werkzeug.security import generate_password_hash

import peran
from app import PRODUKSI, app, db
from database import Event, Kabar, KeputusanAcara, Orang, PeranAcara, Pesan, Task, TaskKomentar

EVENT_NAME = "Gebyar HUT Organisasi 2027 (Demo Juri)"
USER_PASSWORD = "GebyarJuri2027!"
ADMIN_PASSWORD = "AdminJuri2027!"
EVENT_PASSWORD = "GebyarGabung2027!"

ACCOUNTS = (
    ("juri.ketua", "Nabila Putri", USER_PASSWORD, False),
    ("juri.acara", "Raka Mahendra", USER_PASSWORD, False),
    ("juri.pdd", "Sinta Laras", USER_PASSWORD, False),
    ("juri.humas", "Dimas Pratama", USER_PASSWORD, False),
    ("juri.konsumsi", "Maya Syah", USER_PASSWORD, False),
    ("juri.anggota", "Fajar Ramadhan", USER_PASSWORD, False),
    ("juri.admin", "Admin Demo Juri", ADMIN_PASSWORD, True),
)

PENUGASAN = {
    "juri.ketua": ("ketua", None),
    "juri.acara": ("koordinator", "Acara"),
    "juri.pdd": ("koordinator", "PDD"),
    "juri.humas": ("koordinator", "Humas"),
    "juri.konsumsi": ("koordinator", "Konsumsi"),
    "juri.anggota": ("anggota", "Sekretariatan"),
}

PICS = {
    "Acara": "Raka Mahendra",
    "PDD": "Sinta Laras",
    "Perkab": "Rafi Pranata",
    "Konsumsi": "Maya Syah",
    "Humas": "Dimas Pratama",
    "Keamanan": "Bima Saputra",
    "Sponsorship": "Nadia Putri",
    "Bendahara": "Putri Ananda",
    "Sekretaris": "Nabila Putri",
    "Sekretariatan": "Fajar Ramadhan",
}

TUGAS = (
    ("Acara", "Tetapkan tema, target peserta, dan format Gebyar", 125, "done", "tinggi", "Raka Mahendra"),
    ("Acara", "Susun rundown utama dan kebutuhan pengisi acara", 45, "pending", "tinggi", "Raka Mahendra"),
    ("Acara", "Simulasi teknis dan gladi bersih", 7, "pending", "tinggi", "Raka Mahendra"),
    ("PDD", "Finalisasi identitas visual dan panduan desain", 115, "done", "sedang", "Sinta Laras"),
    ("PDD", "Produksi poster, teaser, dan materi publikasi", 48, "pending", "tinggi", "Sinta Laras"),
    ("PDD", "Siapkan backdrop, photobooth, dan layar acara", 14, "pending", "sedang", "Sinta Laras"),
    ("Perkab", "Inventaris perlengkapan panggung dan ruangan", 68, "pending", "sedang", "Rafi Pranata"),
    ("Perkab", "Uji tata suara, pencahayaan, dan proyektor", 14, "pending", "tinggi", "Rafi Pranata"),
    ("Perkab", "Final cek dan serah-terima perlengkapan", 2, "pending", "tinggi", "Rafi Pranata"),
    ("Konsumsi", "Survei vendor dan opsi menu", 82, "done", "sedang", "Maya Syah"),
    ("Konsumsi", "Konfirmasi jumlah konsumsi panitia dan tamu", 14, "pending", "tinggi", "Maya Syah"),
    ("Konsumsi", "Distribusi konsumsi di hari acara", 1, "pending", "sedang", "Maya Syah"),
    ("Humas", "Susun narasi, kanal publikasi, dan timeline konten", 108, "done", "sedang", "Dimas Pratama"),
    ("Humas", "Buka registrasi dan pantau jumlah pendaftar", 50, "pending", "tinggi", "Dimas Pratama"),
    ("Humas", "Kirim reminder dan info teknis peserta", 7, "pending", "sedang", "Dimas Pratama"),
    ("Keamanan", "Pemetaan risiko, titik kumpul, dan rute evakuasi", 75, "pending", "tinggi", "Bima Saputra"),
    ("Keamanan", "Koordinasi izin lokasi dan kebutuhan pengamanan", 45, "pending", "sedang", "Bima Saputra"),
    ("Keamanan", "Briefing petugas dan pengaturan pintu masuk", 1, "pending", "tinggi", "Bima Saputra"),
    ("Sponsorship", "Susun paket sponsor dan daftar calon mitra", 120, "done", "tinggi", "Nadia Putri"),
    ("Sponsorship", "Kirim proposal dan tindak lanjuti calon sponsor", 78, "pending", "tinggi", "Nadia Putri"),
    ("Sponsorship", "Finalisasi logo sponsor dan booth", 20, "pending", "sedang", "Nadia Putri"),
    ("Bendahara", "Susun RAB dan batas pengeluaran tiap seksi", 125, "done", "tinggi", "Putri Ananda"),
    ("Bendahara", "Rekap pemasukan sponsor dan bukti transaksi", 30, "pending", "sedang", "Putri Ananda"),
    ("Bendahara", "Rekonsiliasi kas dan laporan akhir acara", 1, "pending", "sedang", "Putri Ananda"),
    ("Sekretaris", "Buat proposal resmi dan surat permohonan izin", 118, "done", "tinggi", "Nabila Putri"),
    ("Sekretaris", "Catat rapat koordinasi bulanan", 60, "pending", "sedang", "Nabila Putri"),
    ("Sekretaris", "Susun berita acara dan laporan pertanggungjawaban", 0, "pending", "sedang", "Nabila Putri"),
    ("Sekretariatan", "Buka registrasi panitia dan daftar kehadiran", 86, "pending", "sedang", "Fajar Ramadhan"),
    ("Sekretariatan", "Siapkan daftar tamu, sertifikat, dan meja registrasi", 14, "pending", "sedang", "Fajar Ramadhan"),
    ("Sekretariatan", "Rekap kehadiran peserta dan arsip dokumen", 0, "pending", "sedang", "Fajar Ramadhan"),
)

KABAR = (
    ("Acara", "Rapat kick-off menetapkan format Gebyar, sasaran 500 peserta, dan tiga rangkaian acara."),
    ("Humas", "Identitas visual sudah disepakati. Kalender teaser dan pembukaan registrasi sedang disiapkan."),
    ("Sponsorship", "Paket sponsor tersedia dalam tiga pilihan. Tim mulai menghubungi calon mitra."),
    ("Konsumsi", "Tiga vendor masuk pembandingan harga dan opsi konsumsi ramah lingkungan."),
)

KEPUTUSAN = (
    ("Tema dan format acara", "Gebyar dilaksanakan sebagai perayaan ulang tahun organisasi dengan panggung utama, pameran karya, dan malam apresiasi.", "disetujui"),
    ("Target dan kapasitas peserta", "Target awal 500 peserta; kapasitas final mengikuti persetujuan pengelola lokasi.", "disetujui"),
    ("Opsi lokasi cadangan", "Tim sedang membandingkan aula kampus dan gedung serbaguna sebagai lokasi cadangan.", "diajukan"),
)

PESAN = (
    (None, "INFO", "Seluruh koordinator: perbarui progres dan risiko seksi sebelum rapat evaluasi bulanan."),
    ("Acara", "pengingat", "Koordinator Acara, mohon unggah rundown versi terbaru sebelum rapat berikutnya."),
)


def _upsert_account(username, nama, password, admin):
    account = Orang.query.filter_by(username=username).first()
    if account is None:
        account = Orang(username=username, nama=nama, password_hash=generate_password_hash(password), admin=admin)
        db.session.add(account)
    else:
        account.nama = nama
        account.password_hash = generate_password_hash(password)
        account.admin = admin
    return account


def seed_demo():
    if PRODUKSI and os.environ.get("CAPY_DEMO_SEED") != "1":
        raise RuntimeError("Seed demo produksi harus diaktifkan secara eksplisit dengan CAPY_DEMO_SEED=1.")

    with app.app_context():
        accounts = {username: _upsert_account(username, nama, password, admin)
                    for username, nama, password, admin in ACCOUNTS}
        db.session.flush()
        ketua = accounts["juri.ketua"]

        event = Event.query.filter_by(nama=EVENT_NAME).first()
        if event is not None and event.pembuat_id != ketua.id:
            raise RuntimeError(f"Acara bernama {EVENT_NAME!r} sudah ada dan bukan milik akun demo.")
        if event is None:
            event = Event(nama=EVENT_NAME, pembuat_id=ketua.id)
            db.session.add(event)

        tanggal_acara = date.today() + timedelta(days=135)
        event.tanggal = tanggal_acara.isoformat()
        event.lokasi = "Auditorium Kampus dan pelataran utama"
        event.deskripsi = (
            "Perayaan ulang tahun organisasi dengan target 500 peserta. Persiapan berlangsung sekitar "
            "4,5 bulan: perencanaan, kemitraan, publikasi dan registrasi, pemantapan teknis, lalu evaluasi."
        )
        event.password_hash = generate_password_hash(EVENT_PASSWORD)
        event.struktur_json = json.dumps(
            [{"seksi": section, "pic": PICS[section]} for section in peran.SEKSI],
            ensure_ascii=False,
        )
        db.session.flush()

        for username, (role, section) in PENUGASAN.items():
            assignment = PeranAcara.query.filter_by(event_id=event.id, orang_id=accounts[username].id).first()
            if assignment is None:
                assignment = PeranAcara(event_id=event.id, orang_id=accounts[username].id)
                db.session.add(assignment)
            assignment.peran = role
            assignment.seksi = section
            assignment.disetujui = True

        sekarang = datetime.utcnow()
        tasks = {}
        for section, title, days_before, status, priority, pic in TUGAS:
            task = Task.query.filter_by(event_id=event.id, judul=title).first()
            if task is None:
                task = Task(event_id=event.id, judul=title)
                db.session.add(task)
            task.divisi = section
            task.deskripsi = f"Rencana kerja {section} untuk persiapan Gebyar HUT Organisasi."
            task.deadline_iso = (tanggal_acara - timedelta(days=days_before)).strftime("%Y-%m-%dT17:00")
            task.prioritas = priority
            task.status = status
            task.pic = pic
            task.progress = 100 if status == "done" else (65 if days_before == 45 else 50 if days_before in (48, 50) else 25 if days_before == 14 else 0)
            task.completed_at = sekarang - timedelta(days=2) if status == "done" else None
            task.hasil_catatan = "Contoh hasil demo: dokumen kerja tersimpan dan siap ditinjau." if status == "done" else None
            tasks[title] = task

        db.session.flush()
        assigned_task = tasks["Buka registrasi panitia dan daftar kehadiran"]
        assigned_task.penerima_orang_id = accounts["juri.anggota"].id
        assigned_task.penerima_ditugaskan_pada = sekarang
        assigned_task.konfirmasi = None

        for section, text in KABAR:
            update = Kabar.query.filter_by(event_id=event.id, seksi=section, isi=text).first()
            if update is None:
                db.session.add(Kabar(event_id=event.id, seksi=section, isi=text, publik=True))

        for title, text, status in KEPUTUSAN:
            decision = KeputusanAcara.query.filter_by(event_id=event.id, judul=title).first()
            if decision is None:
                decision = KeputusanAcara(event_id=event.id, judul=title)
                db.session.add(decision)
            decision.isi = text
            decision.status = status
            decision.penulis_kunci = f"orang:{ketua.id}"
            decision.penulis_nama = ketua.nama
            decision.catatan = "Data contoh untuk penilaian; diskusikan sebelum diterapkan pada acara nyata."

        for section, level, text in PESAN:
            message = Pesan.query.filter_by(event_id=event.id, isi=text).first()
            if message is None:
                message = Pesan(event_id=event.id, isi=text)
                db.session.add(message)
            message.dari = ketua.nama
            message.ke_seksi = section
            message.ke_anggota_id = None
            message.pengirim = "ketua"
            message.tingkat = level.lower()

        komentar = (
            ("Susun rundown utama dan kebutuhan pengisi acara", "Mohon tambahkan estimasi durasi dan PIC tiap segmen."),
            ("Buka registrasi panitia dan daftar kehadiran", "Daftar panitia sudah dibuka; cek format nama sebelum dibagikan."),
        )
        for title, text in komentar:
            task = tasks[title]
            existing = TaskKomentar.query.filter_by(task_id=task.id, isi=text).first()
            if existing is None:
                db.session.add(TaskKomentar(task_id=task.id, dari=ketua.nama, jenis="komentar", isi=text))

        db.session.commit()
        return event.id, tanggal_acara.isoformat(), len(TUGAS)


def main():
    try:
        event_id, tanggal, jumlah_tugas = seed_demo()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Demo juri siap: {EVENT_NAME} ({tanggal}, sekitar 135 hari dari sekarang).")
    print(f"Acara ID: {event_id}; tugas contoh: {jumlah_tugas}; seksi: {len(peran.SEKSI)}.")
    print("Akun panitia: juri.ketua, juri.acara, juri.pdd, juri.humas, juri.konsumsi, juri.anggota")
    print(f"Password semua akun panitia: {USER_PASSWORD}")
    print(f"Admin: juri.admin / {ADMIN_PASSWORD}")
    print(f"Password pendaftaran acara: {EVENT_PASSWORD}")


if __name__ == "__main__":
    main()
