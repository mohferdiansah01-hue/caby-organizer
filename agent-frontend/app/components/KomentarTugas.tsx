"use client";

import { useEffect, useState } from "react";
import { Loader2, MessageSquare, Send } from "lucide-react";
import { Komentar, fetchKomentar, tulisKomentar } from "../lib/api";

// Komentar dan perintah pada satu tugas. Ketua menulis sebagai perintah, seksi sebagai komentar.
export default function KomentarTugas({ taskId, ketua }: { taskId: string; ketua: boolean }) {
  const [buka, setBuka] = useState(false);
  const [daftar, setDaftar] = useState<Komentar[]>([]);
  const [isi, setIsi] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const muat = () => fetchKomentar(taskId).then(setDaftar).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat"));
  useEffect(() => { if (buka) muat(); }, [buka]); // eslint-disable-line react-hooks/exhaustive-deps

  const kirim = async () => {
    if (!isi.trim()) return;
    setBusy(true);
    setError("");
    try {
      await tulisKomentar(taskId, isi.trim(), ketua ? "perintah" : "komentar");
      setIsi("");
      muat();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengirim");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-2">
      <button type="button" onClick={() => setBuka((v) => !v)} aria-expanded={buka} className="text-xs text-teal-300 hover:text-teal-200 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-teal-400 rounded">
        <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" /> {ketua ? "Beri perintah" : "Komentar"}
      </button>
      {buka && (
        <div className="mt-2 space-y-2 rounded-lg border border-[#5B3A29]/15 p-3">
          {daftar.length === 0 && <p className="text-xs text-slate-500">Belum ada komentar.</p>}
          <ul className="space-y-1.5">
            {daftar.map((k) => (
              <li key={k.id} className="text-xs">
                <span className={`font-semibold ${k.jenis === "perintah" ? "text-amber-300" : "text-slate-300"}`}>{k.dari}{k.jenis === "perintah" ? " (perintah)" : ""}:</span> {k.isi}
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <input value={isi} onChange={(e) => setIsi(e.target.value)} maxLength={1000} placeholder={ketua ? "Tulis perintah untuk seksi ini" : "Tulis komentar"}
              className="flex-1 bg-white border border-[#cbd5e1] rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:border-teal-400" />
            <button type="button" onClick={kirim} disabled={busy || !isi.trim()} aria-label="Kirim" className="p-2 rounded-lg bg-teal-500 hover:bg-teal-400 disabled:opacity-40 text-slate-950 focus-visible:ring-2 focus-visible:ring-teal-300">
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            </button>
          </div>
          {error && <p className="text-xs text-red-300">{error}</p>}
        </div>
      )}
    </div>
  );
}
