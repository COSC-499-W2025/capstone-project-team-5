export default function ComingSoonPage({ page }) {
  return (
    <div className="flex animate-fade-up flex-col items-center justify-center gap-3 py-24 text-muted">
      <span className="text-5xl opacity-20">◈</span>
      <p className="font-mono text-xs uppercase tracking-widest">{page} — coming soon</p>
    </div>
  )
}
