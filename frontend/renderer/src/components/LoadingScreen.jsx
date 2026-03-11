export default function LoadingScreen({ message = 'Loading…' }) {
  return (
    <div className="flex h-screen items-center justify-center bg-bg font-mono text-xs text-muted">
      {message}
    </div>
  )
}
