// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/image", () => ({ default: (p: Record<string, unknown>) => <span data-testid="gambar" data-src={String(p.src)} /> }));
const tugasMenungguSaya = vi.fn();
const konfirmasiTugas = vi.fn();
vi.mock("../lib/api", () => ({
  tugasMenungguSaya: (...a: unknown[]) => tugasMenungguSaya(...a),
  konfirmasiTugas: (...a: unknown[]) => konfirmasiTugas(...a),
}));

import TugasMenungguDashboard from "./TugasMenungguDashboard";

const satu = { id: "t1", judul: "Cetak poster", event_id: "ev1", acara: "Festival", deadline_iso: "2031-01-02T10:00" };

describe("TugasMenungguDashboard", () => {
  beforeEach(() => {
    tugasMenungguSaya.mockReset();
    konfirmasiTugas.mockReset().mockResolvedValue({});
  });

  it("tanpa tugas menunggu, komponen tidak menampilkan apa pun", async () => {
    tugasMenungguSaya.mockResolvedValue([]);
    const { container } = render(<TugasMenungguDashboard />);
    await waitFor(() => expect(tugasMenungguSaya).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("menampilkan judul, acara, dan tenggat tugas yang menunggu", async () => {
    tugasMenungguSaya.mockResolvedValue([satu]);
    render(<TugasMenungguDashboard />);
    expect(await screen.findByText("Cetak poster")).toBeInTheDocument();
    expect(screen.getByText(/Festival/)).toBeInTheDocument();
    expect(screen.getByText(/tenggat 2031-01-02 10:00/)).toBeInTheDocument();
  });

  it("Saya terima mengirim jawaban terima untuk tugas itu, lalu memuat ulang daftar", async () => {
    tugasMenungguSaya.mockResolvedValueOnce([satu]).mockResolvedValueOnce([]);
    render(<TugasMenungguDashboard />);
    await userEvent.click(await screen.findByRole("button", { name: "Saya terima" }));
    await waitFor(() => expect(konfirmasiTugas).toHaveBeenCalledWith("t1", "terima"));
    await waitFor(() => expect(screen.queryByText("Cetak poster")).not.toBeInTheDocument());
  });

  it("Tidak sanggup meminta alasan dulu, dan penolakan tanpa alasan tidak bisa dikirim", async () => {
    tugasMenungguSaya.mockResolvedValue([satu]);
    render(<TugasMenungguDashboard />);
    await userEvent.click(await screen.findByRole("button", { name: "Tidak sanggup" }));
    const kirim = screen.getByRole("button", { name: "Kirim penolakan" });
    expect(kirim).toBeDisabled();
    await userEvent.type(screen.getByPlaceholderText("Alasan singkat, misalnya: sedang ujian"), "sedang ujian");
    expect(kirim).toBeEnabled();
    await userEvent.click(kirim);
    await waitFor(() => expect(konfirmasiTugas).toHaveBeenCalledWith("t1", "tolak", "sedang ujian"));
  });
});
