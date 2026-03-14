import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

const STAT_CARDS = [
  { label: 'Projects', key: 'projects', accent: true },
  { label: 'Skills', key: 'skills', accent: false },
  { label: 'Experience', key: 'experience', accent: false },
  { label: 'Resumes', key: 'resumes', accent: false },
]

const QUICK_ACTIONS = [
  { icon: '◻', label: 'Upload Project', desc: 'Analyze a new zip artifact' },
  { icon: '⬡', label: 'Generate Portfolio', desc: 'Build from analyzed projects' },
  { icon: '▤', label: 'Generate Resume', desc: 'Tailor a resume to a job' },
]

export default function DashboardPage() {
  const { user, apiOk, setPage, setUploadHighlights } = useApp()
  const fileInputRef = useRef(null)
  const isMountedRef = useRef(true)
  const uploadAbortControllerRef = useRef(null)
  const progressTickRef = useRef(null)

  const [stats, setStats] = useState({
    projects: null,
    skills: null,
    experience: null,
    resumes: null,
  })
  const [uploadState, setUploadState] = useState({
    loading: false,
    message: '',
    error: false,
    progress: 0,   // 0-100; -1 = indeterminate pulse
    step: '',      // short label shown inside the bar
  })

  useEffect(() => {
    return () => {
      isMountedRef.current = false
      uploadAbortControllerRef.current?.abort()
      clearInterval(progressTickRef.current)
    }
  }, [])

  async function loadDashboardStats() {
    if (!apiOk || !user?.username) {
      return
    }

    const username = user.username
    const [projects, skills, experience, resumes] = await Promise.allSettled([
      window.api.getProjects(),
      window.api.getSkills(),
      window.api.getWorkExperiences(username),
      window.api.getResumes(username),
    ])

    const projectItems = projects.status === 'fulfilled' ? getProjectItems(projects.value) : []
    if (!isMountedRef.current) {
      return
    }

    setStats({
      projects: projects.status === 'fulfilled' ? projectItems.length : '—',
      skills: skills.status === 'fulfilled' ? (skills.value?.length ?? 0) : '—',
      experience: experience.status === 'fulfilled' ? (experience.value?.length ?? 0) : '—',
      resumes: resumes.status === 'fulfilled' ? (resumes.value?.length ?? 0) : '—',
    })
  }

  useEffect(() => {
    if (!apiOk || !user?.username) {
      return
    }

    loadDashboardStats()
  }, [apiOk, user])

  async function refreshStats() {
    await loadDashboardStats()
  }

  function startUploadFlow() {
    if (uploadState.loading || !apiOk) {
      return
    }

    fileInputRef.current?.click()
  }

  function handleQuickAction(actionLabel) {
    if (actionLabel === 'Upload Project') {
      startUploadFlow()
      return
    }

    if (actionLabel === 'Generate Resume' && apiOk) {
      setPage('resumes')
    }
  }

  async function onUploadFileSelected(event) {
    const [file] = event.target.files || []
    event.target.value = ''

    if (!file) {
      return
    }

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setUploadState({
        loading: false,
        error: true,
        message: 'Please select a .zip file.',
        progress: 0,
        step: '',
      })
      return
    }

    setUploadState({ loading: true, message: 'Reading file…', error: false, progress: 10, step: 'Reading' })

    // Tick +1% every 800 ms, capped at 90% — keeps the bar visibly moving
    // for slow uploads without racing ahead of the server response.
    clearInterval(progressTickRef.current)
    progressTickRef.current = setInterval(() => {
      setUploadState((s) => {
        if (!s.loading || s.progress >= 90) return s
        const next = s.progress + 1
        const step = next < 25 ? 'Reading' : 'Uploading'
        const message = next < 25 ? 'Reading file…' : `Uploading ${file.name}…`
        return { ...s, progress: next, step, message }
      })
    }, 800)

    try {
      uploadAbortControllerRef.current?.abort()
      uploadAbortControllerRef.current = new AbortController()

      const bytes = await file.arrayBuffer()

      if (!isMountedRef.current) return

      const result = await window.api.createProjectUpload({
        name: file.name,
        type: file.type || 'application/zip',
        bytes,
      })

      clearInterval(progressTickRef.current)

      if (!isMountedRef.current) {
        return
      }

      // Server has finished scanning; reflect that before we process the result
      setUploadState((s) => ({ ...s, message: 'Processing projects…', progress: 75, step: 'Scanning' }))

      const actions = result?.actions ?? []
      const created = actions
        .filter((action) => action?.action === 'created')
        .map((action) => action.project_id)
      const merged = actions
        .filter((action) => action?.action === 'merged')
        .map((action) => action.project_id)

      setUploadHighlights({ created, merged })

      setUploadState((s) => ({ ...s, message: 'Refreshing stats…', progress: 90, step: 'Finishing' }))
      await refreshStats()
      if (!isMountedRef.current) {
        return
      }

      const createdCount = result?.created_count ?? 0
      const mergedCount = result?.merged_count ?? 0
      setUploadState({
        loading: false,
        error: false,
        message: `Upload complete. Created ${createdCount}, merged ${mergedCount}.`,
        progress: 100,
        step: 'Done',
      })

      // Small pause so the user can see 100% before navigating away.
      await new Promise((r) => setTimeout(r, 1200))
      if (!isMountedRef.current) return
      setPage('projects')
    } catch (error) {
      clearInterval(progressTickRef.current)
      if (error?.name === 'AbortError' || !isMountedRef.current) {
        return
      }

      setUploadState({
        loading: false,
        error: true,
        message: error?.message || 'Upload failed. Please try again.',
        progress: 0,
        step: '',
      })
    } finally {
      uploadAbortControllerRef.current = null
    }
  }

  return (
    <div className="animate-fade-up space-y-8">
      <PageHeader
        title={user ? `Hey, ${user.username}.` : 'Dashboard'}
        description={apiOk ? 'Your portfolio workspace is ready.' : 'Waiting for API connection…'}
      />

      <div className="grid grid-cols-4 gap-3">
        {STAT_CARDS.map(({ label, key, accent }) => (
          <div key={key} className="stat-card">
            <div className="font-mono text-2xs uppercase tracking-widest text-muted">{label}</div>
            <div className={`mt-1 text-4xl font-extrabold tracking-tight ${accent ? 'text-accent' : ''}`}>
              {stats[key] ?? <span className="text-2xl text-muted">—</span>}
            </div>
          </div>
        ))}
      </div>

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
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              type="button"
              className="card group cursor-pointer text-left disabled:opacity-60"
              onClick={() => handleQuickAction(action.label)}
              disabled={
                action.label === 'Upload Project'
                  ? uploadState.loading || !apiOk
                  : action.label === 'Generate Resume'
                    ? !apiOk
                    : true
              }
            >
              <div className="mb-3 text-2xl opacity-40 transition-opacity group-hover:opacity-80">
                {action.icon}
              </div>
              <div className="mb-1 text-sm font-bold">{action.label}</div>
              <div className="text-xs text-muted">{action.desc}</div>
            </button>
          ))}
        </div>
        {uploadState.loading && (
          <div className="mt-4 space-y-1.5">
            <div className="flex items-center justify-between font-mono text-2xs text-muted uppercase tracking-widest">
              <span>{uploadState.step}</span>
              <span>{uploadState.progress}%</span>
            </div>
            <div className="h-1 w-full overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-accent transition-all duration-500 ease-out"
                style={{ width: `${uploadState.progress}%` }}
              />
            </div>
            <p className="text-xs text-muted">{uploadState.message}</p>
          </div>
        )}
        {!uploadState.loading && uploadState.message && (
          <p
            className={`mt-3 text-xs ${uploadState.error ? 'text-red-400' : 'text-muted'}`}
            onMouseEnter={() => {
              setUploadState((current) => ({ ...current, message: '' }))
            }}
          >
            {uploadState.message}
          </p>
        )}
      </div>
    </div>
  )
}
