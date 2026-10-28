"use client";

import type { ReactNode } from "react";
import Capy, { Ekspresi } from "./Capy";

type Kind = "kosong" | "memuat" | "galat" | "berhasil" | "tunggu" | "ajak" | "pesan" | "beres" | "intip" | "tutup";

// Keadaan kosong, memuat, galat, dan berhasil di seluruh aplikasi. Satu keadaan, satu ekspresi.
const EKSPRESI_KEADAAN: Record<Kind, Ekspresi> = {
  kosong: "kosong",
  memuat: "memuat",
  galat: "galat",
  berhasil: "semangat",
  tunggu: "tunggu",
  ajak: "ajak",
  pesan: "pesan",
  beres: "beres",
  intip: "intip",
  tutup: "tutup",
};

export default function CabyState({ kind, judul, isi, aksi }: { kind: Kind; judul: string; isi?: string; aksi?: ReactNode }) {
  return (
    <div role={kind === "galat" ? "alert" : "status"} className="flex flex-col items-center text-center gap-2 py-6">
      <Capy mood={EKSPRESI_KEADAAN[kind]} size={88} />
      <p className="text-sm font-semibold text-slate-900">{judul}</p>
      {isi && <p className="text-xs text-slate-500 max-w-xs">{isi}</p>}
      {aksi}
    </div>
  );
}
