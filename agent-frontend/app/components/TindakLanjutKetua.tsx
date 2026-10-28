"use client";

import { useEffect, useState } from "react";
import CabyState from "./CabyState";
import Capy from "./Capy";
import { ItemTindakLanjut, PesertaAcara, TindakLanjut, bagikanTugas, fetchPesertaAcara, fetchTindakLanjut } from "../lib/api";

// Yang perlu ditindaklanjuti Ketua hari ini: tugas belum dibagi, belum dijawab lebih dari 24 jam,
// ditolak penerimanya, dan terlambat. Tugas yang belum dibagi atau ditolak bisa langsung dibagikan ulang.
export default function TindakLanjutKetua({ eventId }: { eventId: string }) {
  const [data, setData] = useState<TindakLanjut | null>(null);
  const [peserta, setPeserta] = useState<PesertaAcara[]>([]);
  const [pilih, setPilih] = useState<Record<string, string>>({});
  const [error, setError] = useState("");

  const muat = () => {
    fetchTindakLanjut(eventId).then(setData).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat"));
    fetchPesertaAcara(eventId).then(setPeserta).catch(() => setPeserta([]));
  };
  useEffect(() => { muat(); }, [eventId]); // eslint-disable-line react-hooks/exhaustive-deps

  const bagi = async (item: ItemTindakLanjut) => {
    const orang = pilih[item.id];
    if (!orang) return;
    setError("");
    try { await bagikanTugas(item.id, orang); muat(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal membagikan tugas"); }
  };

  if (!data) return null;
  const total = data.belum_dibagi.length + data.belum_konfirmasi.length + data.ditolak.length + data.terlambat.length;

  const baris = (item: ItemTindakLanjut, keterangan: string, bisaBagi: boolean) => (
    <li key={item.id + keterangan} className="flex flex-wrap items-center justify-between gap-2 border border-[#e2e8f0] rounded-xl px-3 py-2">
      <div className="text-sm">
        <p className="font-semibold text-[#0f172a]">{item.judul}</p>
        <p className="text-xs text-[#64748b]">{keterangan}{item.seksi ? ` · seksi ${item.seksi}` : ""}{item.deadline_iso ? ` · tenggat ${item.deadline_iso.slice(0, 10)}` : ""}</p>
      </div>
      {bisaBagi && (
        <div className="flex gap-2 items-center">
          <select className="border border-[#cbd5e1] rounded-lg px-2 py-1 text-xs" value={pilih[item.id] || ""}
            onChange={(e) => setPilih({ ...pilih, [item.id]: e.target.value })}>
            <option value="">Pilih peserta</option>
            {peserta.map((p) => <option key={p.orang_id} value={p.orang_id}>{p.nama}</option>)}
          </select>
          <button type="button" disabled={!pilih[item.id]} onClick={() => bagi(item)}
            className="px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-600 text-white disabled:opacity-40">Bagikan</button>
        </div>
      )}
    </li>
  );

  return (
    <section className="kartu-infografis p-5 space-y-4">
      <div className="flex items-center gap-3"><Capy mood={total > 0 ? "ketua_kaget" : "beres"} size={56} /><h2 className="font-semibold text-[#0f172a]">Perlu ditindaklanjuti ({total})</h2></div>
      {total === 0 && <CabyState kind="beres" judul="Semua sudah beres" isi="Tidak ada tugas yang perlu kamu tindak lanjuti sekarang." />}

      {data.belum_dibagi.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-[#475569]">Belum dibagi ({data.belum_dibagi.length})</p>
          <ul className="space-y-2">{data.belum_dibagi.map((i) => baris(i, "Belum ada penerima", true))}</ul>
        </div>
      )}
      {data.ditolak.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-[#475569]">Ditolak penerimanya ({data.ditolak.length})</p>
          <ul className="space-y-2">{data.ditolak.map((i) => baris(i, `Ditolak ${i.penerima ?? ""}: ${i.alasan ?? "tanpa alasan"}`, true))}</ul>
        </div>
      )}
      {data.belum_konfirmasi.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-[#475569]">Belum dijawab lebih dari 24 jam ({data.belum_konfirmasi.length})</p>
          <ul className="space-y-2">{data.belum_konfirmasi.map((i) => baris(i, `Menunggu jawaban ${i.penerima ?? ""}`, false))}</ul>
        </div>
      )}
      {data.terlambat.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-red-700">Lewat tenggat ({data.terlambat.length})</p>
          <ul className="space-y-2">{data.terlambat.map((i) => baris(i, `Penerima: ${i.penerima ?? "belum ada"}`, false))}</ul>
        </div>
      )}
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    </section>
  );
}
