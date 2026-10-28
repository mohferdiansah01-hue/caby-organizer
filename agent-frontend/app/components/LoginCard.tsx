"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Capy from "./Capy";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { loginOrang } from "../lib/api";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-400";

export type DemoAccount = { label: string; username: string; password: string };

// Login user: username dan password saja. Acara dan peran dipilih setelah masuk, di dashboard.
export default function LoginCard({ onSuccess, demoAccounts = [] }: { onSuccess?: () => void; demoAccounts?: DemoAccount[] }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const masuk = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setBusy(true);
    setError("");
    try {
      await loginOrang(username.trim(), password, "");
      // Setelah masuk, pindah ke dashboard. Navigasi penuh supaya status sesi di seluruh aplikasi ikut diperbarui.
      if (onSuccess) onSuccess();
      else router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal masuk. Periksa username dan password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={masuk} className="capy-scope rounded-3xl p-6 space-y-4 text-center bg-[#FFFDF7] border border-[#5B3A29]/10 shadow-sm rounded-3xl" style={{ color: "#5B3A29" }}>
      <div className="mx-auto w-28 h-28 flex items-center justify-center">
        <Capy mood="sapa" size={112} />
      </div>
      <div>
        <h1 className="font-display text-2xl font-bold text-[#5B3A29]">Masuk ke Caby Organizer</h1>
        <p className="text-sm text-slate-500 mt-1">Masuk dengan akunmu</p>
      </div>

      {demoAccounts.length > 0 && (
        <section aria-label="Akun demo juri" className="rounded-xl border border-[#5B3A29]/15 bg-[#FFF6E3] p-3 text-left space-y-2">
          <h2 className="text-xs font-bold uppercase text-[#5B3A29]">Akun demo untuk juri</h2>
          {demoAccounts.map((account) => (
            <div key={account.username} className="flex items-center justify-between gap-2 border-t border-[#5B3A29]/10 pt-2">
              <div className="min-w-0 text-[11px] text-[#5B3A29]">
                <p className="font-semibold">{account.label}</p>
                <p className="break-all">Username: <code>{account.username}</code></p>
                <p className="break-all">Password: <code>{account.password}</code></p>
              </div>
              <button type="button" onClick={() => { setUsername(account.username); setPassword(account.password); }}
                aria-label={`Isi akun demo ${account.label}`} className="shrink-0 rounded-lg border border-[#5B3A29]/25 px-2.5 py-1.5 text-xs font-semibold text-[#5B3A29] hover:bg-[#FFD36E]/40 focus-visible:ring-2 focus-visible:ring-[#E8962E]">
                Gunakan
              </button>
            </div>
          ))}
        </section>
      )}

      <label className="block text-left text-xs text-slate-500 space-y-1">
        Username
        <input className={field} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      </label>
      <label className="block text-left text-xs text-slate-500 space-y-1">
        Password
        <input type="password" className={field} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
      </label>

      {error && <div className="flex items-center gap-3 text-left"><Capy mood="privasi" size={56} className="shrink-0" /><p role="alert" className="text-sm text-red-600">{error}</p></div>}

      <button type="submit" disabled={busy || !username || !password}
        className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-indigo-400">
        {busy && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />} Masuk
      </button>
      <p className="text-xs text-slate-500">Belum punya akun? <Link href="/daftar" className="text-teal-600 underline">Daftar</Link> · <Link href="/lupa-password" className="text-teal-600 underline">Lupa password?</Link></p>
    </form>
  );
}
