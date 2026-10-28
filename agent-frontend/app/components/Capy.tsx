import Image from "next/image";

// Semua ekspresi Caby (35 gambar). Setiap keadaan di aplikasi punya ekspresi sendiri.
// Gambar bersifat dekoratif: maknanya sudah ada di teks di sampingnya.
const S = (f: string) => ({ src: `/stickers/${f}.webp`, w: 227, h: 227 });
const R = (f: string) => ({ src: `/${f}.webp`, w: 240, h: 240 });
const W = (f: string) => ({ src: `/capy/${f}.webp`, w: 240, h: 240 });

export const EKSPRESI = {
  // sapaan dan identitas
  sapa: R("capy-idle"),          // masuk, selamat datang
  wow: R("capy-excited"),        // hal baru, ajakan
  intip: R("capy-peek"),         // belum ada catatan
  pikir: R("capy-thinking"),     // sedang memikirkan sesuatu
  ketua: S("cap"),               // Ketua acara
  tanya: S("capi_text"),         // Tanya Capy
  memuat: S("thinking"),         // sedang memuat / berpikir
  // hasil dan status
  semangat: S("cheer"),          // acara dibuat, berhasil
  terima: S("wink"),             // tugas diterima
  tertawa: S("laughing"),        // tim bekerja bersama
  beres: S("cool"),              // semua sudah beres
  bangga: S("smug"),             // acara hampir/sudah selesai
  kaget: S("surprised"),         // perlu perhatian
  bahaya: S("angry"),            // tindakan berbahaya, konfirmasi
  lelah: S("tired"),             // tugas lewat tenggat
  semangat_kejar: S("workout"),  // tenggat dekat, ayo kejar
  // keadaan kosong dan tunggu
  ajak: S("hiking"),             // belum ada acara
  kosong: S("sleepy"),           // belum ada tugas
  pesan: S("headphones"),        // belum ada pesan
  tunggu: S("kopi"),             // menunggu jawaban orang lain
  tutup: S("night_coffee"),      // acara ditutup
  hujan: S("rain"),              // acara sepi / belum ada aktivitas
  malu: S("shy"),                // belum ada keputusan / maaf
  istirahat: S("boba"),          // tips, istirahat
  menjauh: S("back"),            // fitur belum tersedia
  privasi: S("hoodie"),          // keamanan: batas percobaan, akses
  // galat
  galat: S("stressed_laptop"),   // galat umum
  galat_jaringan: S("crying"),   // server tidak bisa dihubungi
  tidak_ditemukan: S("frog"),    // halaman tidak ditemukan
  // gambar Capy penuh
  kopi_dulu: W("capy-5"),
  dukung: W("capy-2"),
  santai: W("capy-3"),
  peringatan: W("capy-4"),
  ketua_kaget: W("capy-1"),
  tips: W("capy-6"),
} as const;

export type Ekspresi = keyof typeof EKSPRESI;

export default function Capy({ mood, size = 96, className = "" }: { mood: Ekspresi; size?: number; className?: string }) {
  const e = EKSPRESI[mood];
  return (
    <Image src={e.src} alt="" aria-hidden="true" width={e.w} height={e.h}
      style={{ width: size, height: "auto" }} className={`object-contain ${className}`} />
  );
}
