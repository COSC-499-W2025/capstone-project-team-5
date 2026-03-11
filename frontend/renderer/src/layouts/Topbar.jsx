import StatusBadge from '../components/StatusBadge'

export default function Topbar({ title, apiOk }) {
  return (
    <header
      className="flex h-[52px] flex-shrink-0 items-center gap-4 border-b border-border px-7"
      style={{ WebkitAppRegion: 'drag' }}
    >
      <span className="font-mono text-2xs uppercase tracking-widest text-muted">
        Zip2Job <span className="font-medium text-ink">{title}</span>
      </span>
      <div className="flex-1" />
      <StatusBadge style={{ WebkitAppRegion: 'no-drag' }}>
        {apiOk ? 'localhost:8000' : 'disconnected'}
      </StatusBadge>
    </header>
  )
}
