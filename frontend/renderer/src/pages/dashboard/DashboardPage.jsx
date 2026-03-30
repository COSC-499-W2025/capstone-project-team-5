import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import ActivityHeatmap from '../../components/ActivityHeatmap'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

const STAT_CARDS = [
  { label: 'Projects', key: 'projects', accent: true },
  { label: 'Skills', key: 'skills', accent: true },
  { label: 'Experience', key: 'experience', accent: true },
  { label: 'Resumes', key: 'resumes', accent: true },
]

const QUICK_ACTIONS = [
  { icon: '◻', label: 'Upload Project', desc: 'Analyze a new zip artifact' },
  { icon: '⬡', label: 'Generate Portfolio', desc: 'Build from analyzed projects' },
  { icon: '▤', label: 'Generate Resume', desc: 'Tailor a resume to a job' },
]

// Messages shown during each upload phase, cycled at regular intervals.
const UPLOAD_MESSAGES = {
  reading: [
    'Reading your file…',
    'Checking archive integrity…',
    'Unpacking file headers…',
  ],
  uploading: [
    'Sending to server…',
    'Upload in progress…',
    'Transferring data…',
    'Almost there…',
  ],
  scanning: [
    'Scanning project structure…',
    'Detecting repositories…',
    'Identifying languages…',
    'Mapping file tree…',
    'Counting contributions…',
  ],
}

function getProjectCount(payload) {
  if (!payload) {
    return 0
  }

  const total = payload?.pagination?.total
  if (Number.isFinite(total)) {
    return total
  }

  return getProjectItems(payload).length
}

function getCollectionCount(payload) {
  if (!payload) {
    return 0
  }

  if (Array.isArray(payload)) {
    return payload.length
  }

  const total = payload?.pagination?.total
  if (Number.isFinite(total)) {
    return total
  }

  if (Array.isArray(payload?.items)) {
    return payload.items.length
  }

  return 0
}

function formatCardCount(count) {
  return Number.isFinite(count) && count > 0 ? count : '—'
}

