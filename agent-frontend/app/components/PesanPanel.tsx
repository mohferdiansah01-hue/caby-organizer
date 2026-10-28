"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AlertTriangle, Bell, Info, Loader2, Send, Zap } from "lucide-react";
import KonfirmasiDialog from "./KonfirmasiDialog";
import CabyState from "./CabyState";
import { Me, PesanItem, TingkatPesan, fetchPesan, kirimPesan, tandaiBaca, peringatanOtomatis, ubahPesan, tarikPesan } from "../lib/api";

const TINGKAT: Record<TingkatPesan, { label: string; kelas: string; ikon: typeof Info }> = {
  info: { label: "Info", kelas: "bg-sky-500/15 text-sky-300 border-sky-500/30", ikon: Info },
  pengingat: { label: "Pengingat", kelas: "bg-amber-500/15 text-amber-300 border-amber-500/30", ikon: Bell },
  peringatan: { label: "Peringatan", kelas: "bg-red-500/15 text-red-300 border-red-500/30", ikon: AlertTriangle },
};
const CONTOH = [
  "Mohon update progres tugasmu hari ini.",
  "Deadline makin dekat. Segera kirim hasil kerja.",
  "Tolong kabari kalau ada kendala di tugasmu.",
];
const input = "bg-white border border-[#cbd5e1] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-400/60 w-full";

// Kirim pesan ke semua anggota, satu seksi, atau satu orang. Ketua bisa semua, koordinator hanya seksinya.
export function KirimPesan({ eventId, me, seksiList }: { eventId: string; me: Me | null; seksiList: string[] }) {
  const [isi, setIsi] = useState("");
  const [tingkat, setTingkat] = useState<TingkatPesan>("pengingat");
  const [target, setTarget] = useState("semua");
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const seksiSaya = me?.ketua ? seksiList : me?.role ? [me.role] : [];

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await kirimPesan({ event_id: eventId, isi: isi.trim(), tingkat, ke: target });
      setIsi("");
      setInfo("Pesan terkirim.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pesan belum terkirim");
    } finally {
      setBusy(false);
    }
  };

  const otomatis = async () => {
    setBusy(true);
    setError("");
    try {
      const hasil = await peringatanOtomatis(eventId);
      setInfo(hasil.jumlah ? `Peringatan dikirim ke ${hasil.dikirim_ke.join(", ")}.` : "Tidak ada tugas yang lewat deadline.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengirim peringatan");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="kartu-infografis p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-lg font-semibold">Kirim pesan ke anggota</h2>
        {me?.ketua && (
          <button type="button" onClick={otomatis} disabled={busy} className="px-3 py-2 rounded-lg border border-red-500/40 text-red-300 hover:bg-red-500/10 text-sm flex items-center gap-2 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-teal-400">
            <Zap className="w-4 h-4" aria-hidden="true" /> Peringatan otomatis untuk tugas terlambat
          </button>
        )}
      </div>
      <form onSubmit={kirim} className="grid gap-3 sm:grid-cols-[1fr_1fr_1.4fr]">
        <label className="text-xs text-slate-400">Tingkat
          <select aria-label="Tingkat" className={input} value={tingkat} onChange={(e) => setTingkat(e.target.value as TingkatPesan)}>
            <option value="info">Info</option><option value="pengingat">Pengingat</option><option value="peringatan">Peringatan</option>
          </select>
        </label>
        <label className="text-xs text-slate-400">Kepada
          <select aria-label="Kepada" className={input} value={target} onChange={(e) => setTarget(e.target.value)}>
            {me?.ketua && <option value="semua">Semua anggota</option>}
            {seksiSaya.map((s) => <option key={s} value={`seksi:${s}`}>Seksi {s}</option>)}
          </select>
        </label>
        <div className="sm:row-span-2 flex flex-col gap-2">
          <p className="text-xs text-slate-400">Contoh cepat</p>
          <div className="flex flex-wrap gap-1.5">
            {CONTOH.map((c) => (
              <button key={c} type="button" onClick={() => setIsi(c)} className="text-[11px] px-2 py-1 rounded-full border border-[#cbd5e1] text-slate-300 hover:border-teal-400 text-left focus-visible:ring-2 focus-visible:ring-teal-400">{c}</button>
            ))}
          </div>
        </div>
        <textarea rows={2} maxLength={500} value={isi} onChange={(e) => setIsi(e.target.value)} placeholder="Tulis pesan yang jelas dan singkat" className={`${input} sm:col-span-2`} />
        <div className="sm:col-span-2 flex items-center justify-end gap-3">
          {info && <span className="text-xs text-teal-300">{info}</span>}
          {error && <span className="text-xs text-red-300">{error}</span>}
          <button type="submit" disabled={busy || !isi.trim()} className="px-4 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 disabled:opacity-40 text-slate-950 text-sm font-semibold flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-teal-300">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Kirim
          </button>
        </div>
      </form>
    </section>
  );
}

