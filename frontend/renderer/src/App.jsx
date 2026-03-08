import { useState, useEffect, createContext, useContext } from 'react'

// ── Context ────────────────────────────────────────────────────────────────
const AppContext = createContext(null)
const useApp = () => useContext(AppContext)

// ── Nav ────────────────────────────────────────────────────────────────────
const NAV = [
  { id: 'dashboard',  label: 'Dashboard',  icon: '◈' },
  { id: 'projects',   label: 'Projects',   icon: '◻' },
  { id: 'skills',     label: 'Skills',     icon: '◆' },
  { id: 'experience', label: 'Experience', icon: '◎' },
  { id: 'education',  label: 'Education',  icon: '▣' },
  { id: 'portfolio',  label: 'Portfolio',  icon: '⬡' },
  { id: 'resumes',    label: 'Resumes',    icon: '▤' },
  { id: 'consents',   label: 'Consents',   icon: '◬' },
]

// ── Root ───────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage]         = useState('dashboard')
  const [apiOk, setApiOk]       = useState(false)
  const [user,  setUser]        = useState(null)
  // null = loading, false = needs setup, true = ready
  const [consentReady, setConsentReady] = useState(null)

  useEffect(() => {
    async function boot() {
      // 1. Health check — if this fails the API is down
      try {
        await window.api.health()
        setApiOk(true)
      } catch {
        setApiOk(false)
        setConsentReady(false)
        return
      }

      // 2. Restore persisted username (may be absent on first run)
      const savedUsername = localStorage.getItem('zip2job_username')
      if (savedUsername) window.api.setUsername(savedUsername)

      // 3. If no saved username → definitely first-run, skip auth'd calls
      if (!savedUsername) {
        setConsentReady(false)
        return
      }

      // 4. We have a username — check consent & fetch user in parallel
      try {
        const [u, consent] = await Promise.all([
          window.api.getCurrentUser(),
          window.api.getLatestConsent(),
        ])
        setUser(u)
        setConsentReady(consent !== null)
      } catch {
        // Token expired / user deleted — send back to login
        localStorage.removeItem('zip2job_username')
        window.api.setUsername(null)
        setConsentReady(false)
      }
    }
    boot()
    const id = setInterval(async () => {
      try { await window.api.health(); setApiOk(true) }
      catch { setApiOk(false) }
    }, 10_000)
    return () => clearInterval(id)
  }, [])

  // Still booting
  if (consentReady === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-bg text-muted font-mono text-xs">
        Starting…
      </div>
    )
  }

  // First-run: no consent recorded yet
  if (!consentReady) {
    return (
      <ConsentSetup onDone={(username) => {
        localStorage.setItem('zip2job_username', username)
        window.api.setUsername(username)
        // Re-fetch user now that username is set
        window.api.getCurrentUser().then(setUser).catch(() => {})
        setConsentReady(true)
      }} />
    )
  }

  const current = NAV.find(n => n.id === page)

  return (
    <AppContext.Provider value={{ user, apiOk, page, setPage }}>
      <div className="flex h-screen overflow-hidden bg-bg text-ink">
        <Sidebar current={page} onNav={setPage} apiOk={apiOk} user={user} />
        <div className="flex flex-col flex-1 overflow-hidden">
          <Topbar title={current?.label ?? page} apiOk={apiOk} />
          <main className="flex-1 overflow-y-auto px-9 py-8">
            <PageRouter page={page} />
          </main>
        </div>
      </div>
    </AppContext.Provider>
  )
}

