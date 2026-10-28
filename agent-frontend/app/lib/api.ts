export type Task = {
  id: string;
  penerima_orang_id?: string | null;
  konfirmasi?: "diterima" | "ditolak" | null;
  konfirmasi_alasan?: string | null;
  judul: string;
  deskripsi: string;
  deadline_iso: string | null;
  prioritas: string;
  status: string;
  kategori: string;
  sisa_jam: number | null;
  reminder_sent: boolean;
  created_at: string | null;
  completed_at: string | null;
  divisi: string;
  pic: string;
  progress: number;
  hasil_url: string | null;
  hasil_catatan: string | null;
  hasil_dikirim_pada: string | null;
  anggota_id?: string | null;
};

export type TaskStats = {
  total: number;
  done: number;
  pending: number;
  overdue: number;
  hari_ini: number;
  progress_persen: number;
};

export type DivisiStat = {
  divisi: string;
  total: number;
  done: number;
  overdue: number;
  hasil: number;
  avg_progress: number;
  pics: string[];
};

export type TeamStats = {
  divisi: DivisiStat[];
  total_tugas: number;
  total_hasil: number;
  total_pic: number;
};

const BASE = "/api";

// Membaca respons server dengan aman. Jika server mengembalikan teks biasa (misalnya "Internal Server Error"),
// pengguna mendapat pesan yang bisa dipahami, bukan error parsing.
export async function readJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    throw new Error((data as { error?: string } | null)?.error || `Server sedang bermasalah (kode ${res.status}). Coba lagi sebentar.`);
  }
  if (data === null) {
    throw new Error("Respons server tidak dikenali. Pastikan backend sudah berjalan.");
  }
  return data as T;
}


export async function fetchTasks(kategori = "semua"): Promise<Task[]> {
  const res = await fetch(`${BASE}/tasks?kategori=${kategori}`);
  const data = await readJson<{ tasks: Task[] }>(res);
  return data.tasks || [];
}

export async function fetchStats(): Promise<TaskStats> {
  const res = await fetch(`${BASE}/tasks/stats`);
  return readJson<TaskStats>(res);
}

export async function fetchTeamStats(): Promise<TeamStats> {
  const res = await fetch(`${BASE}/team/stats`);
  return readJson(res);
}

