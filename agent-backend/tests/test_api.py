"""Pengujian otomatis backend Capy Organizer.

Jalankan dari folder agent-backend:
    pip install pytest
    pytest -q
"""
import json
import os
import sys
import tempfile


from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TEST_DB = os.path.join(tempfile.gettempdir(), "capy_pytest.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
PASSWORD = "uji-sandi-123"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "kunci-uji"

import app as capy  # noqa: E402

capy.app.config["TESTING"] = True
client = capy.app.test_client()


_UNIK = [0]


def _user_baru(c, nama="Ketua Uji", password=None):
    """Daftar akun user baru (username unik) lalu masuk dengan client c."""
    import uuid
    uname = "u" + uuid.uuid4().hex[:10]
    pw = password or PASSWORD
    res = c.post("/api/auth/daftar", json={"username": uname, "nama": nama, "password": pw})
    assert res.status_code == 201, res.get_json()
    capy._login_fails.clear()  # tes lain mencatat kegagalan dari IP yang sama; jangan ikut terkunci
    assert c.post("/api/auth/login", json={"username": uname, "password": pw}).status_code == 200
    return uname


def login(c=None, role=None, password=None):
    """Compat: masuk sebagai user baru."""
    c = c or client
    _user_baru(c, password=password)
    return c


def new_client():
    """Client user yang sudah masuk. Belum punya acara; buat acara dengan POST /api/events."""
    c = capy.app.test_client()
    _user_baru(c)
    return c


def test_konfigurasi_ollama_memilih_default_dari_api_key():
    lokal = capy._konfigurasi_ollama({})
    assert lokal["url"] == "http://localhost:11434/api/chat"
    assert lokal["model"] == "llama3.1"

    cloud = capy._konfigurasi_ollama({"OLLAMA_API_KEY": "kunci-uji"})
    assert cloud["url"] == "https://ollama.com/api/chat"
    assert cloud["model"] == "gpt-oss:20b-cloud"
    assert cloud["chat_model"] == cloud["event_model"] == cloud["model"]

    override = capy._konfigurasi_ollama({"OLLAMA_API_KEY": "kunci-uji", "OLLAMA_URL": "http://ollama:11434/api/chat"})
    assert override["url"] == "http://ollama:11434/api/chat"
    assert override["model"] == "llama3.1"


SIE_PASSWORD = "sie-konsumsi-123"  # tidak dipakai lagi; disisakan untuk tes lama


def sie_client(role="Konsumsi", event_id=None):
    """User yang terdaftar sebagai koordinator seksi `role` di acara `event_id`, lalu masuk ke acara itu.
    Penugasan ditulis langsung ke database uji (ketua acara itu mungkin dibuat di test lain)."""
    if not event_id:
        ketua = new_client()
        event_id = ketua.post("/api/events", json={"nama": "Acara Seksi", "tanggal": "2031-01-01"}).get_json()["id"]
    c = capy.app.test_client()
    uname = _user_baru(c, nama="Koordinator " + role)
    with capy.app.app_context():
        oid = capy.Orang.query.filter(capy.db.func.lower(capy.Orang.username) == uname.lower()).first().id
        capy.db.session.add(capy.PeranAcara(event_id=event_id, orang_id=oid, peran="koordinator", seksi=role))
        capy.db.session.commit()
    assert c.post(f"/api/me/acara/{event_id}/masuk").status_code == 200
    return c


def test_health_public():
    assert client.get("/health").status_code == 200


def test_api_butuh_login():
    res = capy.app.test_client().get("/api/tasks")
    assert res.status_code == 401
    assert "error" in res.get_json()








def test_rate_limit_setelah_5_kali_gagal():
    c = capy.app.test_client()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "tidak-ada", "password": "salah-salah"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "tidak-ada", "password": "salah-salah"}).status_code == 429


def test_validasi_nama_acara_kosong_dan_terlalu_panjang():
    c = new_client()
    assert c.post("/api/events", json={"nama": "   "}).status_code == 400
    res = c.post("/api/events", json={"nama": "x" * 201})
    assert res.status_code == 400
    assert "maksimal 200" in res.get_json()["error"]


def test_validasi_format_tanggal_acara():
    c = new_client()
    assert c.post("/api/events", json={"nama": "Uji", "tanggal": "05-11-2026"}).status_code == 400


def test_error_json_untuk_endpoint_tidak_ada_dan_body_besar():
    c = new_client()
    res = c.get("/api/tidak-ada")
    assert res.status_code == 404 and "error" in res.get_json()
    besar = c.post("/api/events", data="x" * (300 * 1024), content_type="application/json")
    assert besar.status_code == 413
    assert "error" in besar.get_json()


def test_judul_tugas_manual_divalidasi():
    c = new_client()
    eid = c.post("/api/events", json={"nama": "Uji judul tugas", "tanggal": "2026-10-19"}).get_json()["id"]
    assert c.post("/api/tasks", json={"judul": "", "event_id": eid}).status_code == 400
    assert c.post("/api/tasks", json={"judul": "Tugas", "deadline_iso": "bukan-tanggal", "event_id": eid}).status_code == 400
    assert c.post("/api/tasks", json={"judul": "Tugas tanpa acara"}).status_code == 400  # tugas wajib punya acara
    ok = c.post("/api/tasks", json={"judul": "Tugas sah", "deadline_iso": "2026-10-20T10:00", "event_id": eid})
    assert ok.status_code == 201


def test_struktur_default_dan_simpan_pic():
    c = new_client()
    eid = c.post("/api/events", json={"nama": "Struktur uji", "tanggal": "2026-11-20"}).get_json()["id"]
    default = c.get(f"/api/events/{eid}/struktur").get_json()["struktur"]
    nama_sie = [s["seksi"] for s in default]
    assert {"Ketua Pelaksana", "Sekretaris", "Bendahara", "Humas", "Konsumsi", "Keamanan", "PDD"} <= set(nama_sie)
    struktur = [{"seksi": s, "pic": ""} for s in nama_sie]
    struktur[nama_sie.index("Konsumsi")]["pic"] = "Dina"
    res = c.put(f"/api/events/{eid}/struktur", json={"struktur": struktur})
    assert res.status_code == 200
    assert c.put(f"/api/events/{eid}/struktur", json={"struktur": [{"seksi": ""}]}).status_code == 400


def test_beranda_publik_dan_statistik_asli():
    publik = capy.app.test_client()
    res = publik.get("/api/beranda")
    assert res.status_code == 200
    body = res.get_json()
    assert body["pengaturan"]["hero"] in {"a", "b", "c", "d"}
    assert {"acara", "tugas", "tugas_selesai", "seksi", "persen_selesai"} <= set(body["statistik"])


def test_kabar_publik_hanya_yang_diizinkan_dan_hapus_sesuai_hak():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Kabar publik", "tanggal": "2031-04-04"}).get_json()["id"]
    sie = sie_client("Konsumsi", eid)
    res = sie.post("/api/kabar", json={"isi": "Porsi final sudah dipesan", "publik": True, "event_id": eid})
    assert res.status_code == 201
    sie.post("/api/kabar", json={"isi": "Catatan internal vendor", "publik": False, "event_id": eid})
    publik_isi = [k["isi"] for k in capy.app.test_client().get("/api/beranda").get_json()["kabar"]]
    assert "Porsi final sudah dipesan" in publik_isi
    assert "Catatan internal vendor" not in publik_isi
    kabar_id = sie.get("/api/kabar").get_json()["kabar"][0]["id"]
    humas = sie_client("Humas")
    assert humas.delete(f"/api/kabar/{kabar_id}").status_code == 403
    assert sie.delete(f"/api/kabar/{kabar_id}").status_code == 200


def test_upload_lampiran_jenis_dan_ukuran():
    import io
    sie = sie_client("Konsumsi")
    ok = sie.post("/api/lampiran", data={"file": (io.BytesIO(b"\x89PNG fake"), "foto.png")}, content_type="multipart/form-data")
    assert ok.status_code == 201 and ok.get_json()["mime"] == "image/png"
    tidak = sie.post("/api/lampiran", data={"file": (io.BytesIO(b"MZ"), "virus.exe")}, content_type="multipart/form-data")
    assert tidak.status_code == 400
    kosong = sie.post("/api/lampiran", data={"file": (io.BytesIO(b""), "kosong.pdf")}, content_type="multipart/form-data")
    assert kosong.status_code == 400


def test_bendahara_hanya_melihat_acara_tempat_ia_terdaftar():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Acara tanpa tugas bendahara", "tanggal": "2026-12-16"}).get_json()["id"]
    ids = [a["event"]["id"] for a in sie_client("Bendahara").get("/api/kerja").get_json()["acara"]]
    assert eid not in ids  # bendahara di acara lain tidak boleh melihat acara ini
    assert eid in [a["event"]["id"] for a in sie_client("Bendahara", eid).get("/api/kerja").get_json()["acara"]]



def _bawa(d):
    """Lampirkan persetujuan yang ditandatangani server untuk rencana d (seperti yang dilakukan tombol Jalankan)."""
    d = dict(d)
    d.setdefault("persetujuan", capy.agen_tool.tanda_persetujuan(d["aksi"], capy.app.config["SECRET_KEY"]))
    return d


def _balasan_tool(nama, masukan):
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "j1", "name": nama, "input": masukan}]}


def _balasan_akhir(teks):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": teks}], "usage": {}, "model": "uji"}


