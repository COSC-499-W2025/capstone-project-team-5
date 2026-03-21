import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

// ─── Persistent analysis cache ────────────────────────────────────────────────

const CACHE_KEY = 'zip2job_analyses'
function readCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') } catch { return {} }
}
function writeCache(projectId, result) {
  try {
    const c = readCache()
    c[String(projectId)] = result
    localStorage.setItem(CACHE_KEY, JSON.stringify(c))
  } catch { /* quota exceeded */ }
}

function isAnalyzed(p) {
  return !!(p?.importance_score || p?.user_role)
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const SORT_OPTIONS = [
  { value: 'date',  label: 'Date' },
  { value: 'score', label: 'Score' },
  { value: 'name',  label: 'Name' },
]

export default function ProjectsPage() {
  const { apiOk, uploadHighlights, setUploadHighlights, analysisCache } = useApp()
  const [projects, setProjects] = useState([])
  const [error,    setError]    = useState('')
  const [open,     setOpen]     = useState(null)
  const [query,    setQuery]    = useState('')
  const [sort,     setSort]     = useState('date')

  useEffect(() => {
    if (!apiOk) return
    let cancelled = false
    async function load() {
      try {
        const username = window.api.getAuthUsername()
        const [payload, savedUploads] = await Promise.all([
          window.api.getProjects(),
          username ? window.api.getSavedProjects(username).catch(() => []) : Promise.resolve([]),
        ])
        if (cancelled) return

        // Build projectId → saved analysis map from the saved uploads response
        const savedMap = {}
        for (const upload of (savedUploads || [])) {
          for (const sp of (upload.projects || [])) {
            // Newest analysis is last in the array (oldest-first from DB)
            const latest = sp.analyses?.length > 0 ? sp.analyses[sp.analyses.length - 1] : null
            savedMap[sp.id] = {
              importance_score:             sp.importance_score,
              user_role:                    latest?.user_role           ?? sp.user_role,
              user_contribution_percentage: latest?.user_contribution_percentage ?? sp.user_contribution_percentage,
              role_justification:           latest?.role_justification  ?? sp.role_justification,
              user_role_types:              latest?.user_role_types     ?? sp.user_role_types,
              other_languages:              sp.languages,
              tools:                        sp.tools,
              practices:                    sp.practices,
              resume_bullets:               latest?.resume_bullets      ?? [],
              ai_bullets:                   latest?.ai_bullets          ?? [],
              ai_warning:                   latest?.ai_warning,
              skill_timeline:               latest?.skill_timeline      ?? [],
              score_breakdown:              latest?.score_breakdown     ?? {},
              git:                          latest?.git,
              duration:                     latest?.duration            ?? sp.duration,
            }
          }
        }

        // Seed in-memory + localStorage cache with saved analysis data
        for (const [id, data] of Object.entries(savedMap)) {
          if (!analysisCache?.current[id]) {
            if (analysisCache?.current) analysisCache.current[id] = data
            writeCache(id, data)
          }
        }

        const disk  = readCache()
        const items = getProjectItems(payload).map((p) => {
          const hit = analysisCache?.current[p.id] ?? disk[String(p.id)]
          return hit ? { ...p, ...hit, name: p.name, rel_path: p.rel_path } : p
        })
        setProjects(items)
        setError('')
      } catch (err) {
        if (!cancelled) { setError(err?.message || 'Failed to load projects.'); setProjects([]) }
      }
    }
    load()
    return () => { cancelled = true }
  }, [apiOk, uploadHighlights])

  const createdSet = new Set(uploadHighlights.created)
  const mergedSet  = new Set(uploadHighlights.merged)

  function clearHighlight(id) {
    setUploadHighlights((c) => ({
      created: c.created.filter((x) => x !== id),
      merged:  c.merged.filter((x) => x !== id),
    }))
  }

  function handleOpen(project) {
    if (createdSet.has(project.id) || mergedSet.has(project.id)) clearHighlight(project.id)
    setOpen(project)
  }

  function handleAnalysisDone(projectId, result) {
    if (analysisCache?.current) analysisCache.current[projectId] = result
    writeCache(projectId, result)
    const merge = (p) => p.id === projectId ? { ...p, ...result, name: p.name, rel_path: p.rel_path } : p
    setProjects((prev) => prev.map(merge))
    setOpen((prev)  => prev?.id === projectId ? { ...prev, ...result } : prev)
  }

  function handleThumbnailChange(projectId, hasThumbnail) {
    const thumbnailUrl = hasThumbnail ? `/api/projects/${projectId}/thumbnail` : null
    const thumbnailRev = hasThumbnail ? Date.now() : null
    const update = (p) =>
      p.id === projectId
        ? {
            ...p,
            has_thumbnail: hasThumbnail,
            thumbnail_url: thumbnailUrl,
            thumbnail_rev: thumbnailRev,
          }
        : p
    setProjects((prev) => prev.map(update))
    setOpen((prev) =>
      prev?.id === projectId
        ? {
            ...prev,
            has_thumbnail: hasThumbnail,
            thumbnail_url: thumbnailUrl,
            thumbnail_rev: thumbnailRev,
          }
        : prev
    )
  }

  // Filter + sort
  const visible = projects
    .filter((p) => !query || p.name.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => {
      if (sort === 'score') return (b.importance_score ?? -1) - (a.importance_score ?? -1)
      if (sort === 'name')  return a.name.localeCompare(b.name)
      // date: newest first (higher id = newer upload)
      return b.id - a.id
    })

  return (
    <>
    <div className="animate-fade-up space-y-5">
      <PageHeader title="Projects" description="Uploaded and analyzed projects." />
      <InlineError message={error} />

      {/* Search + sort toolbar */}
      {projects.length > 0 && (
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="Search projects…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input pl-8 py-1.5 text-xs"
            />
          </div>
          <div className="flex items-center gap-1">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSort(opt.value)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  sort === opt.value
                    ? 'bg-elevated text-ink border border-border-hi'
                    : 'text-muted hover:text-ink'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-muted ml-auto">
            {visible.length} of {projects.length}
          </span>
        </div>
      )}

      {!error && projects.length === 0 && (
        <EmptyState message="No projects yet. Upload a ZIP from the dashboard." />
      )}

      {query && visible.length === 0 && (
        <p className="text-sm text-muted">No projects match "{query}".</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((p) => (
          <ProjectCard
            key={p.id}
            project={p}
            isNew={createdSet.has(p.id)}
            isMerged={mergedSet.has(p.id)}
            onOpen={handleOpen}
            onMouseEnter={() => {
              if (createdSet.has(p.id) || mergedSet.has(p.id)) clearHighlight(p.id)
            }}
          />
        ))}
      </div>

    </div>

    {open && (
      <ProjectDrawer
        project={open}
        onClose={() => setOpen(null)}
        onAnalysisDone={handleAnalysisDone}
        onThumbnailChange={handleThumbnailChange}
      />
    )}
    </>
  )
}

// ─── Card ─────────────────────────────────────────────────────────────────────

function ProjectCard({ project, isNew, isMerged, onOpen, onMouseEnter }) {
  const [showThumbnail, setShowThumbnail] = useState(Boolean(project.has_thumbnail))

  useEffect(() => {
    setShowThumbnail(Boolean(project.has_thumbnail))
  }, [project.id, project.has_thumbnail, project.thumbnail_rev])

  const borderOverride = isNew
    ? 'border-success/50'
    : isMerged
      ? 'border-accent/50'
      : ''

  return (
    <button
      className={`card text-left w-full !p-0 overflow-hidden ${borderOverride}`}
      onClick={() => onOpen(project)}
      onMouseEnter={onMouseEnter}
    >
      {/* Thumbnail */}
      {showThumbnail && (
        <AuthenticatedThumbnail
          projectId={project.id}
          revision={project.thumbnail_rev}
          alt={`${project.name} thumbnail`}
          className="w-full h-32 object-cover"
          onLoadError={() => setShowThumbnail(false)}
        />
      )}

      {/* Content */}
      <div className="p-5">
        {/* Name + status chips */}
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-semibold text-ink leading-snug">{project.name}</span>
          <div className="flex shrink-0 gap-1 pt-px">
            {isNew             && <Chip variant="success">NEW</Chip>}
            {isMerged && !isNew && <Chip variant="accent">MERGED</Chip>}
          </div>
        </div>

        {/* Path */}
        <p className="mt-1.5 font-mono text-xs text-muted truncate">{project.rel_path}</p>

        {/* Footer */}
        <div className="mt-4 flex items-end justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs text-muted">
              {project.file_count} files
              {project.language && <span> · {project.language}</span>}
            </p>
            {project.user_role && (
              <p className="mt-0.5 text-xs text-ink/70 truncate">{project.user_role}</p>
            )}
          </div>
          {project.importance_score != null && (
            <span className="shrink-0 font-mono text-lg font-bold tabular-nums text-ink leading-none">
              {Math.round(project.importance_score)}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

function Chip({ variant, children }) {
  const cls = {
    success: 'bg-success/15 text-success border-success/30',
    accent:  'bg-accent/15  text-accent  border-accent/30',
  }[variant]
  return (
    <span className={`rounded border px-1.5 py-0.5 font-mono text-2xs ${cls}`}>
      {children}
    </span>
  )
}

// ─── Drawer ───────────────────────────────────────────────────────────────────

const S = { IDLE: 'idle', RUNNING: 'running', DONE: 'done', ERROR: 'error' }

function ProjectDrawer({ project, onClose, onAnalysisDone, onThumbnailChange }) {
  const alreadyDone = isAnalyzed(project)
  const [status, setStatus] = useState(alreadyDone ? S.DONE  : S.IDLE)
  const [data,   setData]   = useState(alreadyDone ? project : null)
  const [err,    setErr]    = useState('')
  const alive = useRef(true)

  // Thumbnail state
  const [hasThumbnail, setHasThumbnail] = useState(project.has_thumbnail ?? false)
  const [thumbErr,     setThumbErr]     = useState('')
  const [thumbVer,     setThumbVer]     = useState(0)
  const thumbInputRef = useRef(null)

  async function handleThumbnailFileSelected(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setThumbErr('')
    try {
      await window.api.uploadProjectThumbnail(project.id, file)
      setHasThumbnail(true)
      setThumbVer((v) => v + 1)
      onThumbnailChange?.(project.id, true)
    } catch (err) {
      setThumbErr(err?.message || 'Failed to upload thumbnail.')
    } finally {
      e.target.value = ''
    }
  }

  async function handleClearThumbnail() {
    setThumbErr('')
    try {
      await window.api.deleteProjectThumbnail(project.id)
      setHasThumbnail(false)
      onThumbnailChange?.(project.id, false)
    } catch (err) {
      setThumbErr(err?.message || 'Failed to clear thumbnail.')
    }
  }

  useEffect(() => {
    alive.current = true
    return () => { alive.current = false }
  }, [])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  useEffect(() => {
    const fn = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', fn)
    return () => document.removeEventListener('keydown', fn)
  }, [onClose])

  async function analyze() {
    setStatus(S.RUNNING)
    setErr('')
    try {
      const result = await window.api.analyzeProject(project.id)
      if (!alive.current) return
      setData(result)
      setStatus(S.DONE)
      onAnalysisDone?.(project.id, result)
    } catch (e) {
      if (!alive.current) return
      setErr(e?.message || 'Analysis failed.')
      setStatus(S.ERROR)
    }
  }

  return (
    <>
      {/* Backdrop — dark enough to hide cards behind */}
      <div className="fixed inset-0 z-40 bg-black/80" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[540px] flex-col border-l border-border bg-surface shadow-2xl text-ink">

        {/* Thumbnail banner */}
        {hasThumbnail && (
          <AuthenticatedThumbnail
            projectId={project.id}
            revision={thumbVer || project.thumbnail_rev}
            alt={`${project.name} thumbnail`}
            className="w-full h-40 object-cover shrink-0"
            onLoadError={(loadErr) => {
              setHasThumbnail(false)
              setThumbErr(loadErr?.message || 'Failed to load thumbnail.')
            }}
          />
        )}

        {/* Header */}
        <div className="flex shrink-0 items-start gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-ink">{project.name}</h2>
            <p className="mt-0.5 font-mono text-xs text-muted">{project.rel_path}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2 pt-0.5">
            {hasThumbnail ? (
              <button
                onClick={handleClearThumbnail}
                className="rounded border border-border-hi px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-elevated"
              >
                Clear Thumbnail
              </button>
            ) : (
              <button
                onClick={() => thumbInputRef.current?.click()}
                className="rounded border border-border-hi px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-elevated"
              >
                Set Thumbnail
              </button>
            )}
            {status !== S.RUNNING && (
              <button
                onClick={analyze}
                className="rounded border border-border-hi px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-elevated"
              >
                {status === S.DONE ? 'Re-analyze' : 'Analyze'}
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded p-1.5 text-muted transition-colors hover:bg-border hover:text-ink"
              aria-label="Close"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>
        {thumbErr && (
          <div className="px-5 pt-2">
            <p className="text-xs text-danger">{thumbErr}</p>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-5 py-4 space-y-4">
            <MetaTable project={project} />

            {/* Status states */}
            {status === S.RUNNING && (
              <div className="flex items-center gap-3 rounded border border-border px-4 py-3 text-sm text-muted">
                <Spinner /> Analyzing…
              </div>
            )}
            {status === S.IDLE && (
              <div className="rounded border border-border px-4 py-3 text-sm text-muted">
                No analysis yet.{' '}
                <button onClick={analyze} className="text-ink underline underline-offset-2">Run it</button>
                {' '}to extract your role, skills, and resume bullets.
              </div>
            )}
            {status === S.ERROR && (
              <div className="rounded border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
                {err}{' '}
                <button onClick={analyze} className="underline underline-offset-2">Retry</button>
              </div>
            )}

            {status === S.DONE && data && <AnalysisDetail data={data} />}
          </div>
        </div>

        <input
          ref={thumbInputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
          className="hidden"
          data-testid="thumbnail-file-input"
          onChange={handleThumbnailFileSelected}
        />
      </div>
    </>
  )
}

// ─── Meta table ───────────────────────────────────────────────────────────────

function parseCollaborators(display) {
  if (!display) return null
  // Strip everything up to and including "N collaborator(s) detected: " (may have emoji prefix)
  return display.replace(/^.*?\d+\s+collaborators?\s+detected:\s*/i, '').trim() || null
}

function MetaTable({ project }) {
  const collaborators = parseCollaborators(project.collaborators_display)

  const items = [
    { label: 'Files',        value: project.file_count },
    { label: 'Language',     value: project.language   },
    { label: 'Framework',    value: project.framework  },
    { label: 'Uploaded',     value: project.created_at ? new Date(project.created_at).toLocaleDateString() : null },
    { label: 'Duration',      value: project.duration, wide: true },
    { label: 'Collaborators', value: collaborators,    wide: true },
  ].filter((c) => c.value != null)

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
      {items.map((item) => (
        <div key={item.label} className={item.wide ? 'col-span-2' : ''}>
          <p className="text-xs text-ink/50 mb-0.5">{item.label}</p>
          <p className="text-ink font-medium leading-snug">{item.value}</p>
        </div>
      ))}
    </div>
  )
}

// ─── Analysis detail ──────────────────────────────────────────────────────────

function AnalysisDetail({ data }) {
  const primaryRole    = data.user_role_types?.primary_role ?? data.user_role
  const secondaryRoles = data.user_role_types?.secondary_roles

  return (
    <div className="space-y-3">

      {/* Role + scores */}
      {(primaryRole || data.importance_score != null) && (
        <div className="rounded border border-border p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs text-ink/50 mb-1">Your role</p>
              <p className="text-sm font-semibold text-ink">{primaryRole}</p>
              {secondaryRoles && <p className="mt-0.5 text-xs text-muted">{secondaryRoles}</p>}
              {data.role_justification && (
                <p className="mt-2 text-xs text-muted leading-relaxed">{data.role_justification}</p>
              )}
            </div>
            <div className="shrink-0 flex gap-5 text-right">
              {data.importance_score != null && (
                <div>
                  <p className="text-xs text-ink/50 mb-0.5">Score</p>
                  <p className="font-mono text-2xl font-bold tabular-nums text-ink leading-none">
                    {Math.round(data.importance_score)}
                  </p>
                </div>
              )}
              {data.user_contribution_percentage != null && (
                <div>
                  <p className="text-xs text-ink/50 mb-0.5">Contrib</p>
                  <p className="font-mono text-2xl font-bold tabular-nums text-ink leading-none">
                    {Math.round(data.user_contribution_percentage)}%
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {data.resume_bullets?.length > 0 && (
        <Section label="Resume bullets">
          <ul className="space-y-2">
            {data.resume_bullets.map((b, i) => (
              <li key={i} className="border-l-2 border-success/60 pl-3 text-sm text-ink/80 leading-relaxed">{b}</li>
            ))}
          </ul>
        </Section>
      )}

      {data.ai_bullets?.length > 0 && (
        <Section label="AI summary" warning={data.ai_warning}>
          <ul className="space-y-2">
            {data.ai_bullets.map((b, i) => (
              <li key={i} className="border-l-2 border-border-hi pl-3 text-sm text-ink/80 leading-relaxed">{b}</li>
            ))}
          </ul>
        </Section>
      )}

      {data.git?.is_repo && <GitSection git={data.git} />}

      <TechStack data={data} />

      {data.score_breakdown && Object.keys(data.score_breakdown).length > 0 && (
        <Section label="Score breakdown">
          <div className="space-y-2.5">
            {Object.entries(data.score_breakdown).map(([k, v]) => (
              <ScoreBar key={k} label={k.replace(/_/g, ' ')} value={v} />
            ))}
          </div>
        </Section>
      )}

      {data.skill_timeline?.length > 0 && (
        <Section label="Skill timeline">
          <div className="space-y-2">
            {data.skill_timeline.map((entry, i) => (
              <div key={i} className="flex items-start gap-3 text-xs">
                <span className="shrink-0 w-20 font-mono text-muted pt-0.5">{entry.date}</span>
                <div className="flex flex-wrap gap-1">
                  {entry.skills.map((s, j) => (
                    <span key={j} className="rounded border border-border px-1.5 py-0.5 font-mono text-ink/70">{s}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function AuthenticatedThumbnail({ projectId, revision, alt, className, onLoadError }) {
  const [src, setSrc] = useState('')

  useEffect(() => {
    let cancelled = false
    let objectUrl = null

    async function loadThumbnail() {
      try {
        const nextUrl = await window.api.getProjectThumbnailObjectUrl(projectId, revision)
        if (cancelled) {
          if (window.api.revokeObjectUrl) {
            window.api.revokeObjectUrl(nextUrl)
          } else {
            URL.revokeObjectURL(nextUrl)
          }
          return
        }
        objectUrl = nextUrl
        setSrc(nextUrl)
      } catch (err) {
        if (!cancelled) {
          setSrc('')
          onLoadError?.(err)
        }
      }
    }

    setSrc('')
    loadThumbnail()

    return () => {
      cancelled = true
      if (objectUrl) {
        if (window.api.revokeObjectUrl) {
          window.api.revokeObjectUrl(objectUrl)
        } else {
          URL.revokeObjectURL(objectUrl)
        }
      }
    }
  }, [projectId, revision, onLoadError])

  if (!src) {
    return null
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onError={(event) => {
        const failedUrl = event.currentTarget.currentSrc
        if (window.api.revokeObjectUrl) {
          window.api.revokeObjectUrl(failedUrl)
        } else if (failedUrl) {
          URL.revokeObjectURL(failedUrl)
        }
        setSrc('')
        onLoadError?.(new Error('Failed to render thumbnail image.'))
      }}
    />
  )
}

// ─── Shared section wrapper ───────────────────────────────────────────────────

function Section({ label, warning, children }) {
  return (
    <div className="rounded border border-border">
      <div className="border-b border-border px-3 py-2">
        <span className="font-mono text-2xs text-ink/60 uppercase tracking-widest">{label}</span>
      </div>
      <div className="p-3">
        {warning && (
          <p className="mb-2 rounded border border-accent/30 bg-accent/10 px-2 py-1 text-xs text-accent/80">
            {warning}
          </p>
        )}
        {children}
      </div>
    </div>
  )
}

function GitSection({ git }) {
  const mine = git.current_author_contribution
  return (
    <Section label="Git activity">
      <div className="space-y-3">
        {mine && (
          <div className="grid grid-cols-3 gap-3 text-sm">
            {[
              { label: 'Commits',    value: mine.commits },
              { label: 'Added',      value: mine.added?.toLocaleString()   },
              { label: 'Removed',    value: mine.deleted?.toLocaleString() },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-ink/50 mb-0.5">{label}</p>
                <p className="font-medium text-ink">{value ?? '—'}</p>
              </div>
            ))}
          </div>
        )}
        {git.author_contributions?.length > 1 && (
          <div className="border-t border-border pt-3 space-y-1.5">
            <p className="text-xs text-ink/50 mb-1.5">All contributors</p>
            {git.author_contributions.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-ink truncate max-w-[55%]">{c.author}</span>
                <span className="font-mono text-ink/50 shrink-0">
                  {c.commits}c · +{c.added?.toLocaleString()} / -{c.deleted?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
        {git.current_author && (
          <p className="text-xs text-ink/30 border-t border-border pt-2">
            attributed to: {git.current_author}
          </p>
        )}
      </div>
    </Section>
  )
}

function TechStack({ data }) {
  const rows = [
    data.other_languages?.length > 0 && { label: 'Languages', tags: data.other_languages },
    data.tools?.length      > 0 && { label: 'Tools',     tags: data.tools },
    data.practices?.length  > 0 && { label: 'Practices', tags: data.practices },
  ].filter(Boolean)
  if (!rows.length) return null
  return (
    <Section label="Tech stack">
      <div className="space-y-3">
        {rows.map(({ label, tags }) => (
          <div key={label}>
            <p className="text-xs text-ink/50 mb-1.5">{label}</p>
            <div className="flex flex-wrap gap-1">
              {tags.map((t, i) => (
                <span key={i} className="rounded border border-border px-2 py-0.5 font-mono text-xs text-ink/70">{t}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function ScoreBar({ label, value }) {
  const pct = Math.min(100, Math.max(0, Math.round(value)))
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-ink/70 capitalize">{label}</span>
        <span className="font-mono text-xs font-semibold tabular-nums text-ink">{pct}</span>
      </div>
      <div className="h-0.5 w-full rounded-full bg-border">
        <div className="h-0.5 rounded-full bg-ink/40 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <svg className="h-3.5 w-3.5 shrink-0 animate-spin text-muted" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
