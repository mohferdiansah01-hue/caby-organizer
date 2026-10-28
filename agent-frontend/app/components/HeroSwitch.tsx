"use client";

import Link from "next/link";
import Image from "next/image";
import { Compass, CalendarDays, Megaphone, Utensils, Package } from "lucide-react";
import { Beranda } from "../lib/api";

// Empat model hero beranda. Pilihan dan teksnya diatur Ketua lewat halaman Acara.
export default function HeroSwitch({ data }: { data: Beranda }) {
  const { pengaturan: p, statistik: s } = data;
  const stats = (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-10">
      {[
        { n: s.acara, l: "Acara dikelola" },
        { n: s.tugas, l: "Tugas tercatat" },
        { n: `${s.persen_selesai}%`, l: "Tugas selesai" },
        { n: s.seksi, l: "Seksi aktif" },
      ].map((x) => (
        <div key={x.l} className="kartu-infografis px-4 py-3 text-center">
          <p className="font-display text-2xl font-bold text-slate-100">{x.n}</p>
          <p className="text-xs text-slate-400">{x.l}</p>
        </div>
      ))}
    </div>
  );
  const cta = (
    <div className="flex flex-wrap gap-3 mt-7">
      <Link href="/events" className="px-5 py-2.5 rounded-full bg-teal-500 text-slate-950 hover:bg-teal-400 font-semibold text-sm hover:bg-teal-400 focus-visible:ring-2 focus-visible:ring-teal-500">
        {p.tombol}
      </Link>
    </div>
  );

  if (p.hero === "b") {
    return (
      <section className="bg-app text-slate-100">
        <div className="max-w-6xl mx-auto px-5 py-14 grid md:grid-cols-2 gap-8 items-center">
          <div>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold leading-tight tracking-tight">{p.judul}</h1>
            <p className="mt-4 text-lg opacity-80 max-w-lg">{p.subjudul}</p>
            {cta}
          </div>
          <Image src="/stickers/cheer.webp" alt="" aria-hidden="true" width={227} height={227} sizes="(min-width: 768px) 448px, 90vw" className="w-full max-w-md mx-auto h-auto object-contain" />
        </div>
        <div className="max-w-6xl mx-auto px-5 pb-10">{stats}</div>
      </section>
    );
  }

  if (p.hero === "c") {
    const crew = [
      { Ikon: Compass, nama: "Ketua", ket: "Memegang arah acara dan jadwal" },
      { Ikon: CalendarDays, nama: "Acara", ket: "Narasumber, materi, dan rundown" },
      { Ikon: Megaphone, nama: "Humas", ket: "Poster, pendaftaran, dan sponsor" },
      { Ikon: Utensils, nama: "Konsumsi", ket: "Vendor dan jumlah porsi" },
      { Ikon: Package, nama: "Perlengkapan", ket: "Tempat, perangkat, dan seminar kit" },
    ];
    return (
      <section className="bg-app text-slate-100">
        <div className="max-w-6xl mx-auto px-5 py-16 text-center">
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold leading-tight tracking-tight">{p.judul}</h1>
          <p className="mt-4 text-lg opacity-80 max-w-2xl mx-auto">{p.subjudul}</p>
          <div className="flex justify-center">{cta}</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-12">
            {crew.map((c) => (
              <div key={c.nama} className="kartu-infografis p-5 flex flex-col items-center gap-2">
                <span className="w-11 h-11 rounded-xl bg-teal-500/15 text-teal-300 flex items-center justify-center" aria-hidden="true">
                  <c.Ikon className="w-5 h-5" />
                </span>
                <p className="font-bold">{c.nama}</p>
                <p className="text-xs text-slate-400">{c.ket}</p>
              </div>
            ))}
          </div>
          <div className="max-w-4xl mx-auto">{stats}</div>
        </div>
      </section>
    );
  }

  if (p.hero === "d") {
    return (
      <section className="bg-app text-slate-100">
        <div className="max-w-6xl mx-auto px-5 py-14 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold leading-tight tracking-tight">{p.judul}</h1>
            <p className="mt-4 text-lg opacity-80 max-w-lg">{p.subjudul}</p>
            {cta}
          </div>
          <div className="relative">
            <div className="kartu-infografis p-5 shadow-2xl shadow-black/40 -rotate-1">
              <div className="flex justify-between items-center mb-3">
                <p className="font-bold">Ringkasan tugas</p>
                <p className="text-xs text-slate-500">{s.acara} acara</p>
              </div>
              <div className="space-y-2">
                {[
                  { w: s.persen_selesai, label: "Selesai", color: "bg-teal-500" },
                  { w: Math.max(10, 100 - s.persen_selesai), label: "Berjalan", color: "bg-teal-400" },
                ].map((r) => (
                  <div key={r.label} className="flex items-center gap-3 text-sm">
                    <span className="w-20 text-slate-400">{r.label}</span>
                    <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div className={`h-full ${r.color}`} style={{ width: `${r.w}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 h-12 rounded-xl bg-slate-950/60 overflow-hidden relative">
                <svg viewBox="0 0 136 46" preserveAspectRatio="none" className="absolute left-0 top-0 h-full w-[200%] anim-ekg-slow">
                  <path d="M0 23 L14 23 L18 15 L22 31 L26 8 L30 37 L34 23 L48 23 L52 15 L56 31 L60 8 L64 37 L68 23 L82 23 L86 15 L90 31 L94 8 L98 37 L102 23 L116 23 L120 15 L124 31 L128 8 L132 37 L136 23 L150 23 L154 15 L158 31 L162 8 L166 37 L170 23 L184 23 L188 15 L192 31 L196 8 L200 37 L204 23 L218 23 L222 15 L226 31 L230 8 L234 37 L238 23 L252 23" fill="none" stroke="#E25B45" strokeWidth={2.2} strokeLinejoin="round" />
                </svg>
              </div>
            </div>
            <Image src="/stickers/stressed_laptop.webp" alt="" aria-hidden="true" width={229} height={231} className="absolute -right-4 -bottom-8 w-28 h-auto anim-bob" />
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-5 pb-10">{stats}</div>
      </section>
    );
  }

  // model a (default): stiker melayang
  return (
    <section className="bg-app text-slate-100">
      <div className="max-w-6xl mx-auto px-5 py-16 grid md:grid-cols-2 gap-10 items-center">
        <div>
          <p className="inline-block text-xs font-extrabold tracking-widest uppercase kartu-infografis/60 rounded-full px-3 py-1.5 mb-5">Aplikasi kepanitiaan</p>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold leading-tight tracking-tight">{p.judul}</h1>
          <p className="mt-4 text-lg opacity-80 max-w-lg">{p.subjudul}</p>
          {cta}
        </div>
        <div className="relative h-80 flex items-center justify-center">
          <Image src="/stickers/cheer.webp" alt="" aria-hidden="true" width={227} height={227} sizes="(min-width: 768px) 256px, 60vw" className="w-56 h-auto anim-bob" />
        </div>
      </div>
      <div className="max-w-6xl mx-auto px-5 pb-10">{stats}</div>
    </section>
  );
}
