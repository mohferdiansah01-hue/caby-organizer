#!/usr/bin/env python3
"""Membuat salinan cadangan database SQLite dengan waktu di namanya.

Jalankan dari folder agent-backend:  python cadangan_db.py
Hasil: folder backups/capy_<waktu>.db (atau CADANGAN_DIR jika diatur). Simpan salinannya di tempat lain secara berkala.
Jika DATABASE_URL bukan SQLite, skrip ini tidak membuat cadangan; gunakan alat bawaan database itu.
"""
import os
import shutil
import sys
from datetime import datetime

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))
url = os.environ.get("DATABASE_URL", "sqlite:///capy.db")
if not url.startswith("sqlite:///"):
    sys.exit("DATABASE_URL bukan SQLite. Gunakan alat cadangan bawaan database tersebut.")
lokasi = url[len("sqlite:///"):]
if not os.path.isabs(lokasi):
    lokasi = os.path.join(HERE, lokasi)
if not os.path.exists(lokasi):
    sys.exit(f"File database belum ada: {lokasi}")
folder = os.environ.get("CADANGAN_DIR") or os.path.join(HERE, "backups")  # di Docker: volume data
os.makedirs(folder, exist_ok=True)
tujuan = os.path.join(folder, f"capy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
shutil.copy2(lokasi, tujuan)
print(f"Cadangan dibuat: {tujuan}")
