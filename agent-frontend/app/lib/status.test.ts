import { describe, expect, it } from "vitest";
import { kelompokTugas, labelKelompok, statusTugas, terlambat } from "./status";
import type { Task } from "./api";

const dasar = { id: "t", judul: "Tugas", status: "pending", progress: 0, deadline_iso: null } as unknown as Task;
const hari = 86400000;

describe("kelompokTugas", () => {
  it("tugas selesai masuk kelompok selesai", () => {
    expect(kelompokTugas({ ...dasar, status: "done", progress: 100 })).toBe("selesai");
  });
  it("progres di atas nol berarti sedang dikerjakan", () => {
    expect(kelompokTugas({ ...dasar, progress: 40 })).toBe("dikerjakan");
  });
  it("tanpa progres berarti belum mulai", () => {
    expect(kelompokTugas(dasar)).toBe("belum");
  });
});

describe("labelKelompok", () => {
  it("memberi label bahasa Indonesia untuk setiap kelompok", () => {
    expect(labelKelompok("selesai")).toBe("Selesai");
    expect(labelKelompok("dikerjakan")).toBe("Dikerjakan");
    expect(labelKelompok("belum")).toBe("Belum mulai");
  });
});

describe("terlambat dan statusTugas", () => {
  it("tenggat yang sudah lewat dan belum selesai dianggap terlambat", () => {
    const lewat = new Date(Date.now() - 2 * hari).toISOString();
    expect(terlambat({ ...dasar, deadline_iso: lewat })).toBe(true);
    expect(statusTugas({ ...dasar, deadline_iso: lewat }).label).toBe("Terlambat");
  });
  it("tugas yang sudah selesai tidak pernah terlambat", () => {
    const lewat = new Date(Date.now() - 2 * hari).toISOString();
    expect(terlambat({ ...dasar, status: "done", deadline_iso: lewat })).toBe(false);
    expect(statusTugas({ ...dasar, status: "done", deadline_iso: lewat }).label).toBe("Selesai");
  });
  it("tenggat dalam dua hari ditandai mendekati", () => {
    const dekat = new Date(Date.now() + 1 * hari).toISOString();
    expect(statusTugas({ ...dasar, deadline_iso: dekat }).label).toBe("Mendekati deadline");
  });
});
