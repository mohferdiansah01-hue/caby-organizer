"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TanyaCapy from "../components/TanyaCapy";
import Capy from "../components/Capy";
import TugasMenungguDashboard from "../components/TugasMenungguDashboard";
import { Balon } from "../components/Infografis";
import CabyState from "../components/CabyState";
import { AuthEvent, AcaraSaya, AcaraTanpaKetua, buatAcara, fetchAcaraSaya, fetchAcaraTanpaKetua, fetchAuthEvents, gabungAcara, klaimAcara, masukAcara, getMe, adminAngkat, adminResetPassword, pengingatSaya, PengingatItem } from "../lib/api";

const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-400";
const LABEL_PERAN: Record<string, string> = { ketua: "Ketua", koordinator: "Koordinator", anggota: "Anggota", pj: "PJ", wakil_ketua: "Wakil Ketua" };

// Dashboard user: acara yang diikuti, buat acara (otomatis jadi Ketua), dan gabung acara dengan password.
export default function DashboardPage() {
  const router = useRouter();
  const [saya, setSaya] = useState<AcaraSaya[]>([]);
  const [terbuka, setTerbuka] = useState<AuthEvent[]>([]);
  const [muatAcaraTerbuka, setMuatAcaraTerbuka] = useState(true);
  const [error, setError] = useState("");

  // buat acara
  const [nama, setNama] = useState("");
  const [tanggal, setTanggal] = useState("");
  const [pwAcara, setPwAcara] = useState("");
  const [template, setTemplate] = useState("kosong");
  const [admin, setAdmin] = useState(false);
  const [tanpaKetua, setTanpaKetua] = useState<AcaraTanpaKetua[]>([]);
  const [adminUser, setAdminUser] = useState("");
  const [adminPw, setAdminPw] = useState("");
  const [adminInfo, setAdminInfo] = useState("");
  const [pengingat, setPengingat] = useState<PengingatItem[]>([]);
  const [busyBuat, setBusyBuat] = useState(false);

  // gabung acara
  const [pilihId, setPilihId] = useState("");
  const [peran, setPeran] = useState<"anggota" | "pj">("anggota");
  const [pwGabung, setPwGabung] = useState("");
  const [busyGabung, setBusyGabung] = useState(false);
  const [pesan, setPesan] = useState("");

  const muat = () => {
    fetchAcaraSaya().then(setSaya).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat acara"));
    setMuatAcaraTerbuka(true);
    fetchAuthEvents().then(setTerbuka).catch(() => setTerbuka([])).finally(() => setMuatAcaraTerbuka(false));
  };
  useEffect(() => {
    muat();
    pengingatSaya().then(setPengingat).catch(() => setPengingat([]));
    getMe().then((m) => {
      if (m?.admin) {
        setAdmin(true);
        fetchAcaraTanpaKetua().then(setTanpaKetua).catch(() => setTanpaKetua([]));
      }
    });
  }, []);

  const sudahIkut = new Set(saya.map((a) => a.id));
  const bisaGabung = terbuka.filter((e) => !sudahIkut.has(e.id));

  const masuk = async (id: string) => {
    setError("");
    try {
      await masukAcara(id);
      router.push(`/events/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal masuk acara");
    }
  };

  const buat = async (e: FormEvent) => {
    e.preventDefault();
    setBusyBuat(true);
    setError("");
    setPesan("");
    try {
      const res = await buatAcara({ nama: nama.trim(), tanggal, password: pwAcara, template });
      setNama(""); setTanggal(""); setPwAcara("");
      await masukAcara(res.id);
      router.push(`/events/${res.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal membuat acara");
    } finally {
      setBusyBuat(false);
    }
  };

  const gabung = async (e: FormEvent) => {
    e.preventDefault();
    if (!pilihId) return;
    setBusyGabung(true);
    setError("");
    setPesan("");
    try {
      await gabungAcara(pilihId, { peran, password: pwGabung });
      setPesan("Kamu sudah bergabung. Tekan Masuk acara untuk membukanya.");
      setPwGabung("");
      setPilihId("");
      muat();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal bergabung");
    } finally {
      setBusyGabung(false);
    }
  };

  return (
    <main className="capy-theme max-w-4xl mx-auto px-4 md:px-6 pt-6 pb-28 md:py-10 space-y-8">
      <Balon mood={admin || saya.some((a) => a.peran === "ketua") ? "ketua" : "sapa"}>
        <strong className="font-display text-xl">Hai! Mau kerjakan apa hari ini?</strong>
        <span className="block mt-1 text-[#7A5C48]">Lihat acara yang kamu ikuti, buat acara baru, atau gabung dengan password dari panitia.</span>
        <div className="mt-3 flex flex-wrap gap-2">
          <a href="#buat-acara" className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-teal-400">Buat acara</a>
          <a href="#gabung-acara" className="rounded-xl border border-[#5B3A29]/30 px-4 py-2 text-sm font-semibold text-[#5B3A29] hover:bg-[#FFD36E]/30 focus-visible:ring-2 focus-visible:ring-teal-400">Gabung acara</a>
        </div>
      </Balon>

      {pesan && <p role="status" className="text-sm text-emerald-300">{pesan}</p>}
      {error && <p role="alert" className="text-sm text-red-300">{error}</p>}

      {admin && (
        <section className="kartu-infografis p-5 space-y-3">
          <h2 className="font-semibold">Acara lama tanpa Ketua</h2>
          {tanpaKetua.length === 0 ? (
            <p className="text-sm text-slate-400">Semua acara sudah punya Ketua.</p>
          ) : (
            <ul className="space-y-2">
              {tanpaKetua.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-2 text-sm">
                  <span>{a.nama}{a.tanggal ? ` · ${a.tanggal}` : ""}</span>
                  <button type="button" onClick={async () => { await klaimAcara(a.id); setTanpaKetua(tanpaKetua.filter((x) => x.id !== a.id)); await masukAcara(a.id); router.push(`/events/${a.id}`); }}
                    className="px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-600 text-white">Jadikan saya Ketua</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="space-y-3">
        <h2 className="font-semibold">Acara saya</h2>
        {saya.length === 0 ? (
          <div className="kartu-infografis">
            <CabyState kind="ajak" judul="Belum ada acara" isi="Buat acara baru, atau gabung dengan password dari panitia." aksi={<a href="#buat-acara" className="text-sm font-semibold text-teal-300 hover:underline">Buat acara</a>} />
          </div>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {saya.map((a) => (
              <li key={a.id} className="kartu-infografis p-4 space-y-2">
                <p className="font-semibold">{a.nama}</p>
                <p className="text-xs text-slate-400">
                  {LABEL_PERAN[a.peran] ?? a.peran}{a.seksi ? ` · ${a.seksi}` : ""}{a.tanggal ? ` · ${a.tanggal}` : ""}{a.tertutup ? " · ditutup" : ""}
                </p>
                <button type="button" onClick={() => masuk(a.id)}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-600 text-white focus-visible:ring-2 focus-visible:ring-teal-400">
                  Masuk acara
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="buat-acara" className="kartu-infografis p-5 space-y-4">
        <h2 className="font-semibold">Buat acara</h2>
        <p className="text-xs text-slate-400">Pembuat acara otomatis menjadi Ketua acara itu.</p>
        <form onSubmit={buat} className="grid gap-3 md:grid-cols-2">
          <label className="text-xs text-slate-400 space-y-1">Nama acara
            <input className={field} value={nama} onChange={(e) => setNama(e.target.value)} required />
          </label>
          <label className="text-xs text-slate-400 space-y-1">Tanggal
            <input type="date" className={field} value={tanggal} onChange={(e) => setTanggal(e.target.value)} />
          </label>
          <label className="text-xs text-slate-400 space-y-1 md:col-span-2">Mulai dari template
            <select aria-label="Mulai dari template" className={field} value={template} onChange={(e) => setTemplate(e.target.value)}>
              <option value="kosong">Kosong</option>
              <option value="pemilihan">Pemilihan / orientasi fakultas</option>
              <option value="seminar">Seminar</option>
              <option value="bakti">Bakti sosial</option>
            </select>
            <span className="text-slate-500">Template membuat tugas awal per seksi dengan tenggat mundur dari tanggal acara. Isi tanggal dulu.</span>
          </label>
          <label className="text-xs text-slate-400 space-y-1 md:col-span-2">Password pendaftaran (minimal 8 karakter, untuk anggota)
            <input type="password" className={field} value={pwAcara} onChange={(e) => setPwAcara(e.target.value)} minLength={8} required />
          </label>
          <div className="md:col-span-2">
            <button type="submit" disabled={busyBuat || !nama || pwAcara.length < 8}
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-sm disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-teal-400">
              Buat acara
            </button>
          </div>
        </form>
      </section>

      <section id="gabung-acara" className="kartu-infografis p-5 space-y-4">
        <h2 className="font-semibold">Gabung acara</h2>
        {muatAcaraTerbuka ? (
          <p role="status" className="text-sm text-slate-400">Memuat daftar acara terbuka...</p>
        ) : bisaGabung.length === 0 ? (
          <div className="flex items-center gap-3"><Capy mood="istirahat" size={56} /><p className="text-sm text-slate-400">Tidak ada acara terbuka yang bisa kamu ikuti.</p></div>
        ) : (
          <form onSubmit={gabung} className="grid gap-3 md:grid-cols-2">
            <label className="text-xs text-slate-400 space-y-1">Acara
              <select aria-label="Acara" className={field} value={pilihId} onChange={(e) => setPilihId(e.target.value)} required>
                <option value="">Pilih acara</option>
                {bisaGabung.map((ev) => <option key={ev.id} value={ev.id}>{ev.nama}{ev.tanggal ? ` · ${ev.tanggal}` : ""}</option>)}
              </select>
            </label>
            <fieldset className="text-xs text-slate-400 space-y-1">
              <legend>Peran</legend>
              <div className="flex gap-2">
                {(["anggota", "pj"] as const).map((p) => (
                  <button key={p} type="button" aria-pressed={peran === p} onClick={() => setPeran(p)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${peran === p ? "bg-indigo-600 text-white border-transparent" : "border-[#cbd5e1] text-slate-300"}`}>
                    {LABEL_PERAN[p]}
                  </button>
                ))}
              </div>
              <p className="text-slate-500">Koordinator ditetapkan Ketua acara.</p>
            </fieldset>
            <label className="text-xs text-slate-400 space-y-1 md:col-span-2">Password pendaftaran acara
              <input type="password" className={field} value={pwGabung} onChange={(e) => setPwGabung(e.target.value)} required />
            </label>
            <div className="md:col-span-2">
              <button type="submit" disabled={busyGabung || !pilihId || !pwGabung}
                className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-sm disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-teal-400">
                Gabung
              </button>
            </div>
          </form>
        )}
      </section>
      {admin && (
        <section className="kartu-infografis p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold">Kelola akun (admin)</h2>
            <button type="button" onClick={() => router.push("/admin")} className="rounded-full bg-[#5B3A29] px-4 py-2 text-xs font-bold text-[#FFF6E3]">Buka pusat admin</button>
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            <input className={field} placeholder="Username" value={adminUser} onChange={(e) => setAdminUser(e.target.value)} />
            <input className={field} type="password" placeholder="Password baru (minimal 8)" value={adminPw} onChange={(e) => setAdminPw(e.target.value)} />
            <div className="flex gap-2">
              <button type="button" disabled={!adminUser} onClick={async () => { try { const r = await adminResetPassword(adminUser.trim(), adminPw); setAdminInfo(r.pesan); setAdminPw(""); } catch (e) { setAdminInfo(e instanceof Error ? e.message : "Gagal"); } }}
                className="px-3 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold disabled:opacity-40">Atur ulang password</button>
              <button type="button" disabled={!adminUser} onClick={async () => { try { const r = await adminAngkat(adminUser.trim(), true); setAdminInfo(`${r.username} sekarang admin.`); } catch (e) { setAdminInfo(e instanceof Error ? e.message : "Gagal"); } }}
                className="px-3 py-2 rounded-xl border border-[#94a3b8] text-xs font-semibold">Jadikan admin</button>
            </div>
          </div>
          {adminInfo && <p role="status" className="text-sm text-[#5B3A29]">{adminInfo}</p>}
        </section>
      )}
      <TugasMenungguDashboard />
      {pengingat.length > 0 && (
        <section className="kartu-infografis p-5 space-y-3">
          <div className="flex items-center gap-3"><Capy mood={pengingat.some((p) => p.lewat) ? "lelah" : "semangat_kejar"} size={56} /><h2 className="font-semibold">Pengingat tenggat ({pengingat.length})</h2></div>
          <ul className="space-y-2">
            {pengingat.map((p) => (
              <li key={p.task_id} className="flex items-center justify-between gap-2 text-sm">
                <span><span className="font-semibold">{p.judul}</span> <span className="text-[#7A5C48]">· {p.acara}</span></span>
                <span className={`text-xs font-bold ${p.lewat ? "text-red-600" : "text-[#9A5B00]"}`}>{p.lewat ? "Lewat tenggat" : `Tenggat ${p.tenggat.replace("T", " ")}`}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      <TanyaCapy />  {/* percakapan umum, tanpa data acara */}
    </main>
  );
}
