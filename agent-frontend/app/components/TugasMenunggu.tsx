"use client";

import { useEffect, useState } from "react";
import { Task, fetchTasks, konfirmasiTugas } from "../lib/api";
import Capy from "./Capy";

// Tugas yang dibagikan Ketua atau koordinator kepadamu dan belum kamu jawab.
export default function TugasMenunggu({ orangId }: { orangId: string }) {
  const [tugas, setTugas] = useState<Task[]>([]);
  const [alasanId, setAlasanId] = useState<string | null>(null);
  const [alasan, setAlasan] = useState("");
  const [error, setError] = useState("");

  const muat = () => fetchTasks().then((all) => setTugas(all.filter((t) => t.penerima_orang_id === orangId && !t.konfirmasi))).catch(() => setTugas([]));
  useEffect(() => { muat(); }, [orangId]); // eslint-disable-line react-hooks/exhaustive-deps

  const terima = async (t: Task) => {
    setError("");
    try { await konfirmasiTugas(t.id, "terima"); await muat(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal menerima tugas"); }
  };

  const tolak = async (t: Task) => {
    setError("");
    try { await konfirmasiTugas(t.id, "tolak", alasan.trim()); setAlasanId(null); setAlasan(""); await muat(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal menolak tugas"); }
  };

  if (tugas.length === 0) return null;

  return (
    <section className="bg-amber-50 border border-amber-200 rounded-3xl p-5 space-y-3">
      <div className="flex items-center gap-3"><Capy mood="dukung" size={56} /><h2 className="font-semibold text-[#0f172a]">Tugas menunggu jawabanmu ({tugas.length})</h2></div>
      <ul className="space-y-3">
        {tugas.map((t) => (
          <li key={t.id} className="bg-white border border-amber-100 rounded-xl p-3 space-y-2">
            <p className="text-sm font-semibold text-[#0f172a]">{t.judul}</p>
            {t.divisi && <p className="text-xs text-[#64748b]">Seksi {t.divisi}{t.deadline_iso ? ` · tenggat ${t.deadline_iso.slice(0, 10)}` : ""}</p>}
            {alasanId === t.id ? (
              <div className="space-y-2">
                <input className="w-full border border-[#cbd5e1] rounded-lg px-3 py-2 text-sm" placeholder="Alasan singkat, misalnya: sedang ujian"
                  value={alasan} onChange={(e) => setAlasan(e.target.value)} />
                <div className="flex gap-2">
                  <button type="button" disabled={!alasan.trim()} onClick={() => tolak(t)}
                    className="px-3 py-1.5 rounded-full text-xs font-semibold bg-red-600 text-white disabled:opacity-40">Kirim penolakan</button>
                  <button type="button" onClick={() => setAlasanId(null)} className="text-xs text-[#64748b] underline">Batal</button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <button type="button" onClick={() => terima(t)}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-600 text-white focus-visible:ring-2 focus-visible:ring-teal-400">Saya terima</button>
                <button type="button" onClick={() => { setAlasanId(t.id); setAlasan(""); }}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold border border-[#94a3b8] text-[#334155] focus-visible:ring-2 focus-visible:ring-teal-400">Tidak sanggup</button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    </section>
  );
}
