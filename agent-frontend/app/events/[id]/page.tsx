"use client";

import PengaturanAcaraKetua from "../../components/PengaturanAcaraKetua";
import TindakLanjutKetua from "../../components/TindakLanjutKetua";
import TugasMenunggu from "../../components/TugasMenunggu";
import AksiKetua from "../../components/AksiKetua";
import KeputusanAcara from "../../components/KeputusanAcara";
import RiwayatBar from "../../components/RiwayatBar";
import TanyaCapy from "../../components/TanyaCapy";
import KabarAcara from "../../components/KabarAcara";
import Lipat from "../../components/Lipat";
import Capy from "../../components/Capy";
import { BatangSkill, GarisWaktuTugas, Judul, warnaSeksi } from "../../components/Infografis";
import { KirimPesan, KotakPesan } from "../../components/PesanPanel";
import { use, useEffect, useState } from "react";
import CabyState from "../../components/CabyState";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { EventDetail, Me, fetchEvent, getMe, masukAcara } from "../../lib/api";
import { kelompokTugas, labelKelompok, Kelompok, terlambat, tglPendek } from "../../lib/status";

// Detail acara: satu layar. Tab per seksi, progres per seksi, dan daftar tugas per status.
export default function DetailAcara({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [detail, setDetail] = useState<EventDetail | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [galat, setGalat] = useState("");
  const [tab, setTab] = useState("Semua");

  useEffect(() => {
    const muat = () => fetchEvent(id).then(setDetail).catch((e) => setGalat(e instanceof Error ? e.message : "Acara tidak ditemukan."));
    // Tautan langsung ke acara harus berfungsi: masuk dulu, baru ambil data dan peran. Dengan begitu komponen Ketua
    // (daftar peserta, tindak lanjut) dimuat saat sesi sudah berada di acara ini.
    masukAcara(id)
      .catch(() => undefined)
      .then(() => Promise.all([muat(), getMe().then(setMe).catch(() => setMe(null))]));
    window.addEventListener("caby:data-berubah", muat);
    return () => window.removeEventListener("caby:data-berubah", muat);
  }, [id]);

  if (galat) return <main className="capy-theme max-w-4xl mx-auto px-4 py-10"><CabyState kind="galat" judul="Acara tidak bisa dimuat" isi={galat} /></main>;
  if (!detail) return <main className="capy-theme max-w-4xl mx-auto px-4 py-10"><CabyState kind="memuat" judul="Memuat acara…" /></main>;

  const { event, seksi, tasks, ringkasan, struktur } = detail;
  const tugasTab = tab === "Semua" ? tasks : tasks.filter((t) => t.divisi === tab);
  const kelompok: Record<Kelompok, typeof tasks> = { belum: [], dikerjakan: [], selesai: [] };
  tugasTab.forEach((t) => kelompok[kelompokTugas(t)].push(t));

  return (
    <main className="capy-theme max-w-6xl mx-auto px-4 md:px-6 pt-6 pb-28 md:py-10 space-y-6">
      {me && <RiwayatBar eventId={id} />}
      <Link href="/events" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-teal-300">
        <ArrowLeft className="w-4 h-4" aria-hidden="true" /> Semua acara
      </Link>

      {(() => {
        const p = ringkasan.progress_persen;
        const mood = ringkasan.total === 0 ? "ajak" : ringkasan.overdue > 0 ? "lelah" : p >= 100 ? "bangga" : p >= 50 ? "tertawa" : "semangat_kejar";
        return (
          <header className="grid items-center gap-4 rounded-[2rem] bg-[#FFD36E] p-6 md:grid-cols-[1fr_auto] md:p-8">
            <div>
              <p className="text-xs font-bold tracking-wide text-[#5B3A29]/80">ACARA · {tglPendek(event.tanggal) || "tanggal belum diisi"}{event.lokasi ? ` · ${event.lokasi}` : ""}</p>
              <h1 className="font-display mt-1 text-3xl font-bold text-[#5B3A29] md:text-5xl">{event.nama}</h1>
              <p className="mt-2 text-sm text-[#5B3A29]/85">{seksi.length} seksi · {ringkasan.total} tugas · {ringkasan.done} selesai · {p}% progres</p>
            </div>
            <Capy mood={mood} size={110} className="md:w-[140px]" />
          </header>
        );
      })()}

      <nav aria-label="Filter seksi" className="flex flex-wrap gap-2">
        {["Semua", ...seksi.map((s) => s.seksi)].map((nama) => (
          <button
            key={nama}
            type="button"
            onClick={() => setTab(nama)}
            aria-pressed={tab === nama}
            className={`px-3 py-1.5 rounded-full text-sm border focus-visible:ring-2 focus-visible:ring-teal-400 ${tab === nama ? "bg-teal-500/15 border-teal-400 text-teal-300" : "border-[#cbd5e1] text-slate-300 hover:border-slate-500"}`}
          >
            {nama}
          </button>
        ))}
      </nav>

      <Judul>Garis waktu tenggat</Judul>
      <GarisWaktuTugas tugas={detail?.tasks ?? []} />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 space-y-5">
          {(["belum", "dikerjakan", "selesai"] as Kelompok[]).map((k) => (
            <div key={k} className="space-y-2">
              <h2 className="text-sm font-semibold text-slate-300">{labelKelompok(k)} <span className="text-slate-500">{kelompok[k].length}</span></h2>
              {kelompok[k].length === 0 && <p className="text-xs text-slate-500">Tidak ada.</p>}
              {kelompok[k].map((t) => (
                <div key={t.id} className="p-3 rounded-xl kartu-infografis">
                  <p className={`text-sm font-medium break-words ${k === "selesai" ? "line-through text-slate-500" : ""}`}>{t.judul}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    {t.divisi || "Tanpa seksi"}{t.pic ? ` · PIC ${t.pic}` : ""}{t.deadline_iso ? ` · ${tglPendek(t.deadline_iso)}` : ""}
                    {terlambat(t) && <span className="text-red-300"> · terlambat</span>}
                  </p>
                </div>
              ))}
            </div>
          ))}
        </section>

        <aside className="space-y-6">
          <section className="space-y-3 rounded-3xl border border-[#5B3A29]/10 bg-[#FFFDF7] p-5">
            <h2 className="font-display font-bold text-[#5B3A29]">Progres per seksi</h2>
            {seksi.length === 0 && <p className="text-sm text-[#7A5C48]">Belum ada seksi.</p>}
            {seksi.map((s2) => <BatangSkill key={s2.seksi} label={s2.seksi} persen={s2.avg_progress} />)}
            <p className="pt-1 text-xs text-[#7A5C48]">{ringkasan.overdue > 0 ? `${ringkasan.overdue} tugas terlambat` : "Tidak ada tugas terlambat"}</p>
          </section>
          <Lipat judul="PIC per seksi">
            <ul className="space-y-2">
              {struktur.map((s2) => (
                <li key={s2.seksi} className="flex items-center gap-3 text-sm">
                  <span className="h-3 w-3 rounded-full" style={{ background: warnaSeksi(s2.seksi) }} aria-hidden="true" />
                  <span className="flex-1 text-[#5B3A29]">{s2.seksi}</span>
                  <span className="text-[#7A5C48]">{s2.pic || "Belum diisi"}</span>
                </li>
              ))}
            </ul>
          </Lipat>
        </aside>
      </div>

      {/* Panel pengelolaan: di bawah papan tugas, supaya isi utama terlihat dulu */}
      {me?.ketua && detail && <Lipat judul="Ajak dan ingatkan lewat WhatsApp"><AksiKetua eventId={id} nama={detail.event.nama} tanggal={detail.event.tanggal ?? null} lokasi={detail.event.lokasi ?? null} /></Lipat>}
      {me?.ketua && <Lipat judul="Perlu ditindaklanjuti" buka><TindakLanjutKetua eventId={id} /></Lipat>}
      {!me?.ketua && me?.orang_id && <TugasMenunggu orangId={me.orang_id} />}
      {me && <Lipat judul="Kabar untuk anggota"><KabarAcara eventId={id} /></Lipat>}
      {me && <Lipat judul="Pesan dari dan ke anggota"><section className="grid gap-4 md:grid-cols-2"><div className="kartu-infografis p-5"><KotakPesan eventId={id} /></div>{me.ketua && <div className="kartu-infografis p-5"><KirimPesan eventId={id} me={me} seksiList={[]} /></div>}</section></Lipat>}
      {me && <Lipat judul="Catatan keputusan"><KeputusanAcara eventId={id} /></Lipat>}
      {me && <Lipat judul="Tanya Capy" buka><TanyaCapy eventId={id} /></Lipat>}
      {me?.ketua && <Lipat judul="Pengaturan acara (Ketua)"><PengaturanAcaraKetua eventId={id} /></Lipat>}
    </main>
  );
}
