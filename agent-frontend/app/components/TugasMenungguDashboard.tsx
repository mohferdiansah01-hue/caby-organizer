"use client";

import { useEffect, useState } from "react";
import { TugasMenungguSaya, konfirmasiTugas, tugasMenungguSaya } from "../lib/api";
import Capy from "./Capy";

// Tugas yang dibagikan kepadaku dan belum kujawab, dari semua acara. Bisa diterima atau ditolak langsung dari dashboard.
export default function TugasMenungguDashboard() {
  const [tugas, setTugas] = useState<TugasMenungguSaya[]>([]);
  const [alasanId, setAlasanId] = useState<string | null>(null);
  const [alasan, setAlasan] = useState("");
  const [error, setError] = useState("");

  const muat = () => tugasMenungguSaya().then(setTugas).catch(() => setTugas([]));
  useEffect(() => { muat(); }, []);

  const terima = async (t: TugasMenungguSaya) => {
    setError("");
    try { await konfirmasiTugas(t.id, "terima"); await muat(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal menerima tugas"); }
  };
  const tolak = async (t: TugasMenungguSaya) => {
    setError("");
    try { await konfirmasiTugas(t.id, "tolak", alasan.trim()); setAlasanId(null); setAlasan(""); await muat(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal menolak tugas"); }
  };

  if (tugas.length === 0) return null;
  return (
    <section className="kartu-infografis space-y-3 p-5">
      <div className="flex items-center gap-3"><Capy mood="dukung" size={56} /><h2 className="font-semibold text-[#5B3A29]">Tugas menunggu jawabanmu ({tugas.length})</h2></div>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <ul className="space-y-2">
        {tugas.map((t) => (
          <li key={t.id} className="rounded-2xl border border-[#5B3A29]/10 bg-white p-3 space-y-2">
            <div>
              <p className="font-semibold text-sm text-[#5B3A29]">{t.judul}</p>
              <p className="text-xs text-[#7A5C48]">{t.acara}{t.deadline_iso ? ` · tenggat ${t.deadline_iso.slice(0, 16).replace("T", " ")}` : ""}</p>
            </div>
            {alasanId === t.id ? (
              <div className="flex flex-wrap gap-2">
                <input className="flex-1 min-w-[12rem] border border-[#cbd5e1] rounded-lg px-3 py-2 text-sm" placeholder="Alasan singkat, misalnya: sedang ujian"
                  value={alasan} onChange={(e) => setAlasan(e.target.value)} />
                <button type="button" disabled={!alasan.trim()} onClick={() => tolak(t)} className="rounded-full bg-[#5B3A29] px-3 py-1.5 text-xs font-bold text-[#FFF6E3] disabled:opacity-40">Kirim penolakan</button>
                <button type="button" onClick={() => setAlasanId(null)} className="text-xs underline text-[#7A5C48]">Batal</button>
              </div>
            ) : (
              <div className="flex gap-2">
                <button type="button" onClick={() => terima(t)} className="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white">Saya terima</button>
                <button type="button" onClick={() => { setAlasanId(t.id); setAlasan(""); }} className="rounded-full border border-[#94a3b8] px-3 py-1.5 text-xs font-semibold">Tidak sanggup</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
