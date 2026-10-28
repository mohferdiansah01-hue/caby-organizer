// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/image", () => ({ default: (p: Record<string, unknown>) => <span data-testid="gambar" data-src={String(p.src)} /> }));
import KonfirmasiDialog from "./KonfirmasiDialog";

describe("KonfirmasiDialog", () => {
  it("menampilkan pesan dan tombol sesuai label", () => {
    render(<KonfirmasiDialog pesan="Hapus tugas ini?" labelYa="Ya, hapus" onYa={() => {}} onBatal={() => {}} />);
    expect(screen.getByRole("dialog")).toHaveTextContent("Hapus tugas ini?");
    expect(screen.getByRole("button", { name: "Ya, hapus" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Batal" })).toBeInTheDocument();
  });

  it("Ya memanggil onYa sekali, Batal memanggil onBatal", async () => {
    const onYa = vi.fn(), onBatal = vi.fn();
    render(<KonfirmasiDialog pesan="Lanjut?" onYa={onYa} onBatal={onBatal} />);
    await userEvent.click(screen.getByRole("button", { name: "Ya, lanjutkan" }));
    expect(onYa).toHaveBeenCalledTimes(1);
    expect(onBatal).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Batal" }));
    expect(onBatal).toHaveBeenCalledTimes(1);
  });

  it("klik di luar kotak dialog membatalkan", async () => {
    const onBatal = vi.fn();
    const { container } = render(<KonfirmasiDialog pesan="Lanjut?" onYa={() => {}} onBatal={onBatal} />);
    await userEvent.click(container.firstChild as HTMLElement);
    expect(onBatal).toHaveBeenCalled();
  });
});
