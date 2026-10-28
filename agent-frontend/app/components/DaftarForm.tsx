"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { daftarAkun } from "../lib/api";
import Capy from "./Capy";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-400";

// Daftar akun user: nama, username, password. Acara dan peran dipilih setelah masuk, di dashboard.
export default function DaftarForm() {
  const [nama, setNama] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [konfirmasi, setKonfirmasi] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sukses, setSukses] = useState("");
  const [kode, setKode] = useState("");
  const [disalin, setDisalin] = useState(false);

  const siap = !!nama && !!username && password.length >= 8 && !!konfirmasi;

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    if (!siap) return;
    if (password !== konfirmasi) {
      setError("Konfirmasi password tidak sama.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await daftarAkun({ username: username.trim(), nama: nama.trim(), password });
      setSukses(res.pesan);
      setKode(res.kode_pemulihan);
      setPassword("");
      setKonfirmasi("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pendaftaran gagal. Coba lagi.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="capy-scope w-full rounded-3xl p-6 space-y-4 text-center bg-[#FFFDF7] border border-[#5B3A29]/10 shadow-sm rounded-3xl" style={{ color: "#5B3A29" }}>
      <div className="mx-auto w-24 h-24 flex items-center justify-center">
        <Capy mood={sukses ? "semangat" : "sapa"} size={96} />
      </div>
      <div>
        <h2 className="font-display text-2xl font-bold text-[#5B3A29]">Daftar akun</h2>
        <p className="text-sm text-slate-500 mt-1">Setelah masuk, kamu bisa membuat acara atau bergabung ke acara.</p>
      </div>

      {sukses ? (
        <div className="space-y-4">
          <p role="status" className="text-sm text-emerald-700">{sukses}</p>
          {kode && (
            <div className="rounded-2xl border-2 border-dashed border-[#E8962E] bg-[#FFF6E3] p-4 space-y-2">
              <div className="flex items-center gap-3 justify-center"><Capy mood="privasi" size={56} /><p className="text-xs font-bold text-[#5B3A29]">Kode pemulihan kamu</p></div>
              <p className="font-mono text-xl font-bold tracking-widest text-[#5B3A29]">{kode}</p>
              <p className="text-xs text-[#7A5C48]">Simpan di tempat aman. Kode ini dipakai jika lupa password dan hanya tampil sekali.</p>
              <button type="button" onClick={() => { navigator.clipboard?.writeText(kode); setDisalin(true); }}
                className="text-xs font-semibold underline text-[#9A5B00]">{disalin ? "Tersalin" : "Salin kode"}</button>
            </div>
          )}
          <Link href="/login" className="inline-block w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm">
            Ke halaman masuk
          </Link>
        </div>
      ) : (
        <form onSubmit={kirim} className="space-y-4 text-left">
          <label className="block text-xs text-slate-500 space-y-1">
            Nama lengkap
            <input className={field} value={nama} onChange={(e) => setNama(e.target.value)} autoComplete="name" required />
          </label>
          <label className="block text-xs text-slate-500 space-y-1">
            Username
            <input className={field} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </label>
          <label className="block text-xs text-slate-500 space-y-1">
            Password (minimal 8 karakter)
            <input type="password" className={field} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" minLength={8} required />
          </label>
          <label className="block text-xs text-slate-500 space-y-1">
            Ulangi password
            <input type="password" className={field} value={konfirmasi} onChange={(e) => setKonfirmasi(e.target.value)} autoComplete="new-password" required />
          </label>

          {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={busy || !siap}
            className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-indigo-400">
            {busy && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />} Daftar
          </button>
          <p className="text-center text-xs text-slate-500">
            Sudah punya akun? <Link href="/login" className="text-teal-600 underline">Masuk</Link>
          </p>
        </form>
      )}
    </div>
  );
}
