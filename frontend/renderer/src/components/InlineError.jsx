export default function InlineError({ message, className = '' }) {
  if (!message) {
    return null
  }

  return <p className={`text-xs text-red-400 ${className}`.trim()}>{message}</p>
}