export async function createTask(payload: {
  event_id: string;
  judul: string;
  deskripsi?: string;
  deadline_iso?: string | null;
  prioritas?: string;
  divisi?: string;
  pic?: string;
}): Promise<Task> {
  const res = await fetch(`${BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson(res);
}

export async function updateTask(id: string, patch: Partial<Task>): Promise<Task> {
  const res = await fetch(`${BASE}/tasks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  return readJson(res);
}

export async function deleteTask(id: string): Promise<void> {
  await fetch(`${BASE}/tasks/${id}`, { method: "DELETE" });
}

// ============================================================
// ACARA (EVENT)
// ============================================================

export type EventItem = {
  id: string;
  nama: string;
  tanggal: string | null;
  lokasi: string;
  deskripsi: string;
  created_at: string | null;
  total_tugas?: number;
  tugas_selesai?: number;
};

export type SeksiStatus = "selesai" | "terlambat" | "perhatian" | "berjalan";

export type SeksiStat = {
  seksi: string;
  total: number;
  done: number;
  overdue: number;
  hari_ini: number;
  avg_progress: number;
  pics: string[];
  sisa_terdekat_jam: number | null;
  status: SeksiStatus;
};

export type CapyMood = "idle" | "peek" | "excited";

export type EventDetail = {
  event: EventItem;
  ringkasan: {
    total: number;
    done: number;
    overdue: number;
    hari_ini: number;
    progress_persen: number;
  };
  seksi: SeksiStat[];
  tasks: Task[];
  capy_mood: CapyMood;
  dampak: Dampak;
  struktur: { seksi: string; pic: string }[];
};

export type ScheduleItem = {
  judul: string;
  divisi: string;
  pic: string;
  deadline_iso: string | null;
  prioritas: string;
  deskripsi: string;
};

export type BriefingItem = {
  judul: string;
  seksi: string;
  pic: string;
  deadline_iso: string | null;
};

export type Briefing = {
  kalimat: string;
  overdue: BriefingItem[];
  hari_ini: BriefingItem[];
  minggu_ini: BriefingItem[];
};

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Permintaan gagal (${res.status})`);
  }
  return data as T;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function fetchEvents(): Promise<EventItem[]> {
  const data = await jsonFetch<{ events: EventItem[] }>(`${BASE}/events`);
  return data.events || [];
}

export async function createEvent(payload: {
  nama: string;
  tanggal?: string | null;
  lokasi?: string;
  deskripsi?: string;
}): Promise<EventItem> {
  return jsonFetch<EventItem>(`${BASE}/events`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
}

export async function fetchEvent(id: string): Promise<EventDetail> {
  return jsonFetch<EventDetail>(`${BASE}/events/${id}`);
}

// ============================================================
// AUTENTIKASI
// ============================================================

export type Me = { role: string; ketua: boolean; event_id: string | null; peran?: string | null; nama?: string | null; orang_id?: string | null; admin?: boolean };
export type AuthEvent = { id: string; nama: string; tanggal: string | null };

export async function fetchAuthEvents(): Promise<AuthEvent[]> {
  const data = await jsonFetch<{ events: AuthEvent[] }>(`${BASE}/auth/events`);
  return data.events || [];
}

export async function getMe(): Promise<Me | null> {
  const res = await fetch(`${BASE}/auth/me`);
  if (!res.ok) return null;
  const data = await readJson<Me & { masuk?: boolean }>(res);
  return data.masuk === false ? null : data;
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, { method: "POST" });
}

export async function checkSession(): Promise<boolean> {
  const res = await fetch(`${BASE}/auth/me`);
  if (!res.ok) return false;
  const data = await res.json().catch(() => null);
  return !!data && data.masuk !== false;
}

// ============================================================
// DAMPAK BERKELANJUTAN (SDG)
// ============================================================

export type DampakItem = {
  key: string;
  label: string;
  sdg: string;
  aktif: boolean;
};

export type Dampak = {
  items: DampakItem[];
  aktif: number;
  total: number;
  skor_persen: number;
};

// ============================================================
// STRUKTUR KEPANITIAAN & PERENCANAAN TUGAS
// ============================================================

export type Seksi = { seksi: string; pic: string };

export type Rencana = {
  items: ScheduleItem[];
  jumlah: number;
  jenis: string;
  jumlah_peserta: number | null;
  rekomendasi: string[];
  sumber: "template" | "template+ai";
  peringatan: string;
};

export async function rencanakan(id: string, teks: string): Promise<Rencana> {
  return jsonFetch<Rencana>(`${BASE}/events/${id}/rencanakan`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ teks }),
  });
}

// ============================================================
// BERANDA, KABAR KERJA, RUANG KERJA
// ============================================================

export type BerandaPengaturan = { hero: string; judul: string; subjudul: string; tombol: string };
export type BerandaStatistik = { acara: number; tugas: number; tugas_selesai: number; seksi: number; persen_selesai: number };
export type LampiranRef = { id: string; nama: string; mime: string; url: string; jenis: string };
export type KabarPublik = { id: string; seksi: string; isi: string; acara: string; waktu: string | null; lampiran?: LampiranRef[] };
export type Beranda = { pengaturan: BerandaPengaturan; statistik: BerandaStatistik; kabar: KabarPublik[] };

export async function fetchBeranda(): Promise<Beranda> {
  const res = await fetch(`${BASE}/beranda`);
  return readJson<Beranda>(res);
}

export type KabarItem = {
  id: string;
  event_id: string | null;
  seksi: string;
  isi: string;
  publik: boolean;
  waktu: string | null;
  bisa_hapus: boolean;
  lampiran?: LampiranRef[];
};

export type KerjaAcara = {
  event: EventItem;
  total: number;
  selesai: number;
  tugas: Task[];
  peran?: string;
};
export type KerjaData = { role: string; ketua: boolean; acara: KerjaAcara[] };

export async function fetchKerja(): Promise<KerjaData> {
  const res = await fetch(`${BASE}/kerja`);
  return readJson<KerjaData>(res);
}

// ============================================================
// AGEN CAPY: kalimat mentah diubah jadi rencana aksi
// ============================================================

export type AgenAksi = { jenis: string; label: string; data: Record<string, unknown> };
export type AgenHasil = { jenis: string; ok: boolean; pesan: string };
export type AgenJawaban = {
  ringkasan: string;
  aksi: AgenAksi[];
  selesai: boolean;
  hasil: AgenHasil[];
  sumber: string;
  persetujuan?: string;
};

export type AgenMode = "rencana" | "eksekusi";

export type AgenIzin = { hapus: boolean; ubah: boolean };

export async function askAgen(
  teks: string,
  eventId?: string | null,
  mode: AgenMode = "rencana",
  izin: AgenIzin = { hapus: true, ubah: true },
  lampiranIds: string[] = [],
): Promise<AgenJawaban> {
  const res = await fetch(`${BASE}/agen`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ teks, event_id: eventId || "", mode, izin, lampiran_ids: lampiranIds }),
  });
  return readJson<AgenJawaban>(res);
}

export async function jalankanAgen(
  aksi: AgenAksi[],
  eventId?: string | null,
  izin: AgenIzin = { hapus: true, ubah: true },
  persetujuan?: string,
): Promise<{ hasil: AgenHasil[]; event_id: string | null }> {
  const res = await fetch(`${BASE}/agen/jalankan`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ aksi, event_id: eventId || "", izin, persetujuan }),
  });
  return readJson(res);
}

// Unggah satu berkas (foto, video, atau dokumen). Mengembalikan id untuk dilampirkan ke tugas atau kabar.
// ============================================================
// ALAT PER SEKSI
// ============================================================

export type AlatInfo = { id: string; judul: string; bisa: boolean };
export type Dokumen = {
  judul: string;
  bagian: { judul: string; paragraf: string[]; daftar: string[]; tabel: { header: string[]; baris: string[][] } | null }[];
};
export type Transaksi = { id: string; tanggal: string | null; uraian: string; kategori: string; tipe: "masuk" | "keluar"; nominal: number; status?: "menunggu" | "disetujui" | "ditolak"; catatan_keputusan?: string | null; };

// ============================================================
// PESAN DAN PERINGATAN
// ============================================================

export type TingkatPesan = "info" | "pengingat" | "peringatan";
export type PesanItem = {
  id: string;
  dari: string;
  tingkat: TingkatPesan;
  isi: string;
  ke: string;
  ke_seksi: string | null;
  ke_anggota_id: string | null;
  waktu: string | null;
  dibaca: boolean;
  bisa_diubah?: boolean;
};

export async function fetchPesan(eventId: string): Promise<{ pesan: PesanItem[]; belum_dibaca: number }> {
  const res = await fetch(`${BASE}/pesan?event_id=${encodeURIComponent(eventId)}`);
  return readJson(res);
}

export async function kirimPesan(body: { event_id: string; isi: string; tingkat: TingkatPesan; ke: string }): Promise<void> {
  const res = await fetch(`${BASE}/pesan`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
  await readJson(res);
}

export async function tandaiBaca(id: string): Promise<void> {
  const res = await fetch(`${BASE}/pesan/${id}/baca`, { method: "POST" });
  await readJson(res);
}

export async function peringatanOtomatis(eventId: string): Promise<{ dikirim_ke: string[]; jumlah: number }> {
  const res = await fetch(`${BASE}/pesan/otomatis`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ event_id: eventId }) });
  return readJson(res);
}

// ============================================================
// PERINTAH DAN KOMENTAR DI TUGAS
// ============================================================

export type Komentar = { id: string; dari: string; jenis: "perintah" | "komentar"; isi: string; waktu: string | null };

export async function fetchKomentar(taskId: string): Promise<Komentar[]> {
  const res = await fetch(`${BASE}/tasks/${taskId}/komentar`);
  const data = await readJson<{ komentar: Komentar[] }>(res);
  return data.komentar;
}

export async function tulisKomentar(taskId: string, isi: string, jenis: "perintah" | "komentar"): Promise<void> {
  const res = await fetch(`${BASE}/tasks/${taskId}/komentar`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ isi, jenis }) });
  await readJson(res);
}

// ============================================================
// LOG AKTIVITAS
// ============================================================

export type AuditItem = {
  id: number;
  waktu: string | null;
  aktor: string;
  peran: string;
  aksi: string;
  rute: string;
  target: string | null;
  status: number;
  ip: string | null;
  metadata: unknown;
  perubahan?: Record<string, { sebelum: unknown; sesudah: unknown }> | null;
};

// ============================================================
// PEMBAGIAN TUGAS DAN HASIL KERJA ANGGOTA
// ============================================================

// ============================================================
// PERSETUJUAN PENGELUARAN
// ============================================================

export type StatusKeuangan = "menunggu" | "disetujui" | "ditolak";
export type PengeluaranMenunggu = {
  id: string;
  tanggal: string | null;
  uraian: string;
  kategori: string;
  tipe: "masuk" | "keluar";
  nominal: number;
  status: StatusKeuangan;
  acara: string;
  event_id: string;
  catatan_keputusan?: string | null;
};

// Pembaca JSON generik untuk endpoint GET sederhana di bawah /api.
// ============================================================
// UBAH DAN TARIK PESAN
// ============================================================

export async function ubahPesan(id: string, isi: string): Promise<void> {
  const res = await fetch(`${BASE}/pesan/${id}`, { method: "PATCH", headers: JSON_HEADERS, body: JSON.stringify({ isi }) });
  await readJson(res);
}

export async function tarikPesan(id: string): Promise<void> {
  const res = await fetch(`${BASE}/pesan/${id}`, { method: "DELETE" });
  await readJson(res);
}

// ============================================================
// PASSWORD SEKSI (Ketua mengatur langsung, tanpa token)
// ============================================================

export async function daftarAkun(body: { username: string; nama: string; password: string }): Promise<{ username: string; pesan: string; kode_pemulihan: string }> {
  return jsonFetch(`${BASE}/auth/daftar`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

export type AcaraSaya = { id: string; nama: string; tanggal: string | null; peran: string; seksi: string | null; tertutup: boolean };
export async function fetchAcaraSaya(): Promise<AcaraSaya[]> {
  const data = await jsonFetch<{ acara: AcaraSaya[] }>(`${BASE}/me/acara`);
  return data.acara || [];
}

export async function buatAcara(body: { nama: string; tanggal: string; password: string; template?: string }): Promise<{ id: string }> {
  return jsonFetch(`${BASE}/events`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

export async function masukAcara(eventId: string): Promise<{ peran: string; ketua: boolean }> {
  return jsonFetch(`${BASE}/me/acara/${encodeURIComponent(eventId)}/masuk`, { method: "POST" });
}

export async function keluarAcara(): Promise<void> {
  await jsonFetch(`${BASE}/me/keluar-acara`, { method: "POST" });
}

export async function aturPasswordAcara(eventId: string, password: string): Promise<void> {
  await jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/password`, { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ password }) });
}

