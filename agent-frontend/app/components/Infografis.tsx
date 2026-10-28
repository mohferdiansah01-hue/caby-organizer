import { useState, type ReactNode } from "react";
import Capy, { Ekspresi } from "./Capy";

// Palet dari mockup infografis CV: kuning, oranye, cokelat tua, biru muda.
export const WARNA = { kuning: "#FFD36E", oranye: "#E8962E", coklat: "#5B3A29", biru: "#A9D8D4", krem: "#FFFDF7", krem2: "#FFF6E3" };
const BADGE = ["#F6A623", "#2BA5A0", "#E0607E", "#9B7BD6", "#5B8DEF", "#7BC47F"];
export const warnaSeksi = (teks: string) => BADGE[Math.abs([...teks].reduce((a, c) => a + c.charCodeAt(0), 0)) % BADGE.length];

// Judul bagian dengan garis di kiri dan kanan, seperti "Abilities" pada mockup.
export function Judul({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 my-4">
      <span className="h-0.5 w-8 rounded bg-[#E8962E]" aria-hidden="true" />
      <h2 className="font-display text-lg md:text-xl font-bold text-[#E8962E]">{children}</h2>
      <span className="h-0.5 flex-1 rounded bg-[#E8962E]/30" aria-hidden="true" />
    </div>
  );
}

// Balon ucapan dengan ekor, untuk sapaan Capy.
export function Balon({ children, mood, sisi = "kiri" }: { children: ReactNode; mood?: Ekspresi; sisi?: "kiri" | "kanan" }) {
  return (
    <div className={`flex items-start gap-4 ${sisi === "kanan" ? "flex-row-reverse" : ""}`}>
      {mood && <Capy mood={mood} size={110} className="shrink-0" />}
      <div className="relative bg-[#FFFDF7] border-2 border-[#5B3A29]/15 rounded-3xl px-5 py-4 text-[#5B3A29] text-sm md:text-base leading-relaxed shadow-sm max-w-xl">
        {children}
      </div>
    </div>
  );
}

// Kartu ikon: lingkaran berisi Capy dengan judul dan keterangan.
export function KartuIkon({ mood, judul, isi, warna = "#FFD36E" }: { mood: Ekspresi; judul: string; isi?: string; warna?: string }) {
  return (
    <div className="flex flex-col items-center text-center gap-2 p-4">
      <div className="w-24 h-24 rounded-full flex items-center justify-center shadow-inner" style={{ background: warna }}>
        <Capy mood={mood} size={72} />
      </div>
      <p className="font-display font-bold text-[#5B3A29] text-sm">{judul}</p>
      {isi && <p className="text-xs text-[#7A5C48]">{isi}</p>}
    </div>
  );
}

// Batang keterampilan: label berwarna dan batang progres, seperti "Software skills" pada mockup.
export function BatangSkill({ label, persen, warna }: { label: string; persen: number; warna?: string }) {
  const c = warna ?? warnaSeksi(label);
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 shrink-0 rounded-lg px-2 py-1 text-center text-xs font-bold text-white truncate" style={{ background: c }}>{label}</span>
      <div className="flex-1 h-4 rounded-full bg-[#A9D8D4]/40 overflow-hidden" role="progressbar" aria-valuenow={persen} aria-valuemin={0} aria-valuemax={100} aria-label={`${label} ${persen}%`}>
        <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, persen))}%`, background: c }} />
      </div>
      <span className="w-10 text-right text-xs font-semibold text-[#5B3A29]">{persen}%</span>
    </div>
  );
}

// Garis waktu tenggat: setiap tugas jadi titik dengan Capy yang menunjukkan keadaannya.
export function GarisWaktuTugas({ tugas }: { tugas: { id: string; judul: string; deadline_iso: string | null; status: string }[] }) {
  const [sekarang] = useState(() => Date.now());
  const items = tugas.filter((t) => t.deadline_iso).sort((a, b) => (a.deadline_iso! < b.deadline_iso! ? -1 : 1)).slice(0, 8);
  if (items.length === 0) return <div className="rounded-3xl bg-[#FFFDF7] border border-[#5B3A29]/10"><div className="flex flex-col items-center py-6 text-center"><Capy mood="kosong" size={88} /><p className="text-sm font-bold text-[#5B3A29]">Belum ada tenggat</p><p className="text-xs text-[#7A5C48]">Tambahkan tugas dengan tenggat untuk melihatnya di sini.</p></div></div>;
  return (
    <div className="rounded-3xl bg-[#FFFDF7] border border-[#5B3A29]/10 p-4 overflow-x-auto">
      <div className="relative flex gap-4 min-w-max px-2 pt-4 pb-2">
        <div className="absolute left-6 right-6 top-[3.25rem] h-1.5 rounded bg-[#A9D8D4]" aria-hidden="true" />
        {items.map((t) => {
          const d = new Date(t.deadline_iso!).getTime();
          const selesai = t.status === "done";
          const lewat = !selesai && d < sekarang;
          const dekat = !selesai && !lewat && d - sekarang < 3 * 24 * 3600 * 1000;
          const mood: Ekspresi = selesai ? "beres" : lewat ? "lelah" : dekat ? "semangat_kejar" : "tertawa";
          const warna = selesai ? "#7BC47F" : lewat ? "#E0607E" : dekat ? "#F6A623" : "#2BA5A0";
          return (
            <div key={t.id} className="relative z-10 flex w-36 flex-col items-center text-center">
              <Capy mood={mood} size={64} />
              <span className="my-2 h-4 w-4 rounded-full ring-4 ring-[#FFFDF7]" style={{ background: warna }} aria-hidden="true" />
              <p className="line-clamp-2 text-xs font-bold text-[#5B3A29]">{t.judul}</p>
              <p className="text-[11px] text-[#7A5C48]">{t.deadline_iso!.slice(0, 10)}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