// Kotak masuk pesan untuk anggota. Pesan yang belum dibaca ditandai. Dibaca lewat tombol.
export function KotakPesan({ eventId }: { eventId: string }) {
  const [pesan, setPesan] = useState<PesanItem[]>([]);
  const [belum, setBelum] = useState(0);
  const [editId, setEditId] = useState<string | null>(null);
  const [editIsi, setEditIsi] = useState("");
  const [tarikId, setTarikId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const muat = useCallback(() => {
    fetchPesan(eventId).then((d) => { setPesan(d.pesan); setBelum(d.belum_dibaca); }).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat pesan"));
  }, [eventId]);

  useEffect(() => { muat(); }, [muat]);

  const baca = async (id: string) => {
    try {
      await tandaiBaca(id);
      muat();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menandai");
    }
  };

  return (
    <section className="kartu-infografis p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg font-semibold">Pesan dari Ketua</h2>
        {belum > 0 && <span className="text-xs px-2 py-1 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">{belum} belum dibaca</span>}
      </div>
      {error && <p className="text-sm text-red-300">{error}</p>}
      {pesan.length === 0 && <CabyState kind="pesan" judul="Belum ada pesan" isi="Pesan dari Ketua dan seksi akan muncul di sini." />}
      <ul className="space-y-2">
        {pesan.map((p) => {
          const t = TINGKAT[p.tingkat] ?? TINGKAT.info;
          const Ikon = t.ikon;
          return (
            <li key={p.id} className={`rounded-xl border px-4 py-3 ${p.dibaca ? "border-[#5B3A29]/15 bg-slate-950/40" : "border-teal-500/40 bg-teal-500/5"}`}>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span className={`px-2 py-0.5 rounded-full border flex items-center gap-1 ${t.kelas}`}><Ikon className="w-3 h-3" aria-hidden="true" /> {t.label}</span>
                <span>dari {p.dari}</span>
                <span>· {p.ke_anggota_id ? "untuk kamu" : p.ke_seksi ? `seksi ${p.ke_seksi}` : "semua"}</span>
              </div>
              <p className="text-sm mt-2 break-words">{p.isi}</p>
              {p.bisa_diubah && (
                <div className="mt-2 flex gap-3 text-xs">
                  <button onClick={() => { setEditId(p.id); setEditIsi(p.isi); }}
                    className="text-teal-300 underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-teal-400 rounded">Ubah</button>
                  <button onClick={() => setTarikId(p.id)}
                    className="text-red-300 underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-teal-400 rounded">Tarik</button>
                </div>
              )}
              {editId === p.id && (
                <div className="mt-2 space-y-2">
                  <textarea className={input} rows={3} value={editIsi} onChange={(e) => setEditIsi(e.target.value)} />
                  <div className="flex gap-2">
                    <button type="button" disabled={!editIsi.trim()} onClick={async () => { await ubahPesan(p.id, editIsi.trim()); setEditId(null); muat(); }}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold disabled:opacity-40">Simpan</button>
                    <button type="button" onClick={() => setEditId(null)} className="text-xs text-slate-400 underline">Batal</button>
                  </div>
                </div>
              )}
              {!p.dibaca && (
                <button onClick={() => baca(p.id)} className="mt-2 text-xs text-teal-300 hover:text-teal-200 underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-teal-400 rounded">
                  Tandai sudah dibaca
                </button>
              )}
            </li>
          );
        })}
      </ul>
      {tarikId && <KonfirmasiDialog pesan="Tarik pesan ini? Pesan hilang dari kotak masuk semua penerima." labelYa="Ya, tarik" onYa={async () => { const id = tarikId; setTarikId(null); await tarikPesan(id); muat(); }} onBatal={() => setTarikId(null)} />}
    </section>
  );
}