// ── Auth + Consent Setup (first-run wizard) ───────────────────────────────
//
// Steps:
//   'auth'    → Login / Register with username + password
//   'consent' → Review external services list, tick consent checkbox
//   'done'    → Success splash, then onDone(username) fires
//
function ConsentSetup({ onDone }) {
  const [authMode,        setAuthMode]        = useState('login')   // 'login' | 'register'
  const [username,        setUsername]        = useState('')
  const [password,        setPassword]        = useState('')
  const [availableData,   setAvailableData]   = useState(null)      // raw API response
  const [useExternal,     setUseExternal]     = useState(false)     // use_external_services
  const [checkedServices, setCheckedServices] = useState({})        // { serviceName: bool }
  const [step,            setStep]            = useState('auth')
  const [error,           setError]           = useState(null)
  const [loading,         setLoading]         = useState(false)

  // ── Step 1: auth ──────────────────────────────────────────────────────
  async function handleAuthSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const fn = authMode === 'register' ? window.api.register : window.api.login
      const res = await fn({ username: username.trim(), password })
      window.api.setUsername(res.username)
      // Load available services list for the consent step
      const data = await window.api.getAvailableServices()
      setAvailableData(data)
      // Pre-tick all external services by default
      const initial = {}
      ;(data.external_services ?? []).forEach(s => { initial[s] = true })
      setCheckedServices(initial)
      setUseExternal(true)
      setStep('consent')
    } catch (err) {
      let msg = err.message ?? 'Something went wrong.'
      try { msg = JSON.parse(msg).detail ?? msg } catch {}
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: consent ───────────────────────────────────────────────────
  async function handleConsentSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      // Build the external_services map: { serviceName: { allowed: bool } }
      const externalServicesMap = {}
      Object.entries(checkedServices).forEach(([name, checked]) => {
        externalServicesMap[name] = { allowed: checked }
      })
      await window.api.giveConsent({
        consent_given:         true,
        use_external_services: useExternal,
        external_services:     externalServicesMap,
        default_ignore_patterns: availableData?.common_ignore_patterns ?? [],
      })
      setStep('done')
      setTimeout(() => onDone(username.trim()), 800)
    } catch (err) {
      let msg = err.message ?? 'Consent submission failed.'
      try { msg = JSON.parse(msg).detail ?? msg } catch {}
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function toggleService(name) {
    setCheckedServices(prev => ({ ...prev, [name]: !prev[name] }))
  }

  return (
    <div className="flex h-screen items-center justify-center bg-bg text-ink">
      <div className="w-[480px] space-y-6">

        {/* Brand */}
        <div>
          <div className="text-2xl font-extrabold tracking-tight">
            Zip<span className="text-accent">2</span>Job
          </div>
          <p className="text-sm text-muted mt-1">
            {step === 'auth'
              ? authMode === 'login' ? 'Welcome back.' : 'Create your account.'
              : 'Review data permissions for your workspace.'}
          </p>
        </div>

        {/* ── Done splash ── */}
        {step === 'done' && (
          <div data-testid="consent-success" className="text-green-400 font-mono text-sm">
            ✓ All set — loading your workspace…
          </div>
        )}

        {/* ── Step 1: Login / Register ── */}
        {step === 'auth' && (
          <div className="space-y-5">
            {/* Mode tabs */}
            <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
              {['login', 'register'].map(mode => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => { setAuthMode(mode); setError(null) }}
                  className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                    authMode === mode ? 'bg-accent text-bg' : 'text-muted hover:text-ink'
                  }`}
                  data-testid={`auth-tab-${mode}`}
                >
                  {mode === 'login' ? 'Log In' : 'Sign Up'}
                </button>
              ))}
            </div>

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-muted">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="e.g. alice"
                  required
                  autoFocus
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent"
                  data-testid="auth-username"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-muted">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent"
                  data-testid="auth-password"
                />
              </div>

              {error && (
                <p data-testid="consent-error" className="text-xs text-red-400 font-mono">{error}</p>
              )}

              <button
                type="submit"
                disabled={!username.trim() || !password || loading}
                className="w-full btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
                data-testid="auth-submit"
              >
                {loading ? 'Please wait…' : authMode === 'login' ? 'Log In' : 'Create Account'}
              </button>
            </form>
          </div>
        )}

        {/* ── Step 2: Consent ── */}
        {step === 'consent' && (
          <form onSubmit={handleConsentSubmit} className="space-y-5">

            {/* Who's logged in */}
            <div className="font-mono text-xs text-muted">
              Signed in as <span className="text-ink font-semibold">{username}</span>
            </div>

            {/* Master toggle */}
            <label className="flex items-center gap-3 p-3 rounded-lg border border-border cursor-pointer hover:border-accent">
              <input
                type="checkbox"
                checked={useExternal}
                onChange={e => setUseExternal(e.target.checked)}
                className="accent-accent w-4 h-4"
                data-testid="consent-use-external"
              />
              <div>
                <div className="font-semibold text-sm">Allow external service access</div>
                <div className="text-xs text-muted">Enables GitHub, LinkedIn, and AI integrations</div>
              </div>
            </label>

            {/* Per-service list */}
            {useExternal && availableData?.external_services?.length > 0 && (
              <fieldset className="space-y-1.5">
                <legend className="text-xs font-semibold uppercase tracking-widest text-muted mb-2">
                  External Services
                </legend>
                {availableData.external_services.map(svc => (
                  <label
                    key={svc}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border cursor-pointer hover:border-accent text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={!!checkedServices[svc]}
                      onChange={() => toggleService(svc)}
                      className="accent-accent w-3.5 h-3.5"
                      data-testid={`consent-service-${svc.replace(/\s+/g, '-').toLowerCase()}`}
                    />
                    {svc}
                  </label>
                ))}
              </fieldset>
            )}

            {error && (
              <p data-testid="consent-error" className="text-xs text-red-400 font-mono">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
              data-testid="consent-submit"
            >
              {loading ? 'Saving…' : 'Save & Continue →'}
            </button>

            <p className="text-xs text-muted text-center">
              You can update these settings at any time from the Dashboard.
            </p>
          </form>
        )}

      </div>
    </div>
  )
}

// ── Sidebar ────────────────────────────────────────────────────────────────
function Sidebar({ current, onNav, apiOk, user }) {
  return (
    <aside className="w-[220px] min-w-[220px] bg-surface border-r border-border flex flex-col">
      <div className="px-5 py-6 border-b border-border">
        <div className="text-xl font-extrabold tracking-tight">
          Zip<span className="text-accent">2</span>Job
        </div>
        <div className="font-mono text-2xs text-muted mt-0.5 tracking-widest uppercase">
          Portfolio Engine
        </div>
      </div>

      <nav className="flex-1 p-3 flex flex-col gap-0.5">
        {NAV.map(item => (
          <button
            key={item.id}
            onClick={() => onNav(item.id)}
            className={`nav-item w-full text-left ${current === item.id ? 'active' : ''}`}
          >
            <span className="w-4 text-center text-sm">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-border space-y-1.5">
        {user && (
          <div className="font-mono text-2xs text-ink truncate">
            {user.username}
          </div>
        )}
        <div className="flex items-center gap-2 font-mono text-2xs text-muted">
          <span className={`w-1.5 h-1.5 rounded-full transition-colors ${
            apiOk
              ? 'bg-success shadow-[0_0_6px_theme(colors.success)] animate-pulse-dot'
              : 'bg-muted'
          }`} />
          {apiOk ? 'api online' : 'api offline'}
        </div>
      </div>
    </aside>
  )
}

// ── Topbar ─────────────────────────────────────────────────────────────────
function Topbar({ title, apiOk }) {
  return (
    <header
      className="h-[52px] border-b border-border flex items-center px-7 gap-4 flex-shrink-0"
      style={{ WebkitAppRegion: 'drag' }}
    >
      <span className="font-mono text-2xs text-muted uppercase tracking-widest">
        Zip2Job <span className="text-ink font-medium">{title}</span>
      </span>
      <div className="flex-1" />
      <span
        className="font-mono text-2xs bg-border border border-border-hi rounded-full px-3 py-1 text-muted"
        style={{ WebkitAppRegion: 'no-drag' }}
      >
        {apiOk ? 'localhost:8000' : 'disconnected'}
      </span>
    </header>
  )
}

// ── Router ─────────────────────────────────────────────────────────────────
function PageRouter({ page }) {
  switch (page) {
    case 'dashboard': return <Dashboard />
    default:          return <ComingSoon label={page} />
  }
}

// ── Dashboard ──────────────────────────────────────────────────────────────
function Dashboard() {
  const { user, apiOk } = useApp()

  const [stats, setStats] = useState({
    projects: null, skills: null, experience: null, resumes: null,
  })

  useEffect(() => {
    if (!apiOk || !user?.username) return
    const u = user.username
    Promise.allSettled([
      window.api.getProjects(),
      window.api.getSkills(),
      window.api.getWorkExperiences(u),
      window.api.getResumes(u),
    ]).then(([projects, skills, exp, resumes]) => {
      setStats({
        projects:   projects.status === 'fulfilled'  ? (projects.value?.length  ?? 0) : '—',
        skills:     skills.status   === 'fulfilled'  ? (skills.value?.length    ?? 0) : '—',
        experience: exp.status      === 'fulfilled'  ? (exp.value?.length       ?? 0) : '—',
        resumes:    resumes.status  === 'fulfilled'  ? (resumes.value?.length   ?? 0) : '—',
      })
    })
  }, [apiOk, user])

  const STAT_CARDS = [
    { label: 'Projects',   key: 'projects',   accent: true  },
    { label: 'Skills',     key: 'skills',     accent: false },
    { label: 'Experience', key: 'experience', accent: false },
    { label: 'Resumes',    key: 'resumes',    accent: false },
  ]

  return (
    <div className="animate-fade-up space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">
          {user ? `Hey, ${user.username}.` : 'Dashboard'}
        </h1>
        <p className="text-sm text-muted mt-1">
          {apiOk
            ? 'Your portfolio workspace is ready.'
            : 'Waiting for API connection…'}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {STAT_CARDS.map(({ label, key, accent }) => (
          <div key={key} className="stat-card">
            <div className="font-mono text-2xs text-muted uppercase tracking-widest">
              {label}
            </div>
            <div className={`text-4xl font-extrabold tracking-tight mt-1 ${accent ? 'text-accent' : ''}`}>
              {stats[key] ?? <span className="text-muted text-2xl">—</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <div className="divider-label">Quick Actions</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: '◻', label: 'Upload Project',     desc: 'Analyze a new zip artifact'   },
            { icon: '⬡', label: 'Generate Portfolio',  desc: 'Build from analyzed projects' },
            { icon: '▤', label: 'Generate Resume',     desc: 'Tailor a resume to a job'     },
          ].map(a => (
            <div key={a.label} className="card cursor-pointer group">
              <div className="text-2xl mb-3 opacity-40 group-hover:opacity-80 transition-opacity">
                {a.icon}
              </div>
              <div className="font-bold text-sm mb-1">{a.label}</div>
              <div className="text-xs text-muted">{a.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Coming Soon stub ───────────────────────────────────────────────────────
function ComingSoon({ label }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-3 text-muted animate-fade-up">
      <span className="text-5xl opacity-20">◈</span>
      <p className="font-mono text-xs uppercase tracking-widest">
        {label} — coming soon
      </p>
    </div>
  )
}