"use client";

import DaftarForm from "../components/DaftarForm";
import Capy from "../components/Capy";
import { Balon } from "../components/Infografis";

export default function DaftarPage() {
  return (
    <main className="min-h-screen bg-[#FFF6E3] text-[#5B3A29] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-5xl grid md:grid-cols-2 gap-8 items-center">
        <section className="bg-[#FFD36E] rounded-[2rem] p-8 flex flex-col items-center gap-6 text-center">
          <Capy mood="ajak" size={220} />
          <Balon mood="semangat">Selamat datang! Isi nama dan username, lalu kamu siap membagi tugas acara.</Balon>
        </section>
        <div className="w-full max-w-md mx-auto"><DaftarForm /></div>
      </div>
    </main>
  );
}
