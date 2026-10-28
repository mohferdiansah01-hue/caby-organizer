"use client";

import { useEffect, useState } from "react";
import { Task, fetchTasks, fetchPesertaAcara, PesertaAcara } from "../lib/api";

// Aksi Ketua yang paling sering dibutuhkan: undangan dan pengingat lewat WhatsApp, serta unduh laporan PDF.
export default function AksiKetua({ eventId, nama, tanggal, lokasi }: { eventId: string; nama: string; tanggal: string | null; lokasi: string | null }) {
  const [tugas, setTugas] = useState<Task[]>([]);
  const [peserta, setPeserta] = useState<PesertaAcara[]>([]);
  const [salin, setSalin] = useState("");

  useEffect(() => {
    fetchTasks().then(setTugas).catch(() => setTugas([]));
    fetchPesertaAcara(eventId).then(setPeserta).catch(() => setPeserta([]));
  }, [eventId]);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const undangan = [
    `Undangan: ${nama}`,
    tanggal ? `Tanggal: ${tanggal}` : null,
    lokasi ? `Tempat: ${lokasi}` : null,
    "",
    `Silakan daftar akun di ${origin}/daftar lalu masuk, buka Dashboard, dan pilih "Gabung acara".`,
    "Password pendaftaran akan saya kirim terpisah.",
  ].filter((x) => x !== null).join("\n");

  // Tugas yang belum selesai dan tenggatnya dalam 3 hari, dikelompokkan per seksi.
  const [sekarang] = useState(() => Date.now());
  const mendekat = tugas.filter((t) => t.status !== "done" && t.deadline_iso && (new Date(t.deadline_iso).getTime() - sekarang) < 3 * 24 * 3600 * 1000);
  const namaPenerima = (id?: string | null) => peserta.find((p) => p.orang_id === id)?.nama;
  const pengingat = mendekat.length === 0
    ? "Pengingat tenggat: tidak ada tugas yang mendekati tenggat dalam 3 hari."
    : ["Pengingat tenggat (3 hari ke depan):", ...mendekat.map((t) =>
        `- ${t.judul} (seksi ${t.divisi ?? "-"}${namaPenerima(t.penerima_orang_id) ? `, ${namaPenerima(t.penerima_orang_id)}` : ", belum ada penerima"}) tenggat ${(t.deadline_iso ?? "").slice(0, 16).replace("T", " ")}`)].join("\n");

  const bukaWa = (teks: string) => window.open(`https://wa.me/?text=${encodeURIComponent(teks)}`, "_blank", "noopener");
  const salinTeks = async (teks: string, label: string) => {
    try { await navigator.clipboard.writeText(teks); setSalin(`${label} disalin.`); }
    catch { setSalin("Gagal menyalin. Salin manual dari teks berikut."); }
  };

  const tombol = "px-3 py-1.5 rounded-full text-xs font-semibold focus-visible:ring-2 focus-visible:ring-teal-400";

  return (
    <section className="kartu-infografis p-5 space-y-4" style={{ color: "#0f172a" }}>
      <h2 className="font-semibold">Ajak dan ingatkan lewat WhatsApp</h2>
      <p className="text-xs text-slate-500">Aplikasi tidak mengirim pesan sendiri. Teks disiapkan, lalu kamu pilih grup atau kontak di WhatsApp.</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => bukaWa(undangan)} className={`${tombol} bg-emerald-600 text-white`}>Bagikan undangan</button>
        <button type="button" onClick={() => bukaWa(pengingat)} className={`${tombol} bg-emerald-600 text-white`}>Kirim pengingat tenggat</button>
        <a href={`/api/events/${eventId}/calendar.ics`} className={`${tombol} border border-[#94a3b8] text-[#1e293b]`}>Tambah tenggat ke kalender</a>
        <a href={`/api/events/${eventId}/dokumen/laporan.pdf`} className={`${tombol} border border-[#94a3b8] text-[#1e293b]`}>Unduh laporan PDF</a>
      </div>
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer">Lihat teks yang akan dikirim</summary>
        <pre className="whitespace-pre-wrap mt-2 bg-slate-50 border border-slate-200 rounded-lg p-3 text-slate-700">{undangan}{"\n\n"}{pengingat}</pre>
        <button type="button" onClick={() => salinTeks(undangan, "Undangan")} className="mt-2 underline">Salin undangan</button>
      </details>
      {salin && <p role="status" className="text-xs text-slate-600">{salin}</p>}
    </section>
  );
}
