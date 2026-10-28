#!/usr/bin/env python3
"""Membuat atau menjadikan admin satu akun. Jalankan sekali saat pertama memasang aplikasi.

Contoh:
  python buat_admin.py panitia_utama              # akun sudah ada: jadikan admin
  python buat_admin.py panitia_utama --nama "Ketua Umum" --baru   # buat akun baru (minta password)
"""
import argparse
import getpass
import sys

from app import app, db, Orang
from werkzeug.security import generate_password_hash


def main():
    ap = argparse.ArgumentParser(description="Jadikan akun admin.")
    ap.add_argument("username")
    ap.add_argument("--nama", default="")
    ap.add_argument("--baru", action="store_true", help="buat akun baru dengan password")
    ap.add_argument("--cabut", action="store_true", help="cabut status admin")
    args = ap.parse_args()
    with app.app_context():
        o = Orang.query.filter(db.func.lower(Orang.username) == args.username.strip().lower()).first()
        if args.cabut:
            if not o:
                sys.exit("Akun tidak ditemukan.")
            o.admin = False
            db.session.commit()
            print(f"Status admin dicabut dari {o.username}.")
            return
        if o is None:
            if not args.baru:
                sys.exit("Akun belum ada. Tambahkan --baru untuk membuatnya.")
            pw = getpass.getpass("Password (minimal 8 karakter): ")
            if len(pw) < 8:
                sys.exit("Password terlalu pendek.")
            o = Orang(username=args.username.strip(), nama=args.nama or args.username, password_hash=generate_password_hash(pw), admin=True)
            db.session.add(o)
        else:
            o.admin = True
        db.session.commit()
        print(f"{o.username} sekarang admin.")


if __name__ == "__main__":
    main()