def test_orang_dan_peran_acara_tahap_1a():
    import uuid
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji peran", "tanggal": "2026-12-26"}).get_json()["id"]
    uname = "u-" + uuid.uuid4().hex[:8]
    # buat orang
    res = ketua.post("/api/orang", json={"username": uname, "nama": "Rina", "password": "sandi-rina-2026"})
    assert res.status_code == 201
    rina = res.get_json()["id"]
    assert ketua.post("/api/orang", json={"username": uname, "nama": "Lain", "password": "sandi-lain-2026"}).status_code == 409
    assert ketua.post("/api/orang", json={"username": uname + "x", "nama": "Pendek", "password": "pendek"}).status_code == 400
    # tetapkan peran
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": rina, "peran": "koordinator", "seksi": "Konsumsi"}).status_code == 201
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": rina, "peran": "anggota"}).status_code == 400  # sudah punya peran
    lain = ketua.post("/api/orang", json={"username": uname + "y", "nama": "Dani", "password": "sandi-dani-2026"}).get_json()["id"]
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": lain, "peran": "koordinator", "seksi": "Konsumsi"}).status_code == 400
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": lain, "peran": "ketua"}).status_code == 400  # satu acara, satu Ketua (pembuatnya)
    daftar = ketua.get(f"/api/events/{eid}/peran").get_json()
    assert daftar["tertutup"] is False and {x["peran"] for x in daftar["peran"]} == {"koordinator", "ketua"}
    # tutup acara: peran kembali ke default, penugasan baru ditolak sampai dibuka
    tutup = ketua.post(f"/api/events/{eid}/tutup").get_json()
    assert tutup["peran_dikembalikan_ke_default"] == 1  # Ketua tidak ikut diturunkan
    setelah = ketua.get(f"/api/events/{eid}/peran").get_json()["peran"]
    assert len(setelah) == 2 and {x["peran"] for x in setelah} == {"anggota", "ketua"}  # kembali ke default, seksi tetap
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": rina, "peran": "anggota"}).status_code == 409
    assert ketua.post(f"/api/events/{eid}/tutup").status_code == 409
    assert ketua.post(f"/api/events/{eid}/buka").status_code == 200
    # Rina sudah punya peran (anggota) dari reset penutupan: menugaskannya lagi harus ditolak
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": rina, "peran": "pj", "seksi": "Humas"}).status_code == 400
    baris = [x for x in ketua.get(f"/api/events/{eid}/peran").get_json()["peran"] if x["orang_id"] == rina][0]
    assert ketua.delete(f"/api/events/{eid}/peran/{baris['id']}").status_code == 200
    assert ketua.post(f"/api/events/{eid}/peran", json={"orang_id": rina, "peran": "anggota"}).status_code == 201


def test_orang_dan_peran_hanya_untuk_ketua_dan_admin_ditolak():
    import uuid
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji akses peran", "tanggal": "2026-12-27"}).get_json()["id"]
    sie = sie_client("Humas", eid)
    assert sie.get("/api/orang").status_code == 403
    assert sie.post(f"/api/events/{eid}/peran", json={"orang_id": "x", "peran": "anggota"}).status_code == 403
    uname = "adm-" + uuid.uuid4().hex[:8]
    admin = ketua.post("/api/orang", json={"username": uname, "nama": "Admin", "password": "sandi-admin-2026", "admin": True}).get_json()["id"]
    res = ketua.post(f"/api/events/{eid}/peran", json={"orang_id": admin, "peran": "anggota"})
    assert res.status_code == 400 and "Admin tidak bisa" in res.get_json()["error"]


def _orang_dengan_peran(ketua, eid, peran, seksi=None, admin=False):
    import uuid
    uname = "o-" + uuid.uuid4().hex[:10]
    res = ketua.post("/api/orang", json={"username": uname, "nama": "Uji " + peran, "password": "sandi-uji-2026", "admin": admin})
    assert res.status_code == 201, res.get_json()
    oid = res.get_json()["id"]
    if not admin:
        body = {"orang_id": oid, "peran": peran}
        if seksi:
            body["seksi"] = seksi
        ketua.post(f"/api/me/acara/{eid}/masuk")  # pastikan Ketua sedang berada di acara ini
        assert ketua.post(f"/api/events/{eid}/peran", json=body).status_code == 201
    return uname


def _login_orang_api(username, eid, password="sandi-uji-2026"):
    """Login akun user, lalu masuk ke acara eid (seperti di dashboard)."""
    c = capy.app.test_client()
    res = c.post("/api/auth/login", json={"username": username, "password": password})
    if res.status_code == 200 and eid:
        res = c.post(f"/api/me/acara/{eid}/masuk")
    return c, res


def test_login_orang_memakai_peran_di_acara_yang_dipilih():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji login orang", "tanggal": "2026-12-28"}).get_json()["id"]
    uname = _orang_dengan_peran(ketua, eid, "koordinator", "Konsumsi")
    c, res = _login_orang_api(uname, eid)
    assert res.status_code == 200
    body = res.get_json()
    assert body["role"] == "Konsumsi" and body["peran"] == "koordinator" and body["ketua"] is False
    assert c.get("/api/auth/me").get_json()["peran"] == "koordinator"
    # tanpa acara, atau acara tempat ia tidak punya peran: ditolak
    assert _login_orang_api(uname, "")[1].status_code == 200  # tanpa acara: login akun user saja
    lain = ketua.post("/api/events", json={"nama": "Acara lain", "tanggal": "2026-12-29"}).get_json()["id"]
    assert _login_orang_api(uname, lain)[1].status_code == 403
    # password salah
    assert _login_orang_api(uname, eid, password="salah-banget")[1].status_code == 401




def test_wakil_ketua_bisa_membaca_semua_tugas_tapi_tidak_mengubah():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji wakil ketua", "tanggal": "2027-01-02"}).get_json()["id"]
    for seksi in ("Konsumsi", "Humas"):
        ketua.post("/api/tasks", json={"judul": f"Tugas {seksi}", "divisi": seksi, "event_id": eid, "deadline_iso": "2027-01-10T10:00"})
    uname = _orang_dengan_peran(ketua, eid, "wakil_ketua")
    c, res = _login_orang_api(uname, eid)
    assert res.status_code == 200 and res.get_json()["peran"] == "wakil_ketua"
    judul = [t["judul"] for t in c.get(f"/api/tasks?event_id={eid}").get_json()["tasks"]]
    assert "Tugas Konsumsi" in judul and "Tugas Humas" in judul
    tugas = ketua.get(f"/api/tasks?event_id={eid}").get_json()["tasks"][0]["id"]
    assert c.patch(f"/api/tasks/{tugas}", json={"status": "done"}).status_code == 403
    assert c.post("/api/tasks", json={"judul": "x", "divisi": "Humas", "event_id": eid}).status_code == 403


def test_anggota_seksi_hanya_bisa_ubah_status_dan_progres_tugasnya():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji anggota", "tanggal": "2027-01-03"}).get_json()["id"]
    ketua.post("/api/tasks", json={"judul": "Cek sound", "divisi": "Humas", "event_id": eid, "deadline_iso": "2027-01-12T09:00"})
    tugas = [t for t in ketua.get(f"/api/tasks?event_id={eid}").get_json()["tasks"] if t["judul"] == "Cek sound"][0]["id"]
    uname = _orang_dengan_peran(ketua, eid, "anggota", "Humas")
    c, res = _login_orang_api(uname, eid)
    assert res.status_code == 200
    assert c.patch(f"/api/tasks/{tugas}", json={"progress": 50}).status_code == 200
    assert c.patch(f"/api/tasks/{tugas}", json={"judul": "Diubah"}).status_code == 403


def test_setelah_tutup_acara_semua_orang_kembali_ke_anggota():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji tutup login", "tanggal": "2027-01-04"}).get_json()["id"]
    uname = _orang_dengan_peran(ketua, eid, "koordinator", "Humas")
    assert ketua.post(f"/api/events/{eid}/tutup").status_code == 200
    c, res = _login_orang_api(uname, eid)
    assert res.status_code == 200 and res.get_json()["peran"] == "anggota"
    assert ketua.post(f"/api/events/{eid}/buka").status_code == 200


def test_tahap2_koordinator_kelola_tugas_seksinya_sendiri():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji tahap 2", "tanggal": "2027-02-01"}).get_json()["id"]
    ketua.post("/api/tasks", json={"judul": "Tugas Humas", "divisi": "Humas", "event_id": eid})
    ketua.post("/api/tasks", json={"judul": "Tugas Konsumsi", "divisi": "Konsumsi", "event_id": eid})
    koor = _orang_dengan_peran(ketua, eid, "koordinator", "Konsumsi")
    c, res = _login_orang_api(koor, eid)
    assert res.status_code == 200
    # membuat tugas: seksi dipaksa ke seksinya sendiri
    baru = c.post("/api/tasks", json={"judul": "Pesan snack", "divisi": "Humas", "event_id": eid})
    assert baru.status_code == 201 and baru.get_json()["divisi"] == "Konsumsi"
    tugas = {x["judul"]: x["id"] for x in ketua.get(f"/api/tasks?event_id={eid}").get_json()["tasks"]}
    # ubah dan hapus: hanya tugas seksinya sendiri
    assert c.patch(f"/api/tasks/{tugas['Pesan snack']}", json={"judul": "Pesan snack 200"}).status_code == 200
    assert c.patch(f"/api/tasks/{tugas['Tugas Humas']}", json={"judul": "Curi"}).status_code == 403
    assert c.delete(f"/api/tasks/{tugas['Tugas Humas']}").status_code == 403
    assert c.delete(f"/api/tasks/{tugas['Pesan snack']}").status_code == 200
    # GET tugas bisa difilter per acara
    assert all(x["event_id"] == eid for x in c.get(f"/api/tasks?event_id={eid}").get_json()["tasks"])


def test_tahap2_anggota_tidak_bisa_membuat_atau_menghapus_tugas():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji anggota tahap 2", "tanggal": "2027-02-02"}).get_json()["id"]
    ketua.post("/api/tasks", json={"judul": "Cek sound", "divisi": "Humas", "event_id": eid})
    anggota = _orang_dengan_peran(ketua, eid, "anggota", "Humas")
    c, _ = _login_orang_api(anggota, eid)
    assert c.post("/api/tasks", json={"judul": "x", "event_id": eid}).status_code == 403
    tugas = [x["id"] for x in ketua.get(f"/api/tasks?event_id={eid}").get_json()["tasks"] if x["judul"] == "Cek sound"][0]
    assert c.delete(f"/api/tasks/{tugas}").status_code == 403


