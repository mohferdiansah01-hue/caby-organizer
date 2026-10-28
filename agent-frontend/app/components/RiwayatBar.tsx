"use client";

import { useEffect, useState } from "react";
import { riwayatBatal, riwayatStatus, riwayatUlang, StatusRiwayat } from "../lib/api";

// Batalkan dan ulangi perubahan terakhir kamu di acara ini. Yang bisa dibatalkan hanya perubahanmu sendiri.
export default function RiwayatBar({ eventId }: { eventId: string }) {
  const [status, setStatus] = useState<StatusRiwayat | null>(null);
  const [error, setError] = useState("");
  const [sibuk, setSibuk] = useState(false);

  const muat = () => riwayatStatus(eventId).then(setStatus).catch(() => setStatus(null));
  useEffect(() => { muat(); }, [eventId]); // eslint-disable-line react-hooks/exhaustive-deps

  const jalan = async (fn: (id: string) => Promise<{ label: string }>) => {
    setSibuk(true); setError("");
    try {
      await fn(eventId);
      window.dispatchEvent(new Event("caby:data-berubah"));
      await muat();
      setSibuk(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal");
      setSibuk(false);
    }
  };

  if (!status || (!status.batal && !status.ulang)) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-[#334155]" role="group" aria-label="Riwayat perubahan">
      <button type="button" disabled={!status.batal || sibuk} onClick={() => jalan(riwayatBatal)}
        title={status.batal ?? "Tidak ada yang bisa dibatalkan"}
        className="px-3 py-1.5 rounded-full border border-[#94a3b8] text-[#1e293b] disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-teal-400">
        ↶ Batalkan{status.batal ? `: ${status.batal}` : ""}
      </button>
      <button type="button" disabled={!status.ulang || sibuk} onClick={() => jalan(riwayatUlang)}
        title={status.ulang ?? "Tidak ada yang bisa diulang"}
        className="px-3 py-1.5 rounded-full border border-[#94a3b8] text-[#1e293b] disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-teal-400">
        ↷ Ulangi{status.ulang ? `: ${status.ulang}` : ""}
      </button>
      {error && <span role="alert" className="text-red-600">{error}</span>}
    </div>
  );
}
