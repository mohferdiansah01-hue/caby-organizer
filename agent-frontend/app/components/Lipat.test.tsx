// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Lipat from "./Lipat";

describe("Lipat", () => {
  it("tertutup secara default: isi tidak terbuka", () => {
    render(<Lipat judul="Pengaturan"><p>Isi rahasia</p></Lipat>);
    const bagian = screen.getByText("Pengaturan").closest("details") as HTMLDetailsElement;
    expect(bagian.open).toBe(false);
  });

  it("buka=true membuka isi sejak awal", () => {
    render(<Lipat judul="Tindak lanjut" buka><p>Isi</p></Lipat>);
    const bagian = screen.getByText("Tindak lanjut").closest("details") as HTMLDetailsElement;
    expect(bagian.open).toBe(true);
  });

  it("judul bisa diketuk untuk membuka dan menutup", async () => {
    render(<Lipat judul="PIC per seksi"><p>Daftar</p></Lipat>);
    const bagian = screen.getByText("PIC per seksi").closest("details") as HTMLDetailsElement;
    await userEvent.click(screen.getByText("PIC per seksi"));
    expect(bagian.open).toBe(true);
    await userEvent.click(screen.getByText("PIC per seksi"));
    expect(bagian.open).toBe(false);
  });
});