export default function DashboardPage() {
  const { user, apiOk, setPage, setUploadHighlights } = useApp()
  const fileInputRef = useRef(null)
  const isMountedRef = useRef(true)
  const uploadAbortControllerRef = useRef(null)
  const progressTickRef = useRef(null)
  const messageTickRef = useRef(null)
  const messageIndexRef = useRef(0)

  const [stats, setStats] = useState({
    projects: '—',
    skills: '—',
    experience: '—',
    resumes: '—',
  })
  const [uploadState, setUploadState] = useState({
    loading: false,
    message: '',
    error: false,
    progress: 0,   // 0-100; -1 = indeterminate pulse
    step: '',      // short label shown inside the bar
  })

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      uploadAbortControllerRef.current?.abort()
      clearInterval(progressTickRef.current)
      clearInterval(messageTickRef.current)
    }
  }, [])

  async function loadDashboardStats() {
    if (!apiOk) {
      return
    }

    const username =
      user?.username ||
      (typeof window.api.getUsername === 'function' ? window.api.getUsername() : null) ||
      localStorage.getItem('zip2job_username')

    const api = window.api
    const defaultStats = {
      projects: '—',
      skills: '—',
      experience: '—',
      resumes: '—',
    }

    if (!api) {
      if (isMountedRef.current) {
        setStats(defaultStats)
      }
      return
    }

    try {
      const projectsPromise =
        typeof api.getProjects === 'function'
          ? api.getProjects()
          : Promise.reject(new Error('Projects API unavailable'))
      const skillsPromise =
        typeof api.getSkills === 'function'
          ? api.getSkills()
          : Promise.reject(new Error('Skills API unavailable'))
      const experiencePromise =
        username && typeof api.getWorkExperiences === 'function'
          ? api.getWorkExperiences(username)
          : Promise.resolve([])
      const resumesPromise =
        username && typeof api.getResumes === 'function'
          ? api.getResumes(username)
          : Promise.resolve([])

      const [projects, skills, experience, resumes] = await Promise.allSettled([
        projectsPromise,
        skillsPromise,
        experiencePromise,
        resumesPromise,
      ])

      if (!isMountedRef.current) {
        return
      }

      const projectCount =
        projects.status === 'fulfilled' ? getProjectCount(projects.value) : 0
      const skillsCount =
        skills.status === 'fulfilled' ? getCollectionCount(skills.value) : 0

      setStats({
        projects:
          projects.status === 'fulfilled' ? formatCardCount(projectCount) : '—',
        skills: skills.status === 'fulfilled' ? formatCardCount(skillsCount) : '—',
        experience:
          experience.status === 'fulfilled'
            ? formatCardCount(getCollectionCount(experience.value))
            : '—',
        resumes:
          resumes.status === 'fulfilled' ? formatCardCount(getCollectionCount(resumes.value)) : '—',
      })


    } catch {
      if (isMountedRef.current) {
        setStats(defaultStats)
      }
    }
  }

  useEffect(() => {
    if (!apiOk) {
      return
    }

    loadDashboardStats()
  }, [apiOk, user?.username])

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

    // Scale the progress tick interval based on file size so smaller zips feel
    // snappier. 1 MB → ~600 ms/tick, 50 MB → ~1200 ms/tick, clamped to [400, 1500].
    const sizeMB = file.size / (1024 * 1024)
    const tickMs = Math.min(1500, Math.max(400, 400 + sizeMB * 16))

    setUploadState({ loading: true, message: UPLOAD_MESSAGES.reading[0], error: false, progress: 10, step: 'Reading' })

    // Progress tick: uses asymptotic easing toward 95% so the bar always keeps
    // visibly moving while waiting for the server — no hard freeze at a cap.
    // Each tick adds 18% of the remaining gap, so progress slows as it
    // approaches 95% but never fully stops.
    clearInterval(progressTickRef.current)
    progressTickRef.current = setInterval(() => {
      setUploadState((s) => {
        if (!s.loading || s.progress >= 95) return s
        const remaining = 95 - s.progress
        const next = Math.min(95, s.progress + Math.max(0.5, remaining * 0.18))
        const rounded = Math.round(next * 10) / 10   // 1 decimal place
        const step = rounded < 25 ? 'Reading' : 'Uploading'
        return { ...s, progress: rounded, step }
      })
    }, tickMs)

    // Message tick: cycle through phase-appropriate messages every 2.5 s.
    clearInterval(messageTickRef.current)
    messageIndexRef.current = 0
    messageTickRef.current = setInterval(() => {
      setUploadState((s) => {
        if (!s.loading) return s
        const pool =
          s.progress < 25
            ? UPLOAD_MESSAGES.reading
            : s.step === 'Scanning'
              ? UPLOAD_MESSAGES.scanning
              : UPLOAD_MESSAGES.uploading
        messageIndexRef.current = (messageIndexRef.current + 1) % pool.length
        return { ...s, message: pool[messageIndexRef.current] }
      })
    }, 2500)

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
      clearInterval(messageTickRef.current)
      progressTickRef.current = null
      messageTickRef.current = null

      if (!isMountedRef.current) return

      // Snap to 90%+ (never go backwards) and switch to scanning phase messages.
      messageIndexRef.current = 0
      setUploadState((s) => ({
        ...s,
        message: UPLOAD_MESSAGES.scanning[0],
        progress: Math.max(s.progress, 90),
        step: 'Scanning',
      }))

      // Tick from current → 99 at a fast fixed pace during result processing.
      progressTickRef.current = setInterval(() => {
        setUploadState((s) => {
          if (!s.loading || s.progress >= 99) return s
          return { ...s, progress: s.progress + 1 }
        })
      }, 300)

      // Cycle scanning messages.
      messageTickRef.current = setInterval(() => {
        setUploadState((s) => {
          if (!s.loading) return s
          messageIndexRef.current = (messageIndexRef.current + 1) % UPLOAD_MESSAGES.scanning.length
          return { ...s, message: UPLOAD_MESSAGES.scanning[messageIndexRef.current] }
        })
      }, 1800)

      const actions = result?.actions ?? []
      const created = actions
        .filter((action) => action?.action === 'created')
        .map((action) => action.project_id)
      const merged = actions
        .filter((action) => action?.action === 'merged')
        .map((action) => action.project_id)

      setUploadHighlights({ created, merged })

      // Fire-and-forget: refresh stats in the background so it never blocks
      // the progress bar from reaching 100%.
      refreshStats().catch(() => {})

      const createdCount = result?.created_count ?? 0
      const mergedCount = result?.merged_count ?? 0
      const summary =
        createdCount > 0 && mergedCount > 0
          ? `Added ${createdCount} new project${createdCount !== 1 ? 's' : ''}, updated ${mergedCount} existing.`
          : createdCount > 0
            ? `${createdCount} new project${createdCount !== 1 ? 's' : ''} created successfully!`
            : mergedCount > 0
              ? `${mergedCount} project${mergedCount !== 1 ? 's' : ''} updated with new files.`
              : 'Upload complete!'

      clearInterval(messageTickRef.current)
      clearInterval(progressTickRef.current)
      progressTickRef.current = null
      messageTickRef.current = null
      setUploadState({
        loading: false,
        error: false,
        message: summary,
        progress: 100,
        step: 'Done',
      })
      window.dispatchEvent(new CustomEvent('z2j:upload-complete'))

      // Small pause so the user can see 100% before navigating away.
      await new Promise((r) => setTimeout(r, 1200))
      if (!isMountedRef.current) return
      setPage('projects')
    } catch (error) {
      clearInterval(progressTickRef.current)
      clearInterval(messageTickRef.current)
      progressTickRef.current = null
      messageTickRef.current = null
      if (error?.name === 'AbortError' || !isMountedRef.current) return

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
        {STAT_CARDS.map(({ label, key, accent }) => {
          const value = stats[key]
          const shouldAccent = accent && value !== '—'

          return (
            <div key={key} className="stat-card">
              <div className="font-mono text-2xs uppercase tracking-widest text-muted">{label}</div>
              <div className={`mt-1 text-3xl font-extrabold tracking-tight ${shouldAccent ? 'text-accent' : ''}`}>
                {value ?? <span className="text-xl text-muted">—</span>}
              </div>
            </div>
          )
        })}
      </div>

      <ActivityHeatmap />

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
          {QUICK_ACTIONS.map((action) => {
            const isUpload = action.label === 'Upload Project';
            // Show pulse only if no projects have been uploaded
            const showPulse = isUpload && (stats.projects === '—' || stats.projects === 0 || stats.projects === '0');
            return (
              <button
                key={action.label}
                type="button"
                className={`card group cursor-pointer text-left disabled:opacity-60${showPulse ? ' upload-pulse' : ''}`}
                onClick={() => handleQuickAction(action.label)}
                disabled={
                  isUpload
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
            );
          })}
        </div>
        {uploadState.loading && (
          <div className="mt-4 space-y-1.5">
            <div className="flex items-center justify-between font-mono text-2xs text-muted uppercase tracking-widest">
              <span>{uploadState.step}</span>
              <span>{Math.floor(uploadState.progress)}%</span>
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
