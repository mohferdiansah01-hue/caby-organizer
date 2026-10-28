from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


def migrate_add_columns():
    """Tambahkan kolom baru ke tabel tasks jika belum ada (SQLite lightweight migration)."""
    new_cols = {
        "divisi": "VARCHAR(64) DEFAULT ''",
        "pic": "VARCHAR(128) DEFAULT ''",
        "progress": "INTEGER DEFAULT 0",
        "hasil_url": "VARCHAR(512)",
        "hasil_catatan": "TEXT",
        "hasil_dikirim_pada": "DATETIME",
        "event_id": "VARCHAR(36)",
        "anggota_id": "VARCHAR(36)",
        "penerima_orang_id": "VARCHAR(36)",
        "penerima_ditugaskan_pada": "DATETIME",
        "konfirmasi": "VARCHAR(16)",
        "konfirmasi_alasan": "TEXT",
        "konfirmasi_pada": "DATETIME",
    }
    engine = db.engine
    with engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(tasks)").fetchall()]
        for col, ddl in new_cols.items():
            if col not in existing:
                conn.exec_driver_sql(f"ALTER TABLE tasks ADD COLUMN {col} {ddl}")
        conn.commit()


def migrate_event_pembuat_columns():
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(events)").fetchall()]
        if existing and "pembuat_id" not in existing:
            conn.exec_driver_sql("ALTER TABLE events ADD COLUMN pembuat_id VARCHAR(36)")
        if existing and "password_hash" not in existing:
            conn.exec_driver_sql("ALTER TABLE events ADD COLUMN password_hash VARCHAR(255)")
        conn.commit()


def migrate_event_columns():
    """Tambahkan kolom baru ke tabel events jika database lama belum punya kolom itu."""
    new_cols = {"dampak_json": "TEXT DEFAULT '{}'", "struktur_json": "TEXT DEFAULT '[]'"}
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(events)").fetchall()]
        for col, ddl in new_cols.items():
            if existing and col not in existing:
                conn.exec_driver_sql(f"ALTER TABLE events ADD COLUMN {col} {ddl}")
        conn.commit()


def migrate_audit_columns():
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(audit_log)").fetchall()]
        if existing and "perubahan" not in existing:
            conn.exec_driver_sql("ALTER TABLE audit_log ADD COLUMN perubahan TEXT")
        conn.commit()


def migrate_pesan_columns():
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(pesan)").fetchall()]
        if existing and "pengirim" not in existing:
            conn.exec_driver_sql("ALTER TABLE pesan ADD COLUMN pengirim VARCHAR(128)")
        conn.commit()


def migrate_lampiran_pengunggah():
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(lampiran)").fetchall()]
        if existing and "pengunggah_id" not in existing:
            conn.exec_driver_sql("ALTER TABLE lampiran ADD COLUMN pengunggah_id VARCHAR(36)")
        conn.commit()


def migrate_pemulihan_columns():
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(orang)").fetchall()]
        if existing and "kode_pemulihan_hash" not in existing:
            conn.exec_driver_sql("ALTER TABLE orang ADD COLUMN kode_pemulihan_hash VARCHAR(255)")
        conn.commit()


def migrate_peran_columns():
    """Penugasan lama dianggap sudah disetujui."""
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(peran_acara)").fetchall()]
        if existing and "disetujui" not in existing:
            conn.exec_driver_sql("ALTER TABLE peran_acara ADD COLUMN disetujui BOOLEAN NOT NULL DEFAULT 1")
        conn.commit()


def migrate_anggota_columns():
    """Masa berlaku token anggota. Anggota lama tanpa tanggal dianggap tidak punya batas."""
    with db.engine.connect() as conn:
        existing = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(anggota)").fetchall()]
        if existing and "kedaluwarsa_pada" not in existing:
            conn.exec_driver_sql("ALTER TABLE anggota ADD COLUMN kedaluwarsa_pada DATETIME")
        conn.commit()




