import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

const ANALYSIS_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  COMPLETE: 'complete',
  ERROR: 'error',
}

function isAnalyzed(project) {
  return !!(project?.importance_score || project?.user_role)
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ProjectsPage() {
  const { apiOk, uploadHighlights, setUploadHighlights, analysisCache } = useApp()
  const [projects, setProjects] = useState([])
  const [error, setError] = useState('')
  const [selectedProject, setSelectedProject] = useState(null)

  useEffect(() => {
    if (!apiOk) return
    let cancelled = false
    async function loadProjects() {
      try {
        const payload = await window.api.getProjects()
        if (!cancelled) {
          const items = getProjectItems(payload).map((p) =>
            analysisCache?.current[p.id] ? { ...p, ...analysisCache.current[p.id] } : p
          )
          setProjects(items)
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Failed to load projects.')
          setProjects([])
        }
      }
    }
    loadProjects()
    return () => { cancelled = true }
  }, [apiOk, uploadHighlights])

  const createdSet = new Set(uploadHighlights.created)
  const mergedSet = new Set(uploadHighlights.merged)

  function clearProjectHighlight(projectId) {
    setUploadHighlights((current) => ({
      created: current.created.filter((id) => id !== projectId),
      merged: current.merged.filter((id) => id !== projectId),
    }))
  }

  function handleProjectClick(project) {
    if (createdSet.has(project.id) || mergedSet.has(project.id)) {
      clearProjectHighlight(project.id)
    }
    setSelectedProject(project)
  }

  // Sync enriched analysis data back into the cards list
  function handleAnalysisComplete(projectId, result) {
    if (analysisCache?.current) analysisCache.current[projectId] = result
    setProjects((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, ...result } : p))
    )
    setSelectedProject((prev) =>
      prev?.id === projectId ? { ...prev, ...result } : prev
    )
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader title="Projects" description="Uploaded and analyzed projects." />
      <InlineError message={error} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => {
          const isCreated = createdSet.has(project.id)
          const isMerged = mergedSet.has(project.id)
          const analyzed = isAnalyzed(project)
          const highlightClass = isCreated
            ? 'border-emerald-400 bg-emerald-500/10'
            : isMerged
              ? 'border-amber-400 bg-amber-500/10'
              : 'border-border'

          return (
            <div
              key={project.id}
              role="button"
              tabIndex={0}
              className={`card border ${highlightClass} cursor-pointer transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`}
              onClick={() => handleProjectClick(project)}
              onKeyDown={(e) => e.key === 'Enter' && handleProjectClick(project)}
              onMouseEnter={() => {
                if (isCreated || isMerged) clearProjectHighlight(project.id)
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-slate-200 truncate">{project.name}</div>
                  <div className="mt-1 text-xs text-slate-500 truncate">{project.rel_path}</div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  {isCreated && (
                    <span className="rounded border border-emerald-400/30 bg-emerald-500/20 px-2 py-0.5 font-mono text-2xs text-emerald-200">
                      NEW
                    </span>
                  )}
                  {!isCreated && isMerged && (
                    <span className="rounded border border-amber-400/30 bg-amber-500/20 px-2 py-0.5 font-mono text-2xs text-amber-100">
                      MERGED
                    </span>
                  )}
                  {analyzed && (
                    <span className="rounded border border-sky-400/30 bg-sky-500/20 px-2 py-0.5 font-mono text-2xs text-sky-200">
                      ANALYZED
                    </span>
                  )}
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span className="font-mono text-sm text-slate-500">{project.file_count} files</span>
                {project.user_role && (
                  <span className="font-mono text-xs text-slate-400">{project.user_role}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {!error && projects.length === 0 && (
        <EmptyState message="No projects yet. Upload a ZIP from the dashboard." />
      )}

      {selectedProject && (
        <ProjectModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
          onAnalysisComplete={handleAnalysisComplete}
        />
      )}
    </div>
  )
}

// ─── Modal shell ──────────────────────────────────────────────────────────────

function ProjectModal({ project, onClose, onAnalysisComplete }) {
  const overlayRef = useRef(null)

  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => e.target === overlayRef.current && onClose()}
    >
      <div className="relative flex h-[75vh] w-full max-w-4xl flex-col rounded-lg border border-border bg-background shadow-2xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-5 py-3">
          <div className="min-w-0">
            <div className="text-lg font-semibold text-slate-200 truncate">{project.name}</div>
            <div className="mt-0.5 font-mono text-base text-slate-500 truncate">
              Project Path: {project.rel_path}
            </div>
          </div>
          <button
            className="shrink-0 rounded p-1 text-slate-500 transition-colors hover:bg-border hover:text-slate-200"
            onClick={onClose}
            aria-label="Close"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3">
          <ProjectDetail
            project={project}
            onAnalysisComplete={onAnalysisComplete}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Detail content ───────────────────────────────────────────────────────────

function ProjectDetail({ project, onAnalysisComplete }) {
  const alreadyAnalyzed = isAnalyzed(project)
  const [status, setStatus] = useState(
    alreadyAnalyzed ? ANALYSIS_STATUS.COMPLETE : ANALYSIS_STATUS.IDLE
  )
  const [data, setData] = useState(alreadyAnalyzed ? project : null)
  const [error, setError] = useState('')
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => { isMountedRef.current = false }
  }, [])

  // Run once on mount — skip if the project already carries analysis data
  useEffect(() => {
    if (!isAnalyzed(project)) {
      runAnalysis()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function runAnalysis() {
    setStatus(ANALYSIS_STATUS.RUNNING)
    setError('')
    try {
      const result = await window.api.analyzeProject(project.id)
      if (!isMountedRef.current) return
      setData(result)
      setStatus(ANALYSIS_STATUS.COMPLETE)
      onAnalysisComplete?.(project.id, result)
    } catch (err) {
      if (!isMountedRef.current) return
      setError(err?.message || 'Analysis failed. Please try again.')
      setStatus(ANALYSIS_STATUS.ERROR)
    }
  }

  return (
    <div className="space-y-3">
      <ProjectMeta project={project} />

      <div className="flex items-center justify-between">
        <span className="font-mono text-base font-semibold text-slate-400">ANALYSIS</span>
        {status !== ANALYSIS_STATUS.RUNNING && (
          <button className="btn btn-secondary text-sm" onClick={runAnalysis}>
            {status === ANALYSIS_STATUS.COMPLETE ? 'Re-analyze' : 'Run Analysis'}
          </button>
        )}
      </div>

      <InlineError message={error} />

      {(status === ANALYSIS_STATUS.IDLE || status === ANALYSIS_STATUS.RUNNING) && (
        <StatusCard>
          <Spinner />
          <span className="text-sm text-slate-400">
            {status === ANALYSIS_STATUS.IDLE ? 'Starting analysis…' : 'Analyzing project…'}
          </span>
        </StatusCard>
      )}

      {status === ANALYSIS_STATUS.ERROR && (
        <StatusCard>
          <span className="text-sm text-slate-400">
            Analysis failed. Use the button above to retry.
          </span>
        </StatusCard>
      )}

      {status === ANALYSIS_STATUS.COMPLETE && data && (
        <AnalysisResults data={data} />
      )}
    </div>
  )
}

// ─── Analysis results ─────────────────────────────────────────────────────────

function AnalysisResults({ data }) {
  return (
    <div className="space-y-3">
      <RoleBanner data={data} />

      {data.resume_bullets?.length > 0 && (
        <BulletSection
          title="RESUME BULLETS"
          bullets={data.resume_bullets}
          accentClass="border-l-emerald-400"
        />
      )}

      {data.ai_bullets?.length > 0 && (
        <BulletSection
          title="AI SUMMARY"
          bullets={data.ai_bullets}
          accentClass="border-l-sky-400"
          warning={data.ai_warning}
        />
      )}

      {data.git?.is_repo && <GitSection git={data.git} />}

      <TechStack data={data} />

      {data.score_breakdown && Object.keys(data.score_breakdown).length > 0 && (
        <Card label="SCORE BREAKDOWN">
          <div className="space-y-2">
            {Object.entries(data.score_breakdown).map(([k, v]) => (
              <ScoreBar key={k} label={k.replace(/_/g, ' ')} value={v} />
            ))}
          </div>
        </Card>
      )}

      {data.skill_timeline?.length > 0 && (
        <SkillTimeline timeline={data.skill_timeline} />
      )}
    </div>
  )
}

// ─── Section components ───────────────────────────────────────────────────────

function ProjectMeta({ project }) {
  const gridItems = [
    { label: 'files', value: project.file_count },
    project.language && { label: 'language', value: project.language },
    project.framework && { label: 'framework', value: project.framework },
    project.created_at && {
      label: 'uploaded',
      value: new Date(project.created_at).toLocaleDateString(),
    },
  ].filter(Boolean)

  return (
    <div className="rounded border border-border p-3 space-y-3">
      <div className="grid grid-cols-3 gap-x-4 gap-y-3">
        {gridItems.map((item) => (
          <MetaItem key={item.label} label={item.label} value={item.value} />
        ))}
      </div>
      {project.duration && (
        <div className="border-t border-border pt-3">
          <div className="font-mono text-sm font-semibold text-slate-400 mb-1">DURATION</div>
          <div className="text-base text-slate-300 leading-relaxed">{project.duration}</div>
        </div>
      )}
      {project.collaborators_display && (
        <div className="border-t border-border pt-3">
          <div className="font-mono text-sm font-semibold text-slate-400 mb-1">COLLABORATORS</div>
          <div className="text-base text-slate-300 leading-relaxed">{project.collaborators_display}</div>
        </div>
      )}
    </div>
  )
}

function RoleBanner({ data }) {
  const primaryRole = data.user_role_types?.primary_role ?? data.user_role
  const secondaryRoles = data.user_role_types?.secondary_roles
  return (
    <div className="rounded border border-border p-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          {primaryRole && (
            <>
              <div className="font-mono text-base font-semibold text-slate-400">YOUR ROLE</div>
              <div className="mt-0.5 text-sm font-semibold text-slate-200">{primaryRole}</div>
              {secondaryRoles && (
                <div className="mt-0.5 font-mono text-sm text-slate-500">{secondaryRoles}</div>
              )}
            </>
          )}
          {data.role_justification && (
            <p className="mt-2 text-base text-slate-400 leading-relaxed">{data.role_justification}</p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2 text-right">
          {data.importance_score != null && (
            <div>
              <div className="font-mono text-sm font-semibold text-slate-400">IMPORTANCE</div>
              <div className="text-2xl font-bold tabular-nums text-slate-200">{Math.round(data.importance_score)}</div>
            </div>
          )}
          {data.user_contribution_percentage != null && (
            <div>
              <div className="font-mono text-sm font-semibold text-slate-400">CONTRIBUTION</div>
              <div className="text-lg font-semibold tabular-nums text-slate-200">
                {Math.round(data.user_contribution_percentage)}%
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function BulletSection({ title, bullets, accentClass, warning }) {
  return (
    <Card label={title}>
      {warning && (
        <div className="mb-2 rounded border border-amber-400/30 bg-amber-500/10 px-2 py-1 font-mono text-2xs text-amber-200">
          {warning}
        </div>
      )}
      <ul className="space-y-1.5">
        {bullets.map((b, i) => (
          <li key={i} className={`border-l-2 pl-3 text-base leading-relaxed text-slate-300 ${accentClass}`}>
            {b}
          </li>
        ))}
      </ul>
    </Card>
  )
}

function GitSection({ git }) {
  const mine = git.current_author_contribution
  return (
    <Card label="GIT ACTIVITY">
      <div className="space-y-3">
        {git.current_author && (
          <div className="font-mono text-sm text-slate-400">Current Git Identity: {git.current_author}</div>
        )}
        {mine && (
          <div className="grid grid-cols-3 gap-3">
            <MetaItem label="commits" value={mine.commits} />
            <MetaItem label="lines added" value={mine.added?.toLocaleString()} />
            <MetaItem label="lines deleted" value={mine.deleted?.toLocaleString()} />
          </div>
        )}
        {git.author_contributions?.length > 1 && (
          <div className="space-y-1">
            <div className="font-mono text-sm font-semibold text-slate-400 mb-1">ALL CONTRIBUTORS</div>
            {git.author_contributions.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-slate-300 truncate max-w-[50%]">{c.author}</span>
                <span className="font-mono text-slate-500 shrink-0">
                  {c.commits} commits · +{c.added?.toLocaleString()} / -{c.deleted?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function TechStack({ data }) {
  const rows = [
    data.other_languages?.length > 0 && { label: 'LANGUAGES', tags: data.other_languages },
    data.tools?.length > 0 && { label: 'TOOLS', tags: data.tools },
    data.practices?.length > 0 && { label: 'PRACTICES', tags: data.practices },
  ].filter(Boolean)
  if (!rows.length) return null
  return (
    <Card label="TECH STACK">
      <div className="space-y-2">
        {rows.map(({ label, tags }) => (
          <div key={label}>
            <div className="font-mono text-sm font-semibold text-slate-400 mb-1">{label}</div>
            <div className="flex flex-wrap gap-1.5">
              {tags.map((t, i) => (
                <span
                  key={i}
                  className="rounded border border-border px-2 py-0.5 font-mono text-sm text-slate-300"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function SkillTimeline({ timeline }) {
  return (
    <Card label="SKILL TIMELINE">
      <div className="space-y-2">
        {timeline.map((entry, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="font-mono text-sm text-slate-500 shrink-0 pt-0.5 w-24">
              {entry.date}
            </span>
            <div className="flex flex-wrap gap-1">
              {entry.skills.map((s, j) => (
                <span
                  key={j}
                  className="rounded border border-border px-1.5 py-0.5 font-mono text-sm text-slate-300"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function ScoreBar({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-sm font-semibold text-slate-400 capitalize">{label}</span>
      <span className="font-mono text-sm font-semibold tabular-nums text-slate-200">{Math.round(value)}</span>
    </div>
  )
}

// ─── Primitives ───────────────────────────────────────────────────────────────

function Card({ label, children }) {
  return (
    <div className="rounded border border-border p-3">
      {label && <div className="font-mono text-sm font-semibold text-slate-400 mb-2">{label}</div>}
      {children}
    </div>
  )
}

function StatusCard({ children }) {
  return (
    <div className="flex items-center gap-3 rounded border border-border p-3">
      {children}
    </div>
  )
}

function MetaItem({ label, value }) {
  return (
    <div>
      <div className="font-mono text-base font-semibold text-slate-400 capitalize">{label}</div>
      <div className="mt-0.5 text-base text-slate-200">{value ?? '—'}</div>
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 shrink-0 animate-spin text-slate-500"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}