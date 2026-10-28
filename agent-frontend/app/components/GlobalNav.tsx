"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Calendar, CheckSquare, ChevronDown, Home, Plus, LogOut, Shield } from "lucide-react";
import { getMe, logout, Me } from "../lib/api";

type Item = { href: string; label: string; ikon: typeof Home };

// Desktop: sidebar ink di kiri. HP: header ringkas dan bar bawah dengan tombol tambah di tengah.
// Menu mengikuti peran: Ketua melihat semuanya, seksi hanya ruang kerjanya. Tamu (belum masuk) tidak melihat navigasi peran.
export default function GlobalNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    getMe().then(setMe).catch(() => setMe(null));
  }, [pathname]);

  const adminItem: Item[] = me?.admin ? [{ href: "/admin", label: "Admin", ikon: Shield }] : [];
  const menuUtama: Item[] = me
    ? me.peran === "pengguna"
      ? [{ href: "/dashboard", label: "Dashboard", ikon: Home }, { href: "/beranda", label: "Beranda", ikon: Home }]
      : me.ketua
        ? [{ href: "/", label: "Beranda", ikon: Home }, { href: "/events", label: "Acara", ikon: Calendar }, { href: "/kerja", label: "Ruang kerja", ikon: CheckSquare }]
        : [{ href: "/kerja", label: "Ruang kerja", ikon: CheckSquare }]
    : [{ href: "/beranda", label: "Beranda", ikon: Home }];
  const items: Item[] = [...menuUtama, ...adminItem];

  const aktif = (href: string) => (href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/"));

  const keluar = async () => {
    await logout();
    setMe(null);
    router.replace("/beranda");
  };

  if (!me) return null;

  const namaProfil = me.nama || me.role || "Akun";
  const peranProfil = me.admin ? "Admin" : me.peran?.replaceAll("_", " ") || "Pengguna";
  const inisial = namaProfil.charAt(0).toUpperCase();

  return (
    <>
      <aside aria-label="Navigasi utama" className="hidden md:flex fixed left-0 top-0 bottom-0 w-64 z-40 flex-col p-5 bg-[#FFFDF7] border-r-2 border-[#5B3A29]/10"
        style={{ color: "#fff" }}>
        <div className="flex items-center gap-3 mb-8">
          <span className="w-10 h-10 rounded-full bg-[#FFD36E] text-[#5B3A29] font-bold flex items-center justify-center">{inisial}</span>
          <span className="font-display font-bold leading-tight text-[#5B3A29]">Caby Organizer</span>
        </div>
        <nav className="space-y-2">
          {items.map((i) => {
            const Ikon = i.ikon;
            const on = aktif(i.href);
            return (
              <Link key={i.href} href={i.href} aria-current={on ? "page" : undefined}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm focus-visible:ring-2 focus-visible:ring-[#E8962E] ${on ? "font-semibold bg-[#FFD36E] text-[#5B3A29]" : "text-[#5B3A29]/80 hover:bg-[#FFD36E]/40e/10"}`}
                style={undefined}>
                <Ikon className="w-4 h-4" aria-hidden="true" /> {i.label}
              </Link>
            );
          })}
        </nav>
        {me.ketua && (
          <Link href="/events" className="mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-[#5B3A29] text-[#FFF6E3]"
            >
            <Plus className="w-4 h-4" aria-hidden="true" /> Buat acara
          </Link>
        )}
        <details className="group relative mt-auto border-t border-[#5B3A29]/15 pt-4">
          <summary aria-label={`Profil ${namaProfil}`} className="flex cursor-pointer list-none items-center gap-3 rounded-xl px-2 py-2 focus-visible:ring-2 focus-visible:ring-[#E8962E] [&::-webkit-details-marker]:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#FFD36E] text-sm font-bold text-[#5B3A29]">{inisial}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-[#5B3A29]">{namaProfil}</span>
              <span className="block truncate text-xs capitalize text-[#5B3A29]/70">{peranProfil}</span>
            </span>
            <ChevronDown className="h-4 w-4 text-[#5B3A29]/70 transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-[#5B3A29]/15 bg-[#FFFDF7] p-3 shadow-lg">
            <p className="text-[11px] text-[#7A5C48]">Profil akun</p>
            <p className="mt-1 truncate text-sm font-semibold text-[#5B3A29]">{namaProfil}</p>
            <p className="mb-3 text-xs capitalize text-[#5B3A29]/70">{peranProfil}</p>
            <button type="button" onClick={keluar} className="flex min-h-[40px] w-full items-center gap-2 rounded-lg px-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-[#E8962E]">
              <LogOut className="h-4 w-4" aria-hidden="true" /> Keluar
            </button>
          </div>
        </details>
      </aside>

      <header className="md:hidden sticky top-0 z-40 bg-[var(--caby-surface)] border-b border-[var(--caby-line)] px-4 py-3 flex items-center justify-between">
        <span className="font-display font-bold text-[var(--caby-ink)]">Caby Organizer</span>
        <details className="group relative">
          <summary aria-label={`Profil ${namaProfil}`} className="flex min-h-[40px] cursor-pointer list-none items-center gap-2 rounded-full border border-[var(--caby-line)] px-2.5 text-[var(--caby-ink)] focus-visible:ring-2 focus-visible:ring-[#E8962E] [&::-webkit-details-marker]:hidden">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#FFD36E] text-xs font-bold text-[#5B3A29]">{inisial}</span>
            <span className="max-w-28 truncate text-xs font-semibold">Profil</span>
            <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="absolute right-0 top-full z-50 mt-2 w-64 rounded-xl border border-[var(--caby-line)] bg-[var(--caby-surface)] p-3 shadow-lg">
            <p className="truncate text-sm font-semibold text-[var(--caby-ink)]">{namaProfil}</p>
            <p className="mb-3 text-xs capitalize text-[var(--caby-muted)]">{peranProfil}</p>
            <button type="button" onClick={keluar} className="flex min-h-[40px] w-full items-center gap-2 rounded-lg px-2 text-sm font-semibold text-red-700 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-[#E8962E]">
              <LogOut className="h-4 w-4" aria-hidden="true" /> Keluar
            </button>
          </div>
        </details>
      </header>

      <nav aria-label="Navigasi bawah" className="md:hidden fixed bottom-3 left-3 right-3 z-40 rounded-3xl bg-[#FFFDF7] shadow-md border-2 border-[#5B3A29]/15 pb-[env(safe-area-inset-bottom,0px)]">
        <div className="flex items-center justify-around px-2 py-2">
          {items.slice(0, 2).map((i) => {
            const Ikon = i.ikon;
            const on = aktif(i.href);
            return (
              <Link key={i.href} href={i.href} aria-current={on ? "page" : undefined}
                className={`flex min-h-[48px] min-w-[60px] flex-col items-center justify-center gap-0.5 text-[11px] whitespace-nowrap px-1.5 py-1 rounded-xl focus-visible:ring-2 focus-visible:ring-[#E8962E] ${on ? "bg-[#FFD36E] text-[#5B3A29] font-bold" : "text-[#5B3A29]/70"}`}>
                <Ikon className="w-5 h-5" aria-hidden="true" />{i.label}
              </Link>
            );
          })}
          {me.ketua && (
            <Link href="/events" aria-label="Buat acara" className="-mt-7 w-14 h-14 rounded-full flex items-center justify-center text-white shadow-md bg-[var(--caby-accent)] focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#E8962E]"
              >
              <Plus className="w-6 h-6" aria-hidden="true" />
            </Link>
          )}
          {items.slice(2).map((i) => {
            const Ikon = i.ikon;
            const on = aktif(i.href);
            return (
              <Link key={i.href} href={i.href} aria-current={on ? "page" : undefined}
                className={`flex min-h-[48px] min-w-[60px] flex-col items-center justify-center gap-0.5 text-[11px] whitespace-nowrap px-1.5 py-1 rounded-xl focus-visible:ring-2 focus-visible:ring-[#E8962E] ${on ? "bg-[#FFD36E] text-[#5B3A29] font-bold" : "text-[#5B3A29]/70"}`}>
                <Ikon className="w-5 h-5" aria-hidden="true" />{i.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