class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    judul = db.Column(db.String(255), nullable=False)
    deskripsi = db.Column(db.Text, default="")
    deadline_iso = db.Column(db.String(32), nullable=True)
    prioritas = db.Column(db.String(16), default="sedang")
    status = db.Column(db.String(16), default="pending")
    reminder_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # --- Fields organisasi / event organizer ---
    divisi = db.Column(db.String(64), default="")          # divisi / seksi kepanitiaan
    pic = db.Column(db.String(128), default="")            # penanggung jawab
    progress = db.Column(db.Integer, default=0)            # 0-100
    hasil_url = db.Column(db.String(512), nullable=True)   # tautan hasil kerja tim
    hasil_catatan = db.Column(db.Text, nullable=True)      # catatan penyerahan hasil
    hasil_dikirim_pada = db.Column(db.DateTime, nullable=True)
    event_id = db.Column(db.String(36), nullable=True, index=True)  # acara tempat tugas ini berada
    anggota_id = db.Column(db.String(36), nullable=True, index=True)  # anggota yang ditugaskan (kosong = seluruh seksi)
    # Penerima tugas (akun user) dan konfirmasinya. konfirmasi: None (belum), "diterima", "ditolak".
    penerima_orang_id = db.Column(db.String(36), nullable=True, index=True)
    penerima_ditugaskan_pada = db.Column(db.DateTime, nullable=True)
    konfirmasi = db.Column(db.String(16), nullable=True)
    konfirmasi_alasan = db.Column(db.Text, nullable=True)
    konfirmasi_pada = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        now = datetime.utcnow()
        kategori = self.kategori(now)
        return {
            "id": self.id,
            "judul": self.judul,
            "deskripsi": self.deskripsi,
            "deadline_iso": self.deadline_iso,
            "prioritas": self.prioritas,
            "status": self.status,
            "kategori": kategori,
            "reminder_sent": self.reminder_sent,
            "penerima_orang_id": self.penerima_orang_id,
            "konfirmasi": self.konfirmasi,
            "konfirmasi_alasan": self.konfirmasi_alasan,
            "penerima_ditugaskan_pada": self.penerima_ditugaskan_pada.isoformat() if self.penerima_ditugaskan_pada else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "sisa_jam": self.sisa_jam(now),
            "divisi": self.divisi or "",
            "pic": self.pic or "",
            "progress": self.progress if self.progress is not None else 0,
            "hasil_url": self.hasil_url,
            "hasil_catatan": self.hasil_catatan,
            "hasil_dikirim_pada": self.hasil_dikirim_pada.isoformat() if self.hasil_dikirim_pada else None,
            "event_id": self.event_id,
            "anggota_id": self.anggota_id,
        }

    def kategori(self, now):
        if self.status == "done":
            return "selesai"
        if not self.deadline_iso:
            return "belum_dijadwalkan"
        try:
            deadline = datetime.fromisoformat(self.deadline_iso)
        except (ValueError, TypeError):
            return "belum_dijadwalkan"
        delta = (deadline - now).total_seconds() / 3600
        if delta < 0:
            return "overdue"
        if delta < 24:
            return "hari_ini"
        if delta < 168:
            return "minggu_ini"
        return "akan_datang"

    def sisa_jam(self, now):
        if not self.deadline_iso:
            return None
        try:
            deadline = datetime.fromisoformat(self.deadline_iso)
            return round((deadline - now).total_seconds() / 3600, 1)
        except (ValueError, TypeError):
            return None


class Event(db.Model):
    """Satu acara / kegiatan kepanitiaan. Tugas-tugas di dalamnya terhubung lewat Task.event_id."""
    __tablename__ = "events"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama = db.Column(db.String(255), nullable=False)
    tanggal = db.Column(db.String(32), nullable=True)      # tanggal acara, format YYYY-MM-DD
    lokasi = db.Column(db.String(255), default="")
    deskripsi = db.Column(db.Text, default="")
    dampak_json = db.Column(db.Text, default="{}")          # pilihan dampak berkelanjutan (JSON)
    struktur_json = db.Column(db.Text, default="[]")        # struktur kepanitiaan: [{"seksi","pic"}]
    pembuat_id = db.Column(db.String(36), nullable=True)    # user yang membuat acara; otomatis menjadi Ketua acara
    password_hash = db.Column(db.String(255), nullable=True)  # password pendaftaran acara, diatur oleh Ketua
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "nama": self.nama,
            "tanggal": self.tanggal,
            "lokasi": self.lokasi or "",
            "deskripsi": self.deskripsi or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



