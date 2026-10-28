"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Capy from "../components/Capy";
import CabyState from "../components/CabyState";
import { CheckCircle2, Circle, Trash2 } from "lucide-react";
import { KerjaData, Task, createTask, deleteTask, fetchKerja, getMe, pakaiDefaultSeksi, updateTask, Me } from "../lib/api";
import KomentarTugas from "../components/KomentarTugas";
import KonfirmasiDialog from "../components/KonfirmasiDialog";
import { Kelompok, kelompokTugas, labelKelompok, terlambat, tglPendek } from "../lib/status";

type Baris = Task & { acara: string };

// Ruang kerja: semua tugas yang boleh dilihat peran ini, dikelompokkan menurut status.
export default function RuangKerja() {
  const [dialog, setDialog] = useState<{ pesan: string; aksi: () => void } | null>(null);
  const [data, setData] = useState<KerjaData | null>(null);
  const [galat, setGalat] = useState("");
  const [seksi, setSeksi] = useState("Semua");
  const [me, setMe] = useState<Me | null>(null);
  const [judulBaru, setJudulBaru] = useState("");
  const [deadlineBaru, setDeadlineBaru] = useState("");
  const [acaraBaru, setAcaraBaru] = useState("");
  const [sedangKerja, setSedangKerja] = useState(false);

  useEffect(() => {
    getMe().then(setMe).catch(() => setMe(null));
  }, []);

  const muat = () =>
    fetchKerja()
      .then((d) => {
        setData(d);
        setGalat("");
      })
      .catch((e) => setGalat(e instanceof Error ? e.message : "Gagal memuat ruang kerja."));

  useEffect(() => {
    muat();
  }, []);

  const semua = useMemo<Baris[]>(
    () => (data?.acara ?? []).flatMap((a) => a.tugas.map((t) => ({ ...t, acara: a.event.nama }))),
    [data],
  );
  const daftarSeksi = useMemo(() => Array.from(new Set(semua.map((t) => t.divisi).filter(Boolean))), [semua]);
  const tampil = seksi === "Semua" ? semua : semua.filter((t) => t.divisi === seksi);

  const grup: Record<Kelompok, Baris[]> = { belum: [], dikerjakan: [], selesai: [] };
  tampil.forEach((t) => grup[kelompokTugas(t)].push(t));

  // Seksi (koordinator) mengelola tugas seksinya sendiri; Ketua mengelola semuanya.
  // Acara tempat pengguna berperan Ketua atau koordinator, dari daftar acara (tidak bergantung pada acara yang sedang dimasuki).
  const acaraBisaKelola = (data?.acara ?? []).filter((a) => a.peran === "ketua" || a.peran === "koordinator");
  const seksiSaya = data?.role ?? "";
  const milikSaya = (t: Baris) => !!me && (me.ketua || (me.peran === "koordinator" && t.divisi.toLowerCase() === seksiSaya.toLowerCase()));
  const acaraTerpilih = acaraBaru || data?.acara[0]?.event.id || "";

  const tambah = async (e: FormEvent) => {
    e.preventDefault();
    if (!judulBaru.trim() || !acaraTerpilih) return;
    setSedangKerja(true);
    try {
      await createTask({ event_id: acaraTerpilih, judul: judulBaru.trim(), deadline_iso: deadlineBaru || null, divisi: seksiSaya || undefined });
      setJudulBaru("");
      setDeadlineBaru("");
      await muat();
    } catch (err) {
      setGalat(err instanceof Error ? err.message : "Gagal menambah tugas.");
    } finally {
      setSedangKerja(false);
    }
  };

  const hapus = (t: Baris) => {
    setDialog({ pesan: `Hapus tugas "${t.judul}"?`, aksi: async () => {
      setDialog(null);
      try {
        await deleteTask(t.id);
        await muat();
      } catch (err) {
        setGalat(err instanceof Error ? err.message : "Gagal menghapus tugas.");
      }
    } });
  };

  const kembaliKeDefault = () => {
    if (!acaraTerpilih || !seksiSaya) return;
    setDialog({ pesan: `Ganti semua tugas ${seksiSaya} di acara ini dengan tugas default? Tugas yang sudah ada akan dihapus.`, aksi: () => { setDialog(null); jalankanDefault(); } });
  };

  const jalankanDefault = async () => {
    if (!acaraTerpilih || !seksiSaya) return;
    setSedangKerja(true);
    try {
      await pakaiDefaultSeksi(acaraTerpilih, seksiSaya);
      await muat();
    } catch (err) {
      setGalat(err instanceof Error ? err.message : "Gagal mengembalikan tugas ke default.");
    } finally {
      setSedangKerja(false);
    }
  };

  const toggle = async (t: Baris) => {
    try {
      await updateTask(t.id, { status: t.status === "done" ? "pending" : "done" });
      await muat();
    } catch (e) {
      setGalat(e instanceof Error ? e.message : "Gagal memperbarui tugas.");
    }
  };

  return (
    <main className="capy-theme max-w-6xl mx-auto px-4 md:px-6 pt-6 pb-28 md:py-10 space-y-6">
      <header className="grid items-center gap-4 rounded-[2rem] bg-[#FFD36E] p-6 md:grid-cols-[1fr_auto] md:p-8">
        <div>
          <p className="text-xs font-bold tracking-wide text-[#5B3A29]/80">TUGAS SAYA DAN SEKSI</p>
          <h1 className="font-display mt-1 text-3xl font-bold text-[#5B3A29] md:text-4xl">Ruang kerja</h1>
        </div>
        <Capy mood="dukung" size={100} className="md:w-[120px]" />
      </header>

      {galat && <p role="alert" className="text-sm text-red-300">{galat}</p>}

      {daftarSeksi.length > 0 && (
        <nav aria-label="Filter seksi" className="flex flex-wrap gap-2">
          {["Semua", ...daftarSeksi].map((nama) => (
            <button
              key={nama}
              type="button"
              onClick={() => setSeksi(nama)}
              aria-pressed={seksi === nama}
              className={`px-3 py-1.5 rounded-full text-sm border focus-visible:ring-2 focus-visible:ring-teal-400 ${seksi === nama ? "bg-teal-500/15 border-teal-400 text-teal-300" : "border-[#cbd5e1] text-slate-300 hover:border-slate-500"}`}
            >
              {nama}
            </button>
          ))}
        </nav>
      )}

      {data && acaraBisaKelola.length > 0 && (
        <section className="kartu-infografis p-4 space-y-3">
          <form onSubmit={tambah} className="grid gap-2 md:grid-cols-[2fr_1fr_1fr_auto] md:items-end">
            <label className="text-xs text-slate-400 space-y-1">Tugas baru
              <input value={judulBaru} onChange={(e) => setJudulBaru(e.target.value)} className="w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm" required />
            </label>
            <label className="text-xs text-slate-400 space-y-1">Deadline
              <input type="datetime-local" value={deadlineBaru} onChange={(e) => setDeadlineBaru(e.target.value)} className="w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-400 space-y-1">Acara
              <select aria-label="Acara" value={acaraTerpilih} onChange={(e) => setAcaraBaru(e.target.value)} className="w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm">
                {acaraBisaKelola.map((a) => <option key={a.event.id} value={a.event.id}>{a.event.nama}</option>)}
              </select>
            </label>
            <button type="submit" disabled={sedangKerja || !judulBaru.trim()} className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-40 text-slate-950 text-sm font-semibold">Tambah</button>
          </form>
          {!me?.ketua && seksiSaya && (
            <button type="button" onClick={kembaliKeDefault} disabled={sedangKerja} className="text-xs text-teal-300 hover:text-teal-200 disabled:opacity-40">
              Kembalikan tugas {seksiSaya} di acara ini ke default
            </button>
          )}
        </section>
      )}

      {!data && !galat && <CabyState kind="memuat" judul="Memuat ruang kerja…" />}
      {data && semua.length === 0 && <CabyState kind="kosong" judul="Belum ada tugas untuk peran ini" isi="Tugas akan muncul di sini setelah dibuat." />}

      <div className="grid gap-6 md:grid-cols-3">
        {(["belum", "dikerjakan", "selesai"] as Kelompok[]).map((k) => (
          <section key={k} className="space-y-2 min-w-0">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              {labelKelompok(k)} <span className="text-xs text-slate-500">{grup[k].length}</span>
            </h2>
            {grup[k].map((t) => (
              <article key={t.id} className="p-3 rounded-xl kartu-infografis">
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => toggle(t)}
                    aria-label={t.status === "done" ? "Tandai belum selesai" : "Tandai selesai"}
                    className="mt-0.5 shrink-0 text-slate-400 hover:text-emerald-300 focus-visible:ring-2 focus-visible:ring-teal-400 rounded"
                  >
                    {t.status === "done" ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <Circle className="w-5 h-5" />}
                  </button>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-medium break-words ${k === "selesai" ? "line-through text-slate-500" : ""}`}>{t.judul}</p>
                    <p className="text-xs text-slate-400 mt-1 break-words">
                      {t.divisi || "Tanpa seksi"} · {t.acara}{t.deadline_iso ? ` · ${tglPendek(t.deadline_iso)}` : ""}
                      {terlambat(t) && <span className="text-red-300"> · terlambat</span>}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <KomentarTugas taskId={t.id} ketua={!!data?.ketua} />
                      {milikSaya(t) && (
                        <button type="button" onClick={() => hapus(t)} aria-label={`Hapus tugas ${t.judul}`} className="text-xs text-red-300 hover:text-red-200 flex items-center gap-1">
                          <Trash2 className="w-3 h-3" aria-hidden="true" /> Hapus
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </section>
        ))}
      </div>

      {dialog && <KonfirmasiDialog pesan={dialog.pesan} labelYa="Ya, lanjutkan" onYa={dialog.aksi} onBatal={() => setDialog(null)} />}
    </main>
  );
}