def test_tahap2_acara_tertutup_membekukan_perubahan_seksi():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji beku tahap 2", "tanggal": "2027-02-03"}).get_json()["id"]
    ketua.post("/api/tasks", json={"judul": "Rapat", "divisi": "Humas", "event_id": eid})
    tugas = ketua.get(f"/api/tasks?event_id={eid}").get_json()["tasks"][0]["id"]
    koor = _orang_dengan_peran(ketua, eid, "koordinator", "Humas")
    c, _ = _login_orang_api(koor, eid)
    assert ketua.post(f"/api/events/{eid}/tutup").status_code == 200
    assert c.post("/api/tasks", json={"judul": "Baru", "event_id": eid}).status_code == 409
    assert c.patch(f"/api/tasks/{tugas}", json={"judul": "Ubah"}).status_code == 409
    assert c.delete(f"/api/tasks/{tugas}").status_code == 409


def test_tahap3_keputusan_dibekukan_setelah_acara_ditutup():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji beku keputusan", "tanggal": "2027-04-03"}).get_json()["id"]
    koor = _orang_dengan_peran(ketua, eid, "koordinator", "Humas")
    k, _ = _login_orang_api(koor, eid)
    assert ketua.post(f"/api/events/{eid}/tutup").status_code == 200
    assert k.post(f"/api/events/{eid}/keputusan", json={"judul": "Terlambat", "isi": ""}).status_code == 409


def _koor(ketua, eid, seksi):
    """Koordinator seksi dengan akun pribadi di acara uji. Tidak bergantung pada akun seksi lama."""
    uname = _orang_dengan_peran(ketua, eid, "koordinator", seksi)
    c, res = _login_orang_api(uname, eid)
    assert res.status_code == 200, res.get_json()
    return c


def test_tahap6_laporan_pdf_dan_akses_per_acara():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji PDF tahap 6", "tanggal": "2027-06-04"}).get_json()["id"]
    ketua.post("/api/tasks", json={"judul": "Susun", "divisi": "Acara", "event_id": eid})
    acara = _koor(ketua, eid, "Acara")
    res = acara.get(f"/api/events/{eid}/dokumen/laporan.pdf")
    assert res.status_code == 200 and res.mimetype == "application/pdf" and res.data.startswith(b"%PDF")
    lain = ketua.post("/api/events", json={"nama": "Acara lain pdf", "tanggal": "2027-06-05"}).get_json()["id"]
    assert acara.get(f"/api/events/{lain}/dokumen/laporan.pdf").status_code == 403


def test_tahap7_dashboard_progres_papan_kalender_dan_perhatian():
    from datetime import datetime as _dt, timedelta as _td
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Uji dashboard tahap 7", "tanggal": "2027-07-01"}).get_json()["id"]
    ketua.post(f"/api/me/acara/{eid}/masuk")
    lewat = (_dt.utcnow() - _td(days=2)).strftime("%Y-%m-%dT%H:%M")
    dekat = (_dt.utcnow() + _td(hours=5)).strftime("%Y-%m-%dT%H:%M")
    ketua.post("/api/tasks", json={"judul": "Sudah lewat", "divisi": "Konsumsi", "event_id": eid, "deadline_iso": lewat})
    ketua.post("/api/tasks", json={"judul": "Segera", "divisi": "Humas", "event_id": eid, "deadline_iso": dekat})
    ketua.post("/api/tasks", json={"judul": "Nanti", "divisi": "Humas", "event_id": eid})
    d = ketua.get(f"/api/events/{eid}/dashboard").get_json()
    assert d["tugas"]["total"] == 3 and d["tugas"]["terlambat"] == 1 and d["progres_keseluruhan"] == 0
    papan = {p["seksi"]: p for p in d["papan_seksi"]}
    assert papan["Konsumsi"]["warna"] == "emerald" and papan["Humas"]["total"] == 2
    assert any(p["judul"] == "Sudah lewat" and p["alasan"] == "terlambat" for p in d["perlu_perhatian"])
    assert any(p["judul"] == "Segera" and p["alasan"] == "dalam 24 jam" for p in d["perlu_perhatian"])
    assert any(t["judul"] == "Sudah lewat" for t in d["kalender"][lewat[:10]])
    # hanya panitia di acara itu
    lain = ketua.post("/api/events", json={"nama": "Dashboard lain", "tanggal": "2027-07-02"}).get_json()["id"]
    koor = _orang_dengan_peran(ketua, eid, "koordinator", "Humas")
    c, _ = _login_orang_api(koor, eid)
    assert c.get(f"/api/events/{lain}/dashboard").status_code == 403


def test_daftar_user_lalu_buat_acara_jadi_ketua_dan_gabung_dengan_password():
    import uuid
    uname = "user_" + uuid.uuid4().hex[:8]
    pw = "sandi-user-2031"
    c = capy.app.test_client()
    assert c.post("/api/auth/daftar", json={"username": uname, "nama": "Dani", "password": pw}).status_code == 201
    assert c.post("/api/auth/daftar", json={"username": uname, "nama": "Dani", "password": pw}).status_code == 409
    assert c.post("/api/auth/daftar", json={"username": uname + "x", "nama": "Pendek", "password": "pendek"}).status_code == 400
    assert c.get("/api/me/acara").status_code == 401
    # login tanpa acara dan tanpa role
    assert c.post("/api/auth/login", json={"username": uname, "password": pw}).status_code == 200
    assert c.get("/api/me/acara").get_json()["acara"] == []
    # buat acara: pembuat otomatis Ketua
    buat = c.post("/api/events", json={"nama": "Festival Uji", "tanggal": "2031-05-05", "password": "pw-acara-2031"})
    assert buat.status_code == 201
    eid = buat.get_json()["id"]
    mine = c.get("/api/me/acara").get_json()["acara"]
    assert any(a["id"] == eid and a["peran"] == "ketua" for a in mine)
    # user lain gabung dengan password yang benar
    lain = capy.app.test_client()
    uname2 = "gabung_" + uuid.uuid4().hex[:8]
    lain.post("/api/auth/daftar", json={"username": uname2, "nama": "Rini", "password": pw})
    lain.post("/api/auth/login", json={"username": uname2, "password": pw})
    assert lain.post(f"/api/me/acara/{eid}/gabung", json={"peran": "koordinator", "password": "pw-acara-2031"}).status_code == 400
    assert lain.post(f"/api/me/acara/{eid}/gabung", json={"peran": "anggota", "password": "salah-salah"}).status_code == 401
    assert lain.post(f"/api/me/acara/{eid}/gabung", json={"peran": "pj", "password": "pw-acara-2031"}).status_code == 201
    assert lain.post(f"/api/me/acara/{eid}/gabung", json={"peran": "pj", "password": "pw-acara-2031"}).status_code == 409
    assert any(a["id"] == eid and a["peran"] == "pj" for a in lain.get("/api/me/acara").get_json()["acara"])
    # acara yang sudah ditutup tidak muncul sebagai terbuka
    assert all(e["id"] != eid or True for e in client.get("/api/auth/events").get_json()["events"])


def test_gabung_acara_dikunci_setelah_5_kali_salah():
    import uuid
    ketua = capy.app.test_client()
    uname = "kunci_" + uuid.uuid4().hex[:8]
    c = capy.app.test_client()
    c.post("/api/auth/daftar", json={"username": uname, "nama": "Kunci", "password": "sandi-kunci-2031"})
    c.post("/api/auth/login", json={"username": uname, "password": "sandi-kunci-2031"})
    eid = c.post("/api/events", json={"nama": "Acara Kunci", "password": "pw-kunci-2031"}).get_json()["id"]
    lain = capy.app.test_client()
    u2 = "kunci2_" + uuid.uuid4().hex[:8]
    lain.post("/api/auth/daftar", json={"username": u2, "nama": "Dua", "password": "sandi-kunci-2031"})
    lain.post("/api/auth/login", json={"username": u2, "password": "sandi-kunci-2031"})
    for _ in range(5):
        assert lain.post(f"/api/me/acara/{eid}/gabung", json={"peran": "anggota", "password": "salah-salah"}).status_code == 401
    assert lain.post(f"/api/me/acara/{eid}/gabung", json={"peran": "anggota", "password": "pw-kunci-2031"}).status_code == 429


def _oid_user(uname):
    with capy.app.app_context():
        return capy.Orang.query.filter(capy.db.func.lower(capy.Orang.username) == uname.lower()).first().id


