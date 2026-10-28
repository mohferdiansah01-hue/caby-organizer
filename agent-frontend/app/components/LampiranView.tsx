"use client";

// Menampilkan lampiran: foto dan video langsung diputar, dokumen menjadi tautan unduh.
export type LampiranItem = { id: string; nama: string; mime: string; url: string; jenis: string };

export default function LampiranView({ items }: { items: LampiranItem[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-2">
      {items.map((l) => {
        if (l.jenis === "image") {
          return (
            <a key={l.id} href={l.url} target="_blank" rel="noopener noreferrer" className="block rounded-lg overflow-hidden border border-[#cbd5e1]">
              {/* Lampiran dari pengguna berasal dari URL dinamis, jadi tidak lewat optimasi next/image. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={l.url} alt={l.nama} className="w-full max-h-64 object-cover" loading="lazy" />
            </a>
          );
        }
        if (l.jenis === "video") {
          return (
            <video key={l.id} src={l.url} controls playsInline preload="metadata" className="w-full max-h-64 rounded-lg bg-black" aria-label={l.nama} />
          );
        }
        return (
          <a key={l.id} href={l.url} target="_blank" rel="noopener noreferrer" className="text-xs underline break-all px-3 py-2 rounded-lg border border-[#cbd5e1]">
            {l.nama}
          </a>
        );
      })}
    </div>
  );
}