export type PesertaAcara = { id: string; orang_id: string; nama: string; peran: string; seksi: string | null };
export async function fetchPesertaAcara(eventId: string): Promise<PesertaAcara[]> {
  const data = await jsonFetch<{ peran: PesertaAcara[] }>(`${BASE}/events/${encodeURIComponent(eventId)}/peran`);
  return data.peran || [];
}

export async function keluarkanPeserta(eventId: string, peranId: string): Promise<void> {
  await jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/peran/${encodeURIComponent(peranId)}`, { method: "DELETE" });
}

export async function gabungAcara(eventId: string, body: { peran: "anggota" | "pj"; password: string }): Promise<void> {
  await jsonFetch(`${BASE}/me/acara/${encodeURIComponent(eventId)}/gabung`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

// Login akun pribadi: peran diambil dari penugasan di acara yang dipilih.
export async function loginOrang(username: string, password: string, eventId: string): Promise<{ event_id: string | null }> {
  return jsonFetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ username, password, event_id: eventId }),
  });
}

// Tahap 2: kembalikan tugas seksi di acara ke tugas default. Menghapus tugas yang sudah ada.
export async function pakaiDefaultSeksi(eventId: string, seksi: string): Promise<{ dihapus: number; dibuat: number }> {
  return jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/seksi/${encodeURIComponent(seksi)}/pakai-default`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ konfirmasi: true }),
  });
}

