#!/usr/bin/env python3
"""Tes end-to-end: menyalakan backend dan frontend sendiri (database sementara), lalu menguji alur utama di browser.

Jalankan dari folder utama proyek:
    pip install playwright requests && python -m playwright install chromium
    python e2e/alur_utama.py
Opsi: CHROME_PATH=/path/ke/chrome untuk memakai browser yang sudah ada.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
import requests
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BE, FE = os.path.join(ROOT, "agent-backend"), os.path.join(ROOT, "agent-frontend")
API, WEB = "http://localhost:5000", "http://localhost:3000"
PW = "sandi-e2e-2026"
ADMIN = ("admin_e2e", "sandi-admin-e2e")
T = str(int(time.time()))[-6:]
hasil = []

def cek(nama, ok, catatan=""):
    hasil.append((bool(ok), nama))
    print(("LULUS " if ok else "GAGAL ") + nama + (f" | {catatan}" if catatan else ""), flush=True)

def tunggu(url, detik=120):
    for _ in range(detik):
        try:
            if requests.get(url, timeout=2).status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False

def nyalakan():
    db = os.path.join(tempfile.mkdtemp(prefix="e2e_"), "capy.db")
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{db}", ADMIN_AWAL_USERNAME=ADMIN[0],
               ADMIN_AWAL_PASSWORD=ADMIN[1], SECRET_KEY="e2e-kunci-uji-0123456789", CORS_ORIGINS=WEB)
    be = subprocess.Popen([sys.executable, "app.py"], cwd=BE, env=env, stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
    fe = subprocess.Popen(["node", "node_modules/next/dist/bin/next", "dev", "-p", "3000"], cwd=FE,
                          env=dict(os.environ, FLASK_BACKEND_URL=API, NEXT_TELEMETRY_DISABLED="1"),
                          stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
    if not tunggu(API + "/health") or not tunggu(WEB + "/beranda"):
        raise SystemExit("Server tidak bisa dinyalakan. Cek Python, Node, dan node_modules.")
    return be, fe, db

def matikan(*proses):
    for p in proses:
        p.terminate()
    for p in proses:
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill()

def masuk(pg, user, pw=PW):
    pg.goto(WEB + "/login", wait_until="networkidle", timeout=120000)
    pg.get_by_label("Username").fill(user); pg.get_by_label("Password").fill(pw)
    pg.get_by_role("button", name="Masuk").click()
    try:
        pg.wait_for_url("**/dashboard", timeout=20000); return True
    except Exception:
        return False

def main():
    be, fe, db = nyalakan()
    try:
        errs = []
        with sync_playwright() as p:
            kw = {"executable_path": os.environ["CHROME_PATH"]} if os.environ.get("CHROME_PATH") else {}
            br = p.chromium.launch(args=["--no-sandbox"], **kw)
            ketua_u, ang_u = f"ketua{T}", f"anggota{T}"
            EV = f"Festival E2E {T}"

            # 1. Daftar ketua: kode pemulihan tampil
            k = br.new_page(viewport={"width": 1280, "height": 900}); k.on("pageerror", lambda e: errs.append(str(e)[:120]))
            k.goto(WEB + "/daftar", wait_until="networkidle", timeout=120000)
            k.get_by_label("Nama lengkap").fill("Ketua E2E"); k.get_by_label("Username").fill(ketua_u)
            k.get_by_label("Password (minimal 8 karakter)").fill(PW); k.get_by_label("Ulangi password").fill(PW)
            k.get_by_role("button", name="Daftar").click(); time.sleep(2.5)
            kode = k.locator("p.font-mono").first.inner_text().strip() if k.locator("p.font-mono").count() else ""
            cek("Daftar menampilkan kode pemulihan", re.match(r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", kode) is not None)

            # 2. Masuk -> dashboard; buat acara -> langsung masuk ke halaman acara
            cek("Masuk pindah ke dashboard", masuk(k, ketua_u))
            k.get_by_label("Nama acara", exact=True).fill(EV); k.get_by_label("Tanggal", exact=True).fill("2031-05-05")
            k.get_by_label("Password pendaftaran (minimal 8 karakter, untuk anggota)").fill("pw-e2e-2026")
            k.get_by_role("button", name="Buat acara").click()
            try:
                k.wait_for_url("**/events/**", timeout=15000); ok = True
            except Exception:
                ok = False
            cek("Buat acara masuk ke halaman acara", ok, k.url)
            acara_id = k.url.rstrip("/").split("/events/")[-1].split("?")[0] if ok else ""

            # 3. Anggota di HP: daftar, gabung dengan password, lalu lebar layar tidak melebihi HP
            a = br.new_page(viewport={"width": 390, "height": 844}, is_mobile=True); a.on("pageerror", lambda e: errs.append(str(e)[:120]))
            a.goto(WEB + "/daftar", wait_until="networkidle", timeout=120000)
            a.get_by_label("Nama lengkap").fill("Anggota E2E"); a.get_by_label("Username").fill(ang_u)
            a.get_by_label("Password (minimal 8 karakter)").fill(PW); a.get_by_label("Ulangi password").fill(PW)
            a.get_by_role("button", name="Daftar").click(); time.sleep(2.5)
            masuk(a, ang_u)
            sel = a.locator("select").filter(has=a.locator("option", has_text="Pilih acara")).first
            a.wait_for_function("""(teks) => [...document.querySelectorAll('select option')].some(o => o.textContent.includes(teks))""", arg=EV, timeout=20000)
            sel.select_option(label=[o.text_content() for o in sel.locator("option").all() if EV in (o.text_content() or "")][0])
            a.get_by_label("Password pendaftaran acara").fill("pw-e2e-2026")
            a.get_by_role("button", name="Gabung", exact=True).click(); time.sleep(2.5)
            cek("Anggota gabung dengan password", a.get_by_text("Kamu sudah bergabung").count() > 0)
            lebar = a.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
            cek("Halaman dashboard anggota tidak melebar dari layar HP", lebar[1] <= lebar[0], f"layar {lebar[0]}, isi {lebar[1]}")

            # 4. Ketua menambah tugas di ruang kerja, membagikannya; anggota menerimanya
            k.goto(WEB + "/kerja", wait_until="networkidle", timeout=120000); time.sleep(1.5)
            k.get_by_label("Tugas baru", exact=True).fill(f"Cetak poster {T}")
            k.get_by_label("Acara", exact=True).select_option(label=EV)
            k.get_by_role("button", name="Tambah", exact=True).click(); time.sleep(2)
            cek("Ketua menambah tugas di ruang kerja", k.get_by_text(f"Cetak poster {T}").count() > 0)
            k.goto(WEB + f"/events/{acara_id}", wait_until="networkidle", timeout=120000); time.sleep(1.5)
            # "Perlu ditindaklanjuti" sudah terbuka sejak awal; jangan diklik lagi karena akan menutupnya.
            pilih = k.locator("select").filter(has=k.locator("option", has_text="Pilih peserta")).first
            pilih.locator("option", has_text="Anggota E2E").first.wait_for(state="attached", timeout=20000)
            pilih.select_option(label=[o.text_content() for o in pilih.locator("option").all() if "Anggota E2E" in (o.text_content() or "")][0])
            k.get_by_role("button", name="Bagikan", exact=True).first.click(); time.sleep(2)
            a.goto(WEB + "/dashboard", wait_until="networkidle", timeout=120000); time.sleep(1.5)
            ada_tombol = a.get_by_role("button", name="Saya terima").count() > 0
            cek("Tugas yang dibagikan muncul di dashboard anggota", ada_tombol)
            if ada_tombol:
                a.get_by_role("button", name="Saya terima").first.click(); time.sleep(2)
                cek("Anggota menerima tugas yang dibagikan", a.get_by_role("button", name="Saya terima").count() == 0)

            # 5. Kabar publik muncul di beranda
            k.get_by_text("Kabar untuk anggota").first.click(); time.sleep(0.8)
            k.get_by_label("Tulis kabar untuk anggota").fill(f"Kabar E2E {T}")
            k.get_by_label("Tampilkan di beranda").check()
            k.get_by_role("button", name="Kirim kabar").click(); time.sleep(2.5)
            cek("Ketua mengirim kabar", k.get_by_text(f"Kabar E2E {T}").count() > 0)
            beranda = br.new_page(viewport={"width": 1280, "height": 900})
            beranda.goto(WEB + "/beranda", wait_until="networkidle", timeout=120000); time.sleep(1.5)
            cek("Kabar publik tampil di beranda", beranda.get_by_text(f"Kabar E2E {T}").count() > 0)

            # 6. Lupa password dengan kode pemulihan
            lp = br.new_page(viewport={"width": 1280, "height": 900})
            lp.goto(WEB + "/lupa-password", wait_until="networkidle", timeout=120000)
            lp.get_by_label("Username").fill(ketua_u); lp.get_by_label("Kode pemulihan").fill(kode)
            lp.get_by_label("Password baru (minimal 8)").fill("sandi-baru-e2e")
            lp.get_by_role("button", name="Atur password baru").click(); time.sleep(2.5)
            cek("Lupa password dengan kode mengatur ulang sandi", lp.locator("p.font-mono").count() > 0)

            # 7. Admin: tombol atur ulang password di halaman admin
            ad = br.new_page(viewport={"width": 1280, "height": 900})
            masuk(ad, ADMIN[0], ADMIN[1])
            ad.goto(WEB + "/admin", wait_until="networkidle", timeout=120000); time.sleep(1.5)
            ad.get_by_role("button", name="Pengguna").click(); time.sleep(1)
            ad.get_by_placeholder("Cari username atau nama").fill(ang_u); ad.get_by_role("button", name="Cari").click(); time.sleep(1.5)
            ad.get_by_role("button", name="Atur ulang password").first.click(); time.sleep(0.5)
            ad.get_by_placeholder("Password baru (minimal 8)").fill("sandi-admin-reset")
            ad.get_by_role("button", name="Simpan").click(); time.sleep(2)
            cek("Admin mengatur ulang password lewat tombol", ad.get_by_role("status").count() > 0)
            cek("Password baru hasil reset bisa dipakai masuk",
                requests.post(API + "/api/auth/login", json={"username": ang_u, "password": "sandi-admin-reset"}).status_code == 200)

            cek("Tidak ada error halaman selama alur", not errs, "; ".join(errs[:3]))
            br.close()
    finally:
        matikan(fe, be)
        shutil.rmtree(os.path.dirname(db), ignore_errors=True)
    lulus = sum(1 for ok, _ in hasil if ok)
    print(f"\nRINGKAS: {lulus} lulus, {len(hasil) - lulus} gagal")
    return 0 if lulus == len(hasil) else 1

if __name__ == "__main__":
    sys.exit(main())
