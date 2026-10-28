// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("next/image", () => ({ default: (p: Record<string, unknown>) => <span data-testid="gambar" data-src={String(p.src)} /> }));
const loginOrang = vi.fn();
vi.mock("../lib/api", () => ({ loginOrang: (...a: unknown[]) => loginOrang(...a) }));

import LoginCard from "./LoginCard";

describe("LoginCard", () => {
  beforeEach(() => { push.mockReset(); loginOrang.mockReset(); });

  it("menampilkan kolom username, password, dan tautan daftar serta lupa password", () => {
    render(<LoginCard />);
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Daftar" })).toHaveAttribute("href", "/daftar");
    expect(screen.getByRole("link", { name: "Lupa password?" })).toHaveAttribute("href", "/lupa-password");
  });

  it("menampilkan kredensial demo dan mengisikan akun terpilih ke form", async () => {
    render(<LoginCard demoAccounts={[{ label: "Ketua acara", username: "juri.ketua", password: "GebyarJuri2027!" }]} />);
    expect(screen.getByText("Username:").parentElement).toHaveTextContent("juri.ketua");
    expect(screen.getByText("Password:").parentElement).toHaveTextContent("GebyarJuri2027!");
    await userEvent.click(screen.getByRole("button", { name: "Isi akun demo Ketua acara" }));
    expect(screen.getByLabelText("Username")).toHaveValue("juri.ketua");
    expect(screen.getByLabelText("Password")).toHaveValue("GebyarJuri2027!");
  });

  it("setelah berhasil masuk tanpa onSuccess, pindah ke dashboard", async () => {
    loginOrang.mockResolvedValue({});
    render(<LoginCard />);
    await userEvent.type(screen.getByLabelText("Username"), "  ketua  ");
    await userEvent.type(screen.getByLabelText("Password"), "sandi-rahasia");
    await userEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(loginOrang).toHaveBeenCalledWith("ketua", "sandi-rahasia", "");
  });

  it("setelah berhasil masuk dengan onSuccess, memanggil onSuccess dan tidak pindah sendiri", async () => {
    loginOrang.mockResolvedValue({});
    const onSuccess = vi.fn();
    render(<LoginCard onSuccess={onSuccess} />);
    await userEvent.type(screen.getByLabelText("Username"), "ketua");
    await userEvent.type(screen.getByLabelText("Password"), "sandi-rahasia");
    await userEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(push).not.toHaveBeenCalled();
  });

  it("password salah menampilkan pesan galat yang dibaca pembaca layar", async () => {
    loginOrang.mockRejectedValue(new Error("Username atau password salah."));
    render(<LoginCard />);
    await userEvent.type(screen.getByLabelText("Username"), "ketua");
    await userEvent.type(screen.getByLabelText("Password"), "salah");
    await userEvent.click(screen.getByRole("button", { name: "Masuk" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Username atau password salah.");
    expect(push).not.toHaveBeenCalled();
  });
});