// ============================================================
// EVALUASI: masukan panitia
// ============================================================
export type MasukanEvaluasi = {
  id: string; isi: string; kategori: string; status: "draf" | "final"; milik_saya: boolean;
  penulis: string; tampil_nama: boolean; jumlah_dukungan: number; sudah_didukung: boolean;
  status_tindak: "diajukan" | "ditanggapi" | "ditindaklanjuti"; tanggapan: string; final_pada: string | null;
  penulis_asli?: string; disembunyikan?: boolean; jumlah_laporan?: number;
};


// ============================================================
// KONFIRMASI TUGAS & TINDAK LANJUT KETUA
// ============================================================
export async function konfirmasiTugas(taskId: string, aksi: "terima" | "tolak", alasan = ""): Promise<Task> {
  return jsonFetch(`${BASE}/tasks/${encodeURIComponent(taskId)}/konfirmasi`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ aksi, alasan }) });
}

export async function bagikanTugas(taskId: string, orangId: string | null): Promise<Task> {
  return jsonFetch(`${BASE}/tasks/${encodeURIComponent(taskId)}/tugaskan`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ orang_id: orangId }) });
}

export type ItemTindakLanjut = { id: string; judul: string; seksi: string | null; deadline_iso: string | null; penerima: string | null; alasan: string | null };
export type TindakLanjut = { belum_dibagi: ItemTindakLanjut[]; belum_konfirmasi: ItemTindakLanjut[]; ditolak: ItemTindakLanjut[]; terlambat: ItemTindakLanjut[] };
export async function fetchTindakLanjut(eventId: string): Promise<TindakLanjut> {
  return jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/tindak-lanjut`);
}

export type AcaraTanpaKetua = { id: string; nama: string; tanggal: string | null };
export async function fetchAcaraTanpaKetua(): Promise<AcaraTanpaKetua[]> {
  const data = await jsonFetch<{ acara: AcaraTanpaKetua[] }>(`${BASE}/admin/acara-tanpa-ketua`);
  return data.acara || [];
}

export async function klaimAcara(eventId: string): Promise<void> {
  await jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/klaim`, { method: "POST" });
}

