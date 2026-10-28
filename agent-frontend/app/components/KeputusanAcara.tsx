"use client";

import { FormEvent, useEffect, useState } from "react";
import { CatatanKeputusan, catatKeputusan, fetchKeputusan } from "../lib/api";
import CabyState from "./CabyState";
import Capy from "./Capy";

const field = "w-full border border-[#cbd5e1] rounded-lg px-3 py-2 text-sm text-[#0f172a] bg-white focus-visible:ring-2 focus-visible:ring-teal-400";

// Catatan keputusan acara: keputusan rapat dicatat di sini, supaya tidak tenggelam di chat.
export default function KeputusanAcara({ eventId }: { eventId: string }) {
  const [daftar, setDaftar] = useState<CatatanKeputusan[]>([]);
  const [judul, setJudul] = useState("");
  const [isi, setIsi] = useState("");
  const [error, setError] = useState("");

  const muat = () => fetchKeputusan(eventId).then(setDaftar).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat keputusan"));
  useEffect(() => { muat(); }, [eventId]); // eslint-disable-line react-hooks/exhaustive-deps

  const simpan = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await catatKeputusan(eventId, { judul: judul.trim(), isi: isi.trim() });
      setJudul(""); setIsi("");
      await muat();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mencatat keputusan");
    }
  };

  return (
    <section className="kartu-infografis p-5 space-y-4" style={{ color: "#0f172a" }}>
      <h2 className="font-semibold">Catatan keputusan</h2>
      <form onSubmit={simpan} className="space-y-2">
        <input className={field} placeholder="Judul keputusan, misalnya: Tempat acara pindah ke aula" value={judul} onChange={(e) => setJudul(e.target.value)} required />
        <textarea className={field} rows={2} placeholder="Isi singkat keputusan (opsional)" value={isi} onChange={(e) => setIsi(e.target.value)} />
        <button type="submit" disabled={!judul.trim()} className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold disabled:opacity-40">Catat keputusan</button>
      </form>
      {daftar.length === 0 ? (
        <CabyState kind="intip" judul="Belum ada keputusan dicatat" isi="Catat keputusan rapat di atas supaya tidak tenggelam di chat." />
      ) : (
        <ul className="space-y-2">
          {daftar.map((k) => (
            <li key={k.id} className="border border-[#e2e8f0] rounded-xl p-3">
              <p className="text-sm font-semibold">{k.judul}</p>
              {k.isi && <p className="text-sm text-[#334155] mt-1 whitespace-pre-wrap">{k.isi}</p>}
              <p className="text-xs text-[#64748b] mt-1">dicatat {k.penulis}{k.created_at ? ` · ${k.created_at.slice(0, 16).replace("T", " ")}` : ""}</p>
            </li>
          ))}
        </ul>
      )}
      {error && <div className="flex items-center gap-3"><Capy mood="malu" size={56} /><p role="alert" className="text-sm text-red-600">{error}</p></div>}
    </section>
  );
}
