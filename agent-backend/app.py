import json
import os
import re
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, session, Response, send_from_directory, g
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
import secrets
import time
import uuid
import requests
from functools import wraps
import peran as aturan_peran
from database import db, ChatAsisten, RiwayatAksi, EventArsip, KeputusanAcara, Orang, PeranAcara, TugasDefault, Task, Event, Pengaturan, Kabar, Lampiran, Pesan, PesanBaca, TaskKomentar, AuditLog, migrate_add_columns, migrate_event_columns, migrate_anggota_columns, migrate_pesan_columns, migrate_audit_columns, migrate_peran_columns, migrate_event_pembuat_columns, migrate_pemulihan_columns, migrate_lampiran_pengunggah, KuotaAsisten

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
load_dotenv(os.path.join(os.path.dirname(_BACKEND_DIR), ".env"))  # fallback konfigurasi lokal di folder utama

app = Flask(__name__)

# --- Konfigurasi dari environment (lihat .env.example) ---
PRODUKSI = os.environ.get("CAPY_PRODUKSI", "0") == "1"
if PRODUKSI and not os.environ.get("SECRET_KEY"):
    raise SystemExit("CAPY_PRODUKSI=1 tetapi SECRET_KEY kosong. Isi SECRET_KEY di .env sebelum menjalankan produksi.")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///capy.db")
