// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/image", () => ({ default: (p: Record<string, unknown>) => <span data-testid="gambar" data-src={String(p.src)} /> }));
const daftarAkun = vi.fn();
vi.mock("../lib/api", () => ({ daftarAkun: (...a: unknown[]) => daftarAkun(...a) }));

import DaftarForm from "./DaftarForm";

async function isi(nama: string, user: string, pw: string, ulang: string) {
  await userEvent.type(screen.getByLabelText("Nama lengkap"), nama);
  await userEvent.type(screen.getByLabelText("Username"), user);
  await userEvent.type(screen.getByLabelText("Password (minimal 8 karakter)"), pw);
  await userEvent.type(screen.getByLabelText("Ulangi password"), ulang);
}

describe("DaftarForm", () => {
  beforeEach(() => daftarAkun.mockReset());

  it("tombol Daftar tidak aktif sebelum semua kolom terisi", () => {
    render(<DaftarForm />);
    expect(screen.getByRole("button", { name: "Daftar" })).toBeDisabled();
  });

  it("password dan ulangnya tidak sama: pesan galat muncul dan akun tidak dibuat", async () => {
    render(<DaftarForm />);
    await isi("Uji", "uji_user", "sandi-satu-2031", "sandi-dua-2031");
    await userEvent.click(screen.getByRole("button", { name: "Daftar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Konfirmasi password tidak sama.");
    expect(daftarAkun).not.toHaveBeenCalled();
  });

  it("pendaftaran berhasil menampilkan kode pemulihan sekali, dengan tombol salin", async () => {
    daftarAkun.mockResolvedValue({ username: "uji_user", pesan: "Akun dibuat.", kode_pemulihan: "4QKX-M8PW-2TN3" });
    render(<DaftarForm />);
    await isi("Uji", "uji_user", "sandi-uji-2031", "sandi-uji-2031");
    await userEvent.click(screen.getByRole("button", { name: "Daftar" }));
    expect(await screen.findByText("4QKX-M8PW-2TN3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salin kode" })).toBeInTheDocument();
    expect(daftarAkun).toHaveBeenCalledWith({ username: "uji_user", nama: "Uji", password: "sandi-uji-2031" });
  });
});
