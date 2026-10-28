"""Aturan peran per acara (Tahap 1a).

Modul ini murni logika: tidak mengimpor Flask atau database. Penugasan peran belum dipakai untuk login
atau pengecekan izin di endpoint lama; itu Tahap 1b.

Sumber aturan: rangkuman-capy-organizer.md bagian 3.1 dan 3.2.
"""

PERAN = ("ketua", "wakil_ketua", "koordinator", "anggota", "pj")
PERAN_DEFAULT = "anggota"
SEKSI = (
    "Acara", "PDD", "Perkab", "Konsumsi", "Humas",
    "Keamanan", "Sponsorship", "Bendahara", "Sekretaris", "Sekretariatan",
)
PERAN_BERSEKSI = {"koordinator"}          # koordinator wajib punya seksi
MAKS_PER_ACARA = {"ketua": 1, "wakil_ketua": 1}

# Apa yang boleh dilakukan tiap peran. Wakil Ketua default hanya memantau dan memberi perintah.
IZIN = {
    "ketua": {"lihat", "kelola_acara", "kelola_peran", "tutup_acara", "beri_perintah", "kelola_tugas_semua", "setujui"},
    "wakil_ketua": {"lihat", "beri_perintah"},
    "koordinator": {"lihat", "kelola_tugas_seksi", "beri_perintah_seksi"},
    "anggota": {"lihat", "kerjakan_tugas"},
    "pj": {"lihat", "kerjakan_tugas"},
}


def boleh(peran, aksi):
    """True jika peran ini punya izin untuk aksi tersebut."""
    return aksi in IZIN.get(peran, set())


def validasi_penugasan(peran, seksi, orang_id, penugasan_ada, orang_admin=False):
    """Kembalikan pesan galat, atau None jika penugasan boleh dibuat.

    penugasan_ada: daftar (orang_id, peran, seksi) yang sudah ada di acara ini.
    orang_admin: admin tidak boleh menjadi peserta acara (keputusan 2, asumsi awal).
    """
    if peran not in PERAN:
        return "Peran tidak dikenal."
    if orang_admin:
        return "Admin tidak bisa menjadi peserta acara."
    if peran in PERAN_BERSEKSI:
        if seksi not in SEKSI:
            return "Koordinator harus punya seksi yang valid."
    elif seksi is not None and seksi not in SEKSI:
        return "Seksi tidak dikenal."

    if any(oid == orang_id for oid, _, _ in penugasan_ada):
        return "Orang ini sudah punya peran di acara ini. Ubah peran lama dulu."

    batas = MAKS_PER_ACARA.get(peran)
    if batas is not None and sum(1 for _, p, _ in penugasan_ada if p == peran) >= batas:
        return f"Acara ini sudah punya {peran.replace('_', ' ')}."

    if peran == "koordinator":
        if any(p == "koordinator" and s == seksi for _, p, s in penugasan_ada):
            return f"Seksi {seksi} sudah punya koordinator."
    return None
