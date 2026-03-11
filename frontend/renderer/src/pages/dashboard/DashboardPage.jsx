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
  })

  useEffect(() => {
    return () => {
      isMountedRef.current = false
      uploadAbortControllerRef.current?.abort()
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
      })
      return
    }

    setUploadState({ loading: true, message: 'Uploading project archive...', error: false })

    try {
      uploadAbortControllerRef.current?.abort()
      uploadAbortControllerRef.current = new AbortController()

      const bytes = await file.arrayBuffer()
      const result = await window.api.createProjectUpload({
        name: file.name,
        type: file.type || 'application/zip',
        bytes,
      })

      const actions = result?.actions ?? []
      const created = actions
        .filter((action) => action?.action === 'created')
        .map((action) => action.project_id)
      const merged = actions
        .filter((action) => action?.action === 'merged')
        .map((action) => action.project_id)

      if (!isMountedRef.current) {
        return
      }

      setUploadHighlights({ created, merged })

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
      })

      setPage('projects')
    } catch (error) {
      if (error?.name === 'AbortError' || !isMountedRef.current) {
        return
      }

      setUploadState({
        loading: false,
        error: true,
        message: error?.message || 'Upload failed. Please try again.',
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
              onClick={action.label === 'Upload Project' ? startUploadFlow : undefined}
              disabled={action.label === 'Upload Project' ? uploadState.loading || !apiOk : true}
            >
              <div className="mb-3 text-2xl opacity-40 transition-opacity group-hover:opacity-80">
                {action.icon}
              </div>
              <div className="mb-1 text-sm font-bold">{action.label}</div>
              <div className="text-xs text-muted">{action.desc}</div>
            </button>
          ))}
        </div>
        {uploadState.message && (
          <p
            className={`mt-3 text-xs ${uploadState.error ? 'text-red-400' : 'text-muted'}`}
            onMouseEnter={() => {
              if (uploadState.loading) {
                return
              }

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
