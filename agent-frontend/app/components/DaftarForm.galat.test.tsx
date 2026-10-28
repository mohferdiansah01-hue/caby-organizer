// @vitest-environment jsdom
import { it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

vi.mock("next/image", () => ({ default: (p: Record<string, unknown>) => <span data-testid="gambar" data-src={String(p.src)} /> }));
const daftarAkun = vi.fn();
vi.mock("../lib/api", () => ({ daftarAkun: (...a: unknown[]) => daftarAkun(...a) }));

import DaftarForm from "./DaftarForm";

// Berkas terpisah: skenario galat dari server dijalankan sendiri agar tidak terpengaruh tes lain.
it("username sudah dipakai: pesan dari server ditampilkan", async () => {
  daftarAkun.mockImplementation(() => Promise.resolve().then(() => { throw new Error("Username sudah dipakai."); }));
  const { container } = render(<DaftarForm />);
  const set = (label: string, v: string) => fireEvent.change(screen.getByLabelText(label), { target: { value: v } });
  set("Nama lengkap", "Uji"); set("Username", "uji_user");
  set("Password (minimal 8 karakter)", "sandi-uji-2031"); set("Ulangi password", "sandi-uji-2031");
  fireEvent.submit(container.querySelector("form")!);
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Username sudah dipakai."));
});
