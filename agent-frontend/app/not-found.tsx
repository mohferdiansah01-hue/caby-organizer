import Link from "next/link";
import Capy from "./components/Capy";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-[#FFF6E3] flex items-center justify-center px-5">
      <div className="text-center space-y-4 max-w-sm">
        <Capy mood="tidak_ditemukan" size={160} className="mx-auto" />
        <h1 className="font-display text-3xl font-bold text-[#5B3A29]">Halaman tidak ditemukan</h1>
        <p className="text-sm text-[#7A5C48]">Mungkin alamatnya salah, atau halamannya sudah dipindah.</p>
        <Link href="/beranda" className="inline-block px-6 py-3 rounded-full bg-[#5B3A29] text-[#FFF6E3] font-bold text-sm">Ke beranda</Link>
      </div>
    </main>
  );
}
