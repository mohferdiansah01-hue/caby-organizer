"use client";

import { FormEvent, useEffect, useState } from "react";
import Capy from "../components/Capy";
import CabyState from "../components/CabyState";
import Link from "next/link";
import { Loader2, Plus } from "lucide-react";
import { EventItem, createEvent, fetchEvents } from "../lib/api";
import { tglPendek } from "../lib/status";

// Daftar acara: kartu sederhana dan satu form untuk membuat acara baru.
export default function AcaraPage() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [galat, setGalat] = useState("");
  const [nama, setNama] = useState("");
  const [tanggal, setTanggal] = useState("");
  const [lokasi, setLokasi] = useState("");
  const [busy, setBusy] = useState(false);
  const [sukses, setSukses] = useState(false);

  const muat = () =>
    fetchEvents()
      .then(setEvents)
      .catch((e) => setGalat(e instanceof Error ? e.message : "Gagal memuat acara."))
      .finally(() => setLoaded(true));

  useEffect(() => {
    muat();
  }, []);

  const buat = async (e: FormEvent) => {
    e.preventDefault();
    if (!nama.trim()) return;
    setBusy(true);
    setGalat("");
    try {
      await createEvent({ nama: nama.trim(), tanggal: tanggal || null, lokasi: lokasi.trim() });
      setNama("");
      setTanggal("");
      setLokasi("");
      await muat();
      setSukses(true);
    } catch (err) {
      setGalat(err instanceof Error ? err.message : "Gagal membuat acara.");
    } finally {
      setBusy(false);
    }
  };

  const hari = new Date().toISOString().slice(0, 10);
  const field = "w-full bg-white border border-[#cbd5e1] rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-400";

  return (
    <main className="capy-theme max-w-6xl mx-auto px-4 md:px-6 pt-6 pb-28 md:py-10 space-y-6">
      <header className="grid items-center gap-4 rounded-[2rem] bg-[#FFD36E] p-6 md:grid-cols-[1fr_auto] md:p-8">
        <div>
          <p className="text-xs font-bold tracking-wide text-[#5B3A29]/80">SEMUA ACARA</p>
          <h1 className="font-display mt-1 text-3xl font-bold text-[#5B3A29] md:text-4xl">Acara</h1>
        </div>
        <Capy mood="wow" size={100} className="md:w-[120px]" />
      </header>

      {galat && <p role="alert" className="text-sm text-red-300">{galat}</p>}
      {sukses && <CabyState kind="berhasil" judul="Acara tersimpan" isi="Acara baru sudah ada di daftar." />}

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 space-y-2">
          {!loaded && <CabyState kind="memuat" judul="Memuat acara…" />}
          {loaded && events.length === 0 && <CabyState kind="kosong" judul="Belum ada acara" isi="Buat acara pertama di samping." />}
          {events.map((ev) => {
            const status = ev.tanggal === hari ? "Berlangsung" : ev.tanggal && ev.tanggal > hari ? "Mendatang" : "Selesai";
            return (
              <Link key={ev.id} href={`/events/${ev.id}`} className="flex items-center gap-4 p-4 rounded-3xl kartu-infografis hover:border-teal-500/50 focus-visible:ring-2 focus-visible:ring-teal-400">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold truncate">{ev.nama}</p>
                  <p className="text-xs text-slate-400 truncate">{tglPendek(ev.tanggal) || "Tanggal belum diisi"}{ev.lokasi ? ` · ${ev.lokasi}` : ""}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs text-slate-400">{ev.tugas_selesai ?? 0} / {ev.total_tugas ?? 0} selesai</p>
                  <p className="text-[11px] text-teal-300 mt-1">{status}</p>
                </div>
              </Link>
            );
          })}
        </section>

        <aside>
          <form onSubmit={buat} className="kartu-infografis p-5 space-y-3">
            <h2 className="font-display font-semibold flex items-center gap-2"><Plus className="w-4 h-4 text-teal-300" aria-hidden="true" /> Buat acara</h2>
            <label className="block text-xs text-slate-400 space-y-1">Nama acara
              <input className={field} value={nama} onChange={(e) => setNama(e.target.value)} required />
            </label>
            <label className="block text-xs text-slate-400 space-y-1">Tanggal
              <input type="date" className={field} value={tanggal} onChange={(e) => setTanggal(e.target.value)} />
            </label>
            <label className="block text-xs text-slate-400 space-y-1">Lokasi
              <input className={field} value={lokasi} onChange={(e) => setLokasi(e.target.value)} />
            </label>
            <button type="submit" disabled={busy || !nama.trim()} className="w-full py-2 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-40 text-slate-950 font-semibold text-sm flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-teal-300">
              {busy && <Loader2 className="w-4 h-4 animate-spin" />} Simpan acara
            </button>
          </form>
        </aside>
      </div>
    </main>
  );
}
