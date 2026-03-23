import { NAV_ITEMS } from '../app/navigation/navItems'
import ZippyMenu from '../components/onboarding/ZippyMenu'

export default function Sidebar({ current, onNav, apiOk, user, onLogout, onStartTour, onStartSetup }) {
  return (
    <aside className="flex min-w-[220px] w-[220px] flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-5 py-6">
        <div className="text-xl font-extrabold tracking-tight">
          Zip<span className="text-accent">2</span>Job
        </div>
        <div className="mt-0.5 font-mono text-2xs uppercase tracking-widest text-muted">
          Portfolio Engine
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            data-tour-id={item.id}
            onClick={() => onNav(item.id)}
            className={`nav-item w-full text-left ${current === item.id ? 'active' : ''}`}
          >
            <span className="w-4 text-center text-sm">{item.icon}</span>
            {item.label}
          </button>
        ))}

        {onStartTour && (
          <div className="mt-auto pt-2">
            <ZippyMenu currentPage={current} onStartTour={onStartTour} onStartSetup={onStartSetup} />
          </div>
        )}
      </nav>

      <div className="space-y-1.5 border-t border-border px-5 py-4">
        {user && <div className="truncate font-mono text-2xs text-ink">{user.username}</div>}
        <div className="flex items-center gap-2 font-mono text-2xs text-muted">
          <span
            className={`h-1.5 w-1.5 rounded-full transition-colors ${
              apiOk
                ? 'bg-success shadow-[0_0_6px_theme(colors.success)] animate-pulse-dot'
                : 'bg-muted'
            }`}
          />
          {apiOk ? 'api online' : 'api offline'}
        </div>
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="mt-1 w-full text-left font-mono text-2xs text-muted hover:text-ink transition-colors"
          >
            ⎋ Log out
          </button>
        )}
      </div>
    </aside>
  )
}