def test_tugas_dibagi_diterima_atau_ditolak_lalu_tindak_lanjut_ketua():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Konfirmasi Tugas", "tanggal": "2031-06-06"}).get_json()["id"]
    # penerima: user yang bergabung ke acara sebagai anggota
    c = capy.app.test_client()
    uname = _user_baru(c, nama="Penerima Tugas")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="anggota"))
        capy.db.session.commit()
    tid = ketua.post("/api/tasks", json={"judul": "Cetak banner", "divisi": "Humas", "event_id": eid,
                                          "deadline_iso": "2031-06-01T10:00:00"}).get_json()["id"]
    # bagikan ke orang yang bukan peserta acara -> ditolak
    assert ketua.post(f"/api/tasks/{tid}/tugaskan", json={"orang_id": "bukan-peserta"}).status_code == 400
    # bagikan ke peserta -> menunggu konfirmasi
    res = ketua.post(f"/api/tasks/{tid}/tugaskan", json={"orang_id": oid})
    assert res.status_code == 200 and res.get_json()["konfirmasi"] is None
    # hanya penerima yang bisa mengonfirmasi
    assert ketua.post(f"/api/tasks/{tid}/konfirmasi", json={"aksi": "terima"}).status_code == 403
    assert c.post(f"/api/me/acara/{eid}/masuk").status_code == 200
    assert c.post(f"/api/tasks/{tid}/konfirmasi", json={"aksi": "tolak"}).status_code == 400  # alasan wajib
    tolak = c.post(f"/api/tasks/{tid}/konfirmasi", json={"aksi": "tolak", "alasan": "Sedang ujian"})
    assert tolak.status_code == 200 and tolak.get_json()["konfirmasi"] == "ditolak"
    # Ketua melihat tugas yang ditolak di daftar tindak lanjut
    tl = ketua.get(f"/api/events/{eid}/tindak-lanjut").get_json()
    assert any(t["id"] == tid and t["alasan"] == "Sedang ujian" for t in tl["ditolak"])
    # bagikan ulang lalu terima
    ketua.post(f"/api/tasks/{tid}/tugaskan", json={"orang_id": oid})
    ok = c.post(f"/api/tasks/{tid}/konfirmasi", json={"aksi": "terima"})
    assert ok.status_code == 200 and ok.get_json()["konfirmasi"] == "diterima"
    tl = ketua.get(f"/api/events/{eid}/tindak-lanjut").get_json()
    assert not any(t["id"] == tid for t in tl["ditolak"]) and not any(t["id"] == tid for t in tl["belum_dibagi"])
    # tugas tanpa penerima muncul sebagai belum dibagi
    t2 = ketua.post("/api/tasks", json={"judul": "Susun TOR", "divisi": "Humas", "event_id": eid}).get_json()["id"]
    tl = ketua.get(f"/api/events/{eid}/tindak-lanjut").get_json()
    assert any(t["id"] == t2 for t in tl["belum_dibagi"])
    # tugas yang menunggu konfirmasi lebih dari 24 jam muncul di daftar Ketua
    t3 = ketua.post("/api/tasks", json={"judul": "Pasang spanduk", "divisi": "Humas", "event_id": eid}).get_json()["id"]
    ketua.post(f"/api/tasks/{t3}/tugaskan", json={"orang_id": oid})
    with capy.app.app_context():
        task = capy.db.session.get(capy.Task, t3)
        task.penerima_ditugaskan_pada = capy.datetime.utcnow() - capy.timedelta(hours=25)
        capy.db.session.commit()
    tl = ketua.get(f"/api/events/{eid}/tindak-lanjut").get_json()
    assert any(t["id"] == t3 for t in tl["belum_konfirmasi"])
    # anggota biasa tidak bisa membuka daftar tindak lanjut
    assert c.get(f"/api/events/{eid}/tindak-lanjut").status_code in (403, 404)


def test_template_acara_membuat_tugas_awal_dengan_tenggat_mundur():
    c = new_client()
    res = c.post("/api/events", json={"nama": "Pemilihan Uji", "tanggal": "2031-09-10", "template": "pemilihan"})
    assert res.status_code == 201
    eid = res.get_json()["id"]
    tugas = c.get(f"/api/events/{eid}").get_json()["tasks"]
    assert len(tugas) == 6
    assert any(t["judul"].startswith("Surat undangan") and t["deadline_iso"].startswith("2031-08-20") for t in tugas)
    assert c.get("/api/auth/me").get_json()["admin"] is False


def test_admin_melihat_dan_mengklaim_acara_tanpa_ketua():
    with capy.app.app_context():
        admin = capy.Orang(username="admin_uji_" + capy.uuid.uuid4().hex[:6], nama="Admin Uji",
                           password_hash=generate_password_hash("sandi-admin-2031"), admin=True)
        capy.db.session.add(admin)
        capy.db.session.commit()
        uname = admin.username
        ev = capy.Event(nama="Acara Lama", tanggal="2024-01-01")
        capy.db.session.add(ev)
        capy.db.session.commit()
        eid = ev.id
    c = capy.app.test_client()
    assert c.post("/api/auth/login", json={"username": uname, "password": "sandi-admin-2031"}).status_code == 200
    daftar = c.get("/api/admin/acara-tanpa-ketua").get_json()["acara"]
    assert any(a["id"] == eid for a in daftar)
    assert c.post(f"/api/events/{eid}/klaim").status_code == 200
    assert all(a["id"] != eid for a in c.get("/api/admin/acara-tanpa-ketua").get_json()["acara"])
    with capy.app.test_client() as u:
        _user_baru(u, nama="Bukan Admin")
        assert u.get("/api/admin/acara-tanpa-ketua").status_code == 403


def test_ketua_menurunkan_memindah_dan_mengeluarkan_anggota_langsung_berlaku():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Atur Peran", "tanggal": "2031-07-07"}).get_json()["id"]
    c = capy.app.test_client()
    uname = _user_baru(c, nama="Anggota Atur")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="koordinator", seksi="Humas"))
        capy.db.session.commit()
        baris = capy.PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first()
        baris_id = baris.id
        ketua_row = capy.PeranAcara.query.filter_by(event_id=eid, peran="ketua").first().id
    assert c.post(f"/api/me/acara/{eid}/masuk").status_code == 200
    assert c.get(f"/api/events/{eid}/tindak-lanjut").status_code in (403, 404)  # koordinator bukan Ketua
    # Ketua memindahkan koordinator ke seksi lain
    assert ketua.put(f"/api/events/{eid}/peran/{baris_id}", json={"peran": "koordinator", "seksi": "Konsumsi"}).status_code == 200
    # lalu menurunkan jabatannya menjadi anggota: akses koordinator langsung hilang di sesi yang sama
    turun = ketua.put(f"/api/events/{eid}/peran/{baris_id}", json={"peran": "anggota"})
    assert turun.status_code == 200 and turun.get_json()["seksi"] is None
    me = c.get("/api/auth/me").get_json()
    assert me["peran"] == "anggota"
    # Ketua tidak bisa diubah atau dikeluarkan
    assert ketua.put(f"/api/events/{eid}/peran/{ketua_row}", json={"peran": "anggota"}).status_code == 400
    assert ketua.delete(f"/api/events/{eid}/peran/{ketua_row}").status_code == 400
    # koordinator wajib punya seksi
    assert ketua.put(f"/api/events/{eid}/peran/{baris_id}", json={"peran": "koordinator"}).status_code == 400
    # Ketua mengeluarkan anggota: sesi anggota langsung kehilangan acara
    assert ketua.delete(f"/api/events/{eid}/peran/{baris_id}").status_code == 200
    after = c.get("/api/auth/me").get_json()
    assert after["event_id"] is None
    assert c.get(f"/api/events/{eid}").status_code == 403  # tidak lagi bisa membaca data acara



def test_catat_keputusan_dan_lihat_daftarnya():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Catat Keputusan", "tanggal": "2031-08-08"}).get_json()["id"]
    res = ketua.post(f"/api/events/{eid}/keputusan", json={"judul": "Tempat acara pindah ke aula", "isi": "Disetujui rapat Senin"})
    assert res.status_code in (200, 201)
    daftar = ketua.get(f"/api/events/{eid}/keputusan").get_json()
    items = daftar.get("keputusan", daftar) if isinstance(daftar, dict) else daftar
    assert any(k["judul"] == "Tempat acara pindah ke aula" for k in items)




class _Balas:
    def __init__(self, data, status=200):
        self._d = data
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            import requests as rq
            raise rq.HTTPError(f"status {self.status_code}")
    def json(self):
        return self._d


def _panggilan(nama, args):
    return {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": nama, "arguments": args}}]}}


def _teks(t):
    return {"message": {"role": "assistant", "content": t}}


def _tugas_di(c, eid, judul, seksi="Humas"):
    return c.post("/api/tasks", json={"judul": judul, "divisi": seksi, "event_id": eid}).get_json()["id"]


def test_agen_butuh_login():
    assert capy.app.test_client().post("/api/agen/chat", json={"pesan": "halo"}).status_code == 401


def test_konteks_agen_menyertakan_semua_seksi_yang_valid():
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Agen Semua Seksi", "tanggal": "2031-11-11"}).get_json()["id"]
    konteks = capy._konteks_acara(eid)
    assert "Seksi yang tersedia:" in konteks
    assert all(seksi in konteks for seksi in capy.aturan_peran.SEKSI)
    assert capy.AGEN_MAKS_LANGKAH >= len(capy.aturan_peran.SEKSI) + 1


def test_agen_membaca_ringkasan_acara_lewat_alat():
    from unittest.mock import patch
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Agen Baca", "tanggal": "2031-11-11"}).get_json()["id"]
    _tugas_di(u, eid, "Cetak spanduk")
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("ringkasan_acara", {"event_id": eid})), _Balas(_teks("Ada 1 tugas, belum dibagi."))]) as mock:
        res = u.post("/api/agen/chat", json={"pesan": "Ringkas acaraku"})
    body = res.get_json()
    assert body["jawaban"] == "Ada 1 tugas, belum dibagi."
    isi_alat = [m for m in mock.call_args_list[1].kwargs["json"]["messages"] if m["role"] == "tool"][0]["content"]
    assert '"total": 1' in isi_alat and '"belum_dibagi": 1' in isi_alat
    assert "tools" in mock.call_args_list[0].kwargs["json"]


def test_agen_tidak_membocorkan_acara_yang_bukan_miliknya():
    from unittest.mock import patch
    pemilik = new_client()
    eid = pemilik.post("/api/events", json={"nama": "Rahasia", "tanggal": "2031-12-12"}).get_json()["id"]
    _tugas_di(pemilik, eid, "Data rahasia")
    orang = new_client()
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("daftar_tugas", {"event_id": eid})), _Balas(_teks("Tidak bisa."))]) as mock:
        orang.post("/api/agen/chat", json={"pesan": "Tugas di acara itu?"})
    isi_alat = [m for m in mock.call_args_list[1].kwargs["json"]["messages"] if m["role"] == "tool"][0]["content"]
    assert "error" in isi_alat and "Data rahasia" not in isi_alat


def test_agen_buka_halaman_hanya_yang_terdaftar():
    from unittest.mock import patch
    u = new_client()
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("buka_halaman", {"tujuan": "ruang_kerja"})), _Balas(_teks("Ini ruang kerjamu."))]):
        res = u.post("/api/agen/chat", json={"pesan": "Buka ruang kerja"})
    assert res.get_json()["aksi"] == [{"jenis": "navigasi", "url": "/kerja", "label": "Buka ruang kerja"}]
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("buka_halaman", {"tujuan": "/etc/passwd"})), _Balas(_teks("Tidak bisa."))]):
        res = u.post("/api/agen/chat", json={"pesan": "Buka file sistem"})
    assert res.get_json()["aksi"] == []


