"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PesertaAcara, aturPasswordAcara, fetchPesertaLengkap, keluarAcara, keluarkanPeserta, serahkanKetua, ubahPeserta } from "../lib/api";
import KonfirmasiDialog from "./KonfirmasiDialog";
import Capy from "./Capy";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-400";
const select = "border border-[#cbd5e1] rounded-lg px-2 py-1 text-xs text-[#0f172a] bg-white focus-visible:ring-2 focus-visible:ring-teal-400";
const PERAN_OPSI = [
  { id: "anggota", label: "Anggota" },
  { id: "pj", label: "PJ" },
  { id: "koordinator", label: "Koordinator seksi" },
  { id: "wakil_ketua", label: "Wakil Ketua" },
];

// Panel Ketua untuk satu acara: password pendaftaran, peserta (turunkan, pindahkan seksi, keluarkan), dan keluar dari acara.
// Tidak ada persetujuan: siapa pun yang punya password bisa langsung gabung.
export default function PengaturanAcaraKetua({ eventId }: { eventId: string }) {
  const router = useRouter();
  const [peserta, setPeserta] = useState<PesertaAcara[]>([]);
  const [seksiTersedia, setSeksiTersedia] = useState<string[]>([]);
  const [password, setPassword] = useState("");
  const [pesan, setPesan] = useState("");
  const [error, setError] = useState("");
  const [keluarkan, setKeluarkan] = useState<PesertaAcara | null>(null);
  const [serah, setSerah] = useState<PesertaAcara | null>(null);

  const muat = () => fetchPesertaLengkap(eventId)
    .then((d) => { setPeserta(d.peran); setSeksiTersedia(d.seksi_tersedia); })
    .catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat peserta"));
  useEffect(() => { muat(); }, [eventId]); // eslint-disable-line react-hooks/exhaustive-deps

  const simpanPassword = async (e: FormEvent) => {
    e.preventDefault();
    setError(""); setPesan("");
    try {
      await aturPasswordAcara(eventId, password);
      setPesan(password ? "Password pendaftaran diperbarui." : "Pendaftaran lewat password ditutup.");
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menyimpan password");
    }
  };

  const ubah = async (p: PesertaAcara, peran: string, seksi: string | null) => {
    setError(""); setPesan("");
    try {
      await ubahPeserta(eventId, p.id, { peran, seksi });
      setPesan(`${p.nama} diperbarui.`);
      await muat();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengubah peserta");
      await muat();
    }
  };

  const hapusPeserta = async (p: PesertaAcara) => {
    setKeluarkan(null); setError(""); setPesan("");
    try {
      await keluarkanPeserta(eventId, p.id);
      setPesan(`${p.nama} dikeluarkan dari acara.`);
      await muat();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengeluarkan peserta");
    }
  };

  return (
    <section className="kartu-infografis p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3"><Capy mood="santai" size={56} /><h2 className="font-semibold">Pengaturan acara (Ketua)</h2></div>
        <button type="button" onClick={() => keluarAcara().then(() => router.push("/dashboard"))}
          className="text-xs text-slate-400 underline">Keluar dari acara</button>
      </div>

      <form onSubmit={simpanPassword} className="flex flex-wrap gap-2 items-end">
        <label className="text-xs text-slate-400 space-y-1 flex-1 min-w-[220px]">Password pendaftaran (kosongkan untuk menutup)
          <input type="password" className={field} value={password} onChange={(e) => setPassword(e.target.value)} minLength={password ? 8 : 0} />
        </label>
        <button type="submit" className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold">Simpan</button>
      </form>

      <div className="space-y-2">
        <p className="text-xs text-slate-400">Peserta acara ({peserta.length}). Peran dan seksi bisa diubah langsung.</p>
        <ul className="space-y-2">
          {peserta.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 text-sm border border-[#5B3A29]/15 rounded-3xl px-3 py-2">
              <span className="font-medium">{p.nama}</span>
              {p.peran === "ketua" ? (
                <span className="text-xs text-slate-400">Ketua acara</span>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <select className={select} value={p.peran} onChange={(e) => {
                    const peran = e.target.value;
                    ubah(p, peran, peran === "koordinator" ? (p.seksi ?? seksiTersedia[0] ?? null) : p.seksi);
                  }}>
                    {PERAN_OPSI.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </select>
                  <select className={select} value={p.seksi ?? ""} onChange={(e) => ubah(p, p.peran, e.target.value || null)}>
                    <option value="">{p.peran === "koordinator" ? "Pilih seksi" : "Tanpa seksi"}</option>
                    {seksiTersedia.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <button type="button" onClick={() => setSerah(p)} className="text-xs text-[#9A5B00] underline">Serahkan Ketua</button>
                  <button type="button" onClick={() => setKeluarkan(p)} className="text-xs text-red-600 underline">Keluarkan</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      {pesan && <p role="status" className="text-sm text-emerald-300">{pesan}</p>}
      {error && <p role="alert" className="text-sm text-red-300">{error}</p>}

      {serah && (
        <KonfirmasiDialog
          bahaya
          pesan={`Serahkan kepemimpinan acara kepada ${serah.nama}? Kamu akan menjadi anggota dan tidak bisa mengatur acara lagi.`}
          labelYa="Ya, serahkan"
          onYa={async () => {
            const p = serah; setSerah(null);
            try { await serahkanKetua(eventId, p.orang_id); window.location.reload(); }
            catch (e) { setError(e instanceof Error ? e.message : "Gagal menyerahkan Ketua"); }
          }}
          onBatal={() => setSerah(null)}
        />
      )}
      {keluarkan && (
        <KonfirmasiDialog
          pesan={`Keluarkan ${keluarkan.nama} dari acara? Ia tidak bisa membuka acara ini lagi sampai gabung ulang dengan password.`}
          labelYa="Ya, keluarkan"
          onYa={() => hapusPeserta(keluarkan)}
          onBatal={() => setKeluarkan(null)}
        />
      )}
    </section>
  );
}