export async function fetchPesertaLengkap(eventId: string): Promise<{ peran: PesertaAcara[]; seksi_tersedia: string[] }> {
  const data = await jsonFetch<{ peran: PesertaAcara[]; seksi_tersedia: string[] }>(`${BASE}/events/${encodeURIComponent(eventId)}/peran`);
  return { peran: data.peran || [], seksi_tersedia: data.seksi_tersedia || [] };
}

export async function ubahPeserta(eventId: string, peranId: string, body: { peran: string; seksi: string | null }): Promise<void> {
  await jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/peran/${encodeURIComponent(peranId)}`, { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

// ============================================================
// CATATAN KEPUTUSAN (langsung tercatat, tanpa persetujuan)
// ============================================================
export type CatatanKeputusan = { id: string; judul: string; isi: string; penulis: string; created_at: string | null };
export async function fetchKeputusan(eventId: string): Promise<CatatanKeputusan[]> {
  const data = await jsonFetch<{ keputusan: CatatanKeputusan[] }>(`${BASE}/events/${encodeURIComponent(eventId)}/keputusan`);
  return data.keputusan || [];
}

export async function catatKeputusan(eventId: string, body: { judul: string; isi: string }): Promise<void> {
  await jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/keputusan`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

// ============================================================
// CAPY (agen): membaca data, membuka halaman, dan mengusulkan perubahan
// ============================================================
export type AksiCapy =
  | { jenis: "navigasi"; url: string; label: string }
  | { jenis: "usulan"; tipe: string; data: Record<string, unknown>; ringkas: string; berbahaya?: boolean };
export type JawabanCapy = { jawaban: string; aksi: AksiCapy[]; mode: string };
export async function agenChat(pesan: string, eventId?: string): Promise<JawabanCapy> {
  return jsonFetch(`${BASE}/agen/chat`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ pesan, event_id: eventId || null }) });
}
export type PesanTersimpan = { peran: "user" | "capy"; isi: string; aksi: AksiCapy[] };
export async function agenRiwayat(eventId?: string): Promise<PesanTersimpan[]> {
  const q = eventId ? `?event_id=${encodeURIComponent(eventId)}` : "";
  const data = await jsonFetch<{ pesan: PesanTersimpan[] }>(`${BASE}/agen/riwayat${q}`);
  return data.pesan || [];
}
export async function agenHapusRiwayat(eventId?: string): Promise<void> {
  const q = eventId ? `?event_id=${encodeURIComponent(eventId)}` : "";
  await jsonFetch(`${BASE}/agen/riwayat${q}`, { method: "DELETE" });
}
export async function agenJalankan(tipe: string, data: Record<string, unknown>): Promise<{ pesan?: string; id?: string }> {
  return jsonFetch(`${BASE}/agen/jalankan`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ tipe, data }) });
}

