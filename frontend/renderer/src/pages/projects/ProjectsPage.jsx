import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

export default function ProjectsPage() {
  const { apiOk, uploadHighlights, setUploadHighlights } = useApp()
  const [projects, setProjects] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!apiOk) {
      return
    }

    let cancelled = false

    async function loadProjects() {
      try {
        const payload = await window.api.getProjects()
        if (!cancelled) {
          setProjects(getProjectItems(payload))
          setError('')
        }
      } catch (error) {
        if (!cancelled) {
          setError(error?.message || 'Failed to load projects.')
          setProjects([])
        }
      }
    }

    loadProjects()

    return () => {
      cancelled = true
    }
  }, [apiOk, uploadHighlights])

  const createdSet = new Set(uploadHighlights.created)
  const mergedSet = new Set(uploadHighlights.merged)

  function clearProjectHighlight(projectId) {
    setUploadHighlights((current) => ({
      created: current.created.filter((id) => id !== projectId),
      merged: current.merged.filter((id) => id !== projectId),
    }))
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader title="Projects" description="Uploaded and analyzed projects." />
      <InlineError message={error} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => {
          const isCreated = createdSet.has(project.id)
          const isMerged = mergedSet.has(project.id)
          const highlightClass = isCreated
            ? 'border-emerald-400 bg-emerald-500/10'
            : isMerged
              ? 'border-amber-400 bg-amber-500/10'
              : 'border-border'

          return (
            <div
              key={project.id}
              className={`card border ${highlightClass}`}
              onMouseEnter={() => {
                if (isCreated || isMerged) {
                  clearProjectHighlight(project.id)
                }
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-bold">{project.name}</div>
                  <div className="mt-1 text-xs text-muted">{project.rel_path}</div>
                </div>
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
              </div>

              <div className="mt-3 font-mono text-2xs text-muted">{project.file_count} files</div>
            </div>
          )
        })}
      </div>

      {!error && projects.length === 0 && (
        <EmptyState message="No projects yet. Upload a ZIP from the dashboard." />
      )}
    </div>
  )
}
