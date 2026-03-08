import { useState, useEffect, useRef, createContext, useContext } from 'react'

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
]

// ── Root ───────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage]   = useState('dashboard')
  const [apiOk, setApiOk] = useState(false)
  const [user,  setUser]  = useState(null)

  useEffect(() => {
    async function boot() {
      try {
        await window.api.health()
        setApiOk(true)
        const u = await window.api.getCurrentUser()
        setUser(u)
      } catch {
        setApiOk(false)
      }
    }
    boot()
    const id = setInterval(async () => {
      try { await window.api.health(); setApiOk(true) }
      catch { setApiOk(false) }
    }, 10_000)
    return () => clearInterval(id)
  }, [])

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
  const fileInputRef = useRef(null)

  const [stats, setStats] = useState({
    projects: null, skills: null, experience: null, resumes: null,
  })
  const [uploadState, setUploadState] = useState({
    loading: false,
    message: '',
    error: false,
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

  async function refreshStats() {
    if (!apiOk || !user?.username) return
    const u = user.username

    const [projects, skills, exp, resumes] = await Promise.allSettled([
      window.api.getProjects(),
      window.api.getSkills(),
      window.api.getWorkExperiences(u),
      window.api.getResumes(u),
    ])

    setStats({
      projects: projects.status === 'fulfilled' ? (projects.value?.length ?? 0) : '—',
      skills: skills.status === 'fulfilled' ? (skills.value?.length ?? 0) : '—',
      experience: exp.status === 'fulfilled' ? (exp.value?.length ?? 0) : '—',
      resumes: resumes.status === 'fulfilled' ? (resumes.value?.length ?? 0) : '—',
    })
  }

  function startUploadFlow() {
    if (uploadState.loading || !apiOk) return
    fileInputRef.current?.click()
  }

  async function onUploadFileSelected(event) {
    const [file] = event.target.files || []
    event.target.value = ''
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setUploadState({
        loading: false,
        error: true,
        message: 'Please select a .zip file.',
      })
      return
    }

    setUploadState({ loading: true, message: 'Uploading project archive...', error: false })

    try {
      const bytes = await file.arrayBuffer()
      const result = await window.api.createProjectUpload({
        name: file.name,
        type: file.type || 'application/zip',
        bytes,
      })

      await refreshStats()

      const createdCount = result?.created_count ?? 0
      const mergedCount = result?.merged_count ?? 0
      setUploadState({
        loading: false,
        error: false,
        message: `Upload complete. Created ${createdCount}, merged ${mergedCount}.`,
      })
    } catch (err) {
      setUploadState({
        loading: false,
        error: true,
        message: err?.message || 'Upload failed. Please try again.',
      })
    }
  }

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
        <input
          ref={fileInputRef}
          type="file"
          accept=".zip,application/zip"
          className="hidden"
          onChange={onUploadFileSelected}
        />
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: '◻', label: 'Upload Project',     desc: 'Analyze a new zip artifact'   },
            { icon: '⬡', label: 'Generate Portfolio',  desc: 'Build from analyzed projects' },
            { icon: '▤', label: 'Generate Resume',     desc: 'Tailor a resume to a job'     },
          ].map(a => (
            <button
              key={a.label}
              type="button"
              className="card cursor-pointer group text-left disabled:opacity-60"
              onClick={a.label === 'Upload Project' ? startUploadFlow : undefined}
              disabled={a.label === 'Upload Project' ? (uploadState.loading || !apiOk) : true}
            >
              <div className="text-2xl mb-3 opacity-40 group-hover:opacity-80 transition-opacity">
                {a.icon}
              </div>
              <div className="font-bold text-sm mb-1">{a.label}</div>
              <div className="text-xs text-muted">{a.desc}</div>
            </button>
          ))}
        </div>
        {uploadState.message && (
          <p className={`mt-3 text-xs ${uploadState.error ? 'text-red-400' : 'text-muted'}`}>
            {uploadState.message}
          </p>
        )}
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