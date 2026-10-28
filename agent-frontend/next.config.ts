import os from "os";
import type { NextConfig } from "next";
import withPWAInit from "@brainwires/next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
});

const flaskBackend = process.env.FLASK_BACKEND_URL || "http://localhost:5000";
const FLASK_URL = (/^[a-z][a-z0-9+.-]*:\/\//i.test(flaskBackend) ? flaskBackend : `http://${flaskBackend}`).replace(/\/+$/, "");

// Alamat LAN yang boleh memuat resource saat `next dev` dibuka dari perangkat lain (HP, laptop lain).
// Next.js memblokir resource dev dari host yang tidak terdaftar, akibatnya React tidak ter-hydrate
// dan halaman terjebak di kerangka "Memeriksa sesi...". Karena itu semua IPv4 LAN milik mesin ini
// otomatis diizinkan. Tambahan manual bisa lewat env: DEV_ALLOWED_ORIGINS=192.168.1.5,10.0.0.7
function ipLanMesin(): string[] {
  const hasil: string[] = [];
  for (const daftar of Object.values(os.networkInterfaces())) {
    for (const alamat of daftar ?? []) {
      if (alamat.family === "IPv4" && !alamat.internal) hasil.push(alamat.address);
    }
  }
  return hasil;
}

const DEV_ORIGINS = Array.from(
  new Set([
    ...ipLanMesin(),
    ...(process.env.DEV_ALLOWED_ORIGINS || "")
      .split(",")
      .map((h) => h.trim())
      .filter(Boolean),
  ]),
);

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: DEV_ORIGINS,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "same-origin" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${FLASK_URL}/api/:path*`,
      },
    ];
  },
};

export default withPWA(nextConfig);
