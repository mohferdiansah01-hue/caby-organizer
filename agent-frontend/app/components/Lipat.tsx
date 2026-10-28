import type { ReactNode } from "react";

// Bagian yang bisa dilipat: judul selalu terlihat, isi dibuka saat diketuk. Membuat halaman panjang lebih ringkas di HP.
export default function Lipat({ judul, buka = false, children }: { judul: string; buka?: boolean; children: ReactNode }) {
  return (
    <details open={buka} className="kartu-infografis group p-4 md:p-5">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-display text-base font-bold text-[#5B3A29] focus-visible:ring-2 focus-visible:ring-[#E8962E] rounded-lg">
        <span>{judul}</span>
        <span aria-hidden="true" className="text-[#E8962E] transition-transform group-open:rotate-180">▾</span>
      </summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}