// Batalkan dan ulangi perubahan (per acara, per orang)
export type StatusRiwayat = { batal: string | null; ulang: string | null };
export async function riwayatStatus(eventId: string): Promise<StatusRiwayat> {
  return jsonFetch(`${BASE}/riwayat?event_id=${encodeURIComponent(eventId)}`);
}
export async function riwayatBatal(eventId: string): Promise<{ label: string }> {
  return jsonFetch(`${BASE}/riwayat/batal`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ event_id: eventId }) });
}
export async function riwayatUlang(eventId: string): Promise<{ label: string }> {
  return jsonFetch(`${BASE}/riwayat/ulang`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ event_id: eventId }) });
}

// Admin: angkat admin dan atur ulang password akun yang lupa
export async function adminAngkat(username: string, admin: boolean): Promise<{ username: string; admin: boolean }> {
  return jsonFetch(`${BASE}/admin/angkat`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ username, admin }) });
}
export async function adminResetPassword(username: string, password: string): Promise<{ pesan: string }> {
  return jsonFetch(`${BASE}/admin/reset-password`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ username, password }) });
}

export async function serahkanKetua(eventId: string, orangId: string): Promise<void> {
  await jsonFetch(`${BASE}/events/${encodeURIComponent(eventId)}/serahkan-ketua`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ orang_id: orangId }) });
}