class Pengaturan(db.Model):
    """Pengaturan tampilan beranda (pasangan kunci dan nilai)."""
    __tablename__ = "pengaturan"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, default="")


class Kabar(db.Model):
    """Kabar kerja dari satu seksi. Yang publik tampil di beranda."""
    __tablename__ = "kabar"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=True, index=True)
    seksi = db.Column(db.String(64), nullable=False)
    isi = db.Column(db.Text, nullable=False)
    publik = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Lampiran(db.Model):
    """File yang diunggah seksi: foto, video, atau dokumen. Disimpan di folder instance/uploads."""
    __tablename__ = "lampiran"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_asli = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(120), nullable=False)
    ukuran = db.Column(db.Integer, default=0)
    berkas = db.Column(db.String(255), nullable=False)          # nama file di disk
    pemilik_seksi = db.Column(db.String(64), nullable=False)
    pengunggah_id = db.Column(db.String(36), nullable=True, index=True)  # akun yang mengunggah (identitas, bukan nama peran)
    task_id = db.Column(db.String(36), nullable=True, index=True)
    kabar_id = db.Column(db.String(36), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Anggota(db.Model):
    """Anggota seksi. Masuk dengan token (bukan password). Peran: koordinator (co) atau anggota."""
    __tablename__ = "anggota"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=False, index=True)
    seksi = db.Column(db.String(64), nullable=False)
    nama = db.Column(db.String(128), nullable=False)
    peran = db.Column(db.String(16), default="anggota")
    token_hash = db.Column(db.String(255), nullable=False)
    kedaluwarsa_pada = db.Column(db.DateTime, nullable=True)  # None berarti tidak ada batas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)




class Pesan(db.Model):
    """Pesan dari Ketua atau koordinator ke anggota. Tingkat: info, pengingat, atau peringatan."""
    __tablename__ = "pesan"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=False, index=True)
    dari = db.Column(db.String(128), nullable=False)
    ke_seksi = db.Column(db.String(64), nullable=True, index=True)      # None berarti semua seksi
    ke_anggota_id = db.Column(db.String(36), nullable=True, index=True)  # None berarti seluruh seksi
    pengirim = db.Column(db.String(128), nullable=True)  # ketua | anggota:<id> | seksi:<nama>
    tingkat = db.Column(db.String(12), default="info")
    isi = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PesanBaca(db.Model):
    """Penanda pesan sudah dibaca oleh pembaca tertentu (id anggota, atau 'seksi:<nama>', atau 'ketua')."""
    __tablename__ = "pesan_baca"

    pesan_id = db.Column(db.String(36), primary_key=True)
    pembaca = db.Column(db.String(128), primary_key=True)


class TaskKomentar(db.Model):
    """Perintah dari Ketua atau komentar dari seksi di sebuah tugas. Ketua tidak mengubah tugas langsung."""
    __tablename__ = "task_komentar"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = db.Column(db.String(36), nullable=False, index=True)
    dari = db.Column(db.String(128), nullable=False)
    jenis = db.Column(db.String(12), default="komentar")  # perintah | komentar
    isi = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    """Catatan aksi tulis (POST, PUT, PATCH, DELETE) yang berhasil. Hanya ditambah, tidak diubah atau dihapus lewat API."""
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    waktu = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    aktor = db.Column(db.String(128), nullable=False)
    peran = db.Column(db.String(32), nullable=False)
    aksi = db.Column(db.String(8), nullable=False)
    rute = db.Column(db.String(255), nullable=False)
    target = db.Column(db.String(36), nullable=True)
    status = db.Column(db.Integer, nullable=False)
    ip = db.Column(db.String(64), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    perubahan = db.Column(db.Text, nullable=True)  # sebelum dan sesudah, hanya untuk field yang berubah




class Orang(db.Model):
    """Akun pribadi per orang (Tahap 1a). Belum dipakai untuk login; itu Tahap 1b."""
    __tablename__ = "orang"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False)
    nama = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    admin = db.Column(db.Boolean, default=False)
    kode_pemulihan_hash = db.Column(db.String(255), nullable=True)  # kode pemulihan sekali pakai, disimpan dalam bentuk hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KuotaAsisten(db.Model):
    """Jumlah pertanyaan Capy per acara per hari. Dipakai sebagai batas pemakaian, bukan biaya."""
    __tablename__ = "kuota_asisten"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kunci = db.Column(db.String(80), index=True, nullable=False)  # event_id atau orang:<id>
    tanggal = db.Column(db.String(10), nullable=False)            # YYYY-MM-DD (UTC)
    jumlah = db.Column(db.Integer, default=0, nullable=False)