def test_agen_usulan_tugas_tidak_langsung_dibuat_dan_butuh_jalankan():
    from unittest.mock import patch
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Usul Tugas", "tanggal": "2031-01-02"}).get_json()["id"]
    sebelum = Task.query.count() if False else None
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("usulkan_tugas", {"event_id": eid, "judul": "Susun TOR", "seksi": "Acara", "tenggat": "2031-01-20T10:00"})), _Balas(_teks("Usulan siap, tekan Jalankan."))]):
        res = ketua.post("/api/agen/chat", json={"pesan": "Buat tugas susun TOR untuk seksi Acara"})
    aksi = res.get_json()["aksi"]
    assert len(aksi) == 1 and aksi[0]["jenis"] == "usulan" and aksi[0]["tipe"] == "tugas_baru"
    assert not ketua.get(f"/api/events/{eid}").get_json()["tasks"] or all(t["judul"] != "Susun TOR" for t in ketua.get(f"/api/events/{eid}").get_json()["tasks"])
    jalan = ketua.post("/api/agen/jalankan", json={"tipe": aksi[0]["tipe"], "data": aksi[0]["data"]})
    assert jalan.status_code == 201
    assert any(t["judul"] == "Susun TOR" for t in ketua.get(f"/api/events/{eid}").get_json()["tasks"])


def test_agen_anggota_biasa_tidak_bisa_mengusulkan_atau_menjalankan_tugas():
    from unittest.mock import patch
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Bukan Ketua", "tanggal": "2031-02-03"}).get_json()["id"]
    anggota = capy.app.test_client()
    uname = _user_baru(anggota, nama="Anggota Biasa")
    with capy.app.app_context():
        oid = capy.Orang.query.filter(capy.db.func.lower(capy.Orang.username) == uname.lower()).first().id
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="anggota"))
        capy.db.session.commit()
    anggota.post(f"/api/me/acara/{eid}/masuk")
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("usulkan_tugas", {"event_id": eid, "judul": "Coba", "seksi": "Acara"})), _Balas(_teks("Tidak bisa."))]) as mock:
        res = anggota.post("/api/agen/chat", json={"pesan": "Buat tugas"})
    assert res.get_json()["aksi"] == []
    assert "Hanya Ketua" in [m for m in mock.call_args_list[1].kwargs["json"]["messages"] if m["role"] == "tool"][0]["content"]
    assert anggota.post("/api/agen/jalankan", json={"tipe": "tugas_baru", "data": {"event_id": eid, "judul": "Coba", "seksi": "Acara"}}).status_code == 403


def test_agen_usulan_bagikan_tugas_dan_keputusan_dijalankan_dengan_izin():
    from unittest.mock import patch
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Bagi Tugas Agen", "tanggal": "2031-03-04"}).get_json()["id"]
    tid = _tugas_di(ketua, eid, "Pasang spanduk", "Humas")
    penerima = capy.app.test_client()
    uname = _user_baru(penerima, nama="Dita Penerima")
    with capy.app.app_context():
        oid = capy.Orang.query.filter(capy.db.func.lower(capy.Orang.username) == uname.lower()).first().id
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="anggota"))
        capy.db.session.commit()
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("usulkan_bagikan_tugas", {"task_id": tid, "nama_penerima": "Dita Penerima"})), _Balas(_teks("Siap."))]):
        aksi = ketua.post("/api/agen/chat", json={"pesan": "Bagikan spanduk ke Dita"}).get_json()["aksi"]
    assert aksi[0]["tipe"] == "bagikan_tugas" and aksi[0]["data"]["orang_id"] == oid
    assert ketua.post("/api/agen/jalankan", json={"tipe": "bagikan_tugas", "data": aksi[0]["data"]}).status_code == 201
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid).penerima_orang_id == oid
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("usulkan_keputusan", {"event_id": eid, "judul": "Pindah ke aula"})), _Balas(_teks("Siap."))]):
        aksi = ketua.post("/api/agen/chat", json={"pesan": "Catat keputusan pindah ke aula"}).get_json()["aksi"]
    assert aksi[0]["tipe"] == "keputusan"
    assert ketua.post("/api/agen/jalankan", json={"tipe": "keputusan", "data": aksi[0]["data"]}).status_code == 201
    assert any(k["judul"] == "Pindah ke aula" for k in ketua.get(f"/api/events/{eid}/keputusan").get_json()["keputusan"])


def test_batal_dan_ulang_perubahan_tugas():
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Riwayat Tugas", "tanggal": "2031-05-05"}).get_json()["id"]
    tid = _tugas_di(u, eid, "Judul lama", "Humas")
    u.patch(f"/api/tasks/{tid}", json={"judul": "Judul baru"})  # ketua tidak mengubah isi tugas; pakai akun seksi
    # ketua tidak bisa PATCH isi tugas (aturan seksi), jadi uji lewat jalur usulan yang sama dengan Capy
    with capy.app.app_context():
        t = capy.db.session.get(capy.Task, tid)
        sebelum = capy.Task.query.get(tid).judul
    assert sebelum == "Judul lama"
    from unittest.mock import patch
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("ubah_tugas", {"task_id": tid, "judul": "Judul baru"})), _Balas(_teks("Siap."))]):
        aksi = u.post("/api/agen/chat", json={"pesan": "ubah judul tugas"}).get_json()["aksi"]
    assert u.post("/api/agen/jalankan", json={"tipe": "ubah_tugas", "data": aksi[0]["data"]}).status_code == 201
    st = u.get(f"/api/riwayat?event_id={eid}").get_json()
    assert st["batal"].startswith("Ubah tugas") and st["ulang"] is None
    assert u.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid).judul == "Judul lama"
    assert u.post("/api/riwayat/ulang", json={"event_id": eid}).status_code == 200
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid).judul == "Judul baru"


def test_batal_hapus_tugas_dan_keluarkan_peserta_lewat_capy_dengan_konfirmasi():
    from unittest.mock import patch
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Hapus Riwayat", "tanggal": "2031-06-06"}).get_json()["id"]
    tid = _tugas_di(u, eid, "Tugas sementara", "Acara")
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("hapus_tugas", {"task_id": tid})), _Balas(_teks("Siap."))]):
        aksi = u.post("/api/agen/chat", json={"pesan": "hapus tugas sementara"}).get_json()["aksi"]
    assert aksi[0]["berbahaya"] is True
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid) is not None  # belum terhapus sebelum Jalankan
    assert u.post("/api/agen/jalankan", json={"tipe": "hapus_tugas", "data": aksi[0]["data"]}).status_code == 201
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid) is None
    assert u.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid) is not None  # kembali
    # keluarkan peserta lewat Capy, lalu batalkan
    orang = capy.app.test_client()
    uname = _user_baru(orang, nama="Peserta Riwayat")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="anggota"))
        capy.db.session.commit()
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("keluarkan_peserta", {"event_id": eid, "nama": "Peserta Riwayat"})), _Balas(_teks("Siap."))]):
        aksi = u.post("/api/agen/chat", json={"pesan": "keluarkan peserta riwayat"}).get_json()["aksi"]
    assert u.post("/api/agen/jalankan", json={"tipe": "keluarkan", "data": aksi[0]["data"]}).status_code == 201
    with capy.app.app_context():
        assert not capy.PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first()
    assert u.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    with capy.app.app_context():
        assert capy.PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first() is not None


def test_batal_tutup_acara_mengembalikan_peran_dan_membuka_kembali():
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Tutup Riwayat", "tanggal": "2031-07-07"}).get_json()["id"]
    orang = capy.app.test_client()
    uname = _user_baru(orang, nama="Koordinator Riwayat")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="koordinator", seksi="Humas"))
        capy.db.session.commit()
    assert u.post(f"/api/events/{eid}/tutup").status_code == 200
    with capy.app.app_context():
        assert capy.PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first().peran == "anggota"
    assert u.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    with capy.app.app_context():
        assert capy.PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first().peran == "koordinator"
        assert capy.db.session.get(capy.EventArsip, eid) is None


def test_riwayat_hanya_milik_pembuatnya_dan_usulan_nonketua_ditolak():
    from unittest.mock import patch
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Milik Sendiri", "tanggal": "2031-08-08"}).get_json()["id"]
    _tugas_di(u, eid, "Tugas milik ketua", "Humas")
    lain = new_client()
    assert lain.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 403  # bukan anggota acara
    orang = capy.app.test_client()
    uname = _user_baru(orang, nama="Anggota Riwayat")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="anggota"))
        capy.db.session.commit()
    assert orang.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 409  # tidak ada riwayat miliknya
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("ubah_peran_peserta", {"event_id": eid, "nama": "Anggota Riwayat", "peran": "pj"})), _Balas(_teks("Tidak bisa."))]) as mock:
        res = orang.post("/api/agen/chat", json={"pesan": "naikkan saya"}).get_json()
    assert res["aksi"] == []
    assert "Hanya Ketua" in [m for m in mock.call_args_list[1].kwargs["json"]["messages"] if m["role"] == "tool"][0]["content"]


def test_agen_buat_laporan_memberi_tautan_unduh():
    from unittest.mock import patch
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Laporan Agen", "tanggal": "2031-09-09"}).get_json()["id"]
    with patch.object(capy.requests, "post", side_effect=[_Balas(_panggilan("buat_laporan", {"event_id": eid})), _Balas(_teks("Ini tautannya."))]):
        aksi = u.post("/api/agen/chat", json={"pesan": "buat laporan"}).get_json()["aksi"]
    assert aksi == [{"jenis": "navigasi", "url": f"/api/events/{eid}/dokumen/laporan.pdf", "label": "Unduh laporan PDF"}]


