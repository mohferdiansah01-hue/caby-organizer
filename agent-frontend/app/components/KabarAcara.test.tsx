// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/image", () => ({ default: (p: Record<string, unknown>) => <span data-testid="gambar" data-src={String(p.src)} /> }));
const fetchKabarAcara = vi.fn();
const buatKabar = vi.fn();
const unggahLampiran = vi.fn();
const hapusKabar = vi.fn();
vi.mock("../lib/api", () => ({
  fetchKabarAcara: (...a: unknown[]) => fetchKabarAcara(...a),
  buatKabar: (...a: unknown[]) => buatKabar(...a),
  unggahLampiran: (...a: unknown[]) => unggahLampiran(...a),
  hapusKabar: (...a: unknown[]) => hapusKabar(...a),
}));

import KabarAcara from "./KabarAcara";

describe("KabarAcara", () => {
  beforeEach(() => {
    fetchKabarAcara.mockReset().mockResolvedValue([]);
    buatKabar.mockReset().mockResolvedValue({ id: "k1" });
    unggahLampiran.mockReset();
    hapusKabar.mockReset();
  });

  it("tanpa kabar menampilkan pesan belum ada kabar", async () => {
    render(<KabarAcara eventId="ev1" />);
    expect(await screen.findByText("Belum ada kabar.")).toBeInTheDocument();
  });

  it("mengirim kabar ke acara yang benar, dengan pilihan tampil di beranda", async () => {
    render(<KabarAcara eventId="ev1" />);
    await userEvent.type(screen.getByLabelText("Tulis kabar untuk anggota"), "Rundown sudah diunggah");
    await userEvent.click(screen.getByLabelText("Tampilkan di beranda"));
    await userEvent.click(screen.getByRole("button", { name: "Kirim kabar" }));
    await waitFor(() => expect(buatKabar).toHaveBeenCalledWith({
      isi: "Rundown sudah diunggah", event_id: "ev1", publik: true, lampiran_ids: [],
    }));
  });

  it("lampiran diunggah dulu, lalu id-nya ikut dikirim bersama kabar", async () => {
    unggahLampiran.mockResolvedValue({ id: "berkas-1" });
    const { container } = render(<KabarAcara eventId="ev1" />);
    await userEvent.type(screen.getByLabelText("Tulis kabar untuk anggota"), "Lihat berkas");
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(["%PDF"], "rundown.pdf", { type: "application/pdf" }));
    await userEvent.click(screen.getByRole("button", { name: "Kirim kabar" }));
    await waitFor(() => expect(buatKabar).toHaveBeenCalledWith(expect.objectContaining({ lampiran_ids: ["berkas-1"] })));
    expect(unggahLampiran).toHaveBeenCalledTimes(1);
  });

  it("tombol Kirim tidak aktif sebelum isi kabar diketik", async () => {
    render(<KabarAcara eventId="ev1" />);
    expect(screen.getByRole("button", { name: "Kirim kabar" })).toBeDisabled();
  });

  it("gagal mengirim menampilkan galat, bukan diam", async () => {
    buatKabar.mockRejectedValue(new Error("Kamu bukan anggota acara ini."));
    render(<KabarAcara eventId="ev1" />);
    await userEvent.type(screen.getByLabelText("Tulis kabar untuk anggota"), "Halo");
    await userEvent.click(screen.getByRole("button", { name: "Kirim kabar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Kamu bukan anggota acara ini.");
  });
});
