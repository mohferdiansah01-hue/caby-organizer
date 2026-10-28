"use client";

import Capy from "./Capy";

// Dialog konfirmasi sendiri, pengganti window.confirm bawaan browser.
export default function KonfirmasiDialog({ pesan, labelYa = "Ya, lanjutkan", onYa, onBatal, bahaya = false }: {
  pesan: string; labelYa?: string; onYa: () => void; onBatal: () => void; bahaya?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4" onClick={onBatal}>
      <div role="dialog" aria-modal="true" aria-labelledby="konfirmasi-judul" onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-3xl p-5 max-w-sm w-full space-y-4 shadow-xl" style={{ color: "#0f172a" }}>
        <div className="flex items-start gap-3">
          <Capy mood={bahaya ? "bahaya" : "kaget"} size={56} className="shrink-0" />
          <p id="konfirmasi-judul" className="text-sm font-semibold pt-2">{pesan}</p>
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onBatal}
            className="px-4 py-2 rounded-xl border border-[#cbd5e1] text-sm text-[#334155] focus-visible:ring-2 focus-visible:ring-teal-400">Batal</button>
          <button type="button" onClick={onYa}
            className="px-4 py-2 rounded-xl bg-red-600 text-white text-sm font-semibold focus-visible:ring-2 focus-visible:ring-teal-400">{labelYa}</button>
        </div>
      </div>
    </div>
  );
}
