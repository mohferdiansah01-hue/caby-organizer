// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const replace = vi.fn();
const getMe = vi.fn();
const logout = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard", useRouter: () => ({ replace }) }));
vi.mock("../lib/api", () => ({ getMe: (...args: unknown[]) => getMe(...args), logout: (...args: unknown[]) => logout(...args) }));

import GlobalNav from "./GlobalNav";

describe("GlobalNav profile menu", () => {
  beforeEach(() => {
    replace.mockReset();
    getMe.mockReset().mockResolvedValue({ nama: "Nabila Putri", role: "Nabila Putri", ketua: true, peran: "ketua", event_id: "event-demo" });
    logout.mockReset().mockResolvedValue(undefined);
  });

  it("shows account details and logs out from the profile menu", async () => {
    const user = userEvent.setup();
    render(<GlobalNav />);

    await waitFor(() => expect(screen.getAllByText("Nabila Putri").length).toBeGreaterThan(0));
    const profiles = screen.getAllByLabelText("Profil Nabila Putri");
    await user.click(profiles[0]);
    expect(screen.getAllByText("Profil akun").length).toBeGreaterThan(0);

    await user.click(screen.getAllByRole("button", { name: "Keluar" })[0]);
    await waitFor(() => expect(logout).toHaveBeenCalledOnce());
    expect(replace).toHaveBeenCalledWith("/beranda");
  });
});
