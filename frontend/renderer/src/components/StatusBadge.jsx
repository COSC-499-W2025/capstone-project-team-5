export default function StatusBadge({ children, style }) {
  return (
    <span
      className="rounded-full border border-border-hi bg-border px-3 py-1 font-mono text-2xs text-muted"
      style={style}
    >
      {children}
    </span>
  )
}
