import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import {
  formatResumeDate,
  hasResumeProfile,
  normalizeResumeItems,
  sortResumesByUpdatedAt,
} from '../../lib/resumes'

function ReadinessItem({ label, ready, detail }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border/70 py-2 last:border-b-0 last:pb-0">
      <div className="min-w-0">
        <div className="text-xs font-semibold text-ink">{label}</div>
        <div className="mt-0.5 text-2xs text-muted">{detail}</div>
      </div>
      <span
        className={`mt-0.5 rounded border px-2 py-0.5 font-mono text-2xs uppercase tracking-widest ${
          ready
            ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
            : 'border-border bg-elevated text-muted'
        }`}
      >
        {ready ? 'Ready' : 'Missing'}
      </span>
    </div>
  )
}

export default function ResumesPage() {
  const { user, apiOk } = useApp()
  const [resumes, setResumes] = useState([])
  const [profile, setProfile] = useState(null)
  const [workCount, setWorkCount] = useState(0)
  const [educationCount, setEducationCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!apiOk || !user?.username) {
      return
    }

    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')

      const [resumeResult, profileResult, workResult, educationResult] = await Promise.allSettled([
        window.api.getResumes(user.username),
        window.api.getProfile(user.username),
        window.api.getWorkExperiences(user.username),
        window.api.getEducations(user.username),
      ])

      if (cancelled) {
        return
      }

      if (resumeResult.status === 'fulfilled') {
        setResumes(sortResumesByUpdatedAt(normalizeResumeItems(resumeResult.value)))
      } else {
        setResumes([])
        setError(resumeResult.reason?.message || 'Failed to load resume entries.')
      }

      setProfile(profileResult.status === 'fulfilled' ? profileResult.value : null)
      setWorkCount(workResult.status === 'fulfilled' ? (workResult.value?.length ?? 0) : 0)
      setEducationCount(
        educationResult.status === 'fulfilled' ? (educationResult.value?.length ?? 0) : 0
      )
      setLoading(false)
    }

    load()

    return () => {
      cancelled = true
    }
  }, [apiOk, user?.username])

  const hasProfile = hasResumeProfile(profile)

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Resumes"
        description="Review saved resume entries and verify the profile data needed before editing and generating the final PDF."
      />

      <InlineError message={error} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_320px]">
        <div className="space-y-4">
          {loading ? (
            <div className="flex justify-center py-12">
              <span className="spinner" />
            </div>
          ) : resumes.length > 0 ? (
            resumes.map((item) => {
              const snapshot = item.analysis_snapshot ?? []
              const bulletCount = item.bullet_points?.length ?? 0

              return (
                <article key={item.project_id} className="card space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="truncate text-lg font-extrabold tracking-tight text-ink">
                        {item.title || item.project_name}
                      </h2>
                      <div className="mt-1 flex flex-wrap items-center gap-3 font-mono text-2xs uppercase tracking-widest text-muted">
                        <span>{item.project_name}</span>
                        <span>{bulletCount} bullets</span>
                        <span>Updated {formatResumeDate(item.updated_at)}</span>
                      </div>
                    </div>
                    <span className="rounded border border-border bg-elevated px-2 py-0.5 font-mono text-2xs uppercase tracking-widest text-muted">
                      Saved Entry
                    </span>
                  </div>

                  {item.description && (
                    <p className="text-sm leading-relaxed text-ink/75">{item.description}</p>
                  )}

                  {snapshot.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {snapshot.map((entry) => (
                        <span key={entry} className="tag">
                          {entry}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="space-y-2 border-t border-border pt-3">
                    {item.bullet_points?.map((bullet) => (
                      <div
                        key={bullet}
                        className="rounded-lg border border-border/70 bg-elevated/40 px-3 py-2 text-sm leading-relaxed text-ink/85"
                      >
                        {bullet}
                      </div>
                    ))}
                  </div>
                </article>
              )
            })
          ) : (
            <EmptyState message="No resume entries yet. Editing and generation land in the next stacked PR." />
          )}
        </div>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <section className="card space-y-4">
            <div>
              <div className="font-mono text-2xs uppercase tracking-widest text-muted">
                Resume Status
              </div>
              <h2 className="mt-2 text-lg font-extrabold tracking-tight text-ink">
                Check what is ready
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                This workspace already reads your saved resume entries. Editing, AI assist, and PDF preview are split into the next PR.
              </p>
            </div>
          </section>

          <section className="card space-y-2">
            <div className="font-mono text-2xs uppercase tracking-widest text-muted">
              Readiness Checklist
            </div>
            <ReadinessItem
              label="Profile"
              ready={hasProfile}
              detail={
                hasProfile
                  ? 'Profile data is available for the resume header.'
                  : 'Create your profile before generating the PDF.'
              }
            />
            <ReadinessItem
              label="Experience"
              ready={workCount > 0}
              detail={`${workCount} saved experience entr${workCount === 1 ? 'y' : 'ies'}`}
            />
            <ReadinessItem
              label="Education"
              ready={educationCount > 0}
              detail={`${educationCount} saved education entr${educationCount === 1 ? 'y' : 'ies'}`}
            />
            <ReadinessItem
              label="Resume Entries"
              ready={resumes.length > 0}
              detail={`${resumes.length} saved project entr${resumes.length === 1 ? 'y' : 'ies'}`}
            />
          </section>
        </aside>
      </div>
    </div>
  )
}
