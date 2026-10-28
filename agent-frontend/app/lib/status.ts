import type { Task } from "./api";

// Status tampilan: dihitung dari progres dan deadline, bukan dari status mentah di database.
export type Kelompok = "belum" | "dikerjakan" | "selesai";

export function kelompokTugas(t: Task): Kelompok {
  if (t.status === "done") return "selesai";
  return t.progress > 0 ? "dikerjakan" : "belum";
}

export function labelKelompok(k: Kelompok): string {
  return k === "selesai" ? "Selesai" : k === "dikerjakan" ? "Dikerjakan" : "Belum mulai";
}

export function terlambat(t: Task): boolean {
  return t.status !== "done" && !!t.deadline_iso && new Date(t.deadline_iso).getTime() < Date.now();
}

export function tglPendek(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? `${iso}T00:00` : iso);
  return d.toLocaleDateString("id-ID", { day: "2-digit", month: "short" });
}

// Status tampilan dihitung dari deadline dan progres, bukan dari status mentah di database.
export function statusTugas(t: Task): { label: string; warna: string } {
  if (t.status === "done") return { label: "Selesai", warna: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30" };
  if (t.deadline_iso && new Date(t.deadline_iso).getTime() < Date.now()) {
    return { label: "Terlambat", warna: "text-red-300 bg-red-500/10 border-red-500/30" };
  }
  if (t.deadline_iso && new Date(t.deadline_iso).getTime() - Date.now() < 2 * 86400000) {
    return { label: "Mendekati deadline", warna: "text-amber-300 bg-amber-500/10 border-amber-500/30" };
  }
  if (t.progress > 0) return { label: "Dalam proses", warna: "text-sky-300 bg-sky-500/10 border-sky-500/30" };
  return { label: "Belum mulai", warna: "text-slate-300 bg-slate-500/10 border-slate-600" };
}

