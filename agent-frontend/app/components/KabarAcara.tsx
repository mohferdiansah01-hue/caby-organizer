"use client";

import { FormEvent, useEffect, useState } from "react";
import { KabarItem, buatKabar, fetchKabarAcara, hapusKabar, unggahLampiran } from "../lib/api";
import LampiranView from "./LampiranView";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm text-[#5B3A29] focus-visible:ring-2 focus-visible:ring-[#E8962E]";

// Kabar untuk anggota acara ini, dengan lampiran opsional. Kabar publik juga tampil di beranda.
export default function KabarAcara({ eventId }: { eventId: string }) {
  const [daftar, setDaftar] = useState<KabarItem[]>([]);
  const [isi, setIsi] = useState("");
  const [publik, setPublik] = useState(false);
  const [berkas, setBerkas] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");

  const muat = () => fetchKabarAcara(eventId).then(setDaftar).catch(() => setDaftar([]));
  useEffect(() => { muat(); }, [eventId]); // eslint-disable-line react-hooks/exhaustive-deps

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(""); setInfo("");
    try {
      const lampiranIds: string[] = [];
      if (berkas) lampiranIds.push((await unggahLampiran(berkas)).id);
      await buatKabar({ isi: isi.trim(), event_id: eventId, publik, lampiran_ids: lampiranIds });
      setIsi(""); setPublik(false); setBerkas(null); setInfo("Kabar terkirim.");
      await muat();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengirim kabar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={kirim} className="space-y-2">
        <label className="block text-xs space-y-1">Tulis kabar untuk anggota
          <textarea className={field} rows={2} maxLength={500} placeholder="Misalnya: rundown final sudah diunggah, cek sebelum Jumat" value={isi} onChange={(e) => setIsi(e.target.value)} required />
        </label>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <label className="flex items-center gap-2"><input type="checkbox" checked={publik} onChange={(e) => setPublik(e.target.checked)} /> Tampilkan di beranda</label>
          <input type="file" aria-label="Lampiran kabar" accept="image/*,video/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx" onChange={(e) => setBerkas(e.target.files?.[0] ?? null)} className="text-xs" />
          <button type="submit" disabled={busy || !isi.trim()} className="ml-auto rounded-full bg-[#5B3A29] px-4 py-2 text-xs font-bold text-[#FFF6E3] disabled:opacity-40">{busy ? "Mengirim…" : "Kirim kabar"}</button>
        </div>
        {info && <p role="status" className="text-xs text-emerald-700">{info}</p>}
        {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
      </form>
      {daftar.length === 0 && <p className="text-xs text-[#7A5C48]">Belum ada kabar.</p>}
      <ul className="space-y-3">
        {daftar.map((k) => (
          <li key={k.id} className="rounded-2xl border border-[#5B3A29]/10 bg-white p-3 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-[#5B3A29] whitespace-pre-wrap">{k.isi}</p>
              {k.bisa_hapus && (
                <button type="button" onClick={async () => { try { await hapusKabar(k.id); await muat(); } catch (e) { setError(e instanceof Error ? e.message : "Gagal menghapus"); } }}
                  className="shrink-0 text-xs underline text-red-700">Hapus</button>
              )}
            </div>
            <p className="text-[11px] text-[#7A5C48]">{k.seksi}{k.waktu ? ` · ${k.waktu.slice(0, 16).replace("T", " ")}` : ""}{k.publik ? " · tampil di beranda" : ""}</p>
            {k.lampiran && k.lampiran.length > 0 && <LampiranView items={k.lampiran} />}
          </li>
        ))}
      </ul>
    </div>
  );
}