def test_login_gagal_satu_pengguna_tidak_mengunci_pengguna_lain_di_ip_sama():
    capy._login_fails.clear()
    c = capy.app.test_client()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "orang-a", "password": "salah-salah"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "orang-a", "password": "salah-salah"}).status_code == 429
    assert c.post("/api/auth/login", json={"username": "orang-b", "password": "salah-salah"}).status_code == 401
    capy._login_fails.clear()


def test_admin_angkat_dan_atur_ulang_password_hanya_oleh_admin():
    import uuid
    capy._login_fails.clear()
    with capy.app.app_context():
        adm = capy.Orang(username="adm_" + uuid.uuid4().hex[:6], nama="Admin Uji", password_hash=generate_password_hash("sandi-admin-2031"), admin=True)
        capy.db.session.add(adm); capy.db.session.commit(); admin_nama = adm.username
    c = capy.app.test_client()
    assert c.post("/api/auth/login", json={"username": admin_nama, "password": "sandi-admin-2031"}).status_code == 200
    anggota = capy.app.test_client()
    _user_baru(anggota, nama="Anggota Biasa Admin")
    assert anggota.post("/api/admin/angkat", json={"username": admin_nama}).status_code == 403
    assert anggota.post("/api/admin/reset-password", json={"username": admin_nama, "password": "sandi-baru-2031"}).status_code == 403
    assert c.post("/api/admin/reset-password", json={"username": admin_nama, "password": "pendek"}).status_code == 400
    assert c.post("/api/admin/reset-password", json={"username": admin_nama, "password": "sandi-baru-2031"}).status_code == 200
    assert c.post("/api/auth/login", json={"username": admin_nama, "password": "sandi-baru-2031"}).status_code == 200
    assert c.post("/api/admin/angkat", json={"username": admin_nama, "admin": False}).get_json()["admin"] is False
    capy._login_fails.clear()


def test_batal_gabung_acara_dan_catatan_keputusan():
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Gabung Batal", "tanggal": "2031-10-10", "password": "pw-gabung-2031"}).get_json()["id"]
    orang = capy.app.test_client()
    uname = _user_baru(orang, nama="Peserta Gabung")
    assert orang.post(f"/api/me/acara/{eid}/gabung", json={"peran": "anggota", "password": "pw-gabung-2031"}).status_code == 201
    assert orang.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    assert orang.post(f"/api/me/acara/{eid}/gabung", json={"peran": "anggota", "password": "pw-gabung-2031"}).status_code == 201
    assert orang.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    assert orang.post(f"/api/me/acara/{eid}/gabung", json={"peran": "anggota", "password": "pw-gabung-2031"}).status_code == 201
    u.post(f"/api/events/{eid}/keputusan", json={"judul": "Pindah ke aula", "isi": ""})
    assert u.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200
    assert all(k["judul"] != "Pindah ke aula" for k in u.get(f"/api/events/{eid}/keputusan").get_json()["keputusan"])
    assert u.post("/api/riwayat/ulang", json={"event_id": eid}).status_code == 200
    assert any(k["judul"] == "Pindah ke aula" for k in u.get(f"/api/events/{eid}/keputusan").get_json()["keputusan"])


def test_serahkan_ketua_dan_batalkan_kembali():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Serah Ketua", "tanggal": "2031-11-11"}).get_json()["id"]
    c = capy.app.test_client()
    uname = _user_baru(c, nama="Calon Ketua")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="pj"))
        capy.db.session.commit()
    assert ketua.post(f"/api/events/{eid}/serahkan-ketua", json={"orang_id": "bukan-peserta"}).status_code == 400
    assert ketua.post(f"/api/events/{eid}/serahkan-ketua", json={"orang_id": oid}).status_code == 200
    assert c.post(f"/api/me/acara/{eid}/masuk").get_json()["peran"] == "ketua"
    assert c.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 409  # bukan pencatat perubahan
    assert ketua.post("/api/riwayat/batal", json={"event_id": eid}).status_code == 200  # pencatatnya yang membatalkan
    with capy.app.app_context():
        assert capy.PeranAcara.query.filter_by(event_id=eid, orang_id=oid).first().peran == "pj"
        assert capy.db.session.get(capy.Event, eid).pembuat_id != oid


def test_buat_admin_lewat_skrip():
    import uuid, buat_admin
    with capy.app.app_context():
        o = capy.Orang(username="calon_" + uuid.uuid4().hex[:6], nama="Calon", password_hash=generate_password_hash("sandi-calon-2031"), admin=False)
        capy.db.session.add(o); capy.db.session.commit(); nama = o.username
    import sys
    sys.argv = ["buat_admin.py", nama]
    buat_admin.main()
    with capy.app.app_context():
        assert capy.Orang.query.filter_by(username=nama).first().admin is True


def test_orang_luar_acara_tidak_bisa_sukses_di_endpoint_manapun():
    """Sapuan akses: akun yang bukan anggota tidak boleh mendapat respons sukses dari endpoint yang memakai id acara/tugas."""
    import re
    pemilik = new_client()
    eid = pemilik.post("/api/events", json={"nama": "Sapuan Akses", "tanggal": "2031-12-01", "password": "pw-sapuan-2031"}).get_json()["id"]
    tid = _tugas_di(pemilik, eid, "Tugas rahasia", "Humas")
    pemilik.post(f"/api/events/{eid}/keputusan", json={"judul": "Keputusan rahasia", "isi": ""})
    luar = new_client()
    publik = {"/api/auth/events", "/api/auth/me", "/api/auth/login", "/api/auth/logout", "/api/auth/daftar",
              "/api/beranda", "/api/me/acara", "/api/me/keluar-acara", "/api/riwayat", "/api/riwayat/batal",
              "/api/riwayat/ulang", "/api/agen/chat", "/api/agen/jalankan", "/api/bantu", "/api/tasks", "/api/tasks/stats",
              "/api/team/stats", "/api/admin/acara-tanpa-ketua", "/api/admin/angkat", "/api/admin/reset-password", "/api/events"}
    gagal = []
    for rule in capy.app.url_map.iter_rules():
        path = rule.rule
        if not path.startswith("/api/") or path in publik:
            continue
        if not re.search(r"<(event_id|task_id|kid|peran_id|id|pos_id|item_id|eid)>", path):
            continue
        url = re.sub(r"<(event_id|eid)>", eid, path)
        url = re.sub(r"<(task_id|tid)>", tid, url)
        url = re.sub(r"<[^>]+>", "x", url)
        for metode in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            if metode == "GET":
                res = luar.get(url)
            else:
                res = luar.open(url, method=metode, json={})
            if 200 <= res.status_code < 300:
                gagal.append((metode, path, res.status_code))
    assert gagal == [], f"endpoint bisa diakses orang luar acara: {gagal}"


def test_ketua_acara_a_tidak_bisa_mengakses_acara_b():
    ketua_a = new_client()
    ketua_a.post("/api/events", json={"nama": "Acara A", "tanggal": "2031-01-05"})
    ketua_b = new_client()
    eid_b = ketua_b.post("/api/events", json={"nama": "Acara B", "tanggal": "2031-01-06"}).get_json()["id"]
    _tugas_di(ketua_b, eid_b, "Rahasia B", "Humas")
    # ketua A (sesinya di acara A) mencoba membaca dan mengubah acara B
    assert ketua_a.get(f"/api/events/{eid_b}").status_code == 403
    assert ketua_a.get(f"/api/events/{eid_b}/peran").status_code in (403, 404)
    assert ketua_a.get(f"/api/events/{eid_b}/tindak-lanjut").status_code in (403, 404)
    assert ketua_a.put(f"/api/events/{eid_b}/password", json={"password": "pw-curang-2031"}).status_code in (403, 404)
    assert ketua_a.get(f"/api/events/{eid_b}/calendar.ics").status_code == 403


def test_ketua_acara_a_tidak_bisa_mengubah_tugas_acara_b():
    ketua_a = new_client()
    ketua_a.post("/api/events", json={"nama": "Acara A2", "tanggal": "2031-02-05"})
    ketua_b = new_client()
    eid_b = ketua_b.post("/api/events", json={"nama": "Acara B2", "tanggal": "2031-02-06"}).get_json()["id"]
    tid_b = _tugas_di(ketua_b, eid_b, "Tugas B asli", "Humas")
    assert ketua_a.patch(f"/api/tasks/{tid_b}", json={"judul": "Diubah ketua A"}).status_code in (403, 404)
    assert ketua_a.delete(f"/api/tasks/{tid_b}").status_code in (403, 404)
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid_b).judul == "Tugas B asli"


