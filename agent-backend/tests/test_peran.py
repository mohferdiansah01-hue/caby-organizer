"""Pengujian aturan peran per acara (Tahap 1a). Murni logika, tanpa Flask."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import peran as p  # noqa: E402


def test_wakil_ketua_hanya_memantau_dan_memberi_perintah():
    assert p.boleh("wakil_ketua", "lihat")
    assert p.boleh("wakil_ketua", "beri_perintah")
    for aksi in ("kelola_acara", "kelola_peran", "tutup_acara", "setujui", "kelola_tugas_semua"):
        assert not p.boleh("wakil_ketua", aksi), aksi


def test_ketua_punya_semua_izin_dan_anggota_tidak_bisa_kelola():
    for aksi in ("kelola_acara", "kelola_peran", "tutup_acara", "setujui"):
        assert p.boleh("ketua", aksi)
    assert p.boleh("anggota", "kerjakan_tugas") and not p.boleh("anggota", "kelola_peran")
    assert not p.boleh("tidak_ada", "lihat")


def test_peran_tidak_dikenal_dan_admin_ditolak():
    assert p.validasi_penugasan("bos", None, "o1", []) == "Peran tidak dikenal."
    assert p.validasi_penugasan("anggota", None, "o1", [], orang_admin=True) == "Admin tidak bisa menjadi peserta acara."


def test_koordinator_wajib_seksi_yang_valid_dan_satu_per_seksi():
    assert "seksi yang valid" in p.validasi_penugasan("koordinator", None, "o1", [])
    assert "seksi yang valid" in p.validasi_penugasan("koordinator", "Hantu", "o1", [])
    ada = [("o2", "koordinator", "Konsumsi")]
    assert "sudah punya koordinator" in p.validasi_penugasan("koordinator", "Konsumsi", "o1", ada)
    assert p.validasi_penugasan("koordinator", "Humas", "o1", ada) is None


def test_satu_ketua_dan_satu_wakil_per_acara():
    assert "sudah punya ketua" in p.validasi_penugasan("ketua", None, "o1", [("o2", "ketua", None)])
    assert "sudah punya wakil ketua" in p.validasi_penugasan("wakil_ketua", None, "o1", [("o2", "wakil_ketua", None)])
    assert p.validasi_penugasan("wakil_ketua", None, "o1", [("o2", "ketua", None)]) is None


def test_orang_yang_sama_tidak_boleh_dua_kali_di_acara_yang_sama():
    ada = [("o1", "anggota", None)]
    assert "sudah punya peran" in p.validasi_penugasan("pj", None, "o1", ada)


def test_anggota_dan_pj_boleh_tanpa_seksi_atau_dengan_seksi_valid():
    assert p.validasi_penugasan("anggota", None, "o1", []) is None
    assert p.validasi_penugasan("pj", "Humas", "o1", []) is None
    assert p.validasi_penugasan("anggota", "Hantu", "o1", []) == "Seksi tidak dikenal."
