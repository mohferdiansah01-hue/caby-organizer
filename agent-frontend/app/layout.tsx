import type { Metadata, Viewport } from "next";
import { Inter, Zilla_Slab, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import AuthGuard from "./auth-guard";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const zillaSlab = Zilla_Slab({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-zilla-slab",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});


export const metadata: Metadata = {
  authors: [{ name: "Moh. Ferdiansah" }],
  creator: "Moh. Ferdiansah",
  title: "Caby Organizer | Aplikasi kepanitiaan",
  description: "Pantau kerja panitia, atur jadwal, dan kumpulkan hasil kerja tim dalam satu tempat.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Caby Organizer",
  },
};

export const viewport: Viewport = {
  themeColor: "#FFD36E",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className={`${inter.variable} ${zillaSlab.variable} ${jetbrainsMono.variable}`} data-theme="kuning" suppressHydrationWarning>
      <head>
      </head>
      <body className="font-sans" suppressHydrationWarning><AuthGuard>{children}</AuthGuard></body>
    </html>
  );
}
