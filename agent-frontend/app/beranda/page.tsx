"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Capy from "../components/Capy";
import { Balon, Judul, KartuIkon, WARNA } from "../components/Infografis";
import CabyState from "../components/CabyState";
import Credit from "../components/Credit";
import { Beranda, fetchBeranda } from "../lib/api";
import LampiranView from "../components/LampiranView";

// Beranda publik: hero kuning gaya infografis CV, ringkasan, cara kerja, dan ajakan.
export default function BerandaPage() {
  const [data, setData] = useState<Beranda | null>(null);
  const [galat, setGalat] = useState(false);

  useEffect(() => {
    fetchBeranda().then(setData).catch(() => setGalat(true));
  }, []);

  const st = data?.statistik;
  const judul = data?.pengaturan.judul || "Halo, aku Capy!";
  const subjudul = data?.pengaturan.subjudul || "Ini cara kepanitiaanku bekerja. Tugas dibagi jelas, tenggat diingatkan, dan keputusan tercatat.";

  return (
    <main className="min-h-screen bg-[#FFF6E3] text-[#5B3A29]">
      {/* Hero kuning */}
      <section className="bg-[#FFD36E] relative overflow-hidden">
        <div className="max-w-6xl mx-auto px-5 py-14 md:py-20 grid md:grid-cols-2 gap-8 items-center">
          <div className="space-y-5">
            <span className="inline-block rounded-full bg-[#FFFDF7] px-4 py-1 text-xs font-bold tracking-wide text-[#5B3A29]">APLIKASI KEPANITIAAN</span>
            <h1 className="font-display text-4xl md:text-6xl font-bold leading-tight">{judul}</h1>
            <p className="text-base md:text-lg text-[#5B3A29]/85 max-w-md">{subjudul}</p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href="/daftar" className="px-6 py-3 rounded-full bg-[#5B3A29] text-[#FFF6E3] font-bold text-sm hover:opacity-90">Daftar akun</Link>
              <Link href="/login" className="px-6 py-3 rounded-full border-2 border-[#5B3A29] font-bold text-sm hover:bg-[#FFFDF7]">Masuk</Link>
            </div>
          </div>
          <div className="flex justify-center">
            <Capy mood="sapa" size={300} />
          </div>
        </div>
      </section>

      {/* Ringkasan: ikon per angka */}
      <section className="max-w-6xl mx-auto px-5 py-10">
        <Judul>Sekilas aplikasi</Judul>
        {galat && <CabyState kind="galat" judul="Ringkasan belum bisa dimuat" isi="Coba muat ulang halaman sebentar lagi." />}
        {!galat && !st && <CabyState kind="memuat" judul="Mengambil ringkasan..." />}
        {st && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-3xl bg-[#FFFDF7] border border-[#5B3A29]/10 shadow-sm"><KartuIkon mood="ajak" judul={`${st.acara} acara`} isi="dikelola" warna={WARNA.kuning} /></div>
            <div className="rounded-3xl bg-[#FFFDF7] border border-[#5B3A29]/10 shadow-sm"><KartuIkon mood="tertawa" judul={`${st.tugas} tugas`} isi="tercatat" warna={WARNA.biru} /></div>
            <div className="rounded-3xl bg-[#FFFDF7] border border-[#5B3A29]/10 shadow-sm"><KartuIkon mood="beres" judul={`${st.persen_selesai}%`} isi="tugas selesai" warna={WARNA.kuning} /></div>
            <div className="rounded-3xl bg-[#FFFDF7] border border-[#5B3A29]/10 shadow-sm"><KartuIkon mood="ketua" judul={`${st.seksi} seksi`} isi="aktif" warna={WARNA.biru} /></div>
          </div>
        )}
      </section>

      {/* Kabar terbaru yang ditandai tampil di beranda */}
      {data && data.kabar.length > 0 && (
        <section className="max-w-6xl mx-auto px-5 py-6">
          <Judul>Kabar terbaru</Judul>
          <ul className="grid gap-4 md:grid-cols-2">
            {data.kabar.slice(0, 6).map((k) => (
              <li key={k.id} className="kartu-infografis p-5 space-y-2">
                <p className="text-sm text-[#5B3A29] whitespace-pre-wrap">{k.isi}</p>
                <p className="text-[11px] text-[#7A5C48]">{k.acara ? `${k.acara} · ` : ""}{k.seksi}{k.waktu ? ` · ${k.waktu.slice(0, 10)}` : ""}</p>
                {k.lampiran && k.lampiran.length > 0 && <LampiranView items={k.lampiran} />}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Cara kerja: garis waktu */}
      <section className="max-w-6xl mx-auto px-5 py-6">
        <Judul>Cara kerjanya</Judul>
        <div className="relative grid md:grid-cols-4 gap-4 pt-4">
          <div className="hidden md:block absolute left-8 right-8 top-14 h-1.5 rounded bg-[#A9D8D4]" aria-hidden="true" />
          {[
            { mood: "ajak" as const, judul: "1. Daftar", isi: "Buat akun dengan nama dan username." },
            { mood: "semangat" as const, judul: "2. Buat atau gabung", isi: "Ketua membuat acara, anggota masuk dengan password." },
            { mood: "terima" as const, judul: "3. Bagi tugas", isi: "Tugas dibagikan dan penerimanya menjawab." },
            { mood: "beres" as const, judul: "4. Selesai", isi: "Laporan PDF dan catatan keputusan tersimpan." },
          ].map((k) => (
            <div key={k.judul} className="relative bg-[#FFFDF7] rounded-3xl border border-[#5B3A29]/10 shadow-sm">
              <KartuIkon mood={k.mood} judul={k.judul} isi={k.isi} warna="#FFD36E" />
            </div>
          ))}
        </div>
      </section>

      {/* Sapaan Capy */}
      <section className="max-w-6xl mx-auto px-5 py-10">
        <Balon mood="tanya">
          Aku bisa membantu membaca data acara yang kamu ikuti, membuka halaman, dan menyiapkan perubahan.
          Perubahan baru terjadi setelah kamu menekan <strong>Jalankan</strong>.
        </Balon>
      </section>

      {/* Ajakan */}
      <section className="max-w-6xl mx-auto px-5 pb-16">
        <div className="rounded-[2rem] bg-[#5B3A29] text-[#FFF6E3] p-8 md:p-12 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <h2 className="font-display text-2xl md:text-3xl font-bold">Siap membagi tugas acara?</h2>
            <p className="text-sm md:text-base opacity-90 mt-2">Daftar akun, lalu buat acara atau gabung dengan password dari panitia.</p>
          </div>
          <div className="flex items-center gap-4">
            <Capy mood="semangat" size={96} />
            <Link href="/daftar" className="px-6 py-3 rounded-full bg-[#FFD36E] text-[#5B3A29] font-bold text-sm hover:opacity-90">Mulai sekarang</Link>
          </div>
        </div>
      </section>

      <footer className="text-center pb-10 space-y-3">
        <Capy mood="wow" size={72} className="mx-auto" />
        <p className="font-display text-lg font-bold">Terima kasih sudah mampir!</p>
        <Credit />
      </footer>
    </main>
  );
}
