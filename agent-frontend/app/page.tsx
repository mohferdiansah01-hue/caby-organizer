"use client";

import { useEffect, useState } from "react";
import CabyState from "./components/CabyState";
import Link from "next/link";
import Image from "next/image";
import { CalendarDays, CheckCircle2, Users, ListTodo } from "lucide-react";
import TanyaCapy from "./components/TanyaCapy";
import {
  EventItem, Task, TaskStats, TeamStats, Me,
  fetchEvents, fetchStats, fetchTeamStats, fetchTasks, getMe,
} from "./lib/api";
import { statusTugas } from "./lib/status";

// Gunakan tanggal lokal perangkat. toISOString() memakai UTC dan bisa membuat
// tanggal acara bergeser sehari untuk pengguna di Indonesia pada jam tertentu.
const hariIni = () => {
  const sekarang = new Date();
  const tahun = sekarang.getFullYear();
  const bulan = String(sekarang.getMonth() + 1).padStart(2, "0");
  const tanggal = String(sekarang.getDate()).padStart(2, "0");
  return `${tahun}-${bulan}-${tanggal}`;
};

function tglPendek(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? `${iso}T00:00` : iso);
  return d.toLocaleDateString("id-ID", { day: "2-digit", month: "short" });
}

export default function Beranda() {
  const [me, setMe] = useState<Me | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [team, setTeam] = useState<TeamStats | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [muat, setMuat] = useState(true);
  const [galat, setGalat] = useState("");

  const muatUlang = () =>
    Promise.all([fetchEvents(), fetchStats(), fetchTeamStats(), fetchTasks("semua"), getMe()])
      .then(([ev, st, tm, tk, who]) => {
        setEvents(ev);
        setStats(st);
        setTeam(tm);
        setTasks(tk);
        setMe(who);
        setGalat("");
      })
      .catch((e) => setGalat(e instanceof Error ? e.message : "Gagal memuat data."))
      .finally(() => setMuat(false));

  useEffect(() => {
    muatUlang();
  }, []);

  const hari = hariIni();
  const mendatang = events
    .filter((e) => (e.tanggal ?? "") >= hari)
    .sort((a, b) => (a.tanggal ?? "").localeCompare(b.tanggal ?? ""))
    .slice(0, 3);
  const tugasTerbaru = tasks
    .filter((t) => t.status !== "done")
    .sort((a, b) => (a.deadline_iso ?? "9999").localeCompare(b.deadline_iso ?? "9999"))
    .slice(0, 4);
  const eventAktif = (mendatang[0] ?? events[0])?.id ?? null;

  const namaKetua = me?.nama || me?.role || "Ketua";

  return (
    <main className="capy-theme max-w-6xl mx-auto px-4 md:px-6 py-6 md:py-10 space-y-6">
      <section className="relative overflow-hidden rounded-3xl p-6 md:p-8 min-h-[190px] bg-indigo-50 border border-indigo-100" >
        <p className="text-sm text-slate-600">Halo, {namaKetua}</p>
        <h1 className="font-display text-2xl md:text-4xl font-bold mt-1 max-w-[62%] md:max-w-md text-slate-900">Atur acara panitia tanpa ribet</h1>
        <p className="text-sm md:text-base text-slate-600 mt-2 max-w-[62%] md:max-w-md">Tulis rundown, lalu tugas dibagi per seksi dengan deadline yang masuk akal.</p>
        <div className="mt-4">
          <Link href="/events" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm focus-visible:ring-2 focus-visible:ring-indigo-400" >
            Buat acara
          </Link>
        </div>
        <Image src="/capy/capy-1.webp" alt="" priority width={200} height={200} className="absolute right-2 bottom-0 w-36 md:w-52 h-auto pointer-events-none" aria-hidden="true" />
      </section>

      {galat && <p role="alert" className="text-sm text-red-300">{galat}</p>}

      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Angka label="Total acara" nilai={events.length} ikon={<CalendarDays className="w-4 h-4" />} />
        <Angka label="Tugas aktif" nilai={stats?.pending ?? 0} ikon={<ListTodo className="w-4 h-4" />} />
        <Angka label="Panitia" nilai={team?.total_pic ?? 0} ikon={<Users className="w-4 h-4" />} />
        <Angka label="Selesai" nilai={stats?.done ?? 0} ikon={<CheckCircle2 className="w-4 h-4" />} />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6 min-w-0">
          <section className="kartu-infografis p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-semibold">Acara mendatang</h2>
              <Link href="/events" className="text-sm text-teal-300 hover:text-teal-200">Lihat semua</Link>
            </div>
            {muat && <CabyState kind="memuat" judul="Memuat acara…" />}
            {!muat && mendatang.length === 0 && (
              <CabyState kind="kosong" judul="Belum ada acara mendatang" isi="Buat acara pertama untuk mulai membagi tugas." aksi={<Link href="/events" className="text-sm font-semibold text-indigo-600 hover:underline">Buat acara</Link>} />
            )}
            <ul className="space-y-2">
              {mendatang.map((ev) => (
                <li key={ev.id}>
                  <Link href={`/events/${ev.id}`} className="flex items-center gap-4 p-3 rounded-xl bg-slate-950/60 border border-[#5B3A29]/15 hover:border-teal-500/50 focus-visible:ring-2 focus-visible:ring-teal-400">
                    <div className="w-14 text-center shrink-0 rounded-lg bg-teal-500/10 py-2">
                      <p className="text-lg font-bold text-teal-300 leading-none">{(ev.tanggal ?? "").slice(8, 10)}</p>
                      <p className="text-[11px] text-slate-400 mt-1">{tglPendek(ev.tanggal)}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold truncate">{ev.nama}</p>
                      <p className="text-xs text-slate-400 truncate">{ev.lokasi || "Lokasi belum diisi"}</p>
                    </div>
                    <span className="ml-auto text-xs text-slate-400 shrink-0">{ev.tanggal === hari ? "Berlangsung" : `${ev.tugas_selesai ?? 0}/${ev.total_tugas ?? 0} selesai`}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="kartu-infografis p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-semibold">Tugas terbaru</h2>
              <Link href="/kerja" className="text-sm text-teal-300 hover:text-teal-200">Lihat semua</Link>
            </div>
            {!muat && tugasTerbaru.length === 0 && (
              <CabyState kind="kosong" judul="Belum ada tugas" isi="Tulis rundown atau tanyakan Capy untuk membuat tugas pertama." />
            )}
            <ul className="space-y-2">
              {tugasTerbaru.map((t) => {
                const st = statusTugas(t);
                return (
                  <li key={t.id} className="flex items-center gap-3 p-3 rounded-xl bg-slate-950/60 border border-[#5B3A29]/15">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-sm break-words">{t.judul}</p>
                      <p className="text-xs text-slate-400">{t.divisi || "Tanpa seksi"}{t.deadline_iso ? ` · ${tglPendek(t.deadline_iso)}` : ""}</p>
                    </div>
                    <span className={`text-[11px] px-2 py-1 rounded-full border shrink-0 ${st.warna}`}>{st.label}</span>
                  </li>
                );
              })}
            </ul>
          </section>
        </div>

        <TanyaCapy eventId={eventAktif ?? undefined} />
      </div>
    </main>
  );
}

function Angka({ label, nilai, ikon }: { label: string; nilai: number; ikon: React.ReactNode }) {
  return (
    <div className="kartu-infografis p-4">
      <p className="text-xs text-slate-400 flex items-center gap-1.5">{ikon} {label}</p>
      <p className="text-2xl font-bold mt-1">{nilai}</p>
    </div>
  );
}
