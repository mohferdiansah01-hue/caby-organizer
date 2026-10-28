export default function AppSkeleton() {
  return (
    <div aria-hidden="true" className="min-h-screen bg-app px-4 py-6 sm:px-8">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded-lg bg-slate-800/60 motion-safe:animate-pulse" />
        <div className="h-28 rounded-3xl bg-slate-900/60 border border-[#5B3A29]/15 motion-safe:animate-pulse" />
        <div className="grid grid-cols-2 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-slate-900/60 border border-[#5B3A29]/15 motion-safe:animate-pulse" />
          ))}
        </div>
        <div className="h-48 rounded-3xl bg-slate-900/60 border border-[#5B3A29]/15 motion-safe:animate-pulse" />
      </div>
    </div>
  );
}
