"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import Capy from "../components/Capy";
import { lupaPassword } from "../lib/api";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2.5 text-sm text-[#5B3A29] focus-visible:ring-2 focus-visible:ring-[#E8962E]";

export default function LupaPasswordPage() {
  const [username, setUsername] = useState("");
  const [kode, setKode] = useState("");
  const [baru, setBaru] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [kodeBaru, setKodeBaru] = useState("");

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const r = await lupaPassword(username.trim(), kode.trim(), baru);
      setKodeBaru(r.kode_pemulihan);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengatur ulang password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#FFF6E3] text-[#5B3A29] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md kartu-infografis p-6 space-y-4">
        <div className="flex items-center gap-3"><Capy mood="privasi" size={72} /><h1 className="font-display text-2xl font-bold">Lupa password</h1></div>
        {kodeBaru ? (
          <div className="space-y-3">
            <p className="text-sm">Password sudah diganti. Kode pemulihan lama tidak berlaku lagi. Ini kode baru, hanya tampil sekali:</p>
            <p className="font-mono text-xl font-bold tracking-widest">{kodeBaru}</p>
            <Link href="/login" className="inline-block px-5 py-2.5 rounded-full bg-[#5B3A29] text-[#FFF6E3] font-bold text-sm">Ke halaman masuk</Link>
          </div>
        ) : (
          <form onSubmit={kirim} className="space-y-3">
            <p className="text-xs text-[#7A5C48]">Masukkan username dan kode pemulihan yang kamu simpan saat mendaftar. Tidak ada email atau SMS yang dikirim.</p>
            <label className="block text-xs space-y-1">Username<input className={field} value={username} onChange={(e) => setUsername(e.target.value)} required /></label>
            <label className="block text-xs space-y-1">Kode pemulihan<input className={field} placeholder="XXXX-XXXX-XXXX" value={kode} onChange={(e) => setKode(e.target.value)} required /></label>
            <label className="block text-xs space-y-1">Password baru (minimal 8)<input type="password" className={field} value={baru} onChange={(e) => setBaru(e.target.value)} minLength={8} required /></label>
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
            <button type="submit" disabled={busy} className="w-full py-2.5 rounded-xl bg-[#5B3A29] text-[#FFF6E3] font-bold text-sm disabled:opacity-40">Atur password baru</button>
            <p className="text-center text-xs"><Link href="/login" className="underline text-[#9A5B00]">Kembali ke masuk</Link></p>
          </form>
        )}
      </div>
    </main>
  );
}