class PeranAcara(db.Model):
    """Penugasan peran seseorang di satu acara."""
    __tablename__ = "peran_acara"
    __table_args__ = (db.UniqueConstraint("event_id", "orang_id", name="uq_peran_event_orang"),)
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=False, index=True)
    orang_id = db.Column(db.String(36), nullable=False, index=True)
    peran = db.Column(db.String(16), nullable=False)
    seksi = db.Column(db.String(64), nullable=True)
    # Pendaftaran mandiri mulai dari False; Ketua menyetujui sebelum akun bisa masuk ke acara.
    disetujui = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RiwayatAksi(db.Model):
    """Catatan perubahan yang bisa dibatalkan/diulang. before/after berisi keadaan baris sebelum dan sesudah."""
    __tablename__ = "riwayat_aksi"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.String(36), index=True, nullable=False)
    orang_id = db.Column(db.String(36), index=True, nullable=True)
    label = db.Column(db.String(255), nullable=False)
    before = db.Column(db.Text, nullable=False)
    after = db.Column(db.Text, nullable=False)
    undone = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatAsisten(db.Model):
    """Riwayat percakapan Capy. Terpisah per orang dan per acara (kunci = event_id, atau 'umum')."""
    __tablename__ = "chat_asisten"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    orang_id = db.Column(db.String(36), index=True, nullable=False)
    kunci = db.Column(db.String(40), index=True, nullable=False)
    peran = db.Column(db.String(10), nullable=False)  # user | capy
    isi = db.Column(db.Text, nullable=False)
    aksi = db.Column(db.Text, nullable=True)           # JSON: usulan/navigasi yang ditampilkan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EventArsip(db.Model):
    """Acara yang sudah ditutup. Selama ada baris di sini, acara tidak bisa diubah peran-nya."""
    __tablename__ = "event_arsip"
    event_id = db.Column(db.String(36), primary_key=True)
    ditutup_pada = db.Column(db.DateTime, default=datetime.utcnow)


class TugasDefault(db.Model):
    """Tugas default per seksi. Dipakai untuk mengisi atau mengembalikan tugas seksi di sebuah acara."""
    __tablename__ = "tugas_default"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seksi = db.Column(db.String(64), nullable=False, index=True)
    judul = db.Column(db.String(255), nullable=False)
    deskripsi = db.Column(db.Text, default="")
    urutan = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)










class KeputusanAcara(db.Model):
    """Keputusan acara: diajukan, revisi, disetujui, ditolak, atau digantikan keputusan baru."""
    __tablename__ = "keputusan_acara"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=False, index=True)
    judul = db.Column(db.String(255), nullable=False)
    isi = db.Column(db.Text, default="")
    status = db.Column(db.String(12), default="diajukan")
    induk_id = db.Column(db.String(36), nullable=True, index=True)  # keputusan yang digantikan
    penulis_kunci = db.Column(db.String(128), nullable=False)
    penulis_nama = db.Column(db.String(128), default="")
    catatan = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)




















class Notulen(db.Model):
    """Notulen rapat. Hanya Sekretaris yang mencatat."""
    __tablename__ = "notulen"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=False, index=True)
    judul = db.Column(db.String(255), nullable=False)
    tanggal = db.Column(db.String(10), default="")
    isi = db.Column(db.Text, default="")
    dicatat_oleh = db.Column(db.String(128), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)