// Lupa password dengan kode pemulihan, kode pemulihan saya, dan pengingat tenggat
export async function lupaPassword(username: string, kode: string, passwordBaru: string): Promise<{ pesan: string; kode_pemulihan: string }> {
  return jsonFetch(`${BASE}/auth/lupa-password`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ username, kode, password_baru: passwordBaru }) });
}
export async function buatKodeBaruSaya(): Promise<{ kode_pemulihan: string; pesan: string }> {
  return jsonFetch(`${BASE}/me/kode-pemulihan`, { method: "POST" });
}
export type PengingatItem = { task_id: string; judul: string; acara: string; event_id: string; tenggat: string; lewat: boolean };
export async function pengingatSaya(): Promise<PengingatItem[]> {
  const data = await jsonFetch<{ pengingat: PengingatItem[] }>(`${BASE}/me/pengingat`);
  return data.pengingat || [];
}

// Halaman admin
export type AdminRingkasan = { pengguna: number; admin: number; acara: number; acara_terbuka: number; tugas: number; tugas_selesai: number; tanya_capy_hari_ini: number; kuota_capy_harian: number };
export async function adminRingkasan(): Promise<AdminRingkasan> {
  return jsonFetch(`${BASE}/admin/ringkasan`);
}
export type AdminPengguna = { id: string; username: string; nama: string; admin: boolean; dibuat: string | null; jumlah_acara: number };
export async function adminPengguna(q = ""): Promise<AdminPengguna[]> {
  const data = await jsonFetch<{ pengguna: AdminPengguna[] }>(`${BASE}/admin/pengguna${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  return data.pengguna || [];
}
export type AdminAcara = { id: string; nama: string; tanggal: string | null; lokasi: string | null; pembuat: string | null; tertutup: boolean; peserta: number; tugas: number };
export async function adminAcara(): Promise<AdminAcara[]> {
  const data = await jsonFetch<{ acara: AdminAcara[] }>(`${BASE}/admin/acara`);
  return data.acara || [];
}

export type AdminAudit = { waktu: string | null; aktor: string; peran: string; aksi: string; rute: string; target: string | null };
export async function adminAudit(aktor = ""): Promise<AdminAudit[]> {
  const data = await jsonFetch<{ audit: AdminAudit[] }>(`${BASE}/admin/audit${aktor ? `?aktor=${encodeURIComponent(aktor)}` : ""}`);
  return data.audit || [];
}

// Tugas yang menunggu jawaban saya di semua acara (tidak perlu masuk acara dulu)
export type TugasMenungguSaya = { id: string; judul: string; event_id: string; acara: string; deadline_iso: string | null };
export async function tugasMenungguSaya(): Promise<TugasMenungguSaya[]> {
  const data = await jsonFetch<{ tugas: TugasMenungguSaya[] }>(`${BASE}/me/tugas-menunggu`);
  return data.tugas || [];
}

// Kabar acara dan unggahan lampiran (dipakai di halaman acara)
export async function unggahLampiran(file: File): Promise<LampiranRef> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}/lampiran`, { method: "POST", body: fd });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.error ?? "Gagal mengunggah berkas");
  }
  return readJson<LampiranRef>(res);
}
export async function fetchKabarAcara(eventId: string): Promise<KabarItem[]> {
  const data = await jsonFetch<{ kabar: KabarItem[] }>(`${BASE}/kabar?event_id=${encodeURIComponent(eventId)}`);
  return data.kabar || [];
}
export async function buatKabar(body: { isi: string; event_id: string; publik: boolean; lampiran_ids: string[] }): Promise<{ id: string }> {
  return jsonFetch(`${BASE}/kabar`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}
export async function hapusKabar(id: string): Promise<void> {
  await jsonFetch(`${BASE}/kabar/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// Admin: uji koneksi Capy ke Ollama (alamat, kunci, model) tanpa mengirim pertanyaan
export async function adminAsistenCek(): Promise<{ ok: boolean; pesan: string; alamat?: string }> {
  return jsonFetch(`${BASE}/admin/asisten-cek`);
}