# SQLite: mode WAL membuat pembacaan tidak menunggu penulisan, dan batas tunggu mencegah "database is locked" saat ramai.
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
    from sqlalchemy import event as _sa_event
    from sqlalchemy.engine import Engine as _SAEngine

    @_sa_event.listens_for(_SAEngine, "connect")
    def _sqlite_pragma(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_NAME"] = "capy_session"
# Di belakang reverse proxy, alamat klien ada di X-Forwarded-For. Aktifkan hanya jika proxy memang dipasang.
if os.environ.get("TRUST_PROXY", "0") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


@app.after_request
def _header_keamanan(res):
    res.headers.setdefault("X-Content-Type-Options", "nosniff")
    res.headers.setdefault("X-Frame-Options", "DENY")
    res.headers.setdefault("Referrer-Policy", "same-origin")
    return res


app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "1" if PRODUKSI else "0") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # unggahan file maksimal 30 MB
JSON_MAX_BYTES = 256 * 1024  # data JSON biasa maksimal 256 KB
UPLOAD_DIR = os.path.join(app.instance_path, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

CORS(app, origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
     supports_credentials=True)
db.init_app(app)

with app.app_context():
    db.create_all()
    migrate_add_columns()
    migrate_event_columns()
    migrate_anggota_columns()
    migrate_pesan_columns()
    migrate_audit_columns()
    migrate_peran_columns()
    migrate_event_pembuat_columns()
    migrate_pemulihan_columns()
    migrate_lampiran_pengunggah()


def _admin_awal_jika_belum_ada():
    """Saat pertama jalan, jika belum ada admin dan ADMIN_AWAL_USERNAME + ADMIN_AWAL_PASSWORD diisi,
    akun admin dibuat otomatis. Tidak mengubah apa pun jika admin sudah ada."""
    user = (os.environ.get("ADMIN_AWAL_USERNAME") or "").strip()
    pw = os.environ.get("ADMIN_AWAL_PASSWORD") or ""
    if not user or len(pw) < 8:
        return None
    if Orang.query.filter_by(admin=True).first():
        if os.environ.get("ADMIN_AWAL_PASSWORD"):
            print("[PERINGATAN] ADMIN_AWAL_PASSWORD masih ada di .env padahal admin sudah dibuat. Hapus baris itu.")
        return None
    o = Orang.query.filter(db.func.lower(Orang.username) == user.lower()).first()
    if o is None:
        o = Orang(username=user, nama=user, password_hash=generate_password_hash(pw), admin=True)
        db.session.add(o)
    else:
        o.admin = True
    db.session.commit()
    print(f"[INFO] Admin awal dibuat: {o.username}. Hapus ADMIN_AWAL_PASSWORD dari .env setelah ini.")
    return o.username


with app.app_context():
    _admin_awal_jika_belum_ada()

if not os.environ.get("SECRET_KEY"):
    print("[PERINGATAN] SECRET_KEY belum diatur. Sesi login akan hilang setiap server di-restart.")



PUBLIC_PATHS = {"/", "/health", "/api/auth/login", "/api/auth/logout", "/api/auth/me", "/api/auth/events", "/api/auth/daftar", "/api/auth/lupa-password", "/api/beranda"}
LOGIN_MAX_FAILS = 5
LOGIN_WINDOW_SECONDS = 300
_login_fails = {}  # ip -> [waktu_gagal, ...]


def _too_many_fails(ip):
    now = time.time()
    recent = [t for t in _login_fails.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]
    _login_fails[ip] = recent
    return len(recent) >= LOGIN_MAX_FAILS


def current_role():
    return session.get("role")


def is_ketua():
    """Ketua berlaku per acara: peran 'ketua' di acara yang sedang dimasuki."""
    return session.get("peran") == "ketua" and bool(session.get("event_id"))


def _seksi_boleh_kelola(divisi):
    """Koordinator (termasuk akun seksi lama) mengelola tugas seksinya sendiri, bukan seksi lain."""
    return session.get("peran") == "koordinator" and role_owns(divisi)


def bisa_lihat_semua():
    """Ketua dan Wakil Ketua boleh membaca semua tugas acara. Penulisan tetap memakai is_ketua()."""
    return is_ketua() or session.get("peran") == "wakil_ketua"


def role_owns(divisi):
    """True jika tugas dengan seksi ini milik sie yang sedang login."""
    return (divisi or "").strip().lower() == (current_role() or "").lower()


def visible_tasks_query(event_id=None):
    """Tugas dibatasi ke satu acara: acara yang diminta, atau acara di sesi. Ketua tanpa acara melihat semua.
    Pengguna tidak melihat acara tempat ia tidak bekerja."""
    q = Task.query
    ev = event_id or session.get("event_id")
    if event_id and not _di_acara(event_id):
        return q.filter(Task.id.is_(None))
    if ev:
        q = q.filter_by(event_id=ev)
    elif not is_ketua():
        return q.filter(Task.id.is_(None))
    peran_ev = _peran_di(ev) if ev else None
    if peran_ev not in ("ketua", "wakil_ketua"):
        # Tugas seksi sendiri, atau tugas yang dibagikan langsung kepada orang ini.
        q = q.filter(db.or_(db.func.lower(Task.divisi) == (current_role() or "").lower(),
                            Task.penerima_orang_id == session.get("orang_id")))
    return q


def ketua_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        eid = kwargs.get("event_id")
        if eid is not None:
            ok = _ketua_acara(eid)  # endpoint acara: Ketua harus memimpin acara di jalur ini
        else:
            ok = is_ketua()
        if not ok:
            return jsonify({"error": "Hanya Ketua Pelaksana yang dapat melakukan ini."}), 403
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# ============================================================




@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    filter_kategori = request.args.get("kategori", "semua")
    tasks = visible_tasks_query(request.args.get("event_id") or None).order_by(Task.created_at.desc()).all()
    result = [t.to_dict() for t in tasks]
    if filter_kategori != "semua":
        result = [t for t in result if t["kategori"] == filter_kategori]
    return jsonify({"tasks": result, "total": len(result)})


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    event_id = str(data.get("event_id") or "").strip()
    if not db.session.get(Event, event_id):
        return jsonify({"error": "Pilih acara dulu."}), 400
    peran_saya = _peran_di(event_id)
    if peran_saya not in ("ketua", "koordinator"):
        return jsonify({"error": "Hanya Ketua atau koordinator seksi di acara ini yang bisa membuat tugas."}), 403
    if peran_saya != "ketua" and _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    try:
        judul = clean_text(data.get("judul"), 255, "Judul", required=True)
        deskripsi = clean_text(data.get("deskripsi"), 5000, "Deskripsi")
        divisi = clean_text(data.get("divisi"), 64, "Seksi")
        pic = clean_text(data.get("pic"), 128, "PIC")
        deadline_iso = clean_deadline(data.get("deadline_iso"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not is_ketua():
        divisi = current_role()  # koordinator hanya bisa membuat tugas untuk seksinya sendiri
    prioritas = str(data.get("prioritas", "sedang")).lower()
    task = Task(
        judul=judul,
        deskripsi=deskripsi,
        deadline_iso=deadline_iso,
        prioritas=prioritas if prioritas in PRIORITAS_VALID else "sedang",
        divisi=divisi,
        pic=pic,
        status="pending",
        event_id=event_id,
    )
    db.session.add(task)
    db.session.flush()
    _riwayat_simpan(event_id, f'Tambah tugas "{task.judul}"', _keadaan_kosong(event_id, "task", task.id),
                    _ambil_keadaan(event_id, [("task", task.id)]))
    db.session.commit()
    return jsonify(task.to_dict()), 201








@app.route("/api/events/<event_id>/seksi/<seksi>/pakai-default", methods=["POST"])
def pakai_default_seksi(event_id, seksi):
    """Ganti tugas seksi di acara ini dengan tugas default. Menghapus tugas yang sudah ada, jadi wajib konfirmasi."""
    if seksi not in aturan_peran.SEKSI:
        return jsonify({"error": "Seksi tidak dikenal."}), 400
    if not db.session.get(Event, event_id):
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    _b = PeranAcara.query.filter_by(event_id=event_id, orang_id=session.get("orang_id")).first()
    if not _b or not (_b.peran == "ketua" or (_b.peran == "koordinator" and _b.seksi == seksi)):
        return jsonify({"error": "Tugas ini bukan milik seksimu."}), 403
    if _b.peran != "ketua" and _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    data = request.get_json(silent=True) or {}
    if data.get("konfirmasi") is not True:
        return jsonify({"error": "Tugas seksi di acara ini akan diganti dengan default dan tugas yang sudah ada dihapus. Kirim konfirmasi: true."}), 400
    dihapus = Task.query.filter_by(event_id=event_id).filter(
        db.func.lower(Task.divisi) == seksi.lower()).delete(synchronize_session=False)
    defaults = TugasDefault.query.filter_by(seksi=seksi).order_by(TugasDefault.urutan, TugasDefault.created_at).all()
    for d in defaults:
        db.session.add(Task(judul=d.judul, deskripsi=d.deskripsi or "", divisi=seksi, event_id=event_id,
                            status="pending", prioritas="sedang"))
    db.session.commit()
    return jsonify({"dihapus": dihapus, "dibuat": len(defaults)})


@app.route("/api/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    if not _di_acara(task.event_id):
        return jsonify({"error": "Tugas ini bukan milik acara yang kamu ikuti."}), 403
    _bidang_tugas = ("judul", "status", "progress", "deadline_iso", "pic", "divisi", "anggota_id", "hasil_url", "hasil_catatan")
    _sebelum_tugas = {k: getattr(task, k) for k in _bidang_tugas}
    _sebelum_riwayat = _ambil_keadaan(task.event_id, [("task", task.id)])
    data = request.get_json(silent=True) or {}
    if _peran_di(task.event_id) == "ketua":
        return jsonify({"error": "Ketua memantau dan memberi perintah lewat komentar. Isi tugas diubah oleh seksinya."}), 403
    if True:
        if not role_owns(task.divisi):
            return jsonify({"error": "Tugas ini bukan milik seksimu."}), 403
        if session.get("peran") == "anggota" and task.anggota_id not in (None, session.get("anggota_id")):
            return jsonify({"error": "Tugas ini dibagikan ke anggota lain."}), 403
        if task.event_id and _acara_tertutup(task.event_id):
            return jsonify({"error": "Acara sudah ditutup."}), 409
        sie_fields = {"status", "progress", "hasil_url", "hasil_catatan"}
        if session.get("peran") == "koordinator":
            sie_fields = sie_fields | {"judul", "deskripsi", "deadline_iso", "prioritas", "pic"}
        if set(data.keys()) - sie_fields:
            return jsonify({"error": "Kamu tidak bisa mengubah bagian itu. Seksi hanya mengubah isi tugasnya sendiri."}), 403
    if "status" in data:
        task.status = data["status"]
        if data["status"] == "done":
            task.completed_at = datetime.utcnow()
            task.progress = 100
        else:
            task.completed_at = None
    for field in ("judul", "deadline_iso", "prioritas", "divisi", "pic", "deskripsi"):
        if field in data:
            setattr(task, field, data[field])
    if "progress" in data:
        task.progress = max(0, min(100, int(data["progress"])))
    if "hasil_url" in data or "hasil_catatan" in data:
        task.hasil_url = data.get("hasil_url") or None
        task.hasil_catatan = data.get("hasil_catatan") or None
        task.hasil_dikirim_pada = datetime.utcnow()
        task.progress = 100
    catat_perubahan(_sebelum_tugas, {k: getattr(task, k) for k in _bidang_tugas})
    _riwayat_simpan(task.event_id, f'Ubah tugas "{task.judul}"', _sebelum_riwayat, _ambil_keadaan(task.event_id, [("task", task.id)]))
    db.session.commit()
    return jsonify(task.to_dict())


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    if not _di_acara(task.event_id):
        return jsonify({"error": "Tugas ini bukan milik acara yang kamu ikuti."}), 403
    if not (_peran_di(task.event_id) == "ketua" or _seksi_di(task.event_id, task.divisi)):
        return jsonify({"error": "Tugas ini bukan milik seksimu."}), 403
    if _peran_di(task.event_id) != "ketua" and task.event_id and _acara_tertutup(task.event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    _sebelum_hapus = _ambil_keadaan(task.event_id, [("task", task.id)])
    _eid_hapus, _judul_hapus = task.event_id, task.judul
    db.session.delete(task)
    _riwayat_simpan(_eid_hapus, f'Hapus tugas "{_judul_hapus}"', _sebelum_hapus, _keadaan_kosong(_eid_hapus, "task", task.id))
    db.session.commit()
    return jsonify({"success": True})




@app.route("/api/tasks/stats", methods=["GET"])
def task_stats():
    tasks = visible_tasks_query().all()
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == "done")
    overdue = sum(1 for t in tasks if t.to_dict()["kategori"] == "overdue")
    hari_ini = sum(1 for t in tasks if t.to_dict()["kategori"] == "hari_ini")
    return jsonify({
        "total": total,
        "done": done,
        "pending": total - done,
        "overdue": overdue,
        "hari_ini": hari_ini,
        "progress_persen": round((done / total * 100) if total > 0 else 0, 1),
    })


@app.route("/api/team/stats", methods=["GET"])
def team_stats():
    """Rekap per divisi untuk monitoring organizer. Sie hanya melihat rekap seksinya sendiri."""
    tasks = [t.to_dict() for t in visible_tasks_query().all()]
    divisi_map = {}
    for t in tasks:
        d = t["divisi"] or "Tanpa Divisi"
        g = divisi_map.setdefault(d, {
            "divisi": d, "total": 0, "done": 0, "overdue": 0,
            "progress_sum": 0, "hasil": 0, "pics": set(),
        })
        g["total"] += 1
        g["progress_sum"] += t["progress"] if t["status"] != "done" else 100
        if t["status"] == "done":
            g["done"] += 1
        if t["kategori"] == "overdue":
            g["overdue"] += 1
        if t["hasil_url"] or t["hasil_catatan"]:
            g["hasil"] += 1
        if t["pic"]:
            g["pics"].add(t["pic"])
    divisis = []
    for g in divisi_map.values():
        divisis.append({
            "divisi": g["divisi"],
            "total": g["total"],
            "done": g["done"],
            "overdue": g["overdue"],
            "hasil": g["hasil"],
            "avg_progress": round(g["progress_sum"] / g["total"], 1),
            "pics": sorted(g["pics"]),
        })
    divisis.sort(key=lambda x: (-x["total"], x["divisi"]))
    return jsonify({
        "divisi": divisis,
        "total_tugas": len(tasks),
        "total_hasil": sum(1 for t in tasks if t["hasil_url"] or t["hasil_catatan"]),
        "total_pic": len({t["pic"] for t in tasks if t["pic"]}),
    })




# ============================================================
# ============================================================

# Harga per 1 juta token, untuk perkiraan biaya. Kosong = 0, dan endpoint memberi tahu bahwa harga belum diisi.





















PRIORITAS_VALID = {"tinggi", "sedang", "rendah"}


# ============================================================
# ROUTES: EVENT / ACARA
# ============================================================

def event_snapshot(event):
    """Rangkuman sebuah acara: tugas, status per seksi, dan mood Capy."""
    now = datetime.utcnow()
    tasks = [t.to_dict() for t in visible_tasks_query(event.id).order_by(Task.created_at).all()]

    seksi_map = {}
    for t in tasks:
        key = t["divisi"] or "Umum"
        g = seksi_map.setdefault(key, {
            "seksi": key, "total": 0, "done": 0, "overdue": 0, "hari_ini": 0,
            "progress_sum": 0, "pics": set(), "sisa_terdekat": None,
        })
        g["total"] += 1
        if t["status"] == "done":
            g["done"] += 1
            g["progress_sum"] += 100
        else:
            g["progress_sum"] += t["progress"] or 0
            if t["sisa_jam"] is not None:
                if g["sisa_terdekat"] is None or t["sisa_jam"] < g["sisa_terdekat"]:
                    g["sisa_terdekat"] = t["sisa_jam"]
        if t["kategori"] == "overdue":
            g["overdue"] += 1
        if t["kategori"] == "hari_ini":
            g["hari_ini"] += 1
        if t["pic"]:
            g["pics"].add(t["pic"])

    seksi_list = []
    for g in seksi_map.values():
        avg = round(g["progress_sum"] / g["total"], 1) if g["total"] else 0
        if g["total"] and g["done"] == g["total"]:
            status = "selesai"
        elif g["overdue"] > 0:
            status = "terlambat"
        elif g["sisa_terdekat"] is not None and g["sisa_terdekat"] <= 72 and avg < 80:
            status = "perhatian"
        else:
            status = "berjalan"
        seksi_list.append({
            "seksi": g["seksi"],
            "total": g["total"],
            "done": g["done"],
            "overdue": g["overdue"],
            "hari_ini": g["hari_ini"],
            "avg_progress": avg,
            "pics": sorted(g["pics"]),
            "sisa_terdekat_jam": round(g["sisa_terdekat"], 1) if g["sisa_terdekat"] is not None else None,
            "status": status,
        })
    seksi_list.sort(key=lambda s: ({"terlambat": 0, "perhatian": 1, "berjalan": 2, "selesai": 3}[s["status"]], s["seksi"]))

    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "done")
    statuses = {s["status"] for s in seksi_list}
    if total and done == total:
        mood = "excited"
    elif statuses & {"terlambat", "perhatian"}:
        mood = "peek"
    else:
        mood = "idle"

    return {
        "event": event.to_dict(),
        "ringkasan": {
            "total": total,
            "done": done,
            "overdue": sum(1 for t in tasks if t["kategori"] == "overdue"),
            "hari_ini": sum(1 for t in tasks if t["kategori"] == "hari_ini"),
            "progress_persen": round(done / total * 100, 1) if total else 0,
        },
        "seksi": seksi_list,
        "tasks": tasks,
        "capy_mood": mood,
        "dampak": dampak_summary(event),
        "struktur": load_struktur(event),
    }


@app.route("/api/events", methods=["GET"])
def list_events():
    events = Event.query.order_by(Event.created_at.desc()).all()
    result = []
    for e in events:
        tasks = visible_tasks_query(e.id).all()
        item = e.to_dict()
        item["total_tugas"] = len(tasks)
        item["tugas_selesai"] = sum(1 for t in tasks if t.status == "done")
        result.append(item)
    return jsonify({"events": result})


# Template acara: tugas awal per seksi, tenggat dihitung mundur dari tanggal acara.
TEMPLATE_ACARA = {
    "kosong": [],
    "pemilihan": [
        ("Sekretaris", "Surat undangan kandidat dan panitia", 21),
        ("Acara", "Rundown dan susunan kampanye", 14),
        ("Perlengkapan", "Sewa tempat dan perlengkapan TPS", 7),
        ("Konsumsi", "Pesan konsumsi panitia", 3),
        ("Humas", "Publikasi jadwal ke seluruh mahasiswa", 14),
        ("Keamanan", "Rencana keamanan dan jalur evakuasi", 5),
    ],
    "seminar": [
        ("Acara", "Susun rundown dan pembicara", 30),
        ("Humas", "Sebar poster dan undangan", 21),
        ("Perlengkapan", "Sewa ruangan dan proyektor", 10),
        ("Konsumsi", "Pesan snack dan makan siang", 3),
        ("Sekretaris", "Daftar hadir dan sertifikat", 3),
    ],
    "bakti": [
        ("Acara", "Tentukan lokasi dan jadwal kegiatan", 30),
        ("Humas", "Koordinasi dengan pihak lokasi", 21),
        ("Perlengkapan", "Siapkan alat dan bahan", 7),
        ("Konsumsi", "Pesan konsumsi peserta", 3),
        ("Keamanan", "Pendataan peserta dan P3K", 5),
    ],
}


@app.route("/api/events", methods=["POST"])
def create_event():
    """Buat acara. Pembuatnya otomatis menjadi Ketua acara itu dan langsung masuk ke acara tersebut."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    data = request.get_json(silent=True) or {}
    try:
        nama = clean_text(data.get("nama"), 200, "Nama acara", required=True)
        lokasi = clean_text(data.get("lokasi"), 200, "Lokasi")
        deskripsi = clean_text(data.get("deskripsi"), 2000, "Deskripsi")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    tanggal = data.get("tanggal") or None
    if tanggal:
        try:
            datetime.strptime(tanggal, "%Y-%m-%d")
        except (ValueError, TypeError):
            return jsonify({"error": "Format tanggal acara harus YYYY-MM-DD"}), 400
    password = str(data.get("password") or "")
    if password and len(password) < 8:
        return jsonify({"error": "Password pendaftaran acara minimal 8 karakter."}), 400
    event = Event(nama=nama, tanggal=tanggal, lokasi=lokasi, deskripsi=deskripsi, pembuat_id=oid,
                  password_hash=generate_password_hash(password) if password else None)
    db.session.add(event)
    db.session.flush()
    db.session.add(PeranAcara(event_id=event.id, orang_id=oid, peran="ketua"))
    template = str(data.get("template") or "kosong")
    if template in TEMPLATE_ACARA and tanggal:
        acara = datetime.strptime(tanggal, "%Y-%m-%d")
        for seksi, judul, mundur in TEMPLATE_ACARA[template]:
            tenggat = (acara - timedelta(days=mundur)).strftime("%Y-%m-%dT17:00")
            db.session.add(Task(event_id=event.id, divisi=seksi, judul=judul, deadline_iso=tenggat))
    db.session.commit()
    _masuk_acara(event.id, "ketua", None)
    return jsonify(event.to_dict()), 201


@app.route("/api/events/<event_id>", methods=["GET"])
def get_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan"}), 404
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu belum terdaftar di acara ini."}), 403
    return jsonify(event_snapshot(event))


@app.route("/api/events/<event_id>", methods=["DELETE"])
@ketua_only
def delete_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan"}), 404
    Task.query.filter_by(event_id=event.id).delete()
    db.session.delete(event)
    db.session.commit()
    return jsonify({"success": True})




# ============================================================
# BACA TIMELINE BERFASE (mis. "Fase 1: Akhir Oktober" dengan poin-poin)
# ============================================================


















# ============================================================
# KEAMANAN: LOGIN ORGANISASI, RATE LIMIT, VALIDASI, ERROR JSON
# ============================================================

@app.before_request
def require_login():
    if request.is_json and (request.content_length or 0) > JSON_MAX_BYTES:
        return jsonify({"error": "Data terlalu besar (maksimal 256 KB)."}), 413
    if request.method == "OPTIONS" or not request.path.startswith("/api/") or request.path in PUBLIC_PATHS:
        return None
    if request.method == "GET" and request.path.startswith("/api/lampiran/"):
        return None  # diperiksa di rute: publik jika lampiran dari kabar publik
    if current_role():
        return None
    return jsonify({"error": "Belum login. Silakan masuk terlebih dahulu."}), 401


@app.route("/api/auth/events", methods=["GET"])
def list_events_public():
    """Daftar acara untuk halaman login. Hanya nama dan tanggal, tanpa data tugas."""
    events = Event.query.order_by(Event.tanggal.desc(), Event.created_at.desc()).all()
    return jsonify({"events": [{"id": e.id, "nama": e.nama, "tanggal": e.tanggal} for e in events if not _acara_tertutup(e.id)]})




# ============================================================
# EVALUASI (masukan panitia): draf pribadi, final dibaca bersama, tindak lanjut Ketua
# ============================================================



def _kunci_pengguna():
    """Identitas stabil: akun pribadi bila ada, jika tidak akun seksi lama atau Ketua."""
    if session.get("orang_id"):
        return "orang:" + session["orang_id"]
    return "peran:" + str(session.get("role") or "")


def _di_acara(event_id):
    """User hanya boleh bekerja di acara tempat ia terdaftar. Keanggotaan dicek langsung, bukan dari sesi."""
    oid = session.get("orang_id")
    if not oid or not event_id:
        return False
    return PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first() is not None


def _event_lampiran(l):
    """Acara tempat sebuah lampiran berada (lewat tugas atau kabar), atau None jika yatim."""
    if l.task_id:
        t = db.session.get(Task, l.task_id)
        return t.event_id if t else None
    if l.kabar_id:
        k = db.session.get(Kabar, l.kabar_id)
        return k.event_id if k else None
    return None


def _peran_di(event_id):
    """Peran user ini di acara tertentu (dari database), atau None."""
    oid = session.get("orang_id")
    if not oid or not event_id:
        return None
    b = PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first()
    return b.peran if b else None


def _seksi_di(event_id, seksi):
    """True jika user ini koordinator seksi tersebut di acara itu (berdasarkan database)."""
    oid = session.get("orang_id")
    if not oid or not event_id or not seksi:
        return False
    b = PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first()
    return bool(b and b.peran == "koordinator" and b.seksi == seksi)


def _ketua_acara(event_id):
    """Ketua hanya berlaku untuk acara yang sedang dimasuki dan benar-benar ia pimpin."""
    return session.get("peran") == "ketua" and session.get("event_id") == event_id and _di_acara(event_id)


























# ============================================================
# KEPUTUSAN ACARA: dicatat langsung, tanpa persetujuan.
# ============================================================

def _keputusan_dict(k):
    return {"id": k.id, "judul": k.judul, "isi": k.isi, "status": k.status, "induk_id": k.induk_id,
            "penulis": k.penulis_nama or "Panitia", "milik_saya": k.penulis_kunci == _kunci_pengguna(),
            "catatan": k.catatan or "", "created_at": k.created_at.isoformat() if k.created_at else None}


@app.route("/api/events/<event_id>/keputusan", methods=["GET"])
def list_keputusan(event_id):
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu tidak bekerja di acara ini."}), 403
    rows = KeputusanAcara.query.filter_by(event_id=event_id).order_by(KeputusanAcara.created_at.desc()).all()
    return jsonify({"keputusan": [_keputusan_dict(k) for k in rows], "tertutup": _acara_tertutup(event_id)})


@app.route("/api/events/<event_id>/keputusan", methods=["POST"])
def ajukan_keputusan(event_id):
    if not _di_acara(event_id) or not db.session.get(Event, event_id):
        return jsonify({"error": "Kamu tidak bekerja di acara ini."}), 403
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    data = request.get_json(silent=True) or {}
    try:
        judul = clean_text(data.get("judul"), 255, "Judul", required=True)
        isi = clean_text(data.get("isi"), 4000, "Isi keputusan")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    k = KeputusanAcara(event_id=event_id, judul=judul, isi=isi, status="disetujui",  # langsung tercatat, tanpa persetujuan
                       penulis_kunci=_kunci_pengguna(), penulis_nama=session.get("nama") or current_role() or "Panitia")
    db.session.add(k)
    db.session.flush()
    _riwayat_simpan(event_id, f'Catat keputusan "{judul}"', _keadaan_kosong(event_id, "keputusan", k.id),
                    _ambil_keadaan(event_id, [("keputusan", k.id)]))
    db.session.commit()
    return jsonify(_keputusan_dict(k)), 201












# ============================================================
# KOMUNIKASI (Tahap 5): pesan, tag, notifikasi, teguran Humas, permintaan antar seksi, surat Humas
# ============================================================

# Tulis yang tetap boleh saat acara ditutup: penutupan/pembukaan, tindak lanjut Ketua, tanda baca,
# dan data pribadi. Semua tulis lain ke acara tertutup ditolak oleh penjaga di bawah.
BEKU_BEBAS_AKHIRAN = ("/tutup", "/buka", "/tindak", "/baca", "/masuk", "/keluar-acara")
BEKU_BEBAS_AWALAN = ("/api/auth", "/api/orang", "/api/me", "/api/tugas-default", "/api/beranda", "/api/help", "/api/agen", "/api/riwayat")


def _event_untuk_permintaan():
    """Acara yang disentuh permintaan ini, dari URL, data yang dirujuk, atau sesi."""
    from database import Lampiran as _Lampiran, Kabar as _Kabar
    va = request.view_args or {}
    if va.get("event_id"):
        return va["event_id"]
    if "task_id" in va:
        t = db.session.get(Task, va["task_id"])
        return t.event_id if t else None
    if "kabar_id" in va:
        k = db.session.get(_Kabar, va["kabar_id"])
        return k.event_id if k else None
    if "lampiran_id" in va:
        l = db.session.get(_Lampiran, va["lampiran_id"])
        if not l:
            return None
        if l.task_id:
            t = db.session.get(Task, l.task_id)
            return t.event_id if t else None
        k = db.session.get(_Kabar, l.kabar_id) if l.kabar_id else None
        return k.event_id if k else None
    if "kid" in va:
        k = db.session.get(KeputusanAcara, va["kid"])
        return k.event_id if k else None
    if "pesan_id" in va:
        p = db.session.get(Pesan, va["pesan_id"])
        return p.event_id if p else None
    if request.form.get("task_id"):
        t = db.session.get(Task, request.form.get("task_id"))
        if t:
            return t.event_id
    body = request.get_json(silent=True)
    if isinstance(body, dict) and body.get("event_id"):
        return str(body["event_id"])
    return session.get("event_id") or None


@app.before_request
def tolak_tulis_acara_tertutup():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE") or not request.path.startswith("/api/"):
        return None
    if request.path.endswith(BEKU_BEBAS_AKHIRAN) or request.path.startswith(BEKU_BEBAS_AWALAN):
        return None
    if request.method == "POST" and request.path == "/api/events":
        return None  # membuat acara baru tidak menulis ke acara yang sedang ditutup
    event_id = _event_untuk_permintaan()
    if event_id and _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup. Data dibekukan."}), 409
    return None




def _kunci_seksi(event_id, seksi):
    """Semua kunci penerima untuk satu seksi: akun seksi lama, dan anggota/PJ yang ditugaskan ke seksi itu."""
    keys = {"peran:" + seksi}
    for b in PeranAcara.query.filter_by(event_id=event_id, seksi=seksi).all():
        if b.peran in ("koordinator", "anggota", "pj"):
            keys.add("orang:" + b.orang_id)
    return keys


def _kunci_ketua(event_id):
    keys = set()
    for b in PeranAcara.query.filter_by(event_id=event_id, peran="ketua").all():
        keys.add("orang:" + b.orang_id)
    return keys




def _tag_penerima(event_id, teks):
    """@Seksi menjangkau seluruh seksi. @NamaDepan menjangkau satu orang di acara itu."""
    keys, low = set(), teks.lower()
    for sk in aturan_peran.SEKSI:
        if "@" + sk.lower() in low:
            keys |= _kunci_seksi(event_id, sk)
    for b in PeranAcara.query.filter_by(event_id=event_id).all():
        o = db.session.get(Orang, b.orang_id)
        if o and o.nama and "@" + o.nama.split()[0].lower() in low:
            keys.add("orang:" + o.id)
    return keys


def _resolve_ke(event_id, ke):
    """Tujuan: 'orang:<id>', 'seksi:<nama>', atau 'ketua'. Mengembalikan (kunci, galat)."""
    ke = str(ke or "")
    if ke == "ketua":
        return _kunci_ketua(event_id), None
    if ke.startswith("seksi:"):
        seksi = ke.split(":", 1)[1].strip()
        if seksi not in aturan_peran.SEKSI:
            return set(), "Seksi tidak dikenal."
        return _kunci_seksi(event_id, seksi), None
    if ke.startswith("orang:"):
        oid = ke.split(":", 1)[1].strip()
        if not PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first():
            return set(), "Orang itu tidak punya peran di acara ini."
        return {"orang:" + oid}, None
    return set(), "Tujuan tidak dikenal."


def _kunci_saya():
    return _kunci_pengguna()


@app.route("/api/events/<event_id>/pesan", methods=["POST"])
def kirim_pesan_langsung(event_id):
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu tidak bekerja di acara ini."}), 403
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    data = request.get_json(silent=True) or {}
    try:
        isi = clean_text(data.get("isi"), 2000, "Isi pesan", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    keys, galat = _resolve_ke(event_id, data.get("ke"))
    if galat:
        return jsonify({"error": galat}), 400
    tag = _tag_penerima(event_id, isi) - keys
    tag.discard(_kunci_saya())
    langsung = keys - {_kunci_saya()}
    keys = langsung | tag
    db.session.commit()
    return jsonify({"terkirim_ke": len(keys)}), 201


























# ============================================================
# ALAT ACARA DAN DOKUMEN (Tahap 6)
# Log dan checklist: seksi Acara. Daftar tamu: Humas. Notulen: Sekretaris. Buku surat: per seksi.
# ============================================================































@app.route("/api/events/<event_id>/dokumen/laporan.pdf", methods=["GET"])
def unduh_laporan_pdf(event_id):
    """Laporan acara dalam PDF: data acara, ringkasan tugas per seksi, log, daftar tamu, dan notulen."""
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu tidak bekerja di acara ini."}), 403
    ev = db.session.get(Event, event_id)
    if not ev:
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    from fpdf import FPDF
    from flask import Response

    def aman(teks):
        return str(teks or "").encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, aman(f"Laporan acara: {ev.nama}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, aman(f"Tanggal: {ev.tanggal or 'belum diisi'}   Lokasi: {ev.lokasi or '-'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def bagian(judul, baris):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, aman(judul), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for b in baris or ["(belum ada)"]:
            pdf.multi_cell(0, 6, aman("- " + b))
        pdf.ln(2)

    tugas = Task.query.filter_by(event_id=event_id).all()
    per_seksi = {}
    for t in tugas:
        per_seksi.setdefault(t.divisi or "Tanpa seksi", [0, 0])
        per_seksi[t.divisi or "Tanpa seksi"][0] += 1
        per_seksi[t.divisi or "Tanpa seksi"][1] += 1 if t.status == "done" else 0
    bagian("Ringkasan tugas per seksi",
           [f"{k}: {v[1]} dari {v[0]} selesai" for k, v in sorted(per_seksi.items())])

    data_pdf = bytes(pdf.output())
    return Response(data_pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="laporan-{event_id[:8]}.pdf"'})


# ============================================================
# DASHBOARD BERSAMA (Tahap 7): progres, papan seksi, kalender, perhatian hari ini, Staf of the Month
# Data hanya untuk panitia yang login di acara itu (keputusan 3: internal).
# ============================================================

# Keputusan 5 (rekomendasi): satu warna tetap per seksi, dipakai frontend.
WARNA_SEKSI = {
    "Acara": "indigo", "PDD": "pink", "Perkab": "amber", "Konsumsi": "emerald", "Humas": "sky",
    "Keamanan": "rose", "Sponsorship": "violet", "Bendahara": "teal", "Sekretaris": "blue",
    "Sekretariatan": "orange",
}






@app.route("/api/events/<event_id>/dashboard", methods=["GET"])
def dashboard_acara(event_id):
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu tidak bekerja di acara ini."}), 403
    ev = db.session.get(Event, event_id)
    if not ev:
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    tugas = Task.query.filter_by(event_id=event_id).all()
    sekarang = datetime.utcnow()

    def deadline(t):
        try:
            return datetime.fromisoformat(t.deadline_iso) if t.deadline_iso else None
        except ValueError:
            return None

    def terlambat(t):
        d = deadline(t)
        return t.status != "done" and d is not None and d < sekarang

    per_seksi = {}
    for t in tugas:
        sk = t.divisi or "Tanpa seksi"
        b = per_seksi.setdefault(sk, {"total": 0, "selesai": 0, "progres": [], "terlambat": 0})
        b["total"] += 1
        b["selesai"] += 1 if t.status == "done" else 0
        b["progres"].append(100 if t.status == "done" else int(t.progress or 0))
        b["terlambat"] += 1 if terlambat(t) else 0
    papan = []
    for sk, b in sorted(per_seksi.items()):
        rata = int(sum(b["progres"]) / len(b["progres"])) if b["progres"] else 0
        papan.append({"seksi": sk, "warna": WARNA_SEKSI.get(sk, "slate"), "total": b["total"], "selesai": b["selesai"],
                      "progres": rata, "terlambat": b["terlambat"],
                      "status": f"{b['selesai']} dari {b['total']} selesai" + (f", {b['terlambat']} terlambat" if b["terlambat"] else "")})

    total = len(tugas)
    selesai = sum(1 for t in tugas if t.status == "done")
    kalender = {}
    for t in tugas:
        d = deadline(t)
        if d:
            kalender.setdefault(d.date().isoformat(), []).append({
                "judul": t.judul, "seksi": t.divisi or "", "warna": WARNA_SEKSI.get(t.divisi or "", "slate"),
                "selesai": t.status == "done"})
    perhatian = []
    for t in tugas:
        d = deadline(t)
        if t.status == "done" or d is None:
            continue
        if d < sekarang:
            perhatian.append({"judul": t.judul, "seksi": t.divisi or "", "alasan": "terlambat", "deadline": t.deadline_iso})
        elif d - sekarang <= timedelta(hours=24):
            perhatian.append({"judul": t.judul, "seksi": t.divisi or "", "alasan": "dalam 24 jam", "deadline": t.deadline_iso})
    return jsonify({
        "acara": {"id": ev.id, "nama": ev.nama, "tanggal": ev.tanggal, "lokasi": ev.lokasi},
        "tertutup": _acara_tertutup(event_id),
        "progres_keseluruhan": int(selesai * 100 / total) if total else 0,
        "tugas": {"total": total, "selesai": selesai, "terlambat": sum(1 for t in tugas if terlambat(t))},
        "papan_seksi": papan,
        "kalender": kalender,
        "perlu_perhatian": perhatian,
    })






# ============================================================
# ARSIP ACARA (Tahap 8): ringkasan saat ditutup, rekap PDD dengan tautan Drive, dan pembacaan arsip
# ============================================================







def _login_orang(ip, username, password):
    """Login akun user. Hanya username dan password. Acara dan peran dipilih di dashboard."""
    orang = Orang.query.filter(db.func.lower(Orang.username) == username.lower()).first()
    if not orang or not check_password_hash(orang.password_hash, password):
        _login_fails.setdefault(ip, []).append(time.time())
        return jsonify({"error": "Username atau password salah."}), 401
    _login_fails.pop(ip, None)
    session.clear()
    session.permanent = True
    session["orang_id"] = orang.id
    session["nama"] = orang.nama
    session["role"] = orang.nama
    session["peran"] = "pengguna"
    session["event_id"] = None
    return jsonify({"role": orang.nama, "ketua": False, "event_id": None, "peran": "pengguna", "nama": orang.nama})


@app.route("/api/auth/login", methods=["POST"])
def login():
    ip = request.remote_addr or "unknown"
    _b = request.get_json(silent=True) or {}
    kunci_login = f"{ip}|{str(_b.get('username') or '').strip().lower()}"
    if _too_many_fails(kunci_login):
        return jsonify({"error": "Terlalu banyak percobaan. Coba lagi dalam 5 menit."}), 429
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    if not username:
        return jsonify({"error": "Username wajib diisi."}), 400
    return _login_orang(kunci_login, username, str(data.get("password", "")))


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/me", methods=["GET"])
def me():
    if current_role():
        return jsonify({"role": current_role(), "ketua": is_ketua(), "event_id": session.get("event_id"),
                        "peran": session.get("peran"), "nama": session.get("nama"), "orang_id": session.get("orang_id"),
                        "admin": bool((db.session.get(Orang, session.get("orang_id")) or Orang(admin=False)).admin)})
    return jsonify({"masuk": False})


def clean_text(value, max_len, field, required=False):
    text = str(value if value is not None else "").strip()
    if required and not text:
        raise ValueError(f"{field} wajib diisi")
    if len(text) > max_len:
        raise ValueError(f"{field} maksimal {max_len} karakter")
    return text


def clean_deadline(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).isoformat(timespec="minutes")
    except (ValueError, TypeError):
        raise ValueError("Format deadline tidak valid")


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint tidak ditemukan"}), 404
    return _e


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "Berkas terlalu besar (maksimal 30 MB)."}), 413


@app.errorhandler(500)
def server_error(_e):
    print("[ERROR] ", _e)
    return jsonify({"error": "Terjadi kesalahan di server. Coba lagi."}), 500



# ============================================================
# BANTUAN CAPY (gelembung di pojok): jawaban tetap dulu, AI hanya bila tidak cocok
# ============================================================






# ============================================================
# BERANDA PUBLIK, KABAR KERJA, RUANG KERJA SEKSI
# ============================================================

HERO_KEYS = {"a", "b", "c", "d"}
BERANDA_DEFAULT = {
    "hero": "a",
    "judul": "Atur acara panitia tanpa ribet",
    "subjudul": "Tulis rundown, lalu tugas dibagi per seksi dengan deadline yang masuk akal. Setiap orang tahu apa yang harus dikerjakan.",
    "tombol": "Coba sekarang",
}


def get_pengaturan():
    cfg = dict(BERANDA_DEFAULT)
    for p in Pengaturan.query.all():
        if p.key in cfg:
            cfg[p.key] = p.value
    return cfg


@app.route("/api/beranda", methods=["GET"])
def get_beranda():
    """Data beranda publik: pengaturan tampilan, angka dari data asli, dan kabar kerja yang diizinkan tampil."""
    cfg = get_pengaturan()
    total_tugas = Task.query.count()
    selesai = Task.query.filter_by(status="done").count()
    nama_acara = {e.id: e.nama for e in Event.query.all()}
    kabar = Kabar.query.filter_by(publik=True).order_by(Kabar.created_at.desc()).limit(8).all()
    return jsonify({
        "pengaturan": cfg,
        "statistik": {
            "acara": Event.query.count(),
            "tugas": total_tugas,
            "tugas_selesai": selesai,
            "seksi": db.session.query(PeranAcara.seksi).filter(PeranAcara.seksi.isnot(None)).distinct().count(),
            "persen_selesai": round(selesai / total_tugas * 100) if total_tugas else 0,
        },
        "kabar": [{
            "id": k.id, "seksi": k.seksi, "isi": k.isi,
            "acara": nama_acara.get(k.event_id, ""),
            "waktu": k.created_at.isoformat() if k.created_at else None,
            "lampiran": [lampiran_dict(l) for l in Lampiran.query.filter_by(kabar_id=k.id).all()],
        } for k in kabar],
    })


@app.route("/api/beranda", methods=["PUT"])
@ketua_only
def set_beranda():
    data = request.get_json(silent=True) or {}
    try:
        hero = str(data.get("hero", "a")).strip().lower()
        if hero not in HERO_KEYS:
            return jsonify({"error": "Pilihan model hero tidak dikenal"}), 400
        judul = clean_text(data.get("judul"), 120, "Judul", required=True)
        subjudul = clean_text(data.get("subjudul"), 300, "Subjudul")
        tombol = clean_text(data.get("tombol"), 40, "Teks tombol")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    for key, value in {"hero": hero, "judul": judul, "subjudul": subjudul, "tombol": tombol}.items():
        row = db.session.get(Pengaturan, key)
        if row:
            row.value = value
        else:
            db.session.add(Pengaturan(key=key, value=value))
    db.session.commit()
    return jsonify(get_pengaturan())


@app.route("/api/kabar", methods=["GET"])
def list_kabar():
    q = Kabar.query
    event_id = request.args.get("event_id")
    if event_id:
        q = q.filter_by(event_id=event_id)
    if not event_id or not _di_acara(event_id):
        q = q.filter_by(publik=True)  # bukan anggota: hanya kabar publik
    items = q.order_by(Kabar.created_at.desc()).limit(50).all()
    return jsonify({"kabar": [{
        "id": k.id, "event_id": k.event_id, "seksi": k.seksi, "isi": k.isi, "publik": bool(k.publik),
        "waktu": k.created_at.isoformat() if k.created_at else None,
        "bisa_hapus": _peran_di(k.event_id) == "ketua" or role_owns(k.seksi),
        "lampiran": [lampiran_dict(l) for l in Lampiran.query.filter_by(kabar_id=k.id).all()],
    } for k in items]})


@app.route("/api/kabar", methods=["POST"])
def create_kabar():
    data = request.get_json(silent=True) or {}
    try:
        isi = clean_text(data.get("isi"), 500, "Kabar", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    event_id = str(data.get("event_id") or "").strip() or None
    if event_id and not db.session.get(Event, event_id):
        return jsonify({"error": "Acara tidak ditemukan"}), 404
    if event_id and not _di_acara(event_id):
        return jsonify({"error": "Kamu bukan anggota acara ini."}), 403
    if not event_id and not _sebagai_admin():
        return jsonify({"error": "Kabar tanpa acara (tampil di beranda) hanya bisa dibuat admin."}), 403
    kabar = Kabar(seksi=current_role(), isi=isi, event_id=event_id, publik=bool(data.get("publik", True)))
    db.session.add(kabar)
    db.session.flush()
    for lid in (data.get("lampiran_ids") or [])[:10]:
        l = db.session.get(Lampiran, str(lid))
        if l and l.pengunggah_id == session.get("orang_id") and not l.kabar_id:
            l.kabar_id = kabar.id
    db.session.commit()
    return jsonify({"id": kabar.id}), 201


@app.route("/api/kabar/<kabar_id>", methods=["DELETE"])
def delete_kabar(kabar_id):
    kabar = db.session.get(Kabar, kabar_id)
    if not kabar:
        return jsonify({"error": "Kabar tidak ditemukan"}), 404
    if not ((kabar.event_id and _peran_di(kabar.event_id) == "ketua") or (role_owns(kabar.seksi) and (not kabar.event_id or _di_acara(kabar.event_id)))):
        return jsonify({"error": "Kamu hanya bisa menghapus kabar seksimu sendiri."}), 403
    db.session.delete(kabar)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/kerja", methods=["GET"])
def get_kerja():
    """Ruang kerja seksi: tugas yang menjadi tanggung jawab seksi ini, dikelompokkan per acara."""
    out = []
    for b in PeranAcara.query.filter_by(orang_id=session.get("orang_id")).all():
        e = db.session.get(Event, b.event_id)
        if e is None:
            continue
        tasks = visible_tasks_query(e.id).order_by(Task.deadline_iso).all()
        # Ketua, wakil, dan koordinator tetap melihat acaranya walau belum ada tugas (di sini mereka menambah tugas).
        # Anggota hanya melihat acara yang punya tugas untuknya. Admin dan Bendahara melihat semua.
        if not tasks and b.peran not in ("ketua", "wakil_ketua", "koordinator") and not bisa_lihat_semua() and (current_role() or "").lower() != "bendahara":
            continue
        items = [t.to_dict() for t in tasks]
        out.append({
            "event": e.to_dict(),
            "peran": b.peran,
            "total": len(items),
            "selesai": sum(1 for t in items if t["status"] == "done"),
            "tugas": items,
        })
    return jsonify({"role": current_role(), "ketua": is_ketua(), "acara": out})


# ============================================================
# LAMPIRAN (foto, video, dokumen) DAN PEMBANTU MENULIS
# ============================================================

IZIN_BERKAS = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif",
    "mp4": "video/mp4", "webm": "video/webm", "mov": "video/quicktime",
    "pdf": "application/pdf", "txt": "text/plain", "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
UKURAN_BERKAS_MAKS = 30 * 1024 * 1024


def lampiran_dict(l):
    return {"id": l.id, "nama": l.nama_asli, "mime": l.mime, "ukuran": l.ukuran,
            "url": f"/api/lampiran/{l.id}", "jenis": l.mime.split("/")[0]}


@app.route("/api/lampiran", methods=["POST"])
def upload_lampiran():
    berkas = request.files.get("file")
    if not berkas or not berkas.filename:
        return jsonify({"error": "Pilih berkas dulu."}), 400
    ext = berkas.filename.rsplit(".", 1)[-1].lower() if "." in berkas.filename else ""
    if ext not in IZIN_BERKAS:
        return jsonify({"error": "Jenis berkas belum didukung. Gunakan foto, video, PDF, atau dokumen perkantoran."}), 400
    data = berkas.read()
    if not data:
        return jsonify({"error": "Berkas kosong."}), 400
    if len(data) > UKURAN_BERKAS_MAKS:
        return jsonify({"error": "Berkas terlalu besar (maksimal 30 MB)."}), 413
    task_id = str(request.form.get("task_id") or "").strip() or None
    if task_id:
        task = db.session.get(Task, task_id)
        if not task:
            return jsonify({"error": "Tugas tidak ditemukan."}), 404
        if not _di_acara(task.event_id) or not (_peran_di(task.event_id) == "ketua" or role_owns(task.divisi)):
            return jsonify({"error": "Tugas ini bukan milik seksimu."}), 403
    nama_disk = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(UPLOAD_DIR, nama_disk), "wb") as f:
        f.write(data)
    l = Lampiran(nama_asli=berkas.filename[:255], mime=IZIN_BERKAS[ext], ukuran=len(data), pengunggah_id=session.get("orang_id"),
                 berkas=nama_disk, pemilik_seksi=current_role(), task_id=task_id)
    db.session.add(l)
    db.session.commit()
    return jsonify(lampiran_dict(l)), 201


@app.route("/api/lampiran/<lampiran_id>", methods=["GET"])
def get_lampiran(lampiran_id):
    l = db.session.get(Lampiran, lampiran_id)
    if not l:
        return jsonify({"error": "Berkas tidak ditemukan."}), 404
    publik = False
    if l.kabar_id:
        kb = db.session.get(Kabar, l.kabar_id)
        publik = bool(kb and kb.publik)
    if not publik and not current_role():
        return jsonify({"error": "Belum login. Silakan masuk terlebih dahulu."}), 401
    if not publik:
        _eid_l = _event_lampiran(l)
        if _eid_l and not _di_acara(_eid_l):
            return jsonify({"error": "Berkas ini milik acara yang tidak kamu ikuti."}), 403
        if not _eid_l and not (l.pengunggah_id == session.get("orang_id") or _sebagai_admin()):
            return jsonify({"error": "Belum login atau berkas ini tidak tersedia untukmu."}), 401
    inline = l.mime.split("/")[0] in ("image", "video") or l.mime == "application/pdf"
    resp = send_from_directory(UPLOAD_DIR, l.berkas, mimetype=l.mime, as_attachment=not inline,
                               download_name=l.nama_asli)
    resp.headers["Cache-Control"] = "private, max-age=3600"
    return resp


@app.route("/api/lampiran/<lampiran_id>", methods=["DELETE"])
def delete_lampiran(lampiran_id):
    l = db.session.get(Lampiran, lampiran_id)
    if not l:
        return jsonify({"error": "Berkas tidak ditemukan."}), 404
    _eid_l = _event_lampiran(l)
    if not _eid_l:
        if not (l.pengunggah_id == session.get("orang_id") or _sebagai_admin()):
            return jsonify({"error": "Berkas ini bukan milikmu."}), 403
    elif not _di_acara(_eid_l) or not (_peran_di(_eid_l) == "ketua" or role_owns(l.pemilik_seksi)):
        return jsonify({"error": "Kamu hanya bisa menghapus berkas seksimu sendiri."}), 403
    try:
        os.remove(os.path.join(UPLOAD_DIR, l.berkas))
    except OSError:
        pass
    db.session.delete(l)
    db.session.commit()
    return jsonify({"success": True})










# ============================================================
# AGEN CAPY: kalimat mentah diubah menjadi rencana aksi, lalu dijalankan
# ============================================================
































@app.route("/api/orang", methods=["GET"])
@ketua_only
def list_orang():
    """Daftar akun pribadi. Hanya Ketua."""
    return jsonify({"orang": [{"id": o.id, "username": o.username, "nama": o.nama, "admin": bool(o.admin)}
                              for o in Orang.query.order_by(Orang.nama).all()]})


@app.route("/api/orang", methods=["POST"])
@ketua_only
def tambah_orang():
    """Buat akun pribadi. Hanya Ketua (sementara; admin terpisah menyusul di Tahap 1b)."""
    data = request.get_json(silent=True) or {}
    try:
        username = clean_text(data.get("username"), 64, "Username", required=True)
        nama = clean_text(data.get("nama"), 128, "Nama", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    password = str(data.get("password") or "")
    if len(password) < 8:
        return jsonify({"error": "Password minimal 8 karakter."}), 400
    if Orang.query.filter(db.func.lower(Orang.username) == username.lower()).first():
        return jsonify({"error": "Username sudah dipakai."}), 409
    orang = Orang(username=username, nama=nama, password_hash=generate_password_hash(password),
                  admin=bool(data.get("admin")))
    db.session.add(orang)
    db.session.commit()
    return jsonify({"id": orang.id, "username": orang.username, "nama": orang.nama, "admin": bool(orang.admin)}), 201


def _acara_tertutup(event_id):
    return db.session.get(EventArsip, event_id) is not None


@app.route("/api/events/<event_id>/peran", methods=["GET"])
@ketua_only
def list_peran_acara(event_id):
    if not db.session.get(Event, event_id):
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    baris = PeranAcara.query.filter_by(event_id=event_id).all()
    nama = {o.id: o.nama for o in Orang.query.filter(Orang.id.in_([b.orang_id for b in baris])).all()} if baris else {}
    return jsonify({"tertutup": _acara_tertutup(event_id), "seksi_tersedia": list(aturan_peran.SEKSI),
                    "peran": [{"id": b.id, "orang_id": b.orang_id, "nama": nama.get(b.orang_id, ""),
                               "peran": b.peran, "seksi": b.seksi} for b in baris]})


@app.route("/api/events/<event_id>/peran", methods=["POST"])
@ketua_only
def tetapkan_peran_acara(event_id):
    if not db.session.get(Event, event_id):
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup. Buka dulu untuk mengubah peran."}), 409
    data = request.get_json(silent=True) or {}
    orang = db.session.get(Orang, str(data.get("orang_id") or ""))
    if not orang:
        return jsonify({"error": "Orang tidak ditemukan."}), 404
    peran = str(data.get("peran") or "")
    seksi = str(data.get("seksi") or "").strip() or None
    ada = [(b.orang_id, b.peran, b.seksi) for b in PeranAcara.query.filter_by(event_id=event_id).all()]
    galat = aturan_peran.validasi_penugasan(peran, seksi, orang.id, ada, orang_admin=bool(orang.admin))
    if galat:
        return jsonify({"error": galat}), 400
    baris = PeranAcara(event_id=event_id, orang_id=orang.id, peran=peran,
                       seksi=seksi if peran in aturan_peran.PERAN_BERSEKSI or seksi else None)
    db.session.add(baris)
    db.session.commit()
    return jsonify({"id": baris.id, "orang_id": orang.id, "nama": orang.nama, "peran": peran, "seksi": baris.seksi}), 201


@app.route("/api/events/<event_id>/peran/<peran_id>", methods=["PUT"])
@ketua_only
def ubah_peran_acara(event_id, peran_id):
    """Ketua menurunkan jabatan, menaikkan, atau memindahkan anggota ke seksi lain.
    Ketua tidak bisa diubah di sini; pindah Ketua dilakukan dengan menutup dan membuat ulang acara."""
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    baris = db.session.get(PeranAcara, peran_id)
    if not baris or baris.event_id != event_id:
        return jsonify({"error": "Penugasan tidak ditemukan."}), 404
    if baris.peran == "ketua":
        return jsonify({"error": "Peran Ketua tidak bisa diubah dari sini."}), 400
    data = request.get_json(silent=True) or {}
    peran = str(data.get("peran") or baris.peran)
    if peran not in ("anggota", "pj", "koordinator", "wakil_ketua"):
        return jsonify({"error": "Peran harus anggota, pj, koordinator, atau wakil ketua."}), 400
    seksi = data.get("seksi") or None
    if peran != "koordinator" and seksi is not None and seksi not in aturan_peran.SEKSI:
        return jsonify({"error": "Seksi tidak dikenal."}), 400
    ada = [(b.orang_id, b.peran, b.seksi) for b in PeranAcara.query.filter_by(event_id=event_id).all() if b.id != baris.id]
    galat = aturan_peran.validasi_penugasan(peran, seksi, baris.orang_id, ada)
    if galat:
        return jsonify({"error": galat}), 400
    _sebelum_peran = _ambil_keadaan(event_id, [("peran", baris.id)])
    baris.peran = peran
    baris.seksi = seksi
    _riwayat_simpan(event_id, f"Ubah peran {baris.orang_id[:8]}", _sebelum_peran, _ambil_keadaan(event_id, [("peran", baris.id)]))
    db.session.commit()
    return jsonify({"id": baris.id, "peran": baris.peran, "seksi": baris.seksi})


@app.route("/api/events/<event_id>/peran/<peran_id>", methods=["DELETE"])
@ketua_only
def hapus_peran_acara(event_id, peran_id):
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    baris = db.session.get(PeranAcara, peran_id)
    if not baris or baris.event_id != event_id:
        return jsonify({"error": "Penugasan tidak ditemukan."}), 404
    if baris.peran == "ketua":
        return jsonify({"error": "Ketua tidak bisa dikeluarkan dari acaranya sendiri."}), 400
    _sebelum_keluar = _ambil_keadaan(event_id, [("peran", baris.id)])
    db.session.delete(baris)
    _riwayat_simpan(event_id, "Keluarkan peserta", _sebelum_keluar, _keadaan_kosong(event_id, "peran", baris.id))
    db.session.commit()
    return jsonify({"success": True})


# ============================================================
# AKUN USER: daftar, lalu buat atau gabung acara dari dashboard
# ============================================================

@app.route("/api/auth/daftar", methods=["POST"])
def daftar_akun():
    """Daftar akun user: nama, username, password. Tanpa acara dan tanpa role."""
    data = request.get_json(silent=True) or {}
    try:
        username = clean_text(data.get("username"), 64, "Username", required=True)
        nama = clean_text(data.get("nama"), 128, "Nama", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    password = str(data.get("password") or "")
    if len(password) < 8:
        return jsonify({"error": "Password minimal 8 karakter."}), 400
    if Orang.query.filter(db.func.lower(Orang.username) == username.lower()).first():
        return jsonify({"error": "Username sudah dipakai."}), 409
    orang = Orang(username=username, nama=nama, password_hash=generate_password_hash(password), admin=False)
    db.session.add(orang)
    db.session.commit()
    kode, hash_pulih = _buat_kode_pemulihan()
    orang.kode_pemulihan_hash = hash_pulih
    db.session.commit()
    return jsonify({"username": orang.username, "kode_pemulihan": kode,
                    "pesan": "Akun dibuat. Simpan kode pemulihan ini; hanya tampil sekali. Kode dipakai jika lupa password."}), 201


def _orang_login():
    oid = session.get("orang_id")
    if not oid or not db.session.get(Orang, oid):
        return None
    return oid


@app.route("/api/me/acara", methods=["GET"])
def me_daftar_acara():
    """Acara yang diikuti user ini, beserta perannya."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    acara = []
    for b in PeranAcara.query.filter_by(orang_id=oid).all():
        ev = db.session.get(Event, b.event_id)
        if not ev:
            continue
        acara.append({"id": ev.id, "nama": ev.nama, "tanggal": ev.tanggal, "peran": b.peran,
                      "seksi": b.seksi, "tertutup": _acara_tertutup(ev.id)})
    return jsonify({"acara": acara})


@app.before_request
def _sinkron_keanggotaan():
    """Akses mengikuti data terbaru: anggota yang dikeluarkan atau diturunkan langsung berubah di sesinya."""
    if not request.path.startswith("/api/") or request.path.startswith(("/api/auth/login", "/api/auth/logout", "/api/auth/daftar", "/api/auth/events", "/api/me", "/api/beranda")):
        return None
    event_id = session.get("event_id")
    oid = session.get("orang_id")
    if not event_id or not oid:
        return None
    baris = PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first()
    if not baris:
        session["event_id"] = None
        session["peran"] = "pengguna"
        session["role"] = session.get("nama")
        return None
    peran = baris.peran
    if _acara_tertutup(event_id) and peran != "ketua":
        peran = "anggota"
    if session.get("peran") != peran or session.get("role") not in (baris.seksi, session.get("nama")):
        _masuk_acara(event_id, peran, baris.seksi)
    return None


def _masuk_acara(event_id, peran, seksi):
    """Set acara aktif di sesi. Koordinator memakai nama seksinya sebagai identitas (role),
    supaya aturan kepemilikan tugas per seksi tetap berlaku."""
    session["event_id"] = event_id
    session["peran"] = peran
    session["role"] = seksi if seksi else session.get("nama")


@app.route("/api/me/acara/<event_id>/masuk", methods=["POST"])
def me_masuk_acara(event_id):
    """Masuk ke dashboard acara tempat user terdaftar. Peran diambil dari penugasan di acara itu."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    baris = PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first()
    if not baris:
        return jsonify({"error": "Kamu belum terdaftar di acara ini."}), 403
    # Acara yang sudah ditutup: semua selain Ketua masuk sebagai anggota (hanya bisa membaca)
    peran = baris.peran
    if _acara_tertutup(event_id) and peran != "ketua":
        peran = "anggota"
    _masuk_acara(event_id, peran, baris.seksi)
    return jsonify({"event_id": event_id, "peran": peran, "seksi": baris.seksi, "role": session.get("role"),
                    "ketua": peran == "ketua"})


@app.route("/api/me/keluar-acara", methods=["POST"])
def me_keluar_acara():
    """Keluar dari acara aktif dan kembali ke dashboard user."""
    session["event_id"] = None
    session["peran"] = "pengguna"
    session["role"] = session.get("nama")
    return jsonify({"success": True})


def _sebagai_admin():
    oid = _orang_login()
    orang = db.session.get(Orang, oid) if oid else None
    return orang if orang and orang.admin else None


@app.route("/api/admin/angkat", methods=["POST"])
def admin_angkat():
    """Admin menjadikan akun lain admin, atau mencabut statusnya."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    data = request.get_json(silent=True) or {}
    o = Orang.query.filter(db.func.lower(Orang.username) == str(data.get("username") or "").strip().lower()).first()
    if not o:
        return jsonify({"error": "Username tidak ditemukan."}), 404
    o.admin = bool(data.get("admin", True))
    db.session.commit()
    return jsonify({"username": o.username, "admin": o.admin})


@app.route("/api/admin/reset-password", methods=["POST"])
def admin_reset_password():
    """Admin mengatur ulang password akun yang lupa password. Password baru diberikan admin lewat jalur lain."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    data = request.get_json(silent=True) or {}
    o = Orang.query.filter(db.func.lower(Orang.username) == str(data.get("username") or "").strip().lower()).first()
    if not o:
        return jsonify({"error": "Username tidak ditemukan."}), 404
    pw = str(data.get("password") or "")
    if len(pw) < 8:
        return jsonify({"error": "Password minimal 8 karakter."}), 400
    o.password_hash = generate_password_hash(pw)
    db.session.commit()
    return jsonify({"username": o.username, "pesan": "Password sudah diatur ulang."})


@app.route("/api/admin/audit", methods=["GET"])
def admin_audit():
    """Catatan aksi tulis terbaru (hanya dibaca, tidak bisa diubah). Hanya admin."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    q = AuditLog.query
    if request.args.get("aktor"):
        q = q.filter(AuditLog.aktor.contains(str(request.args["aktor"])[:128]))
    rows = q.order_by(AuditLog.waktu.desc(), AuditLog.id.desc()).limit(300).all()
    return jsonify({"audit": [{"waktu": r.waktu.isoformat() if r.waktu else None, "aktor": r.aktor, "peran": r.peran,
                               "aksi": r.aksi, "rute": r.rute, "target": r.target} for r in rows]})


@app.route("/api/admin/asisten-cek", methods=["GET"])
def admin_asisten_cek():
    """Uji koneksi Capy ke Ollama: alamat, kunci, dan keberadaan model. Tidak mengirim pertanyaan ke model."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
    tags_url = (OLLAMA_URL or "").rsplit("/api/", 1)[0] + "/api/tags"
    try:
        res = requests.get(tags_url, headers=headers, timeout=15)
        res.raise_for_status()
        nama = [m.get("name", "") for m in res.json().get("models", [])]
    except requests.RequestException as exc:
        return jsonify({"ok": False, "pesan": _pesan_galat_asisten(exc), "alamat": tags_url}), 200
    cocok = [m for m in {OLLAMA_MODEL, CAPY_MODEL_OBROLAN, CAPY_MODEL_ACARA} if m and m not in nama]
    if cocok:
        return jsonify({"ok": True, "pesan": "Terhubung, tetapi beberapa model tidak ada di daftar: " + ", ".join(cocok) + ". Jika ini model cloud, pastikan nama dan aksesnya sesuai akunmu.", "model": nama[:50], "alamat": tags_url})
    return jsonify({"ok": True, "pesan": "Terhubung dan semua model yang dipakai tersedia.", "model": nama[:50], "alamat": tags_url})


@app.route("/api/admin/ringkasan", methods=["GET"])
def admin_ringkasan():
    """Angka utama untuk halaman admin."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    hari = datetime.utcnow().strftime("%Y-%m-%d")
    pemakaian_hari_ini = db.session.query(db.func.coalesce(db.func.sum(KuotaAsisten.jumlah), 0)).filter(KuotaAsisten.tanggal == hari).scalar()
    return jsonify({
        "pengguna": Orang.query.count(),
        "admin": Orang.query.filter_by(admin=True).count(),
        "acara": Event.query.count(),
        "acara_terbuka": Event.query.count() - EventArsip.query.count(),
        "tugas": Task.query.count(),
        "tugas_selesai": Task.query.filter_by(status="done").count(),
        "tanya_capy_hari_ini": int(pemakaian_hari_ini or 0),
        "kuota_capy_harian": ASISTEN_KUOTA_HARIAN,
    })


@app.route("/api/admin/pengguna", methods=["GET"])
def admin_pengguna():
    """Daftar akun. Hanya admin. Kode pemulihan dan password tidak pernah ditampilkan."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    q = str(request.args.get("q") or "").strip().lower()
    query = Orang.query
    if q:
        query = query.filter(db.or_(db.func.lower(Orang.username).contains(q), db.func.lower(Orang.nama).contains(q)))
    rows = query.order_by(Orang.created_at.desc()).limit(200).all()
    jumlah_acara = dict(db.session.query(PeranAcara.orang_id, db.func.count(PeranAcara.id)).group_by(PeranAcara.orang_id).all())
    return jsonify({"pengguna": [{
        "id": o.id, "username": o.username, "nama": o.nama, "admin": bool(o.admin),
        "dibuat": o.created_at.isoformat() if o.created_at else None,
        "jumlah_acara": int(jumlah_acara.get(o.id, 0)),
    } for o in rows]})


@app.route("/api/admin/acara", methods=["GET"])
def admin_acara():
    """Semua acara dengan pembuat dan jumlah peserta. Hanya admin."""
    if not _sebagai_admin():
        return jsonify({"error": "Hanya admin."}), 403
    arsip = {a.event_id for a in EventArsip.query.all()}
    peserta = dict(db.session.query(PeranAcara.event_id, db.func.count(PeranAcara.id)).group_by(PeranAcara.event_id).all())
    tugas = dict(db.session.query(Task.event_id, db.func.count(Task.id)).group_by(Task.event_id).all())
    nama_pembuat = {o.id: o.nama for o in Orang.query.all()}
    rows = Event.query.order_by(Event.created_at.desc()).limit(200).all()
    return jsonify({"acara": [{
        "id": e.id, "nama": e.nama, "tanggal": e.tanggal, "lokasi": e.lokasi,
        "pembuat": nama_pembuat.get(e.pembuat_id) if e.pembuat_id else None,
        "tertutup": e.id in arsip, "peserta": int(peserta.get(e.id, 0)), "tugas": int(tugas.get(e.id, 0)),
    } for e in rows]})


@app.route("/api/admin/acara-tanpa-ketua", methods=["GET"])
def acara_tanpa_ketua():
    """Acara lama tanpa pembuat. Hanya admin; dipakai untuk mengklaim acara lama."""
    oid = _orang_login()
    orang = db.session.get(Orang, oid) if oid else None
    if not orang or not orang.admin:
        return jsonify({"error": "Hanya admin."}), 403
    rows = Event.query.filter(Event.pembuat_id.is_(None)).order_by(Event.created_at.desc()).all()
    return jsonify({"acara": [{"id": e.id, "nama": e.nama, "tanggal": e.tanggal} for e in rows]})


@app.route("/api/events/<event_id>/klaim", methods=["POST"])
def klaim_acara_lama(event_id):
    """Acara lama yang dibuat sebelum ada pembuat: hanya admin yang bisa menetapkan dirinya sebagai Ketua."""
    oid = _orang_login()
    orang = db.session.get(Orang, oid) if oid else None
    if not orang or not orang.admin:
        return jsonify({"error": "Hanya admin yang bisa mengklaim acara lama."}), 403
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    if event.pembuat_id:
        return jsonify({"error": "Acara ini sudah punya Ketua."}), 409
    event.pembuat_id = oid
    if not PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first():
        db.session.add(PeranAcara(event_id=event_id, orang_id=oid, peran="ketua"))
    db.session.commit()
    return jsonify({"success": True, "event_id": event_id})


@app.route("/api/events/<event_id>/serahkan-ketua", methods=["POST"])
@ketua_only
def serahkan_ketua(event_id):
    """Ketua menyerahkan kepemimpinan acara kepada peserta lain. Ketua lama menjadi anggota."""
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    data = request.get_json(silent=True) or {}
    baru = PeranAcara.query.filter_by(event_id=event_id, orang_id=str(data.get("orang_id") or "")).first()
    lama = PeranAcara.query.filter_by(event_id=event_id, orang_id=session.get("orang_id")).first()
    if not baru or not lama or baru.id == lama.id:
        return jsonify({"error": "Pilih peserta lain di acara ini."}), 400
    refs = [("peran", lama.id), ("peran", baru.id)]
    sebelum = _ambil_keadaan(event_id, refs)
    ev = db.session.get(Event, event_id)
    sebelum["items"].append({"m": "event", "id": event_id, "parsial": True, "row": {"pembuat_id": ev.pembuat_id}})
    lama.peran, lama.seksi = "anggota", None
    baru.peran, baru.seksi = "ketua", None
    ev.pembuat_id = baru.orang_id
    db.session.flush()
    sesudah = _ambil_keadaan(event_id, refs)
    sesudah["items"].append({"m": "event", "id": event_id, "parsial": True, "row": {"pembuat_id": ev.pembuat_id}})
    _riwayat_simpan(event_id, "Serahkan Ketua", sebelum, sesudah)
    db.session.commit()
    return jsonify({"success": True, "ketua_baru": baru.orang_id})


@app.route("/api/events/<event_id>/password", methods=["PUT"])
@ketua_only
def atur_password_acara(event_id):
    """Ketua mengatur password pendaftaran acara. Kosongkan untuk menutup pendaftaran lewat password."""
    event = db.session.get(Event, event_id)
    if not event or event_id != session.get("event_id"):
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    password = str((request.get_json(silent=True) or {}).get("password") or "")
    if password and len(password) < 8:
        return jsonify({"error": "Password minimal 8 karakter."}), 400
    event.password_hash = generate_password_hash(password) if password else None
    db.session.commit()
    return jsonify({"success": True, "ada_password": bool(event.password_hash)})


@app.route("/api/me/acara/<event_id>/gabung", methods=["POST"])
def me_gabung_acara(event_id):
    """Gabung ke acara dengan password pendaftaran dari Ketua. Peran yang bisa dipilih: anggota atau pj."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup. Pendaftaran tidak dibuka."}), 409
    data = request.get_json(silent=True) or {}
    peran = str(data.get("peran") or "").strip()
    if peran not in ("anggota", "pj"):
        return jsonify({"error": "Pilih peran: anggota atau PJ. Koordinator ditetapkan Ketua acara."}), 400
    if PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first():
        return jsonify({"error": "Kamu sudah terdaftar di acara ini."}), 409
    kunci = f"gabung:{oid}:{event_id}"
    if _too_many_fails(kunci):
        return jsonify({"error": "Terlalu banyak percobaan password. Coba lagi dalam 5 menit."}), 429
    password = str(data.get("password") or "")
    if not event.password_hash or not check_password_hash(event.password_hash, password):
        _login_fails.setdefault(kunci, []).append(time.time())
        return jsonify({"error": "Password acara salah."}), 401
    _login_fails.pop(kunci, None)
    pa = PeranAcara(event_id=event_id, orang_id=oid, peran=peran)
    db.session.add(pa)
    db.session.flush()
    _riwayat_simpan(event_id, "Gabung acara", _keadaan_kosong(event_id, "peran", pa.id), _ambil_keadaan(event_id, [("peran", pa.id)]))
    db.session.commit()
    return jsonify({"event_id": event_id, "peran": peran}), 201


@app.route("/api/events/<event_id>/tutup", methods=["POST"])
@ketua_only
def tutup_acara(event_id):
    """Tutup acara: semua peran kembali ke default (anggota, seksi tetap), dan peran tidak bisa diubah sampai acara dibuka lagi."""
    if not db.session.get(Event, event_id):
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    if _acara_tertutup(event_id):
        return jsonify({"error": "Acara sudah ditutup."}), 409
    refs = [("peran", b.id) for b in PeranAcara.query.filter_by(event_id=event_id).all()]
    sebelum_tutup = _ambil_keadaan(event_id, refs, tertutup=False)
    dikembalikan = PeranAcara.query.filter(PeranAcara.event_id == event_id, PeranAcara.peran != "ketua").update(
        {"peran": aturan_peran.PERAN_DEFAULT}, synchronize_session=False)
    db.session.add(EventArsip(event_id=event_id))
    db.session.flush()
    db.session.expire_all()
    _riwayat_simpan(event_id, "Tutup acara", sebelum_tutup, _ambil_keadaan(event_id, refs, tertutup=True))
    db.session.commit()
    return jsonify({"success": True, "peran_dikembalikan_ke_default": dikembalikan})


@app.route("/api/events/<event_id>/buka", methods=["POST"])
@ketua_only
def buka_acara(event_id):
    arsip = db.session.get(EventArsip, event_id)
    if not arsip:
        return jsonify({"error": "Acara belum ditutup."}), 409
    _riwayat_simpan(arsip.event_id, "Buka acara", _ambil_keadaan(arsip.event_id, [], tertutup=True),
                    _ambil_keadaan(arsip.event_id, [], tertutup=False))
    db.session.delete(arsip)
    db.session.commit()
    return jsonify({"success": True})










# ============================================================
# AKUN SEKSI (PASSWORD)
# ============================================================



# ============================================================
# ALAT PER SEKSI: rundown, tata tertib, konsumsi, konsep PDD, LPJ, keuangan, pantau
# ============================================================

























# ------------------------------------------------------------ Keuangan (Bendahara)























# ============================================================
# PESAN DAN PERINGATAN DARI KETUA KE ANGGOTA
# ============================================================

TINGKAT_PESAN = {"info", "pengingat", "peringatan"}


def pembaca_saya():
    """Kunci pembaca untuk penanda sudah dibaca: id orang, atau seksi, atau ketua."""
    if is_ketua():
        return "ketua"
    if session.get("peran") == "wakil_ketua":
        return "wakil"
    if session.get("anggota_id"):
        return session["anggota_id"]
    return f"seksi:{current_role()}"


def boleh_kirim_ke(seksi):
    return is_ketua() or session.get("peran") == "wakil_ketua" or (session.get("peran") == "koordinator" and role_owns(seksi))


def pesan_untuk_saya(q):
    if bisa_lihat_semua():
        return q
    seksi = (current_role() or "").lower()
    kondisi = [db.func.lower(Pesan.ke_seksi) == seksi, Pesan.ke_seksi.is_(None)]
    if session.get("anggota_id"):
        kondisi.append(Pesan.ke_anggota_id == session["anggota_id"])
    return q.filter(db.or_(*kondisi))


def pengirim_saya():
    if is_ketua():
        return "ketua"
    if session.get("peran") == "wakil_ketua":
        return "wakil"
    if session.get("anggota_id"):
        return f"anggota:{session['anggota_id']}"
    return f"seksi:{current_role()}"


def pesan_dict(p, dibaca_set):
    return {"id": p.id, "dari": p.dari, "tingkat": p.tingkat, "isi": p.isi, "bisa_diubah": p.pengirim == pengirim_saya(),
            "ke": p.ke_anggota_id and "anggota" or (p.ke_seksi and f"seksi:{p.ke_seksi}") or "semua",
            "ke_seksi": p.ke_seksi, "ke_anggota_id": p.ke_anggota_id,
            "waktu": p.created_at.isoformat() if p.created_at else None, "dibaca": p.id in dibaca_set}


def _dibaca_saya():
    return {b.pesan_id for b in PesanBaca.query.filter_by(pembaca=pembaca_saya()).all()}


@app.route("/api/pesan", methods=["GET"])
def daftar_pesan():
    event_id = request.args.get("event_id")
    q = Pesan.query
    if event_id:
        q = q.filter_by(event_id=event_id)
    rows = pesan_untuk_saya(q).order_by(Pesan.created_at.desc()).limit(100).all()
    dibaca = _dibaca_saya()
    return jsonify({"pesan": [pesan_dict(p, dibaca) for p in rows],
                    "belum_dibaca": sum(1 for p in rows if p.id not in dibaca)})


@app.route("/api/pesan", methods=["POST"])
def kirim_pesan():
    data = request.get_json(silent=True) or {}
    event_id = str(data.get("event_id") or "").strip()
    if not db.session.get(Event, event_id):
        return jsonify({"error": "Pilih acara dulu."}), 400
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu bukan anggota acara ini."}), 403
    try:
        isi = clean_text(data.get("isi"), 500, "Isi pesan", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    tingkat = str(data.get("tingkat", "info")).lower()
    if tingkat not in TINGKAT_PESAN:
        return jsonify({"error": "Tingkat harus info, pengingat, atau peringatan."}), 400
    ke = str(data.get("ke", "semua"))
    ke_seksi, ke_anggota_id = None, None
    if ke.startswith("seksi:"):
        ke_seksi = ke.split(":", 1)[1].strip()[:64]
    elif ke.startswith("orang:"):
        oid_tujuan = ke.split(":", 1)[1].strip()
        baris_tujuan = PeranAcara.query.filter_by(event_id=event_id, orang_id=oid_tujuan).first()
        if not baris_tujuan:
            return jsonify({"error": "Peserta tidak ditemukan di acara ini."}), 404
        ke_seksi, ke_anggota_id = baris_tujuan.seksi, baris_tujuan.orang_id
    elif ke != "semua":
        return jsonify({"error": "Tujuan tidak dikenal."}), 400
    _peran_pengirim = _peran_di(event_id)
    if _peran_pengirim not in ("ketua", "wakil_ketua") and (ke_seksi is None or not boleh_kirim_ke(ke_seksi)):
        return jsonify({"error": "Kamu hanya bisa mengirim pesan ke seksimu sendiri."}), 403
    p = Pesan(event_id=event_id, dari=("Ketua Pelaksana" if _peran_pengirim == "ketua" else "Wakil Ketua" if _peran_pengirim == "wakil_ketua" else current_role() + (" (koordinator)" if session.get("peran") == "koordinator" else "")),
              ke_seksi=ke_seksi, ke_anggota_id=ke_anggota_id, tingkat=tingkat, isi=isi, pengirim=pengirim_saya())
    db.session.add(p)
    db.session.commit()
    return jsonify({"id": p.id}), 201


@app.route("/api/pesan/<pesan_id>", methods=["PATCH"])
def ubah_pesan(pesan_id):
    """Pengirim atau Ketua bisa memperbaiki isi atau tingkat pesan yang sudah terkirim."""
    p = db.session.get(Pesan, pesan_id)
    if not p:
        return jsonify({"error": "Pesan tidak ditemukan."}), 404
    if not (_peran_di(p.event_id) == "ketua" or p.pengirim == pengirim_saya()):
        return jsonify({"error": "Hanya pengirim atau Ketua yang bisa mengubah pesan ini."}), 403
    _sebelum_pesan = {"isi": p.isi, "tingkat": p.tingkat}
    data = request.get_json(silent=True) or {}
    if "isi" in data:
        try:
            p.isi = clean_text(data.get("isi"), 500, "Isi pesan", required=True)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    if "tingkat" in data:
        if str(data["tingkat"]).lower() not in TINGKAT_PESAN:
            return jsonify({"error": "Tingkat harus info, pengingat, atau peringatan."}), 400
        p.tingkat = str(data["tingkat"]).lower()
    catat_perubahan(_sebelum_pesan, {"isi": p.isi, "tingkat": p.tingkat})
    db.session.commit()
    return jsonify({"id": p.id, "isi": p.isi, "tingkat": p.tingkat})


@app.route("/api/pesan/<pesan_id>", methods=["DELETE"])
def tarik_pesan(pesan_id):
    """Tarik pesan yang sudah terkirim. Pesan yang ditarik hilang dari kotak masuk semua penerima."""
    p = db.session.get(Pesan, pesan_id)
    if not p:
        return jsonify({"error": "Pesan tidak ditemukan."}), 404
    if not (_peran_di(p.event_id) == "ketua" or p.pengirim == pengirim_saya()):
        return jsonify({"error": "Hanya pengirim atau Ketua yang bisa menarik pesan ini."}), 403
    PesanBaca.query.filter_by(pesan_id=pesan_id).delete()
    db.session.delete(p)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/pesan/<pesan_id>/baca", methods=["POST"])
def tandai_dibaca(pesan_id):
    p = db.session.get(Pesan, pesan_id)
    if not p:
        return jsonify({"error": "Pesan tidak ditemukan."}), 404
    if not pesan_untuk_saya(Pesan.query.filter_by(id=pesan_id)).first():
        return jsonify({"error": "Pesan ini bukan untukmu."}), 403
    pembaca = pembaca_saya()
    if not PesanBaca.query.filter_by(pesan_id=pesan_id, pembaca=pembaca).first():
        db.session.add(PesanBaca(pesan_id=pesan_id, pembaca=pembaca))
        db.session.commit()
    return jsonify({"success": True})


@app.route("/api/pesan/otomatis", methods=["POST"])
def peringatan_otomatis():
    """Ketua mengirim peringatan ke setiap seksi yang punya tugas lewat deadline."""
    data = request.get_json(silent=True) or {}
    ev = db.session.get(Event, str(data.get("event_id") or ""))
    if not ev:
        return jsonify({"error": "Pilih acara dulu."}), 400
    if _peran_di(ev.id) != "ketua":
        return jsonify({"error": "Hanya Ketua Pelaksana di acara ini."}), 403
    now = datetime.utcnow()
    per_seksi = {}
    for t in Task.query.filter_by(event_id=ev.id).all():
        if t.status != "done" and t.deadline_iso and datetime.fromisoformat(t.deadline_iso) < now:
            per_seksi.setdefault(t.divisi or "Umum", []).append(t.judul)
    dibuat = []
    for seksi, judul in per_seksi.items():
        contoh = ", ".join(judul[:3]) + (" dan lainnya" if len(judul) > 3 else "")
        isi = f"{len(judul)} tugas sudah lewat deadline: {contoh}. Mohon segera diselesaikan atau kabari Ketua kalau ada kendala."
        p = Pesan(event_id=ev.id, dari="Ketua Pelaksana", ke_seksi=seksi, tingkat="peringatan", isi=isi[:500], pengirim="ketua")
        db.session.add(p)
        dibuat.append(seksi)
    db.session.commit()
    return jsonify({"dikirim_ke": dibuat, "jumlah": len(dibuat)})


# ============================================================
# PERINTAH DAN KOMENTAR DI TUGAS
# ============================================================

@app.route("/api/tasks/<task_id>/komentar", methods=["GET"])
def daftar_komentar(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    if not _di_acara(task.event_id):
        return jsonify({"error": "Tugas ini bukan milik acara yang kamu ikuti."}), 403
    if not (bisa_lihat_semua() or role_owns(task.divisi)):
        return jsonify({"error": "Tugas ini bukan milik seksimu."}), 403
    rows = TaskKomentar.query.filter_by(task_id=task_id).order_by(TaskKomentar.created_at).all()
    return jsonify({"komentar": [{"id": k.id, "dari": k.dari, "jenis": k.jenis, "isi": k.isi,
                                  "waktu": k.created_at.isoformat() if k.created_at else None} for k in rows]})


@app.route("/api/tasks/<task_id>/komentar", methods=["POST"])
def tulis_komentar(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    if not _di_acara(task.event_id):
        return jsonify({"error": "Tugas ini bukan milik acara yang kamu ikuti."}), 403
    data = request.get_json(silent=True) or {}
    try:
        isi = clean_text(data.get("isi"), 1000, "Isi", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if _peran_di(task.event_id) == "ketua":
        jenis = "perintah" if str(data.get("jenis", "perintah")).lower() == "perintah" else "komentar"
        dari = "Ketua Pelaksana"
    elif session.get("peran") == "wakil_ketua":
        jenis = "perintah" if str(data.get("jenis", "perintah")).lower() == "perintah" else "komentar"
        dari = "Wakil Ketua"
    elif role_owns(task.divisi):
        jenis = "komentar"
        dari = current_role() + (" (koordinator)" if session.get("peran") == "koordinator" else "")
    else:
        return jsonify({"error": "Tugas ini bukan milik seksimu."}), 403
    k = TaskKomentar(task_id=task_id, dari=dari, jenis=jenis, isi=isi)
    db.session.add(k)
    db.session.commit()
    return jsonify({"id": k.id}), 201


# ============================================================
# LOG AKTIVITAS (AUDIT TRAIL)
# ============================================================

AUDIT_REDAKSI = ("password", "token", "kredensial", "hash")


def _redaksi(obj):
    """Sembunyikan nilai rahasia dan batasi panjang agar log tidak membengkak."""
    if isinstance(obj, dict):
        return {k: ("***" if any(x in str(k).lower() for x in AUDIT_REDAKSI) else _redaksi(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redaksi(x) for x in obj[:50]]
    if isinstance(obj, str):
        return obj[:300]
    return obj


def catat_perubahan(sebelum, sesudah):
    """Simpan sebelum dan sesudah untuk field yang berubah. Dicatat ke log aktivitas oleh catat_audit."""
    dif = {k: {"sebelum": sebelum.get(k), "sesudah": sesudah.get(k)}
           for k in set(sebelum) | set(sesudah) if sebelum.get(k) != sesudah.get(k)}
    if dif:
        g.audit_perubahan = json.dumps(_redaksi(dif), ensure_ascii=False, default=str)[:4000]


@app.after_request
def catat_audit(resp):
    """Mencatat aksi tulis yang berhasil, dan percobaan masuk yang gagal. Kegagalan pencatatan tidak menggagalkan permintaan."""
    try:
        gagal_masuk = request.path.startswith("/api/auth/") and resp.status_code in (401, 429)
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path.startswith("/api/") and (resp.status_code < 400 or gagal_masuk):
            if gagal_masuk:
                aktor, peran = "tamu (gagal masuk)", "tamu"
            elif is_ketua():
                aktor, peran = "Ketua Pelaksana", "ketua"
            elif current_role():
                aktor = current_role() + (" (anggota)" if session.get("anggota_id") else "")
                peran = session.get("peran") or "seksi"
            else:
                aktor, peran = "tamu", "tamu"
            body = request.get_json(silent=True)
            meta = json.dumps(_redaksi(body), ensure_ascii=False) if body is not None else None
            target = next((p for p in request.path.split("/") if re.match(r"^[0-9a-f-]{36}$", p)), None)
            db.session.add(AuditLog(aktor=aktor[:128], peran=peran[:32], aksi=request.method, rute=request.path[:255],
                                    target=target, status=resp.status_code, ip=(request.remote_addr or "")[:64],
                                    metadata_json=meta, perubahan=getattr(g, "audit_perubahan", None)))
            db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print("[AUDIT] gagal mencatat:", exc)
    return resp




# ============================================================
# PEMBAGIAN TUGAS KE ANGGOTA DAN HASIL KERJA ANGGOTA
# ============================================================



@app.route("/api/tasks/<task_id>/tugaskan", methods=["POST"])
def tugaskan_tugas(task_id):
    """Ketua atau koordinator seksi membagi tugas ke satu akun user yang terdaftar di acara ini.
    Penerima lalu wajib menerima atau menolak tugas itu. Kirim orang_id null untuk melepas tugas."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    if not _di_acara(task.event_id):
        return jsonify({"error": "Tugas ini bukan milik acara yang kamu ikuti."}), 403
    if not (_peran_di(task.event_id) == "ketua" or _seksi_di(task.event_id, task.divisi)):
        return jsonify({"error": "Hanya Ketua atau koordinator seksi ini yang bisa membagi tugas."}), 403
    data = request.get_json(silent=True) or {}
    orang_id = data.get("orang_id") or None
    if orang_id:
        baris = PeranAcara.query.filter_by(event_id=task.event_id, orang_id=orang_id).first()
        if not baris:
            return jsonify({"error": "Orang ini belum terdaftar di acara ini."}), 400
        if task.penerima_orang_id != orang_id:
            task.penerima_ditugaskan_pada = datetime.utcnow()
            task.konfirmasi = None
            task.konfirmasi_alasan = None
            task.konfirmasi_pada = None
        task.penerima_orang_id = orang_id
    else:
        task.penerima_orang_id = None
        task.penerima_ditugaskan_pada = None
        task.konfirmasi = None
        task.konfirmasi_alasan = None
        task.konfirmasi_pada = None
    db.session.commit()
    return jsonify(task.to_dict())


@app.route("/api/tasks/<task_id>/konfirmasi", methods=["POST"])
def konfirmasi_tugas(task_id):
    """Penerima tugas menerima atau menolak tugas yang dibagikan kepadanya."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    if not _di_acara(task.event_id):
        return jsonify({"error": "Tugas ini bukan milik acara yang kamu ikuti."}), 403
    oid = _orang_login()
    if not oid or task.penerima_orang_id != oid:
        return jsonify({"error": "Tugas ini tidak dibagikan kepadamu."}), 403
    data = request.get_json(silent=True) or {}
    aksi = data.get("aksi")
    if aksi == "terima":
        task.konfirmasi = "diterima"
        task.konfirmasi_alasan = None
    elif aksi == "tolak":
        try:
            alasan = clean_text(data.get("alasan"), 500, "Alasan", required=True)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        task.konfirmasi = "ditolak"
        task.konfirmasi_alasan = alasan
    else:
        return jsonify({"error": "Aksi harus terima atau tolak."}), 400
    task.konfirmasi_pada = datetime.utcnow()
    db.session.commit()
    return jsonify(task.to_dict())


@app.route("/api/events/<event_id>/tindak-lanjut", methods=["GET"])
@ketua_only
def tindak_lanjut_acara(event_id):
    """Daftar yang harus ditindaklanjuti Ketua: belum dibagi, belum dikonfirmasi lebih dari 24 jam,
    ditolak penerimanya, dan terlambat."""
    if event_id != session.get("event_id"):
        return jsonify({"error": "Acara tidak ditemukan."}), 404
    now = datetime.utcnow()
    tugas = Task.query.filter(Task.event_id == event_id, Task.status != "done").all()
    orang_nama = {o.id: o.nama for o in Orang.query.all()}
    def item(t, alasan):
        return {"id": t.id, "judul": t.judul, "seksi": t.divisi, "deadline_iso": t.deadline_iso,
                "penerima": orang_nama.get(t.penerima_orang_id) if t.penerima_orang_id else None,
                "alasan": alasan}
    belum_dibagi, belum_konfirmasi, ditolak, terlambat = [], [], [], []
    for t in tugas:
        if not t.penerima_orang_id:
            belum_dibagi.append(item(t, None))
        elif t.konfirmasi == "ditolak":
            ditolak.append(item(t, t.konfirmasi_alasan))
        elif t.konfirmasi is None and t.penerima_ditugaskan_pada and now - t.penerima_ditugaskan_pada > timedelta(hours=24):
            belum_konfirmasi.append(item(t, None))
        if t.deadline_iso:
            try:
                if datetime.fromisoformat(t.deadline_iso) < now:
                    terlambat.append(item(t, None))
            except ValueError:
                pass
    return jsonify({"belum_dibagi": belum_dibagi[:50], "belum_konfirmasi": belum_konfirmasi[:50],
                    "ditolak": ditolak[:50], "terlambat": terlambat[:50]})


@app.route("/api/seksi/hasil", methods=["GET"])
def hasil_seksi():
    """Hasil kerja tiap anggota di seksi yang dikoordinasi (atau semua seksi untuk Ketua)."""
    if _peran_di(request.args.get("event_id")) not in ("ketua", "koordinator"):
        return jsonify({"error": "Hanya Ketua atau koordinator seksi."}), 403
    q = visible_tasks_query(request.args.get("event_id"))
    rows = q.order_by(Task.deadline_iso).all()
    nama = {o.id: o.nama for o in Orang.query.all()}
    hasil = []
    for t in rows:
        hasil.append({"id": t.id, "judul": t.judul, "seksi": t.divisi, "status": t.status,
                      "anggota_id": t.penerima_orang_id, "anggota": nama.get(t.penerima_orang_id) or "Belum dibagi",
                      "hasil_url": t.hasil_url, "hasil_catatan": t.hasil_catatan,
                      "hasil_dikirim_pada": t.hasil_dikirim_pada.isoformat() if t.hasil_dikirim_pada else None})
    return jsonify({"hasil": hasil})


# ============================================================
# DAMPAK BERKELANJUTAN (SDG) — checklist yang bisa dicentang panitia
# ============================================================

DAMPAK_ITEMS = [
    {"key": "undangan_digital", "label": "Undangan dan materi dibagikan digital (tanpa cetak)", "sdg": "SDG 12"},
    {"key": "sertifikat_digital", "label": "Sertifikat dikirim secara digital", "sdg": "SDG 12"},
    {"key": "bebas_plastik_sekali_pakai", "label": "Bebas plastik sekali pakai", "sdg": "SDG 12"},
    {"key": "konsumsi_ramah_lingkungan", "label": "Konsumsi tanpa styrofoam", "sdg": "SDG 12"},
    {"key": "pemilahan_sampah", "label": "Tersedia pemilahan sampah di lokasi", "sdg": "SDG 11"},
    {"key": "akses_inklusif", "label": "Akses ramah difabel (jalur kursi roda, kursi prioritas)", "sdg": "SDG 10"},
    {"key": "materi_terbuka", "label": "Materi belajar dibagikan secara terbuka", "sdg": "SDG 4"},
    {"key": "kolaborasi_komunitas", "label": "Melibatkan komunitas atau mitra lokal", "sdg": "SDG 17"},
]


def dampak_summary(event):
    try:
        pilihan = json.loads(event.dampak_json or "{}")
    except (ValueError, TypeError):
        pilihan = {}
    items = [{**item, "aktif": bool(pilihan.get(item["key"]))} for item in DAMPAK_ITEMS]
    aktif = sum(1 for i in items if i["aktif"])
    return {
        "items": items,
        "aktif": aktif,
        "total": len(items),
        "skor_persen": round(aktif / len(items) * 100, 1),
    }






# ============================================================
# INTEROPERABILITAS: kalender (ICS) dan ekspor CSV
# ============================================================

def ics_escape(text):
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.route("/api/events/<event_id>/calendar.ics", methods=["GET"])
def event_calendar(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan"}), 404
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu belum terdaftar di acara ini."}), 403
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Caby Organizer//UINIC 8.0//ID",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{ics_escape(event.nama)}",
    ]
    for task in visible_tasks_query(event.id).all():
        if not task.deadline_iso:
            continue
        try:
            start = datetime.fromisoformat(task.deadline_iso)
        except ValueError:
            continue
        end = start + timedelta(hours=1)
        status = "Selesai" if task.status == "done" else "Belum selesai"
        seksi_txt = task.divisi or "-"
        pic_txt = task.pic or "-"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{task.id}@capy-organizer",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{ics_escape(task.judul)}",
            f"DESCRIPTION:{ics_escape(f'Seksi: {seksi_txt}; PIC: {pic_txt}; Status: {status}')}",
            "BEGIN:VALARM",
            "TRIGGER:-PT1H",
            "ACTION:DISPLAY",
            "DESCRIPTION:Pengingat tugas Capy",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"
    return Response(body, mimetype="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="{event.id}.ics"'})




# ============================================================
# STRUKTUR KEPANITIAAN & PERENCANAAN TUGAS
# ============================================================

SEKSI_DEFAULT = ["Ketua Pelaksana", "Sekretaris", "Bendahara", "Humas", "Acara", "Konsumsi", "Keamanan", "Perlengkapan", "PDD"]


def load_struktur(event):
    """Struktur tersimpan, atau daftar sie standar dengan PIC kosong."""
    try:
        saved = json.loads(event.struktur_json or "[]")
    except (ValueError, TypeError):
        saved = []
    if saved:
        return saved
    return [{"seksi": s, "pic": ""} for s in SEKSI_DEFAULT]




@app.route("/api/events/<event_id>/struktur", methods=["GET"])
def get_struktur(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan"}), 404
    if not _di_acara(event_id):
        return jsonify({"error": "Kamu belum terdaftar di acara ini."}), 403
    return jsonify({"struktur": load_struktur(event)})


@app.route("/api/events/<event_id>/struktur", methods=["PUT"])
@ketua_only
def set_struktur(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Acara tidak ditemukan"}), 404
    incoming = (request.get_json(silent=True) or {}).get("struktur", [])
    if not isinstance(incoming, list) or len(incoming) > 20:
        return jsonify({"error": "Struktur harus berupa daftar maksimal 20 sie"}), 400
    cleaned = []
    try:
        for item in incoming:
            if not isinstance(item, dict):
                raise ValueError("Format sie tidak valid")
            seksi = clean_text(item.get("seksi"), 64, "Nama sie", required=True)
            pic = clean_text(item.get("pic"), 128, "PIC")
            cleaned.append({"seksi": seksi, "pic": pic})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    event.struktur_json = json.dumps(cleaned)
    db.session.commit()
    return jsonify({"struktur": load_struktur(event)})















# ============================================================
# ASISTEN CAPY: tanya jawab untuk panitia, dengan pencarian web (opsional)
# ============================================================
# Asisten Capy (mode demo): memakai Ollama lokal. Gratis, tanpa pencarian web.
# Untuk produksi, ganti dengan layanan model yang stabil (berbayar) dan tambahkan pencarian web.
def _konfigurasi_ollama(env):
    api_key = env.get("OLLAMA_API_KEY", "")
    url = env.get("OLLAMA_URL")
    cloud = "ollama.com" in url if url is not None else bool(api_key)
    if url is None:
        url = "https://ollama.com/api/chat" if cloud else "http://localhost:11434/api/chat"
    model = env.get("OLLAMA_MODEL", "gpt-oss:20b-cloud" if cloud else "llama3.1")
    return {
        "url": url,
        "api_key": api_key,
        "model": model,
        "chat_model": env.get("CAPY_MODEL_OBROLAN", model),
        "event_model": env.get("CAPY_MODEL_ACARA", model),
    }


_OLLAMA_CONFIG = _konfigurasi_ollama(os.environ)
OLLAMA_URL = _OLLAMA_CONFIG["url"]
OLLAMA_MODEL = _OLLAMA_CONFIG["model"]
# Dua mode: ngobrol bebas dan kerja di acara (wajib mendukung alat). Jika tidak diisi, memakai model default.
CAPY_MODEL_OBROLAN = _OLLAMA_CONFIG["chat_model"]
CAPY_MODEL_ACARA = _OLLAMA_CONFIG["event_model"]
OLLAMA_API_KEY = _OLLAMA_CONFIG["api_key"]  # kosong untuk Ollama lokal
ASISTEN_MAKS_PER_MENIT = int(os.environ.get("ASISTEN_MAKS_PER_MENIT", "20"))
_asisten_pemakaian = {}  # oid -> [waktu, ...]
app.logger.info(
    "Capy Ollama config loaded: %s; models=%s",
    "cloud" if "ollama.com" in OLLAMA_URL else "local",
    ", ".join(sorted({OLLAMA_MODEL, CAPY_MODEL_OBROLAN, CAPY_MODEL_ACARA})),
)


def _pesan_galat_asisten(exc):
    """Pesan yang menjelaskan penyebab gagal, sesuai jenisnya (kunci, model, koneksi, atau server)."""
    cloud = "ollama.com" in (OLLAMA_URL or "")
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        kode = exc.response.status_code
        detail = ""
        try:
            detail = (exc.response.json().get("error") or "")[:160]
        except ValueError:
            detail = (exc.response.text or "")[:160]
        if kode in (401, 403):
            return "Kunci OLLAMA_API_KEY ditolak. Periksa kunci di agent-backend/.env, lalu jalankan ulang backend." + (f" ({detail})" if detail else "")
        if kode == 404:
            if any(kata in detail.lower() for kata in ("endpoint", "route", "path")):
                return "Endpoint Ollama tidak ditemukan. Periksa OLLAMA_URL; Ollama Cloud memakai https://ollama.com/api/chat." + (f" ({detail})" if detail else "")
            return f"Model '{OLLAMA_MODEL}' tidak ditemukan di Ollama. Untuk Cloud, gunakan tag API yang valid, misalnya gpt-oss:20b-cloud (bukan gpt-oss:20b:cloud)." + (f" ({detail})" if detail else "")
        if kode == 429:
            return "Batas pemakaian Ollama tercapai. Coba lagi beberapa saat lagi."
        return f"Ollama menolak permintaan (kode {kode})." + (f" {detail}" if detail else "")
    if isinstance(exc, requests.Timeout):
        return "Ollama terlalu lama menjawab. Coba lagi, atau gunakan pertanyaan yang lebih pendek."
    if cloud:
        return "Tidak bisa terhubung ke Ollama Cloud. Periksa koneksi internet server dan OLLAMA_URL di .env."
    return "Tidak bisa terhubung ke Ollama lokal. Pastikan Ollama berjalan (ollama serve) dan model sudah diunduh (ollama pull " + OLLAMA_MODEL + ")."


def _asisten_siap():
    """Ollama dianggap siap jika alamatnya diisi. Jika tidak terjangkau, panggilan akan memberi galat sendiri."""
    return bool(OLLAMA_URL)


def _asisten_boleh(oid):
    now = time.time()
    recent = [t for t in _asisten_pemakaian.get(oid, []) if now - t < 60]
    _asisten_pemakaian[oid] = recent
    if len(recent) >= ASISTEN_MAKS_PER_MENIT:
        return False
    recent.append(now)
    return True


def _konteks_acara(eid=None):
    """Ringkasan satu acara untuk model. Hanya acara yang boleh dilihat user ini; kosong untuk percakapan umum."""
    eid = eid or session.get("event_id")
    oid = session.get("orang_id")
    if not eid or not oid:
        return ""
    ev = db.session.get(Event, eid)
    baris = PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first()
    if not ev or not baris:
        return ""
    tugas = Task.query.filter_by(event_id=eid).all()
    selesai = sum(1 for t in tugas if t.status == "done")
    return (f"Acara: {ev.nama} (id {ev.id}, tanggal {ev.tanggal or 'belum ditentukan'}, lokasi {ev.lokasi or 'belum ditentukan'}). "
            f"Peran saya: {baris.peran}, seksi: {baris.seksi or '-'}. "
            f"Seksi yang tersedia: {', '.join(aturan_peran.SEKSI)}. "
            f"Tugas: {len(tugas)} total, {selesai} selesai.")


# ============================================================
# RIWAYAT: batalkan dan ulangi perubahan (per acara, per orang)
# ============================================================
MODEL_RIWAYAT = {"task": Task, "peran": PeranAcara, "keputusan": KeputusanAcara, "event": Event}


def _rekam_baris(m, id_):
    obj = db.session.get(MODEL_RIWAYAT[m], id_)
    if obj is None:
        return None
    return {c.name: (getattr(obj, c.name).isoformat() if isinstance(getattr(obj, c.name), datetime) else getattr(obj, c.name))
            for c in obj.__table__.columns}


def _ambil_keadaan(event_id, refs, tertutup=None):
    return {"event_id": event_id, "tertutup": tertutup,
            "items": [{"m": m, "id": i, "row": _rekam_baris(m, i)} for m, i in refs]}


def _keadaan_kosong(event_id, m, id_):
    """Keadaan sebelum sebuah baris dibuat: tidak ada."""
    return {"event_id": event_id, "tertutup": None, "items": [{"m": m, "id": id_, "row": None}]}


def _terapkan_keadaan(keadaan):
    eid = keadaan["event_id"]
    for it in keadaan["items"]:
        M = MODEL_RIWAYAT[it["m"]]
        obj = db.session.get(M, it["id"])
        if it.get("parsial"):  # hanya kolom yang tercatat yang dikembalikan
            for k, v in it["row"].items():
                setattr(obj, k, v)
            db.session.add(obj)
            continue
        if it["row"] is None:
            if obj is not None:
                db.session.delete(obj)
            continue
        if obj is None:
            obj = M(id=it["id"])
        for col in M.__table__.columns:
            if col.name in it["row"]:
                v = it["row"][col.name]
                if isinstance(col.type, db.DateTime) and isinstance(v, str):
                    v = datetime.fromisoformat(v)
                setattr(obj, col.name, v)
        db.session.add(obj)
    if keadaan.get("tertutup") is not None:
        arsip = db.session.get(EventArsip, eid)
        if keadaan["tertutup"] and arsip is None:
            db.session.add(EventArsip(event_id=eid))
        if not keadaan["tertutup"] and arsip is not None:
            db.session.delete(arsip)
    db.session.flush()


def _riwayat_simpan(event_id, label, sebelum, sesudah):
    """Catat satu perubahan. Mengulang kini dihapus: perubahan baru menghapus riwayat ulang yang lama."""
    if not event_id:
        return
    oid = session.get("orang_id")
    RiwayatAksi.query.filter_by(event_id=event_id, orang_id=oid, undone=True).delete()
    db.session.add(RiwayatAksi(event_id=event_id, orang_id=oid, label=label[:255],
                               before=json.dumps(sebelum, ensure_ascii=False, default=str),
                               after=json.dumps(sesudah, ensure_ascii=False, default=str),
                               undone=False, created_at=datetime.utcnow()))


def _riwayat_pindah(event_id, arah):
    """arah 'batal' atau 'ulang'. Kembalikan (label, galat)."""
    oid = _orang_login()
    if not oid:
        return None, ("Masuk dulu.", 401)
    if not PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first():
        return None, ("Kamu tidak terdaftar di acara ini.", 403)
    undone_nilai = arah == "ulang"
    r = RiwayatAksi.query.filter_by(event_id=event_id, orang_id=oid, undone=undone_nilai).order_by(RiwayatAksi.id.desc()).first()
    if not r:
        return None, ("Tidak ada yang bisa diulang." if undone_nilai else "Tidak ada yang bisa dibatalkan.", 409)
    # Acara yang sudah ditutup dibekukan. Hanya penutupan dan pembukaannya sendiri yang boleh dibatalkan/diulang.
    if _acara_tertutup(event_id) and r.label not in ("Tutup acara", "Buka acara"):
        return None, ("Acara sudah ditutup. Hanya penutupan atau pembukaan acara yang bisa dibatalkan.", 409)
    _terapkan_keadaan(json.loads(r.after if undone_nilai else r.before))
    r.undone = not undone_nilai
    db.session.commit()
    return r.label, None


@app.route("/api/riwayat", methods=["GET"])
def riwayat_status():
    """Apa yang bisa dibatalkan dan diulang oleh user ini di acara itu."""
    oid = _orang_login()
    eid = str(request.args.get("event_id") or "")
    if not oid or not PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first():
        return jsonify({"error": "Kamu tidak terdaftar di acara ini."}), 403
    batal = RiwayatAksi.query.filter_by(event_id=eid, orang_id=oid, undone=False).order_by(RiwayatAksi.id.desc()).first()
    ulang = RiwayatAksi.query.filter_by(event_id=eid, orang_id=oid, undone=True).order_by(RiwayatAksi.id.desc()).first()
    return jsonify({"batal": batal.label if batal else None, "ulang": ulang.label if ulang else None})


@app.route("/api/riwayat/batal", methods=["POST"])
def riwayat_batal():
    label, galat = _riwayat_pindah(str((request.get_json(silent=True) or {}).get("event_id") or ""), "batal")
    if galat:
        return jsonify({"error": galat[0]}), galat[1]
    return jsonify({"label": label})


@app.route("/api/riwayat/ulang", methods=["POST"])
def riwayat_ulang():
    label, galat = _riwayat_pindah(str((request.get_json(silent=True) or {}).get("event_id") or ""), "ulang")
    if galat:
        return jsonify({"error": galat[0]}), galat[1]
    return jsonify({"label": label})


ASISTEN_SISTEM = (
    "Kamu Capy, asisten panitia acara kampus. Jawab dalam Bahasa Indonesia yang singkat dan ramah. "
    "Gunakan alat yang tersedia untuk membaca data acara, membuka halaman, atau mengusulkan perubahan. "
    "Perubahan data hanya diusulkan; pengguna yang menjalankannya. Jangan mengarang data acara: "
    "jika data belum ada di hasil alat, katakan belum tahu. Jika pertanyaan tidak butuh data acara, jawab langsung. "
    "Jika diminta membuat tugas untuk semua sie, buat satu usulan untuk setiap seksi yang tercantum di konteks acara; jangan melewatkan atau menambahkan seksi."
)
AGEN_HALAMAN = {"dashboard": "/dashboard", "beranda": "/beranda", "ruang_kerja": "/kerja", "daftar_acara": "/events"}
AGEN_MAKS_LANGKAH = max(4, len(aturan_peran.SEKSI) + 2)


def _agen_alat_definisi():
    def f(nama, deskripsi, props, wajib=()):
        return {"type": "function", "function": {"name": nama, "description": deskripsi,
                "parameters": {"type": "object", "properties": props, "required": list(wajib)}}}
    teks = {"type": "string"}
    return [
        f("cari_acara", "Daftar acara yang saya ikuti beserta peran saya di tiap acara.", {}),
        f("ringkasan_acara", "Ringkasan satu acara: jumlah tugas, selesai, terlambat, dan belum dibagi.",
          {"event_id": teks}, ["event_id"]),
        f("daftar_tugas", "Daftar tugas di satu acara (maksimal 30).",
          {"event_id": teks, "seksi": teks}, ["event_id"]),
        f("tugas_saya", "Tugas yang dibagikan kepada saya dan belum saya jawab, di satu acara.",
          {"event_id": teks}, ["event_id"]),
        f("buka_halaman", "Buka halaman aplikasi. tujuan: dashboard, beranda, ruang_kerja, daftar_acara, atau acara (dengan event_id).",
          {"tujuan": teks, "event_id": teks}, ["tujuan"]),
        f("usulkan_tugas", "Usulkan tugas baru di satu acara. Hanya Ketua atau koordinator seksi terkait. Belum dibuat sampai pengguna menekan Jalankan.",
          {"event_id": teks, "judul": teks, "seksi": teks, "tenggat": {"type": "string", "description": "YYYY-MM-DDTHH:MM, boleh kosong"}}, ["event_id", "judul", "seksi"]),
        f("usulkan_bagikan_tugas", "Usulkan membagikan tugas kepada satu peserta acara (nama orangnya). Belum berlaku sampai Jalankan.",
          {"task_id": teks, "nama_penerima": teks}, ["task_id", "nama_penerima"]),
        f("usulkan_keputusan", "Usulkan mencatat keputusan rapat di satu acara. Belum tercatat sampai Jalankan.",
          {"event_id": teks, "judul": teks, "isi": teks}, ["event_id", "judul"]),
        f("buat_undangan", "Ambil data acara untuk menulis teks undangan (password tidak disertakan).",
          {"event_id": teks}, ["event_id"]),
        f("buat_laporan", "Siapkan tautan unduh laporan PDF satu acara.",
          {"event_id": teks}, ["event_id"]),
        f("ubah_tugas", "Usulkan mengubah judul, tenggat (YYYY-MM-DDTHH:MM), atau status (pending/done) sebuah tugas. Belum berlaku sampai Jalankan.",
          {"task_id": teks, "judul": teks, "tenggat": teks, "status": teks}, ["task_id"]),
        f("hapus_tugas", "Usulkan menghapus sebuah tugas. Tindakan berbahaya: pengguna akan diminta konfirmasi tambahan.",
          {"task_id": teks}, ["task_id"]),
        f("ubah_peran_peserta", "Usulkan mengubah peran atau seksi peserta acara (dicari dengan nama). Hanya Ketua.",
          {"event_id": teks, "nama": teks, "peran": teks, "seksi": teks}, ["event_id", "nama", "peran"]),
        f("keluarkan_peserta", "Usulkan mengeluarkan peserta acara (dicari dengan nama). Hanya Ketua. Tindakan berbahaya.",
          {"event_id": teks, "nama": teks}, ["event_id", "nama"]),
        f("tutup_acara", "Usulkan menutup acara. Hanya Ketua. Tindakan berbahaya: peran semua peserta kembali ke anggota.",
          {"event_id": teks}, ["event_id"]),
        f("batalkan_terakhir", "Usulkan membatalkan perubahan terakhir kamu di acara ini.",
          {"event_id": teks}, ["event_id"]),
        f("ulangi_terakhir", "Usulkan mengulangi perubahan yang baru dibatalkan.",
          {"event_id": teks}, ["event_id"]),
    ]


def _agen_ambil_acara(event_id):
    """Acara harus diikuti oleh user ini. Kembalikan (peserta, None) atau (None, pesan_galat)."""
    oid = _orang_login()
    if not oid:
        return None, "Masuk dulu."
    baris = PeranAcara.query.filter_by(event_id=event_id, orang_id=oid).first()
    if not baris:
        return None, "Kamu tidak terdaftar di acara itu."
    return baris, None


def _izin_ubah_tugas(t):
    """Ketua, atau koordinator seksi tugas itu. Kembalikan (baris, galat)."""
    baris, galat = _agen_ambil_acara(t.event_id)
    if galat:
        return None, galat
    if baris.peran == "ketua" or (baris.peran == "koordinator" and baris.seksi == t.divisi):
        return baris, None
    return None, "Hanya Ketua atau koordinator seksi tugas ini yang bisa mengubahnya."


def _cari_peserta_nama(eid, nama):
    """Cari peserta acara dengan nama persis (tanpa huruf besar). Harus tepat satu."""
    nama = (nama or "").strip().lower()
    cocok = []
    for p in PeranAcara.query.filter_by(event_id=eid).all():
        o = db.session.get(Orang, p.orang_id)
        if o and (o.nama or "").strip().lower() == nama:
            cocok.append(p)
    if len(cocok) != 1:
        return None, "Nama itu tidak ditemukan tepat satu di acara ini."
    return cocok[0], None


def _agen_jalankan_alat(nama, args):
    """Jalankan satu alat. Hasil baca dikembalikan; navigasi dan usulan dicatat untuk pengguna."""
    args = args or {}
    if nama == "cari_acara":
        oid = _orang_login()
        acara = []
        for b in PeranAcara.query.filter_by(orang_id=oid).all():
            ev = db.session.get(Event, b.event_id)
            if ev:
                acara.append({"event_id": ev.id, "nama": ev.nama, "tanggal": ev.tanggal, "peran": b.peran, "seksi": b.seksi})
        return {"acara": acara}, None
    eid = str(args.get("event_id") or "")
    if nama in ("ringkasan_acara", "daftar_tugas", "tugas_saya"):
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return {"error": galat}, None
        tugas = Task.query.filter_by(event_id=eid).all()
        if nama == "ringkasan_acara":
            sekarang = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
            return {"total": len(tugas), "selesai": sum(t.status == "done" for t in tugas),
                    "terlambat": sum(1 for t in tugas if t.status != "done" and t.deadline_iso and t.deadline_iso < sekarang),
                    "belum_dibagi": sum(1 for t in tugas if not t.penerima_orang_id and t.status != "done")}, None
        if nama == "tugas_saya":
            oid = _orang_login()
            return {"tugas": [{"id": t.id, "judul": t.judul, "tenggat": t.deadline_iso, "konfirmasi": t.konfirmasi}
                              for t in tugas if t.penerima_orang_id == oid and t.konfirmasi is None]}, None
        if args.get("seksi"):
            tugas = [t for t in tugas if (t.divisi or "").lower() == str(args["seksi"]).lower()]
        return {"tugas": [{"id": t.id, "judul": t.judul, "seksi": t.divisi, "tenggat": t.deadline_iso,
                           "status": t.status} for t in tugas[:30]]}, None
    if nama == "buka_halaman":
        tujuan = str(args.get("tujuan") or "")
        if tujuan == "acara":
            baris, galat = _agen_ambil_acara(eid)
            if galat:
                return {"error": galat}, None
            return {"ok": True}, {"jenis": "navigasi", "url": f"/events/{eid}", "label": "Buka acara"}
        if tujuan in AGEN_HALAMAN:
            label = {"dashboard": "Buka dashboard", "beranda": "Buka beranda", "ruang_kerja": "Buka ruang kerja", "daftar_acara": "Buka daftar acara"}[tujuan]
            return {"ok": True}, {"jenis": "navigasi", "url": AGEN_HALAMAN[tujuan], "label": label}
        return {"error": "Halaman itu belum tersedia lewat Capy."}, None
    if nama == "usulkan_tugas":
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return {"error": galat}, None
        seksi = str(args.get("seksi") or "")
        if not (baris.peran == "ketua" or (baris.peran == "koordinator" and baris.seksi == seksi)):
            return {"error": "Hanya Ketua atau koordinator seksi itu yang bisa mengusulkan tugas ini."}, None
        data = {"event_id": eid, "judul": str(args.get("judul") or "")[:200], "seksi": seksi,
                "tenggat": str(args.get("tenggat") or "") or None}
        return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "tugas_baru", "data": data,
                "ringkas": f"Buat tugas \"{data['judul']}\" untuk seksi {seksi}" + (f", tenggat {data['tenggat']}" if data["tenggat"] else "")}
    if nama == "usulkan_bagikan_tugas":
        t = db.session.get(Task, str(args.get("task_id") or ""))
        if not t:
            return {"error": "Tugas tidak ditemukan."}, None
        baris, galat = _agen_ambil_acara(t.event_id)
        if galat or not (baris.peran == "ketua" or (baris.peran == "koordinator" and baris.seksi == t.divisi)):
            return {"error": "Kamu tidak bisa membagikan tugas ini."}, None
        nama_p = str(args.get("nama_penerima") or "").strip().lower()
        cocok = [p for p in PeranAcara.query.filter_by(event_id=t.event_id).all()
                 if (Orang.query.get(p.orang_id).nama or "").lower() == nama_p]
        if len(cocok) != 1:
            return {"error": "Nama penerima tidak ditemukan tepat satu di acara ini."}, None
        penerima = Orang.query.get(cocok[0].orang_id)
        return {"ok": True}, {"jenis": "usulan", "tipe": "bagikan_tugas",
                "data": {"task_id": t.id, "orang_id": penerima.id},
                "ringkas": f"Bagikan tugas \"{t.judul}\" kepada {penerima.nama}"}
    if nama == "usulkan_keputusan":
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return {"error": galat}, None
        data = {"event_id": eid, "judul": str(args.get("judul") or "")[:200], "isi": str(args.get("isi") or "")[:2000]}
        return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "keputusan", "data": data,
                "ringkas": f"Catat keputusan: \"{data['judul']}\""}
    if nama == "buat_undangan":
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return {"error": galat}, None
        ev = db.session.get(Event, eid)
        return {"nama": ev.nama, "tanggal": ev.tanggal, "lokasi": ev.lokasi, "catatan": "Password pendaftaran tidak disertakan; Ketua mengirimnya terpisah."}, None
    if nama == "buat_laporan":
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return {"error": galat}, None
        return {"ok": True}, {"jenis": "navigasi", "url": f"/api/events/{eid}/dokumen/laporan.pdf", "label": "Unduh laporan PDF"}
    if nama in ("ubah_tugas", "hapus_tugas"):
        t = db.session.get(Task, str(args.get("task_id") or ""))
        if not t:
            return {"error": "Tugas tidak ditemukan."}, None
        _, galat = _izin_ubah_tugas(t)
        if galat:
            return {"error": galat}, None
        if nama == "hapus_tugas":
            return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "hapus_tugas", "berbahaya": True,
                    "data": {"task_id": t.id}, "ringkas": f"Hapus tugas \"{t.judul}\" (tidak bisa diulang kecuali dengan Batalkan)"}
        data = {"task_id": t.id}
        if args.get("judul"):
            data["judul"] = str(args["judul"])[:200]
        if args.get("tenggat"):
            data["tenggat"] = str(args["tenggat"])
        if args.get("status") in ("pending", "done"):
            data["status"] = args["status"]
        if len(data) == 1:
            return {"error": "Tidak ada perubahan yang diminta."}, None
        return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "ubah_tugas", "data": data,
                "ringkas": f"Ubah tugas \"{t.judul}\": " + ", ".join(f"{k} = {v}" for k, v in data.items() if k != "task_id")}
    if nama in ("ubah_peran_peserta", "keluarkan_peserta"):
        baris, galat = _agen_ambil_acara(eid)
        if galat or baris.peran != "ketua":
            return {"error": "Hanya Ketua yang bisa mengubah atau mengeluarkan peserta."}, None
        target, galat = _cari_peserta_nama(eid, args.get("nama"))
        if galat:
            return {"error": galat}, None
        if target.peran == "ketua":
            return {"error": "Peran Ketua tidak bisa diubah atau dikeluarkan dari sini."}, None
        nama_peserta = db.session.get(Orang, target.orang_id).nama
        if nama == "keluarkan_peserta":
            return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "keluarkan", "berbahaya": True,
                    "data": {"event_id": eid, "peran_id": target.id}, "ringkas": f"Keluarkan {nama_peserta} dari acara"}
        peran = str(args.get("peran") or "")
        seksi = args.get("seksi") or None
        ada = [(b.orang_id, b.peran, b.seksi) for b in PeranAcara.query.filter_by(event_id=eid).all() if b.id != target.id]
        galat = aturan_peran.validasi_penugasan(peran, seksi, target.orang_id, ada) if peran in ("anggota", "pj", "koordinator", "wakil_ketua") else "Peran tidak dikenal."
        if galat:
            return {"error": galat}, None
        return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "ubah_peran",
                "data": {"event_id": eid, "peran_id": target.id, "peran": peran, "seksi": seksi},
                "ringkas": f"Ubah {nama_peserta} menjadi {peran}" + (f" seksi {seksi}" if seksi else "")}
    if nama == "tutup_acara":
        baris, galat = _agen_ambil_acara(eid)
        if galat or baris.peran != "ketua":
            return {"error": "Hanya Ketua yang bisa menutup acara."}, None
        if _acara_tertutup(eid):
            return {"error": "Acara sudah ditutup."}, None
        return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": "tutup", "berbahaya": True,
                "data": {"event_id": eid}, "ringkas": "Tutup acara: peran semua peserta kembali ke anggota dan data dibekukan"}
    if nama in ("batalkan_terakhir", "ulangi_terakhir"):
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return {"error": galat}, None
        tipe = "batal" if nama == "batalkan_terakhir" else "ulang"
        return {"ok": True, "status": "menunggu Jalankan"}, {"jenis": "usulan", "tipe": tipe, "data": {"event_id": eid},
                "ringkas": "Batalkan perubahan terakhir" if tipe == "batal" else "Ulangi perubahan yang dibatalkan"}
    return {"error": f"Alat {nama} tidak dikenal."}, None


def agen_chat(pesan, riwayat, konteks, model=None):
    """Loop agen: model boleh memanggil alat beberapa kali. Kembalikan (jawaban, aksi)."""
    model = model or OLLAMA_MODEL
    headers = {"content-type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    pesan_model = [{"role": "system", "content": ASISTEN_SISTEM + ("\n\n" + konteks if konteks else "")}]
    for r in riwayat[-6:]:
        if r.get("role") in ("user", "assistant") and isinstance(r.get("content"), str):
            pesan_model.append({"role": r["role"], "content": r["content"][:2000]})
    pesan_model.append({"role": "user", "content": pesan})
    aksi, pakai_alat = [], True
    for _ in range(AGEN_MAKS_LANGKAH):
        body = {"model": model, "messages": pesan_model, "stream": False}
        if pakai_alat:
            body["tools"] = _agen_alat_definisi()
        res = requests.post(OLLAMA_URL, json=body, headers=headers, timeout=180)
        if res.status_code == 400 and pakai_alat:
            pakai_alat = False  # model tidak mendukung alat: jawab tanpa alat
            continue
        res.raise_for_status()
        msg = res.json().get("message") or {}
        panggilan = msg.get("tool_calls") or []
        if not panggilan:
            return (msg.get("content") or "").strip(), aksi
        pesan_model.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": panggilan})
        for p in panggilan:
            fn = p.get("function") or {}
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            hasil, tambahan = _agen_jalankan_alat(fn.get("name", ""), args)
            if tambahan:
                aksi.append(tambahan)
            pesan_model.append({"role": "tool", "name": fn.get("name", ""), "content": json.dumps(hasil, ensure_ascii=False, default=str)})
    return "Maaf, aku belum bisa menyelesaikan itu. Coba tanyakan dengan kalimat yang lebih sederhana.", aksi


def jalankan_usulan(tipe, data):
    """Jalankan usulan yang sudah disetujui pengguna. Izin dicek ulang di sini; data dari klien tidak dipercaya begitu saja."""
    if tipe == "tugas_baru":
        eid = str(data.get("event_id") or "")
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return None, galat
        seksi = str(data.get("seksi") or "")
        if not (baris.peran == "ketua" or (baris.peran == "koordinator" and baris.seksi == seksi)):
            return None, "Kamu tidak berwenang membuat tugas untuk seksi itu."
        judul = str(data.get("judul") or "").strip()[:200]
        if not judul:
            return None, "Judul tugas kosong."
        t = Task(event_id=eid, divisi=seksi, judul=judul, deadline_iso=data.get("tenggat") or None)
        db.session.add(t)
        db.session.flush()
        _riwayat_simpan(eid, f'Tambah tugas "{judul}"', _keadaan_kosong(eid, "task", t.id), _ambil_keadaan(eid, [("task", t.id)]))
        db.session.commit()
        return {"id": t.id, "pesan": f"Tugas \"{judul}\" dibuat."}, None
    if tipe == "bagikan_tugas":
        t = db.session.get(Task, str(data.get("task_id") or ""))
        if not t:
            return None, "Tugas tidak ditemukan."
        baris, galat = _agen_ambil_acara(t.event_id)
        if galat or not (baris.peran == "ketua" or (baris.peran == "koordinator" and baris.seksi == t.divisi)):
            return None, "Kamu tidak berwenang membagikan tugas ini."
        if not PeranAcara.query.filter_by(event_id=t.event_id, orang_id=data.get("orang_id")).first():
            return None, "Penerima tidak terdaftar di acara ini."
        sebelum = _ambil_keadaan(t.event_id, [("task", t.id)])
        t.penerima_orang_id = data.get("orang_id")
        t.penerima_ditugaskan_pada = datetime.utcnow()
        t.konfirmasi = None
        _riwayat_simpan(t.event_id, f'Bagikan tugas "{t.judul}"', sebelum, _ambil_keadaan(t.event_id, [("task", t.id)]))
        db.session.commit()
        return {"id": t.id, "pesan": "Tugas dibagikan. Penerima perlu menerima atau menolak."}, None
    if tipe == "keputusan":
        eid = str(data.get("event_id") or "")
        baris, galat = _agen_ambil_acara(eid)
        if galat:
            return None, galat
        judul = str(data.get("judul") or "").strip()[:200]
        if not judul:
            return None, "Judul keputusan kosong."
        k = KeputusanAcara(event_id=eid, judul=judul, isi=str(data.get("isi") or "")[:2000], status="disetujui",
                           penulis_kunci=_kunci_pengguna(), penulis_nama=session.get("nama") or "Panitia")
        db.session.add(k)
        db.session.flush()
        _riwayat_simpan(eid, f'Catat keputusan "{judul}"', _keadaan_kosong(eid, "keputusan", k.id),
                        _ambil_keadaan(eid, [("keputusan", k.id)]))
        db.session.commit()
        return {"id": k.id, "pesan": f"Keputusan \"{judul}\" dicatat."}, None
    if tipe == "ubah_tugas":
        t = db.session.get(Task, str(data.get("task_id") or ""))
        if not t:
            return None, "Tugas tidak ditemukan."
        _, galat = _izin_ubah_tugas(t)
        if galat:
            return None, galat
        sebelum = _ambil_keadaan(t.event_id, [("task", t.id)])
        if data.get("judul"):
            t.judul = str(data["judul"]).strip()[:200]
        if data.get("tenggat"):
            t.deadline_iso = str(data["tenggat"])
        if data.get("status") in ("pending", "done"):
            t.status = data["status"]
            t.completed_at = datetime.utcnow() if data["status"] == "done" else None
            if data["status"] == "done":
                t.progress = 100
        _riwayat_simpan(t.event_id, f'Ubah tugas "{t.judul}"', sebelum, _ambil_keadaan(t.event_id, [("task", t.id)]))
        db.session.commit()
        return {"id": t.id, "pesan": f'Tugas "{t.judul}" diperbarui.'}, None
    if tipe == "hapus_tugas":
        t = db.session.get(Task, str(data.get("task_id") or ""))
        if not t:
            return None, "Tugas tidak ditemukan."
        _, galat = _izin_ubah_tugas(t)
        if galat:
            return None, galat
        eid, judul = t.event_id, t.judul
        sebelum = _ambil_keadaan(eid, [("task", t.id)])
        db.session.delete(t)
        _riwayat_simpan(eid, f'Hapus tugas "{judul}"', sebelum, _keadaan_kosong(eid, "task", str(data["task_id"])))
        db.session.commit()
        return {"pesan": f'Tugas "{judul}" dihapus. Ketik Batalkan untuk mengembalikannya.'}, None
    if tipe == "ubah_peran":
        eid = str(data.get("event_id") or "")
        baris, galat = _agen_ambil_acara(eid)
        if galat or baris.peran != "ketua":
            return None, "Hanya Ketua yang bisa mengubah peran."
        target = db.session.get(PeranAcara, str(data.get("peran_id") or ""))
        if not target or target.event_id != eid or target.peran == "ketua":
            return None, "Penugasan tidak bisa diubah."
        peran = str(data.get("peran") or "")
        seksi = data.get("seksi") or None
        ada = [(b.orang_id, b.peran, b.seksi) for b in PeranAcara.query.filter_by(event_id=eid).all() if b.id != target.id]
        galat = aturan_peran.validasi_penugasan(peran, seksi, target.orang_id, ada)
        if galat:
            return None, galat
        sebelum = _ambil_keadaan(eid, [("peran", target.id)])
        target.peran, target.seksi = peran, seksi
        _riwayat_simpan(eid, "Ubah peran peserta", sebelum, _ambil_keadaan(eid, [("peran", target.id)]))
        db.session.commit()
        return {"pesan": "Peran peserta diperbarui."}, None
    if tipe == "keluarkan":
        eid = str(data.get("event_id") or "")
        baris, galat = _agen_ambil_acara(eid)
        if galat or baris.peran != "ketua":
            return None, "Hanya Ketua yang bisa mengeluarkan peserta."
        target = db.session.get(PeranAcara, str(data.get("peran_id") or ""))
        if not target or target.event_id != eid or target.peran == "ketua":
            return None, "Peserta ini tidak bisa dikeluarkan."
        sebelum = _ambil_keadaan(eid, [("peran", target.id)])
        pid = target.id
        db.session.delete(target)
        _riwayat_simpan(eid, "Keluarkan peserta", sebelum, _keadaan_kosong(eid, "peran", pid))
        db.session.commit()
        return {"pesan": "Peserta dikeluarkan dari acara. Ketik Batalkan untuk mengembalikannya."}, None
    if tipe == "tutup":
        eid = str(data.get("event_id") or "")
        baris, galat = _agen_ambil_acara(eid)
        if galat or baris.peran != "ketua":
            return None, "Hanya Ketua yang bisa menutup acara."
        if _acara_tertutup(eid):
            return None, "Acara sudah ditutup."
        refs = [("peran", b.id) for b in PeranAcara.query.filter_by(event_id=eid).all()]
        sebelum = _ambil_keadaan(eid, refs, tertutup=False)
        PeranAcara.query.filter(PeranAcara.event_id == eid, PeranAcara.peran != "ketua").update(
            {"peran": aturan_peran.PERAN_DEFAULT}, synchronize_session=False)
        db.session.add(EventArsip(event_id=eid))
        db.session.flush()
        db.session.expire_all()
        _riwayat_simpan(eid, "Tutup acara", sebelum, _ambil_keadaan(eid, refs, tertutup=True))
        db.session.commit()
        return {"pesan": "Acara ditutup."}, None
    if tipe in ("batal", "ulang"):
        label, galat = _riwayat_pindah(str(data.get("event_id") or ""), "batal" if tipe == "batal" else "ulang")
        if galat:
            return None, galat[0]
        return {"pesan": f"Dibatalkan: {label}." if tipe == "batal" else f"Diulang: {label}."}, None
    return None, "Jenis usulan tidak dikenal."


# ============================================================
# PEMULIHAN PASSWORD (tanpa email/telepon): kode pemulihan sekali pakai
# ============================================================
_ALFABET_KODE = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # tanpa huruf yang mirip (0/O, 1/I)


def _buat_kode_pemulihan():
    """Kembalikan (kode_tampil, hash_untuk_disimpan). Kode hanya ditampilkan sekali."""
    raw = "".join(secrets.choice(_ALFABET_KODE) for _ in range(12))
    kode = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
    return kode, generate_password_hash(raw)


def _cek_kode_pemulihan(kode, hash_tersimpan):
    if not hash_tersimpan:
        return False
    raw = re.sub(r"[^A-Z0-9]", "", str(kode or "").upper())
    return len(raw) == 12 and check_password_hash(hash_tersimpan, raw)


@app.route("/api/auth/lupa-password", methods=["POST"])
def lupa_password():
    """Atur ulang password dengan kode pemulihan. Kode lama langsung hangus dan kode baru diberikan sekali."""
    data = request.get_json(silent=True) or {}
    ip = request.remote_addr or "unknown"
    kunci = f"lupa|{ip}|{str(data.get('username') or '').strip().lower()}"
    if _too_many_fails(kunci):
        return jsonify({"error": "Terlalu banyak percobaan. Coba lagi dalam 5 menit."}), 429
    o = Orang.query.filter(db.func.lower(Orang.username) == str(data.get("username") or "").strip().lower()).first()
    if not o or not _cek_kode_pemulihan(data.get("kode"), o.kode_pemulihan_hash):
        _login_fails.setdefault(kunci, []).append(time.time())
        return jsonify({"error": "Username atau kode pemulihan salah."}), 401
    pw = str(data.get("password_baru") or "")
    if len(pw) < 8:
        return jsonify({"error": "Password baru minimal 8 karakter."}), 400
    _login_fails.pop(kunci, None)
    o.password_hash = generate_password_hash(pw)
    kode, hash_baru = _buat_kode_pemulihan()
    o.kode_pemulihan_hash = hash_baru
    db.session.commit()
    return jsonify({"pesan": "Password sudah diganti. Simpan kode pemulihan baru ini; hanya tampil sekali.", "kode_pemulihan": kode})


@app.route("/api/me/kode-pemulihan", methods=["POST"])
def buat_ulang_kode_pemulihan():
    """Buat kode pemulihan baru (kode lama hangus). Dipakai oleh akun yang dibuat sebelum fitur ini ada."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dulu."}), 401
    o = db.session.get(Orang, oid)
    kode, hash_baru = _buat_kode_pemulihan()
    o.kode_pemulihan_hash = hash_baru
    db.session.commit()
    return jsonify({"kode_pemulihan": kode, "pesan": "Simpan kode ini; hanya tampil sekali."})


# ============================================================
# KUOTA CAPY HARIAN (batas pemakaian, bukan biaya) dan PENGINGAT TENGGAT
# ============================================================
ASISTEN_KUOTA_HARIAN = int(os.environ.get("ASISTEN_KUOTA_HARIAN", "200"))


def _kuota_pakai(kunci):
    """Tambah satu pemakaian untuk hari ini. Kembalikan (boleh, sisa, kapan_bisa_lagi)."""
    hari = datetime.utcnow().strftime("%Y-%m-%d")
    k = KuotaAsisten.query.filter_by(kunci=kunci, tanggal=hari).first()
    if k is None:
        k = KuotaAsisten(kunci=kunci, tanggal=hari, jumlah=0)
        db.session.add(k)
    if k.jumlah >= ASISTEN_KUOTA_HARIAN:
        return False, 0, "besok pukul 00.00 UTC"
    k.jumlah += 1
    db.session.commit()
    return True, ASISTEN_KUOTA_HARIAN - k.jumlah, None


@app.route("/api/me/tugas-menunggu", methods=["GET"])
def tugas_menunggu_saya():
    """Tugas yang dibagikan kepada saya dan belum saya jawab, dari semua acara yang saya ikuti (tanpa perlu masuk acara dulu)."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dulu."}), 401
    rows = Task.query.filter(Task.penerima_orang_id == oid, Task.konfirmasi.is_(None), Task.status != "done") \
        .order_by(Task.deadline_iso.is_(None), Task.deadline_iso).limit(50).all()
    hasil = []
    for t in rows:
        if not _di_acara(t.event_id):
            continue
        ev = db.session.get(Event, t.event_id)
        hasil.append({"id": t.id, "judul": t.judul, "event_id": t.event_id, "acara": ev.nama if ev else "", "deadline_iso": t.deadline_iso})
    return jsonify({"tugas": hasil})


@app.route("/api/me/pengingat", methods=["GET"])
def pengingat_saya():
    """Tugas yang perlu diperhatikan saya: tenggat dalam 3 hari atau sudah lewat, di semua acara yang saya ikuti."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dulu."}), 401
    sekarang = datetime.utcnow()
    batas = (sekarang + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    now_s = sekarang.strftime("%Y-%m-%dT%H:%M")
    hasil = []
    for b in PeranAcara.query.filter_by(orang_id=oid).all():
        ev = db.session.get(Event, b.event_id)
        if not ev:
            continue
        q = Task.query.filter(Task.event_id == ev.id, Task.status != "done", Task.deadline_iso.isnot(None), Task.deadline_iso <= batas)
        if b.peran not in ("ketua", "wakil_ketua"):
            if b.peran == "koordinator" and b.seksi:
                q = q.filter(db.func.lower(Task.divisi) == b.seksi.lower())
            else:
                q = q.filter(Task.penerima_orang_id == oid)
        for t in q.order_by(Task.deadline_iso).limit(20).all():
            hasil.append({"task_id": t.id, "judul": t.judul, "acara": ev.nama, "event_id": ev.id,
                          "tenggat": t.deadline_iso, "lewat": t.deadline_iso < now_s})
    hasil.sort(key=lambda x: x["tenggat"])
    return jsonify({"pengingat": hasil[:30]})


RIWAYAT_UMUM = "umum"
RIWAYAT_DIKIRIM = 12  # jumlah pesan terakhir yang dikirim ke model, supaya fokus dan ringan


def _kunci_riwayat(event_id):
    return event_id if event_id else RIWAYAT_UMUM


@app.route("/api/agen/riwayat", methods=["GET"])
def agen_riwayat():
    """Percakapan saya di satu acara (atau 'umum'). Tidak pernah menampilkan percakapan orang lain."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    eid = str(request.args.get("event_id") or "") or None
    if eid and not _di_acara(eid):
        return jsonify({"error": "Kamu tidak terdaftar di acara ini."}), 403
    rows = ChatAsisten.query.filter_by(orang_id=oid, kunci=_kunci_riwayat(eid)).order_by(ChatAsisten.id.desc()).limit(100).all()
    rows.reverse()
    return jsonify({"pesan": [{"peran": r.peran, "isi": r.isi, "aksi": json.loads(r.aksi) if r.aksi else []} for r in rows]})


@app.route("/api/agen/riwayat", methods=["DELETE"])
def agen_hapus_riwayat():
    """Mulai baru: hapus percakapan saya di satu acara (atau 'umum'). Percakapan orang lain tidak tersentuh."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    eid = str(request.args.get("event_id") or "") or None
    if eid and not _di_acara(eid):
        return jsonify({"error": "Kamu tidak terdaftar di acara ini."}), 403
    n = ChatAsisten.query.filter_by(orang_id=oid, kunci=_kunci_riwayat(eid)).delete()
    db.session.commit()
    return jsonify({"dihapus": n})


@app.route("/api/agen/chat", methods=["POST"])
def agen_chat_endpoint():
    """Capy: membaca data acara, membuka halaman, dan mengusulkan perubahan. Riwayat disimpan per acara."""
    oid = _orang_login()
    if not oid:
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    if not _asisten_siap():
        return jsonify({"error": "Asisten belum aktif. Pastikan Ollama berjalan."}), 503
    data = request.get_json(silent=True) or {}
    try:
        pesan = clean_text(data.get("pesan"), 1000, "Pesan", required=True)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    eid = str(data.get("event_id") or "") or None
    if eid and not _di_acara(eid):
        return jsonify({"error": "Kamu tidak terdaftar di acara ini."}), 403
    if not _asisten_boleh(oid):
        return jsonify({"error": "Terlalu sering bertanya. Coba lagi sebentar."}), 429
    kunci = _kunci_riwayat(eid)
    boleh, sisa, kapan = _kuota_pakai(eid or f"orang:{oid}")
    if not boleh:
        return jsonify({"error": f"Kuota Capy untuk hari ini sudah habis. Bisa dipakai lagi {kapan}.", "kuota_habis": True, "kapan": kapan}), 429
    lama = ChatAsisten.query.filter_by(orang_id=oid, kunci=kunci).order_by(ChatAsisten.id.desc()).limit(RIWAYAT_DIKIRIM).all()
    lama.reverse()
    riwayat = [{"role": "user" if r.peran == "user" else "assistant", "content": r.isi} for r in lama]
    try:
        # Di luar acara: mode ngobrol. Di dalam acara: mode kerja (model yang mendukung alat).
        if eid:
            jawaban, aksi = agen_chat(pesan, riwayat, _konteks_acara(eid), model=CAPY_MODEL_ACARA)
        else:
            jawaban, aksi = agen_chat(pesan, riwayat, "Mode ngobrol: kamu teman ngobrol panitia. Bicara santai dan membantu; data acara tidak ada di sini.", model=CAPY_MODEL_OBROLAN)
    except requests.RequestException as exc:
        app.logger.warning("Asisten gagal: %s", exc)
        return jsonify({"error": _pesan_galat_asisten(exc)}), 502
    jawaban = jawaban or "Maaf, aku belum punya jawaban untuk itu."
    db.session.add(ChatAsisten(orang_id=oid, kunci=kunci, peran="user", isi=pesan))
    db.session.add(ChatAsisten(orang_id=oid, kunci=kunci, peran="capy", isi=jawaban,
                               aksi=json.dumps(aksi, ensure_ascii=False) if aksi else None))
    db.session.commit()
    return jsonify({"jawaban": jawaban, "aksi": aksi, "mode": "demo"})


@app.route("/api/agen/jalankan", methods=["POST"])
def agen_jalankan_endpoint():
    """Pengguna menekan Jalankan pada usulan dari Capy."""
    if not _orang_login():
        return jsonify({"error": "Masuk dengan akun user dulu."}), 401
    data = request.get_json(silent=True) or {}
    hasil, galat = jalankan_usulan(str(data.get("tipe") or ""), data.get("data") or {})
    if galat:
        return jsonify({"error": galat}), 403
    return jsonify(hasil), 201


@app.route("/")
def index():
    return jsonify({"service": "Caby Organizer API", "status": "ok", "endpoints": ["/api/auth/login", "/api/tasks", "/api/events", "/health"]})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
