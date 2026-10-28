"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { AksiCapy, agenChat, agenHapusRiwayat, agenJalankan, agenRiwayat } from "../lib/api";
import Capy from "./Capy";
import KonfirmasiDialog from "./KonfirmasiDialog";

type Pesan = { peran: "user" | "capy" | "sistem"; teks: string; aksi?: AksiCapy[] };

const field = "w-full border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm text-[#0f172a] bg-white focus-visible:ring-2 focus-visible:ring-teal-400";
const CONTOH = ["Ringkas acara saya", "Tugas apa yang menunggu jawabanku?", "Buka ruang kerja", "Bagaimana menyusun rundown 3 jam?"];

// Capy: bisa membaca data acara yang boleh kamu lihat, membuka halaman, dan mengusulkan perubahan.
// Perubahan baru terjadi setelah kamu menekan Jalankan.
export default function TanyaCapy({ eventId }: { eventId?: string }) {
  const [pesan, setPesan] = useState<Pesan[]>([]);
  const [siap, setSiap] = useState(false);
  const [tanyaHapus, setTanyaHapus] = useState(false);
  const [tanya, setTanya] = useState("");
  const [busy, setBusy] = useState(false);
  const [jalan, setJalan] = useState<number | null>(null);
  const [tanyaDulu, setTanyaDulu] = useState<{ indeks: number; a: Extract<AksiCapy, { jenis: "usulan" }> } | null>(null);

  useEffect(() => {
    setSiap(false);
    setPesan([]);
    agenRiwayat(eventId).then((r) => { setPesan(r.map((m) => ({ peran: m.peran, teks: m.isi, aksi: m.aksi }))); setSiap(true); })
      .catch(() => setSiap(true));
  }, [eventId]);

  const mulaiBaru = async () => {
    setTanyaHapus(false);
    await agenHapusRiwayat(eventId).catch(() => undefined);
    setPesan([]);
  };

  const kirimTeks = async (teks: string) => {
    const t = teks.trim();
    if (!t || busy) return;
    setPesan((p) => [...p, { peran: "user", teks: t }]);
    setTanya("");
    setBusy(true);
    try {
      const hasil = await agenChat(t, eventId);
      setPesan((p) => [...p, { peran: "capy", teks: hasil.jawaban, aksi: hasil.aksi }]);
    } catch (err) {
      setPesan((p) => [...p, { peran: "sistem", teks: err instanceof Error ? err.message : "Capy belum bisa menjawab." }]);
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => { e.preventDefault(); kirimTeks(tanya); };

  const jalankanUsulan = async (indeks: number, a: Extract<AksiCapy, { jenis: "usulan" }>) => {
    setJalan(indeks);
    try {
      const hasil = await agenJalankan(a.tipe, a.data);
      setPesan((p) => [
        ...p.map((m, i) => (i === indeks ? { ...m, aksi: (m.aksi ?? []).filter((x) => x !== a) } : m)),
        { peran: "sistem", teks: hasil.pesan ?? "Selesai." },
      ]);
    } catch (err) {
      setPesan((p) => [...p, { peran: "sistem", teks: err instanceof Error ? err.message : "Gagal menjalankan usulan." }]);
    } finally {
      setJalan(null);
    }
  };

  const batalkan = (indeks: number) => {
    setPesan((p) => p.map((m, i) => (i === indeks ? { ...m, aksi: (m.aksi ?? []).filter((x) => x.jenis !== "usulan") } : m)));
    setPesan((p) => [...p, { peran: "sistem", teks: "Usulan dibatalkan. Tidak ada yang berubah." }]);
  };

  return (
    <>
    {tanyaHapus && (
      <KonfirmasiDialog
        pesan={`Hapus percakapan ${eventId ? "di acara ini" : "umum"}? Riwayat hanya milikmu dan tidak bisa dikembalikan.`}
        labelYa="Ya, hapus"
        onYa={mulaiBaru}
        onBatal={() => setTanyaHapus(false)}
      />
    )}
    {tanyaDulu && (
      <KonfirmasiDialog
        pesan={`${tanyaDulu.a.ringkas}. Tindakan ini berbahaya. Lanjutkan?`}
        labelYa="Ya, jalankan"
        bahaya
        onYa={() => { const x = tanyaDulu; setTanyaDulu(null); jalankanUsulan(x.indeks, x.a); }}
        onBatal={() => setTanyaDulu(null)}
      />
    )}
    <section className="bg-white border border-[#e2e8f0] rounded-2xl p-5 space-y-4" style={{ color: "#0f172a" }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Capy mood="tanya" size={48} />
          <h2 className="font-semibold">{eventId ? "Asisten acara" : "Ngobrol dengan Capy"}</h2>
        </div>
        <div className="flex items-center gap-2">
          {pesan.length > 0 && <button type="button" onClick={() => setTanyaHapus(true)} className="text-xs underline text-[#7A5C48]">Mulai baru</button>}
        </div>
      </div>
      <p className="text-xs text-[#64748b]">
        {eventId
          ? "Capy membaca data acara ini dan bisa mengusulkan perubahan. Perubahan baru terjadi setelah kamu menekan Jalankan."
          : "Ngobrol santai atau tanya apa saja. Di dalam acara, Capy bisa membantu mengurus tugas."}
      </p>

      {siap && pesan.length === 0 && !busy && (
        <div className="space-y-2">
          <div className="flex items-center gap-3"><Capy mood="tips" size={56} /><span className="text-xs text-[#64748b]">Coba salah satu contoh ini:</span></div>
          <div className="flex flex-wrap gap-2">
          {CONTOH.map((c) => (
            <button key={c} type="button" onClick={() => kirimTeks(c)} className="text-xs px-3 py-1.5 rounded-full border border-[#cbd5e1] text-[#334155]">{c}</button>
          ))}
          </div>
        </div>
      )}

      {pesan.length > 0 && (
        <ol className="space-y-3 max-h-[420px] overflow-y-auto pr-1" aria-live="polite">
          {pesan.map((m, i) => (
            <li key={i} className={m.peran === "user" ? "text-right" : ""}>
              <div className={`inline-block max-w-[90%] text-left text-sm whitespace-pre-wrap rounded-2xl px-3 py-2 ${
                m.peran === "user" ? "bg-[#4f46e5] text-[#ffffff]" : m.peran === "sistem" ? "bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0] text-xs" : "bg-[#f1f5f9] text-[#0f172a]"}`}>
                {m.teks}
              </div>
              {(m.aksi ?? []).map((a, k) =>
                a.jenis === "navigasi" ? (
                  <div key={k} className="mt-2"><Link href={a.url} className="inline-block text-xs font-semibold px-3 py-1.5 rounded-full bg-teal-600 text-white">{a.label}</Link></div>
                ) : (
                  <div key={k} className="mt-2 border border-amber-300 bg-amber-50 rounded-xl p-3 text-left space-y-2">
                    <p className="text-xs font-semibold text-amber-900">Usulan perubahan</p>
                    <p className="text-sm">{a.ringkas}</p>
                    <div className="flex gap-2">
                      <button type="button" disabled={jalan !== null} onClick={() => (a.berbahaya ? setTanyaDulu({ indeks: i, a }) : jalankanUsulan(i, a))}
                        className="px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-600 text-white disabled:opacity-40">{jalan === i ? "Menjalankan..." : "Jalankan"}</button>
                      <button type="button" onClick={() => batalkan(i)} className="px-3 py-1.5 rounded-full text-xs font-semibold border border-[#94a3b8] text-[#1e293b]">Batal</button>
                    </div>
                  </div>
                ))}
            </li>
          ))}
        </ol>
      )}

      {busy && <div className="flex items-center gap-3 text-xs text-[#475569]"><Capy mood="pikir" size={40} /> Capy sedang berpikir...</div>}

      <form onSubmit={submit} className="flex gap-2 items-end">
        <textarea className={field} rows={2} maxLength={1000} placeholder="Tanya atau minta sesuatu, misalnya: buka ruang kerja" value={tanya} onChange={(e) => setTanya(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); kirimTeks(tanya); } }} />
        <button type="submit" disabled={busy || !tanya.trim()} className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold disabled:opacity-40">Kirim</button>
      </form>
    </section>
    </>
  );
}
