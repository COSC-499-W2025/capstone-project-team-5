import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'
import {
  DEFAULT_RESUME_TEMPLATE,
  EMPTY_RESUME_FORM,
  RESUME_TEMPLATE_OPTIONS,
  buildResumeDraft,
  formatResumeDate,
  getAvailableResumeProjects,
  hasResumeProfile,
  normalizeResumeItems,
  parseSnapshotInput,
  prepareBulletPoints,
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

function downloadBlobFile(bytes, contentType, filename) {
  const url = URL.createObjectURL(new Blob([bytes], { type: contentType || 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'resume.pdf'
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

export default function ResumesPage() {
  const { user, apiOk } = useApp()
  const previewUrlRef = useRef('')

  const [resumes, setResumes] = useState([])
  const [projects, setProjects] = useState([])
  const [profile, setProfile] = useState(null)
  const [workCount, setWorkCount] = useState(0)
  const [educationCount, setEducationCount] = useState(0)
  const [llmConfig, setLlmConfig] = useState({ is_allowed: false, model_preferences: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [editingProjectId, setEditingProjectId] = useState(null)
  const [form, setForm] = useState(EMPTY_RESUME_FORM)
  const [useAiAssist, setUseAiAssist] = useState(false)
  const [draftLoading, setDraftLoading] = useState(false)
  const [draftStatus, setDraftStatus] = useState('')
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmId, setConfirmId] = useState(null)

  const [templateName, setTemplateName] = useState(DEFAULT_RESUME_TEMPLATE)
  const [previewState, setPreviewState] = useState({
    url: '',
    filename: '',
    bytes: null,
    contentType: 'application/pdf',
    stale: false,
  })
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!llmConfig?.is_allowed) {
      setUseAiAssist(false)
    }
  }, [llmConfig])

  useEffect(() => {
    if (!apiOk || !user?.username) {
      return
    }

    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')

      const [
        resumeResult,
        profileResult,
        workResult,
        educationResult,
        projectResult,
        llmResult,
      ] = await Promise.allSettled([
        window.api.getResumes(user.username),
        window.api.getProfile(user.username),
        window.api.getWorkExperiences(user.username),
        window.api.getEducations(user.username),
        window.api.getProjects(),
        window.api.getLLMConfig(),
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

      if (projectResult.status === 'fulfilled') {
        setProjects(getProjectItems(projectResult.value))
      } else {
        setProjects([])
        setError((current) => current || projectResult.reason?.message || 'Failed to load projects.')
      }

      setProfile(profileResult.status === 'fulfilled' ? profileResult.value : null)
      setWorkCount(workResult.status === 'fulfilled' ? (workResult.value?.length ?? 0) : 0)
      setEducationCount(
        educationResult.status === 'fulfilled' ? (educationResult.value?.length ?? 0) : 0
      )
      setLlmConfig(
        llmResult.status === 'fulfilled'
          ? llmResult.value ?? { is_allowed: false, model_preferences: [] }
          : { is_allowed: false, model_preferences: [] }
      )
      setLoading(false)
    }

    load()

    return () => {
      cancelled = true
    }
  }, [apiOk, user?.username])

  function replacePreview(bytes, contentType, filename) {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
    }

    const url = URL.createObjectURL(new Blob([bytes], { type: contentType || 'application/pdf' }))
    previewUrlRef.current = url
    setPreviewState({
      url,
      filename: filename || 'resume.pdf',
      bytes,
      contentType: contentType || 'application/pdf',
      stale: false,
    })
  }

  function markPreviewStale() {
    setPreviewState((current) => (current.url ? { ...current, stale: true } : current))
  }

  function openCreate() {
    setShowForm(true)
    setEditingProjectId(null)
    setForm(EMPTY_RESUME_FORM)
    setUseAiAssist(Boolean(llmConfig?.is_allowed))
    setDraftStatus('')
    setFormError('')
    setConfirmId(null)
  }

  function openEdit(item) {
    setShowForm(true)
    setEditingProjectId(item.project_id)
    setForm({
      project_id: String(item.project_id),
      project_name: item.project_name ?? '',
      title: item.title ?? item.project_name ?? '',
      description: item.description ?? '',
      analysis_snapshot: (item.analysis_snapshot ?? []).join(', '),
      bullet_points: item.bullet_points?.length ? item.bullet_points : [''],
    })
    setDraftStatus('')
    setFormError('')
    setConfirmId(null)
  }

  function cancelForm() {
    setShowForm(false)
    setEditingProjectId(null)
    setForm(EMPTY_RESUME_FORM)
    setDraftStatus('')
    setFormError('')
  }

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function updateBullet(index, value) {
    setForm((current) => ({
      ...current,
      bullet_points: current.bullet_points.map((bullet, bulletIndex) =>
        bulletIndex === index ? value : bullet
      ),
    }))
  }

  function addBullet() {
    setForm((current) => ({
      ...current,
      bullet_points: [...current.bullet_points, ''],
    }))
  }

  function removeBullet(index) {
    setForm((current) => {
      const nextBullets = current.bullet_points.filter((_, bulletIndex) => bulletIndex !== index)
      return {
        ...current,
        bullet_points: nextBullets.length > 0 ? nextBullets : [''],
      }
    })
  }

  const availableProjects = getAvailableResumeProjects(projects, resumes, editingProjectId)
  const hasProfile = hasResumeProfile(profile)
  const canGeneratePreview =
    apiOk && Boolean(user?.username) && hasProfile && resumes.length > 0 && !previewLoading

  async function hydrateDraft(projectIdValue) {
    updateField('project_id', projectIdValue)
    setDraftStatus('')
    setFormError('')

    if (!projectIdValue) {
      setForm((current) => ({
        ...current,
        project_id: '',
        project_name: '',
        title: '',
        description: '',
        analysis_snapshot: '',
        bullet_points: [''],
      }))
      return
    }

    const project = projects.find((item) => String(item.id) === String(projectIdValue))
    if (!project) {
      return
    }

    if (!project.rel_path) {
      setDraftStatus('This project cannot be analyzed (no source files to scan).')
      return
    }

    setDraftLoading(true)
    setForm((current) => ({
      ...current,
      project_id: String(project.id),
      project_name: project.name,
      title: project.name,
    }))

    try {
      let analysis = null
      let nextStatus = ''

      if (useAiAssist && llmConfig?.is_allowed) {
        try {
          analysis = await window.api.analyzeProject(project.id, { useAi: true })
          nextStatus = 'AI-assisted draft ready.'
        } catch {
          analysis = await window.api.analyzeProject(project.id, { useAi: false })
          nextStatus = 'AI assist failed. Local analysis loaded instead.'
        }
      } else {
        analysis = await window.api.analyzeProject(project.id, { useAi: false })
        nextStatus = 'Local analysis draft ready.'
      }

      const nextDraft = buildResumeDraft(project, analysis)
      setForm(nextDraft)
      setDraftStatus(nextStatus)
    } catch (draftError) {
      setFormError(draftError?.message || 'Failed to build a resume draft for this project.')
      setDraftStatus('')
    } finally {
      setDraftLoading(false)
    }
  }

  async function handleSave(event) {
    event.preventDefault()

    const nextBullets = prepareBulletPoints(form.bullet_points)
    if (!form.project_id) {
      setFormError('Select a project to build a resume entry.')
      return
    }
    if (!form.title.trim()) {
      setFormError('A resume title is required.')
      return
    }
    if (nextBullets.length === 0) {
      setFormError('Add at least one bullet point before saving.')
      return
    }

    setSaving(true)
    setFormError('')

    const commonPayload = {
      title: form.title.trim(),
      description: form.description.trim(),
      bullet_points: nextBullets,
      analysis_snapshot: parseSnapshotInput(form.analysis_snapshot),
    }

    try {
      let savedItem = null

      if (editingProjectId) {
        savedItem = await window.api.updateResume(user.username, editingProjectId, commonPayload)
        setResumes((current) =>
          sortResumesByUpdatedAt(
            current.map((item) => (item.project_id === editingProjectId ? savedItem : item))
          )
        )
      } else {
        savedItem = await window.api.createResume(user.username, {
          project_id: parseInt(form.project_id, 10),
          ...commonPayload,
        })
        setResumes((current) => sortResumesByUpdatedAt([savedItem, ...current]))
      }

      markPreviewStale()
      cancelForm()
    } catch (saveError) {
      setFormError(saveError?.message || 'Failed to save the resume entry.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(projectId) {
    try {
      await window.api.deleteResume(user.username, projectId)
      setResumes((current) => current.filter((item) => item.project_id !== projectId))
      setConfirmId(null)
      markPreviewStale()
    } catch (deleteError) {
      setError(deleteError?.message || 'Failed to delete the resume entry.')
    }
  }

  async function handlePreviewPdf() {
    if (!canGeneratePreview) {
      return
    }

    setPreviewLoading(true)
    setPreviewError('')

    try {
      const result = await window.api.downloadResumePdf(user.username, {
        template_name: templateName,
      })
      replacePreview(result.bytes, result.contentType, result.filename)
    } catch (previewFailure) {
      setPreviewError(previewFailure?.message || 'Failed to generate the PDF preview.')
    } finally {
      setPreviewLoading(false)
    }
  }

  function handleDownloadPreview() {
    if (!previewState.bytes) {
      return
    }

    downloadBlobFile(previewState.bytes, previewState.contentType, previewState.filename)
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Resumes"
        description="Shape project analysis into a final resume, preview the PDF, and export the finished version."
        action={!showForm && (
          <button
            type="button"
            onClick={openCreate}
            disabled={availableProjects.length === 0}
            className="btn-primary text-xs disabled:cursor-not-allowed disabled:opacity-40"
          >
            {availableProjects.length === 0 ? 'All Projects Added' : '+ Add Resume Entry'}
          </button>
        )}
      />

      <InlineError message={error} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_320px]">
        <div className="space-y-6">
          {showForm && (
            <form onSubmit={handleSave} className="card space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-sm font-bold">
                    {editingProjectId ? 'Edit Resume Entry' : 'Build Resume Entry'}
                  </h2>
                  <p className="mt-1 text-xs text-muted">
                    Save polished project bullets now. The PDF preview uses every saved entry.
                  </p>
                </div>
                <button type="button" className="btn-ghost text-xs" onClick={cancelForm}>
                  Cancel
                </button>
              </div>

              <InlineError message={formError} />

              {!editingProjectId && (
                <div className="rounded-lg border border-border bg-elevated/70 p-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-xs font-semibold text-ink">Draft Assist</div>
                      <p className="mt-1 text-2xs leading-relaxed text-muted">
                        Use AI when consent allows it, otherwise build from local project analysis.
                      </p>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-ink">
                      <input
                        type="checkbox"
                        checked={useAiAssist}
                        onChange={(event) => setUseAiAssist(event.target.checked)}
                        disabled={!llmConfig?.is_allowed || draftLoading}
                      />
                      Use AI Assist
                    </label>
                  </div>
                  <p className="mt-2 font-mono text-2xs uppercase tracking-widest text-muted">
                    {llmConfig?.is_allowed
                      ? `AI ready${llmConfig.model_preferences?.[0] ? ` · ${llmConfig.model_preferences[0]}` : ''}`
                      : 'Local analysis only'}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {editingProjectId ? (
                  <div className="rounded-lg border border-border bg-elevated/60 px-3 py-2">
                    <div className="text-2xs uppercase tracking-widest text-muted">Project</div>
                    <div className="mt-1 text-sm font-semibold text-ink">{form.project_name}</div>
                  </div>
                ) : (
                  <label className="space-y-1">
                    <span className="font-mono text-2xs uppercase tracking-widest text-muted">
                      Project
                    </span>
                    <select
                      value={form.project_id}
                      onChange={(event) => hydrateDraft(event.target.value)}
                      className="input"
                      disabled={draftLoading || availableProjects.length === 0}
                    >
                      <option value="">Choose a project…</option>
                      {availableProjects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <label className="space-y-1">
                  <span className="font-mono text-2xs uppercase tracking-widest text-muted">
                    Title
                  </span>
                  <input
                    className="input"
                    value={form.title}
                    onChange={(event) => updateField('title', event.target.value)}
                    placeholder="Project title for the resume"
                  />
                </label>
              </div>

              <label className="space-y-1">
                <span className="font-mono text-2xs uppercase tracking-widest text-muted">
                  Description
                </span>
                <textarea
                  rows={3}
                  className="input w-full"
                  value={form.description}
                  onChange={(event) => updateField('description', event.target.value)}
                  placeholder="Short summary for the entry"
                />
              </label>

              <label className="space-y-1">
                <span className="font-mono text-2xs uppercase tracking-widest text-muted">
                  Technologies
                </span>
                <input
                  className="input"
                  value={form.analysis_snapshot}
                  onChange={(event) => updateField('analysis_snapshot', event.target.value)}
                  placeholder="React, FastAPI, PostgreSQL"
                />
              </label>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-mono text-2xs uppercase tracking-widest text-muted">
                      Bullet Points
                    </div>
                    {draftStatus && <p className="mt-1 text-2xs text-muted">{draftStatus}</p>}
                  </div>
                  <button type="button" className="btn-ghost text-xs" onClick={addBullet}>
                    + Add Bullet
                  </button>
                </div>

                {draftLoading && (
                  <div className="flex items-center gap-2 rounded-lg border border-border bg-elevated/60 px-3 py-3 text-xs text-muted">
                    <span className="spinner" />
                    Building a draft from project analysis…
                  </div>
                )}

                <div className="space-y-3">
                  {form.bullet_points.map((bullet, index) => (
                    <div key={`${index}-${bullet.length}`} className="flex items-start gap-3">
                      <div className="pt-2 font-mono text-2xs uppercase tracking-widest text-muted">
                        {index + 1}
                      </div>
                      <textarea
                        rows={3}
                        className="input w-full"
                        value={bullet}
                        onChange={(event) => updateBullet(index, event.target.value)}
                        placeholder="Describe the project impact, scope, and results."
                      />
                      <button
                        type="button"
                        className="btn-ghost text-xs"
                        onClick={() => removeBullet(index)}
                        disabled={form.bullet_points.length === 1}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={saving || draftLoading}
                  className="btn-primary text-xs disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {saving ? 'Saving…' : editingProjectId ? 'Save Changes' : 'Save Resume Entry'}
                </button>
                <button type="button" className="btn-ghost text-xs" onClick={cancelForm}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          {(previewLoading || previewError || previewState.url) && (
            <section className="card space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold">PDF Preview</h2>
                  <p className="mt-1 text-xs text-muted">
                    Review the full generated document before downloading it.
                  </p>
                </div>
                {previewState.url && (
                  <div className="flex items-center gap-2">
                    {previewState.stale && (
                      <span className="rounded border border-amber-400/30 bg-amber-500/10 px-2 py-0.5 font-mono text-2xs uppercase tracking-widest text-amber-100">
                        Stale
                      </span>
                    )}
                    <button type="button" className="btn-primary text-xs" onClick={handleDownloadPreview}>
                      Download PDF
                    </button>
                  </div>
                )}
              </div>

              <InlineError message={previewError} />

              {previewLoading ? (
                <div className="flex min-h-[240px] items-center justify-center rounded-lg border border-border bg-elevated/50">
                  <div className="flex items-center gap-3 text-xs text-muted">
                    <span className="spinner" />
                    Rendering PDF preview…
                  </div>
                </div>
              ) : previewState.url ? (
                <iframe
                  title="Resume PDF preview"
                  src={previewState.url}
                  className="h-[640px] w-full rounded-lg border border-border bg-white"
                />
              ) : null}
            </section>
          )}

          {loading ? (
            <div className="flex justify-center py-12">
              <span className="spinner" />
            </div>
          ) : resumes.length > 0 ? (
            <div className="space-y-4">
              {resumes.map((item) => {
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

                      <div className="flex items-center gap-2">
                        <button type="button" className="btn-ghost text-xs" onClick={() => openEdit(item)}>
                          Edit
                        </button>
                        {confirmId === item.project_id ? (
                          <>
                            <span className="text-xs text-red-400">Delete?</span>
                            <button
                              type="button"
                              className="btn-ghost text-xs text-red-400"
                              onClick={() => handleDelete(item.project_id)}
                            >
                              Yes
                            </button>
                            <button
                              type="button"
                              className="btn-ghost text-xs"
                              onClick={() => setConfirmId(null)}
                            >
                              No
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            className="btn-ghost text-xs"
                            onClick={() => setConfirmId(item.project_id)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
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
              })}
            </div>
          ) : (
            <EmptyState message="No resume entries yet. Add a project to start shaping the final document." />
          )}
        </div>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <section className="card space-y-4">
            <div>
              <div className="font-mono text-2xs uppercase tracking-widest text-muted">
                Generate Resume
              </div>
              <h2 className="mt-2 text-lg font-extrabold tracking-tight text-ink">
                Preview the final PDF
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                The preview combines your profile, work experience, education, and every saved resume entry.
              </p>
            </div>

            <label className="space-y-1">
              <span className="font-mono text-2xs uppercase tracking-widest text-muted">
                Template
              </span>
              <select
                value={templateName}
                onChange={(event) => {
                  setTemplateName(event.target.value)
                  markPreviewStale()
                }}
                className="input"
              >
                {RESUME_TEMPLATE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex flex-col gap-2">
              <button
                type="button"
                className="btn-primary text-xs disabled:cursor-not-allowed disabled:opacity-40"
                onClick={handlePreviewPdf}
                disabled={!canGeneratePreview}
              >
                {previewLoading ? 'Generating…' : previewState.url ? 'Refresh Preview' : 'Preview PDF'}
              </button>
              <button
                type="button"
                className="btn-ghost text-xs disabled:cursor-not-allowed disabled:opacity-40"
                onClick={handleDownloadPreview}
                disabled={!previewState.bytes}
              >
                Download PDF
              </button>
            </div>

            <InlineError message={previewError} />
          </section>

          <section className="card space-y-2">
            <div className="font-mono text-2xs uppercase tracking-widest text-muted">
              Readiness Checklist
            </div>
            <ReadinessItem
              label="Profile"
              ready={hasProfile}
              detail={hasProfile ? 'Profile data is available for the resume header.' : 'Create your profile before generating the PDF.'}
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
            <ReadinessItem
              label="Draft Assist"
              ready={Boolean(llmConfig?.is_allowed)}
              detail={llmConfig?.is_allowed ? 'AI-assisted analysis is available from the form toggle.' : 'Local analysis is available without AI consent.'}
            />
          </section>
        </aside>
      </div>
    </div>
  )
}
