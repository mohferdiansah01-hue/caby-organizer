"use client";

import { useCallback, useEffect, useRef, useState, ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import LoginCard from "./components/LoginCard";
import AppSkeleton from "./components/AppSkeleton";
import GlobalNav from "./components/GlobalNav";

const PUBLIC_PATHS = ["/login", "/daftar", "/lupa-password", "/beranda"];
type Status = "checking" | "in" | "out";

// Penjaga sesi. Saat belum login, kerangka halaman tetap terlihat (diredupkan),
// dan kartu login muncul di atasnya. Tidak ada redirect paksa dan tidak ada layar kosong.
export default function AuthGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const [status, setStatus] = useState<Status>(isPublic ? "in" : "checking");
  const [netError, setNetError] = useState(false);
  const statusRef = useRef<Status>(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  const checkSession = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/me");
      const data = res.ok ? await res.json().catch(() => null) : null;
      if (!res.ok || !data || data.masuk === false) {
        if (pathname === "/") {
          router.replace("/beranda");
        } else {
          setStatus("out");
        }
        return;
      }
      const me: { role: string; ketua: boolean; peran?: string | null } = data;
      if (!me.ketua && pathname === "/") {
        // Pengguna yang belum punya acara masuk ke dashboard; yang sudah di dalam acara ke ruang kerja.
        router.replace(me.peran === "pengguna" || !me.peran ? "/dashboard" : "/kerja");
        return;
      }
      setStatus("in");
    } catch {
      setStatus("out");
    }
  }, [pathname, router]);

  // Jika server menjawab 401 di tengah pemakaian (sesi habis), tampilkan kartu login lagi.
  useEffect(() => {
    const original = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const res = await original(input, init);
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (res.status === 401 && url.includes("/api/") && !url.includes("/api/auth/")) {
        setStatus("out");
      }
      return res;
    };
    return () => {
      window.fetch = original;
    };
  }, []);

  useEffect(() => {
    if (isPublic) {
      if (pathname === "/beranda") {
        let disposed = false;
        fetch("/api/auth/me")
          .then(async (res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (disposed) return;
            if (!data || data.masuk === false) {
              setStatus("in");
              return;
            }
            const me: { ketua: boolean; peran?: string | null } = data;
            const tujuan = me.ketua ? "/" : me.peran === "pengguna" || !me.peran ? "/dashboard" : "/kerja";
            router.replace(tujuan);
          })
          .catch(() => {
            if (!disposed) setStatus("in");
          });
        return () => { disposed = true; };
      }
      queueMicrotask(() => setStatus("in"));
      return;
    }
    queueMicrotask(() => { setStatus("checking"); setNetError(false); checkSession(); });
    // Jika server tidak merespons dalam 8 detik, tampilkan kartu login dengan pesan, jangan berputar terus.
    const timer = setTimeout(() => {
      if (statusRef.current === "checking") {
        setNetError(true);
        setStatus("out");
      }
    }, 8000);
    return () => clearTimeout(timer);
  }, [pathname, isPublic, checkSession]);

  if (isPublic) {
    return (
      <>
        <GlobalNav />
        {children}
      </>
    );
  }

  if (status === "in") {
    return (
      <>
        <GlobalNav />
        {children}
      </>
    );
  }

  return (
    <>
      <GlobalNav />
      <div className={status === "out" ? "pointer-events-none select-none blur-[2px] opacity-60" : ""}>
        <AppSkeleton />
      </div>
      {status === "out" && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 capy-login-bg">
          <div className="w-full max-w-md">
            {netError && (
              <p role="alert" className="mb-3 text-sm text-amber-200 bg-amber-500/10 border border-amber-500/40 rounded-lg px-3 py-2">
                Server belum merespons. Pastikan backend berjalan di port 5000, lalu muat ulang halaman.
              </p>
            )}
            <LoginCard onSuccess={() => window.location.reload()} />
          </div>
        </div>
      )}
      {status === "checking" && (
        <p className="fixed bottom-4 right-20 text-xs text-slate-400">Memeriksa sesi...</p>
      )}
    </>
  );
}
