"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Capy from "../components/Capy";
import { Judul, KartuIkon, WARNA } from "../components/Infografis";
import KonfirmasiDialog from "../components/KonfirmasiDialog";
import { AdminAcara, AdminAudit, AdminPengguna, AdminRingkasan, adminAcara, adminAngkat, adminAsistenCek, adminAudit, adminPengguna, adminResetPassword, adminRingkasan, getMe } from "../lib/api";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm text-[#5B3A29] focus-visible:ring-2 focus-visible:ring-[#E8962E]";
type Tab = "ringkasan" | "pengguna" | "acara" | "log";

// Halaman admin: ringkasan, daftar akun (jadikan/cabut admin, atur ulang password), dan daftar acara.
export default function AdminPage() {
  const [izin, setIzin] = useState<"cek" | "ya" | "tidak">("cek");
  const [tab, setTab] = useState<Tab>("ringkasan");
  const [ringkas, setRingkas] = useState<AdminRingkasan | null>(null);
  const [pengguna, setPengguna] = useState<AdminPengguna[]>([]);
  const [acara, setAcara] = useState<AdminAcara[]>([]);
  const [cari, setCari] = useState("");
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const [resetUser, setResetUser] = useState<AdminPengguna | null>(null);
  const [resetPw, setResetPw] = useState("");
  const [cabut, setCabut] = useState<AdminPengguna | null>(null);
  const [audit, setAudit] = useState<AdminAudit[]>([]);
  const [asisten, setAsisten] = useState<{ ok: boolean; pesan: string; alamat?: string } | null>(null);

  useEffect(() => {
    getMe().then((m) => setIzin(m?.admin ? "ya" : "tidak")).catch(() => setIzin("tidak"));
  }, []);

  const muat = () => {
    adminRingkasan().then((r) => { setRingkas(r); setError(""); }).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat"));
    adminPengguna(cari).then(setPengguna).catch(() => undefined);
    adminAcara().then(setAcara).catch(() => undefined);
    adminAudit().then(setAudit).catch(() => undefined);
  };
  useEffect(() => { if (izin === "ya") muat(); }, [izin]); // eslint-disable-line react-hooks/exhaustive-deps

  if (izin === "cek") return <main className="p-10 text-center text-[#5B3A29]">Memeriksa akses…</main>;
  if (izin === "tidak")
    return (
      <main className="mx-auto max-w-md p-10 text-center space-y-4 text-[#5B3A29]">
        <Capy mood="privasi" size={140} className="mx-auto" />
        <h1 className="font-display text-2xl font-bold">Khusus admin</h1>
        <p className="text-sm">Halaman ini hanya bisa dibuka oleh akun admin.</p>
        <Link href="/dashboard" className="inline-block rounded-full bg-[#5B3A29] px-5 py-2.5 text-sm font-bold text-[#FFF6E3]">Ke dashboard</Link>
      </main>
    );

  const tabBtn = (t: Tab, label: string) => (
    <button type="button" onClick={() => setTab(t)} aria-pressed={tab === t}
      className={`rounded-full px-4 py-2 text-sm font-semibold border ${tab === t ? "bg-[#FFD36E] border-transparent text-[#5B3A29]" : "border-[#94a3b8] text-[#5B3A29]"}`}>{label}</button>
  );

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 pb-28 pt-6 md:py-10 text-[#5B3A29]">
      <header className="grid items-center gap-4 rounded-[2rem] bg-[#FFD36E] p-6 md:grid-cols-[1fr_auto] md:p-8">
        <div>
          <p className="text-xs font-bold tracking-wide text-[#5B3A29]/80">ADMIN</p>
          <h1 className="font-display mt-1 text-3xl font-bold md:text-4xl">Pusat admin</h1>
          <p className="mt-2 text-sm">Pantau akun, acara, dan pemakaian Capy. Perubahan hanya dilakukan oleh admin.</p>
        </div>
        <Capy mood="ketua" size={110} />
      </header>

      <div className="flex flex-wrap gap-2">{tabBtn("ringkasan", "Ringkasan")}{tabBtn("pengguna", "Pengguna")}{tabBtn("acara", "Acara")}{tabBtn("log", "Log aktivitas")}</div>
      {info && <p role="status" className="text-sm text-emerald-700">{info}</p>}
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

      {tab === "ringkasan" && (
        <>
          <Judul>Angka utama</Judul>
          <section className="kartu-infografis space-y-2 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold">Koneksi Capy ke Ollama</p>
              <button type="button" onClick={() => adminAsistenCek().then(setAsisten).catch((e) => setAsisten({ ok: false, pesan: e instanceof Error ? e.message : "Gagal memeriksa" }))}
                className="rounded-full bg-[#5B3A29] px-4 py-2 text-xs font-bold text-[#FFF6E3]">Cek koneksi</button>
            </div>
            {asisten && (
              <p role="status" className={`text-sm ${asisten.ok ? "text-emerald-700" : "text-red-700"}`}>{asisten.pesan}{asisten.alamat ? ` (${asisten.alamat})` : ""}</p>
            )}
          </section>
          {!ringkas ? <p className="text-sm">Memuat…</p> : (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div className="kartu-infografis"><KartuIkon mood="ajak" judul={`${ringkas.pengguna}`} isi="akun" warna={WARNA.kuning} /></div>
              <div className="kartu-infografis"><KartuIkon mood="ketua" judul={`${ringkas.admin}`} isi="admin" warna={WARNA.biru} /></div>
              <div className="kartu-infografis"><KartuIkon mood="tertawa" judul={`${ringkas.acara_terbuka}/${ringkas.acara}`} isi="acara terbuka" warna={WARNA.kuning} /></div>
              <div className="kartu-infografis"><KartuIkon mood="beres" judul={`${ringkas.tugas_selesai}/${ringkas.tugas}`} isi="tugas selesai" warna={WARNA.biru} /></div>
              <div className="kartu-infografis md:col-span-2"><KartuIkon mood="tanya" judul={`${ringkas.tanya_capy_hari_ini} / ${ringkas.kuota_capy_harian}`} isi="pertanyaan Capy hari ini (dihitung per acara)" warna={WARNA.kuning} /></div>
            </div>
          )}
        </>
      )}

      {tab === "pengguna" && (
        <section className="kartu-infografis space-y-4 p-5">
          <div className="flex flex-wrap gap-2">
            <input className={field} placeholder="Cari username atau nama" value={cari} onChange={(e) => setCari(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") muat(); }} />
            <button type="button" onClick={muat} className="rounded-xl bg-[#5B3A29] px-4 text-sm font-bold text-[#FFF6E3]">Cari</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-[#5B3A29]/15 text-xs text-[#7A5C48]"><th className="py-2">Username</th><th className="hidden sm:table-cell">Nama</th><th className="hidden sm:table-cell">Acara</th><th>Peran</th><th className="text-right">Aksi</th></tr></thead>
              <tbody>
                {pengguna.map((p) => (
                  <tr key={p.id} className="border-b border-[#5B3A29]/10">
                    <td className="py-2 font-mono text-xs">{p.username}</td>
                    <td className="hidden sm:table-cell">{p.nama}</td>
                    <td className="hidden sm:table-cell">{p.jumlah_acara}</td>
                    <td>{p.admin ? <span className="rounded-full bg-[#FFD36E] px-2 py-0.5 text-xs font-bold">Admin</span> : "Pengguna"}</td>
                    <td className="align-top">
                     <div className="flex flex-col items-end gap-1 text-right sm:flex-row sm:flex-wrap sm:justify-end sm:gap-x-3">
                      {p.admin
                        ? <button type="button" onClick={() => setCabut(p)} className="text-xs underline text-red-700">Cabut admin</button>
                        : <button type="button" onClick={async () => { try { await adminAngkat(p.username, true); setInfo(`${p.username} sekarang admin.`); muat(); } catch (e) { setError(e instanceof Error ? e.message : "Gagal"); } }} className="text-xs underline text-[#9A5B00]">Jadikan admin</button>}
                      <button type="button" onClick={() => { setResetUser(p); setResetPw(""); }} className="text-xs underline">Atur ulang<span className="hidden sm:inline"> password</span></button>
                     </div>
                    </td>
                  </tr>
                ))}
                {pengguna.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-xs text-[#7A5C48]">Tidak ada akun yang cocok.</td></tr>}
              </tbody>
            </table>
          </div>
          {resetUser && (
            <div className="rounded-2xl border border-[#E8962E] bg-[#FFF6E3] p-4 space-y-2">
              <p className="text-sm font-semibold">Atur ulang password untuk {resetUser.username}</p>
              <div className="flex flex-wrap gap-2">
                <input type="password" className={field} placeholder="Password baru (minimal 8)" value={resetPw} onChange={(e) => setResetPw(e.target.value)} />
                <button type="button" disabled={resetPw.length < 8} onClick={async () => { try { const r = await adminResetPassword(resetUser.username, resetPw); setInfo(r.pesan); setResetUser(null); } catch (e) { setError(e instanceof Error ? e.message : "Gagal"); } }}
                  className="rounded-xl bg-[#5B3A29] px-4 text-sm font-bold text-[#FFF6E3] disabled:opacity-40">Simpan</button>
                <button type="button" onClick={() => setResetUser(null)} className="text-xs underline">Batal</button>
              </div>
              <p className="text-xs text-[#7A5C48]">Sampaikan password baru lewat jalur yang aman. Kode pemulihan lama akan tetap berlaku sampai pengguna memakainya.</p>
            </div>
          )}
        </section>
      )}

      {tab === "acara" && (
        <section className="kartu-infografis space-y-3 p-5">
          {acara.length === 0 && <p className="text-sm text-[#7A5C48]">Belum ada acara.</p>}
          <ul className="space-y-2">
            {acara.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-[#5B3A29]/10 bg-white p-3">
                <div>
                  <p className="font-semibold">{a.nama}</p>
                  <p className="text-xs text-[#7A5C48]">{a.tanggal ?? "tanggal belum diisi"}{a.lokasi ? ` · ${a.lokasi}` : ""} · Ketua: {a.pembuat ?? "belum ada"}</p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span>{a.peserta} peserta</span><span>{a.tugas} tugas</span>
                  <span className={`rounded-full px-2 py-0.5 font-bold ${a.tertutup ? "bg-[#5B3A29] text-[#FFF6E3]" : "bg-[#A9D8D4] text-[#1e293b]"}`}>{a.tertutup ? "Ditutup" : "Terbuka"}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "log" && (
        <section className="kartu-infografis space-y-3 p-5">
          <p className="text-xs text-[#7A5C48]">Aktivitas tulis terbaru (hanya dibaca). Dicatat otomatis oleh server.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead><tr className="border-b border-[#5B3A29]/15 text-[#7A5C48]"><th className="py-2">Waktu</th><th>Aktor</th><th>Peran</th><th>Aksi</th><th>Rute</th></tr></thead>
              <tbody>
                {audit.map((a, i) => (
                  <tr key={i} className="border-b border-[#5B3A29]/10">
                    <td className="py-1.5 whitespace-nowrap">{a.waktu ? a.waktu.slice(0, 16).replace("T", " ") : "-"}</td>
                    <td>{a.aktor}</td><td>{a.peran}</td><td className="font-mono">{a.aksi}</td><td className="font-mono break-all">{a.rute}</td>
                  </tr>
                ))}
                {audit.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-[#7A5C48]">Belum ada aktivitas.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {cabut && (
        <KonfirmasiDialog bahaya pesan={`Cabut status admin dari ${cabut.username}?`} labelYa="Ya, cabut"
          onYa={async () => { const p = cabut; setCabut(null); try { await adminAngkat(p.username, false); setInfo(`${p.username} bukan admin lagi.`); muat(); } catch (e) { setError(e instanceof Error ? e.message : "Gagal"); } }}
          onBatal={() => setCabut(null)} />
      )}
    </main>
  );
}