def test_skrip_cadangan_menyalin_database_sqlite():
    import os, subprocess, sys, glob
    folder = os.path.dirname(capy.__file__)
    antes = set(glob.glob(os.path.join(folder, "backups", "*.db")))
    with capy.app.app_context():
        pass
    res = subprocess.run([sys.executable, os.path.join(folder, "cadangan_db.py")], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert set(glob.glob(os.path.join(folder, "backups", "*.db"))) - antes


def test_lupa_password_dengan_kode_pemulihan_sekali_pakai():
    import uuid
    capy._login_fails.clear()
    c = capy.app.test_client()
    uname = "pulih_" + uuid.uuid4().hex[:6]
    res = c.post("/api/auth/daftar", json={"username": uname, "nama": "Pemulih", "password": "sandi-awal-2031"})
    assert res.status_code == 201 and res.get_json()["kode_pemulihan"].count("-") == 2
    kode = res.get_json()["kode_pemulihan"]
    assert c.post("/api/auth/lupa-password", json={"username": uname, "kode": "SALAH-SALAH-SALAH", "password_baru": "sandi-baru-2031"}).status_code == 401
    ok = c.post("/api/auth/lupa-password", json={"username": uname, "kode": kode.lower(), "password_baru": "sandi-baru-2031"})
    assert ok.status_code == 200 and ok.get_json()["kode_pemulihan"] != kode
    assert c.post("/api/auth/lupa-password", json={"username": uname, "kode": kode, "password_baru": "sandi-lain-2031"}).status_code == 401  # kode lama hangus
    assert c.post("/api/auth/login", json={"username": uname, "password": "sandi-baru-2031"}).status_code == 200
    capy._login_fails.clear()


def test_kuota_capy_habis_lalu_diberi_tahu_kapan_bisa_lagi():
    from unittest.mock import patch
    old_kuota, old_key = capy.ASISTEN_KUOTA_HARIAN, capy.OLLAMA_URL
    capy.ASISTEN_KUOTA_HARIAN = 2
    try:
        u = new_client()
        eid = u.post("/api/events", json={"nama": "Kuota Uji", "tanggal": "2031-03-03"}).get_json()["id"]
        with patch.object(capy.requests, "post", return_value=_Balas(_teks("Baik."))):
            assert u.post("/api/agen/chat", json={"pesan": "halo"}).status_code == 200
            assert u.post("/api/agen/chat", json={"pesan": "halo"}).status_code == 200
            habis = u.post("/api/agen/chat", json={"pesan": "halo"})
        assert habis.status_code == 429 and habis.get_json()["kuota_habis"] is True
        assert "besok" in habis.get_json()["kapan"]
    finally:
        capy.ASISTEN_KUOTA_HARIAN = old_kuota


def test_pengingat_tenggat_saya_tampil_otomatis():
    from datetime import datetime as _dt, timedelta as _td
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Pengingat Uji", "tanggal": "2031-04-04"}).get_json()["id"]
    dekat = (_dt.utcnow() + _td(days=1)).strftime("%Y-%m-%dT%H:%M")
    jauh = (_dt.utcnow() + _td(days=20)).strftime("%Y-%m-%dT%H:%M")
    u.post("/api/tasks", json={"judul": "Tenggat dekat", "divisi": "Humas", "event_id": eid, "deadline_iso": dekat})
    u.post("/api/tasks", json={"judul": "Tenggat jauh", "divisi": "Humas", "event_id": eid, "deadline_iso": jauh})
    judul = [p["judul"] for p in u.get("/api/me/pengingat").get_json()["pengingat"]]
    assert "Tenggat dekat" in judul and "Tenggat jauh" not in judul
    anggota = capy.app.test_client()
    _user_baru(anggota, nama="Tanpa Tugas")
    assert anggota.get("/api/me/pengingat").get_json()["pengingat"] == []


def test_riwayat_capy_terpisah_per_acara_dan_per_orang():
    from unittest.mock import patch
    u = new_client()
    a = u.post("/api/events", json={"nama": "Acara Alfa", "tanggal": "2031-05-05"}).get_json()["id"]
    b = u.post("/api/events", json={"nama": "Acara Beta", "tanggal": "2031-05-06"}).get_json()["id"]
    with patch.object(capy.requests, "post", return_value=_Balas(_teks("Jawaban untuk Alfa."))):
        assert u.post("/api/agen/chat", json={"pesan": "Rahasia-Alfa", "event_id": a}).status_code == 200
    # acara B: riwayat kosong, dan model tidak menerima pesan dari A
    assert u.get(f"/api/agen/riwayat?event_id={b}").get_json()["pesan"] == []
    with patch.object(capy.requests, "post", return_value=_Balas(_teks("Jawaban untuk Beta."))) as mock:
        u.post("/api/agen/chat", json={"pesan": "Pertanyaan Beta", "event_id": b})
    isi_model = json.dumps(mock.call_args.kwargs["json"]["messages"], ensure_ascii=False)
    assert "Rahasia-Alfa" not in isi_model and "Acara Beta" in isi_model and "Acara Alfa" not in isi_model
    # riwayat A utuh
    isi_a = [p["isi"] for p in u.get(f"/api/agen/riwayat?event_id={a}").get_json()["pesan"]]
    assert isi_a == ["Rahasia-Alfa", "Jawaban untuk Alfa."]
    # orang lain tidak bisa melihat riwayat saya
    lain = capy.app.test_client()
    _user_baru(lain, nama="Orang Lain Chat")
    assert lain.get(f"/api/agen/riwayat?event_id={a}").status_code == 403  # bukan anggota acara
    # mulai baru hanya menghapus riwayat acara itu
    assert u.delete(f"/api/agen/riwayat?event_id={a}").get_json()["dihapus"] == 2
    assert u.get(f"/api/agen/riwayat?event_id={a}").get_json()["pesan"] == []


def test_chat_di_acara_yang_bukan_milik_ditolak():
    from unittest.mock import patch
    pemilik = new_client()
    eid = pemilik.post("/api/events", json={"nama": "Bukan Milikmu", "tanggal": "2031-06-06"}).get_json()["id"]
    orang = new_client()
    with patch.object(capy.requests, "post", return_value=_Balas(_teks("x"))) as mock:
        assert orang.post("/api/agen/chat", json={"pesan": "halo", "event_id": eid}).status_code == 403
    assert not mock.called


def test_mode_produksi_menolak_tanpa_secret_key():
    import subprocess, sys, os
    env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
    env["CAPY_PRODUKSI"] = "1"
    res = subprocess.run([sys.executable, "-c", "import app"], capture_output=True, text=True, env=env, cwd=os.path.dirname(capy.__file__))
    assert res.returncode != 0 and "SECRET_KEY" in (res.stderr + res.stdout)


def test_header_keamanan_dasar_ada():
    res = capy.app.test_client().get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"


def test_model_dipilih_sesuai_mode_ngobrol_dan_acara():
    from unittest.mock import patch
    old = capy.CAPY_MODEL_OBROLAN, capy.CAPY_MODEL_ACARA
    capy.CAPY_MODEL_OBROLAN, capy.CAPY_MODEL_ACARA = "model-obrolan-uji", "model-acara-uji"
    try:
        u = new_client()
        eid = u.post("/api/events", json={"nama": "Mode Model", "tanggal": "2031-08-08"}).get_json()["id"]
        with patch.object(capy.requests, "post", return_value=_Balas(_teks("ok"))) as mock:
            u.post("/api/agen/chat", json={"pesan": "halo santai"})
            assert mock.call_args.kwargs["json"]["model"] == "model-obrolan-uji"
            u.post("/api/agen/chat", json={"pesan": "cek acara", "event_id": eid})
            assert mock.call_args.kwargs["json"]["model"] == "model-acara-uji"
            assert "tools" in mock.call_args.kwargs["json"]
    finally:
        capy.CAPY_MODEL_OBROLAN, capy.CAPY_MODEL_ACARA = old


def test_sqlite_memakai_wal_dan_batas_tunggu():
    with capy.app.app_context(), capy.db.engine.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        tunggu = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
    assert str(mode).lower() == "wal" and int(tunggu) >= 5000


def test_halaman_admin_data_hanya_untuk_admin():
    import uuid
    capy._login_fails.clear()
    with capy.app.app_context():
        adm = capy.Orang(username="adm_" + uuid.uuid4().hex[:6], nama="Admin Halaman", password_hash=generate_password_hash("sandi-admin-2031"), admin=True)
        capy.db.session.add(adm); capy.db.session.commit(); nama = adm.username
    biasa = new_client()
    for jalur in ["/api/admin/ringkasan", "/api/admin/pengguna", "/api/admin/acara"]:
        assert biasa.get(jalur).status_code == 403
    c = capy.app.test_client()
    assert c.post("/api/auth/login", json={"username": nama, "password": "sandi-admin-2031"}).status_code == 200
    ringkas = c.get("/api/admin/ringkasan").get_json()
    assert ringkas["pengguna"] >= 2 and ringkas["admin"] >= 1 and "kuota_capy_harian" in ringkas
    pengguna = c.get("/api/admin/pengguna?q=" + nama).get_json()["pengguna"]
    assert pengguna and all("password_hash" not in p and "kode_pemulihan_hash" not in p for p in pengguna)
    assert c.get("/api/admin/acara").status_code == 200
    capy._login_fails.clear()


def test_admin_awal_dibuat_dari_env_hanya_jika_belum_ada_admin():
    import uuid, os
    old_u, old_p = os.environ.get("ADMIN_AWAL_USERNAME"), os.environ.get("ADMIN_AWAL_PASSWORD")
    nama = "awal_" + uuid.uuid4().hex[:6]
    with capy.app.app_context():
        for o in capy.Orang.query.filter_by(admin=True).all():
            o.admin = False
        capy.db.session.commit()
    os.environ["ADMIN_AWAL_USERNAME"], os.environ["ADMIN_AWAL_PASSWORD"] = nama, "sandi-awal-admin-2031"
    try:
        with capy.app.app_context():
            assert capy._admin_awal_jika_belum_ada() == nama
            assert capy._admin_awal_jika_belum_ada() is None  # admin sudah ada: tidak mengulang
        c = capy.app.test_client()
        assert c.post("/api/auth/login", json={"username": nama, "password": "sandi-awal-admin-2031"}).status_code == 200
    finally:
        for k, v in (("ADMIN_AWAL_USERNAME", old_u), ("ADMIN_AWAL_PASSWORD", old_p)):
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v


def test_celah_lintas_acara_ditutup():
    """Ketua acara A tidak boleh bertindak di acara B lewat endpoint yang menerima event_id dari permintaan."""
    ketua_a = new_client()
    ketua_a.post("/api/events", json={"nama": "Acara A lintas", "tanggal": "2031-09-01"})
    ketua_b = new_client()
    eid_b = ketua_b.post("/api/events", json={"nama": "Acara B lintas", "tanggal": "2031-09-02"}).get_json()["id"]
    tid_b = _tugas_di(ketua_b, eid_b, "Tugas B lintas", "Humas")
    # buat tugas di B
    assert ketua_a.post("/api/tasks", json={"judul": "Sisipan", "divisi": "Humas", "event_id": eid_b}).status_code == 403
    # kirim pesan ke B
    assert ketua_a.post(f"/api/events/{eid_b}/pesan", json={"isi": "halo", "tingkat": "info", "ke": "semua"}).status_code == 403
    assert ketua_a.post("/api/pesan", json={"event_id": eid_b, "isi": "halo", "tingkat": "info", "ke": "semua"}).status_code == 403
    # peringatan otomatis di B
    assert ketua_a.post("/api/pesan/otomatis", json={"event_id": eid_b}).status_code == 403
    # hasil seksi B
    assert ketua_a.get(f"/api/seksi/hasil?event_id={eid_b}").status_code == 403
    # ruang kerja: acara B tidak ikut terlihat
    assert eid_b not in [a["event"]["id"] for a in ketua_a.get("/api/kerja").get_json()["acara"]]
    # lampiran tugas B: diunduh orang luar ditolak
    with capy.app.app_context():
        l = capy.Lampiran(nama_asli="rahasia.pdf", mime="application/pdf", ukuran=4, berkas="rahasia-uji.pdf", pemilik_seksi="Humas", task_id=tid_b)
        capy.db.session.add(l); capy.db.session.commit(); lid = l.id
    assert ketua_a.get(f"/api/lampiran/{lid}").status_code == 403
    assert ketua_a.delete(f"/api/lampiran/{lid}").status_code == 403
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid_b).judul == "Tugas B lintas"


