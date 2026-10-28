import { connection } from "next/server";
import LoginCard, { type DemoAccount } from "../components/LoginCard";
import Capy from "../components/Capy";

const AKUN_DEMO: DemoAccount[] = [
  { label: "Ketua acara", username: "juri.ketua", password: "GebyarJuri2027!" },
  { label: "Koordinator Acara", username: "juri.acara", password: "GebyarJuri2027!" },
  { label: "Koordinator PDD", username: "juri.pdd", password: "GebyarJuri2027!" },
  { label: "Koordinator Humas", username: "juri.humas", password: "GebyarJuri2027!" },
  { label: "Koordinator Konsumsi", username: "juri.konsumsi", password: "GebyarJuri2027!" },
  { label: "Anggota", username: "juri.anggota", password: "GebyarJuri2027!" },
  { label: "Admin juri", username: "juri.admin", password: "AdminJuri2027!" },
];

export default async function LoginPage() {
  await connection();
  const demoMode = process.env.CAPY_DEMO_MODE === "1" || process.env.NODE_ENV === "development";
  const demoAccounts = demoMode ? AKUN_DEMO : [];

  return (
    <main className="min-h-screen bg-[#FFF6E3] text-[#5B3A29] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-5xl grid md:grid-cols-2 gap-8 items-center">
        <section className="bg-[#FFD36E] rounded-[2rem] p-8 flex flex-col items-center gap-6 text-center">
          <Capy mood="sapa" size={220} />
          <p className="max-w-sm rounded-2xl border border-[#5B3A29]/10 bg-[#FFFDF7] px-5 py-4 text-sm text-[#5B3A29]">
            Hai! Masuk dulu, ya. Setelah itu kamu bisa buat acara atau gabung dengan password dari panitia.
          </p>
        </section>
        <div className="w-full max-w-md mx-auto"><LoginCard demoAccounts={demoAccounts} /></div>
      </div>
    </main>
  );
}