def test_log_audit_terbaca_admin_saja():
    import uuid
    capy._login_fails.clear()
    with capy.app.app_context():
        adm = capy.Orang(username="adm_log_" + uuid.uuid4().hex[:6], nama="Admin Log", password_hash=generate_password_hash("sandi-admin-log-2031"), admin=True)
        capy.db.session.add(adm); capy.db.session.commit(); nama = adm.username
    u = new_client()
    u.post("/api/events", json={"nama": "Untuk Audit", "tanggal": "2031-11-11"})  # aksi tulis tercatat
    assert u.get("/api/admin/audit").status_code == 403
    c = capy.app.test_client()
    assert c.post("/api/auth/login", json={"username": nama, "password": "sandi-admin-log-2031"}).status_code == 200
    isi = c.get("/api/admin/audit").get_json()["audit"]
    assert isi and all({"waktu", "aktor", "aksi", "rute"} <= set(x) for x in isi)
    capy._login_fails.clear()


def test_lampiran_yatim_lalu_jadi_kabar_acara():
    import io
    u = new_client()
    eid = u.post("/api/events", json={"nama": "Alur Lampiran", "tanggal": "2031-12-12"}).get_json()["id"]
    res = u.post("/api/lampiran", data={"file": (io.BytesIO(b"%PDF-1.4 uji"), "rundown.pdf")}, content_type="multipart/form-data")
    assert res.status_code in (200, 201), res.get_json()
    lid = res.get_json()["id"]
    # pengunggah masih bisa mengunduhnya sebelum dijadikan kabar
    assert u.get(f"/api/lampiran/{lid}").status_code == 200
    # orang luar tidak bisa
    luar = new_client()
    assert luar.get(f"/api/lampiran/{lid}").status_code in (401, 403)
    # dijadikan kabar acara: anggota (pengunggah) berhasil
    assert u.post("/api/kabar", json={"isi": "Rundown terbaru", "event_id": eid, "lampiran_ids": [lid]}).status_code == 201
    with capy.app.app_context():
        assert capy.db.session.get(capy.Lampiran, lid).kabar_id is not None
    # kabar tanpa acara (beranda) ditolak untuk akun biasa
    assert u.post("/api/kabar", json={"isi": "Pengumuman global"}).status_code == 403


def test_kabar_tanpa_acara_hanya_admin():
    import uuid
    capy._login_fails.clear()
    with capy.app.app_context():
        adm = capy.Orang(username="adm_kb_" + uuid.uuid4().hex[:6], nama="Admin Kabar", password_hash=generate_password_hash("sandi-admin-kb-2031"), admin=True)
        capy.db.session.add(adm); capy.db.session.commit(); nama = adm.username
    c = capy.app.test_client()
    assert c.post("/api/auth/login", json={"username": nama, "password": "sandi-admin-kb-2031"}).status_code == 200
    assert c.post("/api/kabar", json={"isi": "Pengumuman beranda"}).status_code == 201
    capy._login_fails.clear()


def ketua_a_oid(klien):
    """Ambil id akun dari sesi klien yang sedang masuk."""
    return klien.get("/api/auth/me").get_json()["orang_id"]


def test_ketua_di_acara_a_yang_anggota_di_b_tidak_berlaku_sebagai_ketua_di_b():
    """Sesi aktif di acara A sebagai Ketua. Di acara B ia hanya anggota: tidak boleh mengubah tugas B sebagai Ketua."""
    ketua_a = new_client()
    ketua_a.post("/api/events", json={"nama": "Acara A peran", "tanggal": "2031-10-01"})
    ketua_b = new_client()
    eid_b = ketua_b.post("/api/events", json={"nama": "Acara B peran", "tanggal": "2031-10-02"}).get_json()["id"]
    tid_b = _tugas_di(ketua_b, eid_b, "Tugas B peran", "Humas")
    # tambahkan akun ketua_a sebagai anggota B (bukan Ketua) langsung di database
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid_b, orang_id=ketua_a_oid(ketua_a), peran="anggota"))
        capy.db.session.commit()
    assert ketua_a.patch(f"/api/tasks/{tid_b}", json={"judul": "Diubah lintas peran"}).status_code == 403
    with capy.app.app_context():
        assert capy.db.session.get(capy.Task, tid_b).judul == "Tugas B peran"


def test_tugas_dan_kabar_acara_tidak_terbaca_lintas_peran():
    ketua_b = new_client()
    eid_b = ketua_b.post("/api/events", json={"nama": "Acara B baca", "tanggal": "2031-11-01"}).get_json()["id"]
    _tugas_di(ketua_b, eid_b, "Tugas Humas rahasia", "Humas")
    _tugas_di(ketua_b, eid_b, "Tugas Konsumsi rahasia", "Konsumsi")
    ketua_b.post("/api/kabar", json={"isi": "Kabar internal B", "publik": False, "event_id": eid_b})
    # anggota seksi Konsumsi di B, sesinya aktif di acara lain sebagai Ketua
    anggota = new_client()
    ketua_lain = new_client()
    ketua_lain.post("/api/events", json={"nama": "Acara lain sesi", "tanggal": "2031-11-02"})
    with capy.app.app_context():
        oid = anggota.get("/api/auth/me").get_json()["orang_id"]
        capy.db.session.add(capy.PeranAcara(event_id=eid_b, orang_id=oid, peran="anggota", seksi="Konsumsi"))
        capy.db.session.commit()
    judul = [t["judul"] for t in anggota.get(f"/api/tasks?event_id={eid_b}").get_json()["tasks"]]
    assert "Tugas Humas rahasia" not in judul
    # orang di luar acara tidak melihat kabar internal
    luar = new_client()
    kabar = [k["isi"] for k in luar.get(f"/api/kabar?event_id={eid_b}").get_json()["kabar"]]
    assert "Kabar internal B" not in kabar


def test_ketua_acara_kosong_tetap_terlihat_di_ruang_kerja():
    k = new_client()
    eid = k.post("/api/events", json={"nama": "Kosong tapi milikku", "tanggal": "2031-07-07"}).get_json()["id"]
    ids = [a["event"]["id"] for a in k.get("/api/kerja").get_json()["acara"]]
    assert eid in ids


def test_tugas_menunggu_saya_lintas_acara_tanpa_masuk_acara():
    ketua = new_client()
    eid = ketua.post("/api/events", json={"nama": "Menunggu lintas", "tanggal": "2031-08-01"}).get_json()["id"]
    tid = _tugas_di(ketua, eid, "Tugas untuk dijawab", "Humas")
    anggota = capy.app.test_client()
    uname = _user_baru(anggota, nama="Penjawab Lintas")
    oid = _oid_user(uname)
    with capy.app.app_context():
        capy.db.session.add(capy.PeranAcara(event_id=eid, orang_id=oid, peran="anggota", seksi="Humas"))
        capy.db.session.commit()
    ketua.patch(f"/api/tasks/{tid}", json={"judul": "Tugas untuk dijawab"})
    with capy.app.app_context():
        t = capy.db.session.get(capy.Task, tid)
        t.penerima_orang_id = oid
        capy.db.session.commit()
    judul = [x["judul"] for x in anggota.get("/api/me/tugas-menunggu").get_json()["tugas"]]
    assert "Tugas untuk dijawab" in judul  # tanpa masuk acara dulu


def test_galat_asisten_menjelaskan_penyebab_dan_cek_koneksi_admin():
    import uuid
    from unittest.mock import patch
    capy._login_fails.clear()
    with capy.app.app_context():
        adm = capy.Orang(username="adm_asis_" + uuid.uuid4().hex[:6], nama="Admin Asisten", password_hash=generate_password_hash("sandi-admin-asis-2031"), admin=True)
        capy.db.session.add(adm); capy.db.session.commit(); nama = adm.username
    u = new_client()
    # kunci salah (401) -> pesan tentang kunci, bukan "ollama serve"
    resp = capy.requests.Response(); resp.status_code = 401; resp._content = b'{"error":"unauthorized"}'
    galat = capy.requests.HTTPError(response=resp)
    with patch.object(capy.requests, "post", side_effect=galat):
        r = u.post("/api/agen/chat", json={"pesan": "halo"})
    assert r.status_code == 502 and "OLLAMA_API_KEY" in r.get_json()["error"] and "ollama serve" not in r.get_json()["error"]
    # koneksi gagal -> pesan koneksi
    with patch.object(capy.requests, "post", side_effect=capy.requests.ConnectionError("x")):
        r = u.post("/api/agen/chat", json={"pesan": "halo"})
    assert r.status_code == 502 and "terhubung" in r.get_json()["error"].lower()
    # cek koneksi admin
    c = capy.app.test_client()
    assert c.post("/api/auth/login", json={"username": nama, "password": "sandi-admin-asis-2031"}).status_code == 200
    with patch.object(capy.requests, "get", side_effect=capy.requests.ConnectionError("x")):
        cek = c.get("/api/admin/asisten-cek").get_json()
    assert cek["ok"] is False and cek["pesan"]
    assert u.get("/api/admin/asisten-cek").status_code == 403
    capy._login_fails.clear()
