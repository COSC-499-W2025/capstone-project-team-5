import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import InlineError from '../../components/InlineError'

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalysesPage() {
  const { apiOk, user } = useApp()
  const [projects, setProjects] = useState([])   // flat list of SavedProjectSummary
  const [error,    setError]    = useState('')
  const [selected, setSelected] = useState(null) // SavedProjectSummary

  useEffect(() => {
    if (!apiOk || !user?.username) return
    const username = user.username

    async function load() {
      try {
        const [allProjects, savedUploads] = await Promise.all([
          window.api.getProjects('?limit=100'),
          window.api.getSavedProjects(username).catch(() => []),
        ])

        // Build projectId → SavedProjectSummary map from saved uploads
        const savedMap = {}
        for (const upload of (savedUploads || [])) {
          for (const sp of (upload.projects || [])) {
            savedMap[sp.id] = sp
          }
        }

        // Use analyzed projects from getProjects() as the base list,
        // enriched with analyses history from getSavedProjects() when available.
        const items = (allProjects?.items || [])
          .filter((p) => p.importance_score != null || p.user_role)
          .map((p) => savedMap[p.id] ? { ...p, ...savedMap[p.id] } : p)

        items.sort((a, b) => {
          const aDate = a.analyses?.[0]?.created_at ?? ''
          const bDate = b.analyses?.[0]?.created_at ?? ''
          if (bDate !== aDate) return bDate.localeCompare(aDate)
          return b.id - a.id
        })

        setProjects(items)
        setError('')
      } catch (err) {
        setError(err?.message || 'Failed to load analyses.')
      }
    }

    load()
  }, [apiOk, user?.username])

  function handleUpdate(projectId, patch) {
    setProjects((prev) => prev.map((p) => p.id === projectId ? { ...p, ...patch } : p))
    setSelected((prev) => prev?.id === projectId ? { ...prev, ...patch } : prev)
  }

  return (
    <div className="-mx-9 -my-8 flex h-full">

      {/* ── Left: project list ─────────────────────────────────── */}
      <div className="w-72 shrink-0 border-r border-border flex flex-col">
        <div className="border-b border-border px-4 py-3">
          <p className="font-mono text-2xs text-ink/60 uppercase tracking-widest">
            {projects.length} project{projects.length !== 1 ? 's' : ''}
          </p>
        </div>
        <InlineError message={error} />
        {projects.length === 0 && !error && (
          <p className="px-4 py-6 text-sm text-muted">No saved analyses yet.</p>
        )}
        <div className="flex-1 overflow-y-auto py-1">
          {projects.map((p) => (
            <ProjectRow
              key={p.id}
              project={p}
              active={selected?.id === p.id}
              onClick={() => setSelected(p)}
            />
          ))}
        </div>
      </div>

      {/* ── Right: detail ─────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {selected ? (
          <ProjectDetail project={selected} onUpdate={handleUpdate} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            Select a project to view its analyses.
          </div>
        )}
      </div>

    </div>
  )
}

// ─── Left panel row ───────────────────────────────────────────────────────────

function ProjectRow({ project, active, onClick }) {
  const latestDate = project.analyses?.[0]?.created_at
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 transition-colors hover:bg-elevated border-b border-border/50 ${
        active ? 'bg-elevated border-l-2 border-l-accent' : 'border-l-2 border-l-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold text-ink leading-snug truncate">{project.name}</span>
        {project.analyses_count > 0 && (
          <span className="shrink-0 rounded bg-border px-1.5 py-0.5 font-mono text-2xs text-muted">
            {project.analyses_count}
          </span>
        )}
      </div>
      <p className="mt-0.5 font-mono text-2xs text-muted truncate">{project.rel_path}</p>
      {project.user_role && (
        <p className="mt-1 text-2xs text-ink/60 truncate">{project.user_role}</p>
      )}
      {latestDate && (
        <p className="mt-1 text-2xs text-muted">
          {new Date(latestDate).toLocaleDateString()}
        </p>
      )}
    </button>
  )
}

// ─── Right panel detail ───────────────────────────────────────────────────────

function ProjectDetail({ project, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [form,    setForm]    = useState({
    user_role:                    project.user_role                    ?? '',
    role_justification:           project.role_justification           ?? '',
    importance_score:             project.importance_score             ?? '',
    user_contribution_percentage: project.user_contribution_percentage ?? '',
    is_showcase:                  project.is_showcase                  ?? false,
  })
  const [saving,  setSaving]  = useState(false)
  const [saveErr, setSaveErr] = useState('')

  // Reset form if project changes
  useEffect(() => {
    setEditing(false)
    setForm({
      user_role:                    project.user_role                    ?? '',
      role_justification:           project.role_justification           ?? '',
      importance_score:             project.importance_score             ?? '',
      user_contribution_percentage: project.user_contribution_percentage ?? '',
      is_showcase:                  project.is_showcase                  ?? false,
    })
  }, [project.id])

  async function save() {
    setSaving(true)
    setSaveErr('')
    try {
      const patch = {
        user_role:                    form.user_role                    || null,
        role_justification:           form.role_justification           || null,
        importance_score:             form.importance_score !== '' ? Number(form.importance_score) : null,
        user_contribution_percentage: form.user_contribution_percentage !== '' ? Number(form.user_contribution_percentage) : null,
        is_showcase:                  form.is_showcase,
      }
      const updated = await window.api.updateProject(project.id, patch)
      onUpdate(project.id, updated)
      setEditing(false)
    } catch (e) {
      setSaveErr(e?.message || 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="px-8 py-7 max-w-2xl space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-ink">{project.name}</h2>
          <p className="mt-0.5 font-mono text-xs text-muted">{project.rel_path}</p>
          <div className="mt-1.5 flex flex-wrap gap-2 text-xs text-muted">
            {project.file_count != null && <span>{project.file_count} files</span>}
            {project.lines_of_code     && <span>· {project.lines_of_code.toLocaleString()} lines</span>}
            {project.has_git_repo      && <span>· git</span>}
            {project.is_collaborative  && <span>· collaborative</span>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {editing ? (
            <>
              <button
                onClick={() => { setEditing(false); setSaveErr('') }}
                className="rounded border border-border-hi px-3 py-1.5 text-xs text-muted transition-colors hover:text-ink"
              >
                Cancel
              </button>
              <button
                onClick={save}
                disabled={saving}
                className="rounded border border-border-hi bg-elevated px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-border disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="rounded border border-border-hi px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-elevated"
            >
              Edit
            </button>
          )}
        </div>
      </div>

      {saveErr && (
        <p className="rounded border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">{saveErr}</p>
      )}

      {/* Fields */}
      {editing ? (
        <EditForm form={form} setForm={setForm} />
      ) : (
        <ReadOnlyFields project={project} />
      )}

      {/* Tech stack */}
      {(project.languages?.length > 0 || project.tools?.length > 0 || project.practices?.length > 0) && (
        <Section label="Tech stack">
          <div className="space-y-3">
            {project.languages?.length > 0 && (
              <TagRow label="Languages" tags={project.languages} />
            )}
            {project.tools?.length > 0 && (
              <TagRow label="Tools" tags={project.tools} />
            )}
            {project.practices?.length > 0 && (
              <TagRow label="Practices" tags={project.practices} />
            )}
          </div>
        </Section>
      )}

      {/* Analysis history */}
      {project.analyses?.length > 0 && (
        <Section label={`Analysis history · ${project.analyses.length}`}>
          <div className="space-y-3">
            {[...project.analyses].reverse().map((a) => (
              <AnalysisEntry
                key={a.id}
                analysis={a}
                projectId={project.id}
                onUpdate={(updated) => onUpdate(project.id, {
                  analyses: project.analyses.map((x) => x.id === updated.id ? updated : x),
                })}
              />
            ))}
          </div>
        </Section>
      )}

    </div>
  )
}

// ─── Edit form ────────────────────────────────────────────────────────────────

function EditForm({ form, setForm }) {
  function field(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  }
  return (
    <div className="space-y-4">
      <Field label="Role">
        <input
          type="text"
          className="input w-full text-sm"
          value={form.user_role}
          onChange={field('user_role')}
          placeholder="e.g. Full Stack Developer"
        />
      </Field>
      <Field label="Role justification">
        <textarea
          className="input w-full text-sm resize-none"
          rows={3}
          value={form.role_justification}
          onChange={field('role_justification')}
          placeholder="Why this role was assigned…"
        />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Importance score">
          <input
            type="number"
            className="input w-full text-sm"
            value={form.importance_score}
            onChange={field('importance_score')}
            min={0} max={100} step={1}
            placeholder="0–100"
          />
        </Field>
        <Field label="Contribution %">
          <input
            type="number"
            className="input w-full text-sm"
            value={form.user_contribution_percentage}
            onChange={field('user_contribution_percentage')}
            min={0} max={100} step={1}
            placeholder="0–100"
          />
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm text-ink cursor-pointer select-none">
        <input
          type="checkbox"
          className="accent-accent"
          checked={form.is_showcase}
          onChange={field('is_showcase')}
        />
        Mark as showcase project
      </label>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <p className="text-xs text-ink/50 mb-1">{label}</p>
      {children}
    </div>
  )
}

// ─── Read-only fields ─────────────────────────────────────────────────────────

function ReadOnlyFields({ project }) {
  const items = [
    { label: 'Role',           value: project.user_role },
    { label: 'Justification',  value: project.role_justification },
    { label: 'Score',          value: project.importance_score != null ? Math.round(project.importance_score) : null },
    { label: 'Contribution',   value: project.user_contribution_percentage != null ? `${Math.round(project.user_contribution_percentage)}%` : null },
    { label: 'Date range',     value: project.start_date ? `${fmtDate(project.start_date)} → ${fmtDate(project.end_date)}` : null },
  ].filter((i) => i.value != null)

  if (!items.length) {
    return <p className="text-sm text-muted">No analysis data. Click Edit to add details manually.</p>
  }

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3">
      {items.map((item) => (
        <div key={item.label} className={item.label === 'Justification' ? 'col-span-2' : ''}>
          <p className="text-xs text-ink/50 mb-0.5">{item.label}</p>
          <p className="text-sm text-ink font-medium leading-snug">{item.value}</p>
        </div>
      ))}
    </div>
  )
}

function fmtDate(d) {
  if (!d) return '?'
  return new Date(d).toLocaleDateString()
}

// ─── Analysis entry ───────────────────────────────────────────────────────────

function AnalysisEntry({ analysis: initialAnalysis, projectId, onUpdate }) {
  const [analysis, setAnalysis] = useState(initialAnalysis)
  const [expanded, setExpanded] = useState(false)
  const [editing,  setEditing]  = useState(false)
  const [form,     setForm]     = useState({
    language: '', summary_text: '', resume_bullets: [], ai_bullets: [],
    score_breakdown: {}, skill_timeline: [],
    tools: [], practices: [], other_languages: [],
  })
  const [saving,   setSaving]   = useState(false)
  const [err,      setErr]      = useState('')

  function startEdit(e) {
    e.stopPropagation()
    setForm({
      language:        analysis.language        ?? '',
      summary_text:    analysis.summary_text    ?? '',
      resume_bullets:  analysis.resume_bullets ? [...analysis.resume_bullets] : [],
      ai_bullets:      analysis.ai_bullets     ? [...analysis.ai_bullets]     : [],
      score_breakdown:  analysis.score_breakdown ? { ...analysis.score_breakdown } : {},
      skill_timeline:   analysis.skill_timeline  ? analysis.skill_timeline.map((e) => ({ ...e, skills: [...(e.skills || [])] })) : [],
      tools:            analysis.tools            ? [...analysis.tools]            : [],
      practices:        analysis.practices        ? [...analysis.practices]        : [],
      other_languages:  analysis.other_languages  ? [...analysis.other_languages]  : [],
    })
    setEditing(true)
    setExpanded(true)
    setErr('')
  }

  function makeBulletHandlers(key) {
    return {
      set:    (i, val) => setForm((f) => ({ ...f, [key]: f[key].map((b, j) => j === i ? val : b) })),
      add:    ()       => setForm((f) => ({ ...f, [key]: [...f[key], ''] })),
      remove: (i)      => setForm((f) => ({ ...f, [key]: f[key].filter((_, j) => j !== i) })),
    }
  }

  async function save(e) {
    e.stopPropagation()
    setSaving(true)
    setErr('')
    try {
      const updated = await window.api.updateAnalysis(projectId, analysis.id, {
        language:        form.language       || null,
        summary_text:    form.summary_text   || null,
        resume_bullets:  form.resume_bullets.filter(Boolean),
        ai_bullets:      form.ai_bullets.filter(Boolean),
        score_breakdown:  form.score_breakdown,
        skill_timeline:   form.skill_timeline,
        tools:            form.tools,
        practices:        form.practices,
        other_languages:  form.other_languages,
      })
      setAnalysis(updated)
      setEditing(false)
      onUpdate?.(updated)
    } catch (e) {
      setErr(e?.message || 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  function cancel(e) {
    e.stopPropagation()
    setEditing(false)
    setErr('')
  }

  return (
    <div className="rounded border border-border transition-colors hover:border-border-hi">
      {/* Header row */}
      <div
        className="flex items-center justify-between gap-3 px-3 py-2.5 cursor-pointer"
        onClick={() => !editing && setExpanded((x) => !x)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-mono text-xs text-ink/60 shrink-0">
            {new Date(analysis.created_at).toLocaleString()}
          </span>
          {analysis.language && (
            <span className="rounded border border-border px-1.5 py-0.5 font-mono text-2xs text-muted shrink-0">
              {analysis.language}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {!editing && (
            <button
              onClick={startEdit}
              className="rounded px-2 py-0.5 text-2xs text-muted transition-colors hover:bg-elevated hover:text-ink"
            >
              Edit
            </button>
          )}
          {editing ? (
            <>
              <button
                onClick={cancel}
                className="rounded px-2 py-0.5 text-2xs text-muted transition-colors hover:text-ink"
              >
                Cancel
              </button>
              <button
                onClick={save}
                disabled={saving}
                className="rounded border border-border-hi bg-elevated px-2 py-0.5 text-2xs font-medium text-ink transition-colors hover:bg-border disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <svg
              className={`h-3 w-3 text-muted transition-transform ${expanded ? 'rotate-180' : ''}`}
              viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          )}
        </div>
      </div>

      {/* Expanded body */}
      {(expanded || editing) && (
        <div className="border-t border-border px-3 pb-3 pt-2.5">
          {err && (
            <p className="mb-2 text-xs text-danger">{err}</p>
          )}
          {editing ? (
            <div className="space-y-4" onClick={(e) => e.stopPropagation()}>
              <EditField label="Language">
                <input type="text" className="input w-full text-sm" value={form.language}
                  onChange={(e) => setForm((f) => ({ ...f, language: e.target.value }))} />
              </EditField>
              <EditField label="Summary">
                <textarea className="input w-full text-sm resize-none" rows={3} value={form.summary_text}
                  onChange={(e) => setForm((f) => ({ ...f, summary_text: e.target.value }))}
                  placeholder="Write a summary…" />
              </EditField>
              <BulletEditor
                label="Resume bullets"
                bullets={form.resume_bullets}
                handlers={makeBulletHandlers('resume_bullets')}
                color="success"
              />
              <BulletEditor
                label="AI bullets"
                bullets={form.ai_bullets}
                handlers={makeBulletHandlers('ai_bullets')}
                color="border-hi"
              />
              {Object.keys(form.score_breakdown).length > 0 && (
                <EditField label="Score breakdown">
                  <div className="space-y-2">
                    {Object.entries(form.score_breakdown).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-3">
                        <span className="text-xs text-ink/70 capitalize flex-1">{k.replace(/_/g, ' ')}</span>
                        <input
                          type="number"
                          className="input w-20 text-xs text-right"
                          value={v}
                          min={0} max={100} step={1}
                          onChange={(e) => setForm((f) => ({
                            ...f,
                            score_breakdown: { ...f.score_breakdown, [k]: Number(e.target.value) },
                          }))}
                        />
                      </div>
                    ))}
                  </div>
                </EditField>
              )}
              {(['tools', 'practices', 'other_languages']).map((key) => (
                form[key].length > 0 && (
                  <EditField key={key} label={key === 'other_languages' ? 'Languages' : key.charAt(0).toUpperCase() + key.slice(1)}>
                    <TagEditor
                      tags={form[key]}
                      onChange={(tags) => setForm((f) => ({ ...f, [key]: tags }))}
                    />
                  </EditField>
                )
              ))}
              {form.skill_timeline.length > 0 && (
                <EditField label="Skill timeline">
                  <div className="space-y-2">
                    {form.skill_timeline.map((entry, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <input
                          type="text"
                          className="input w-24 text-xs font-mono shrink-0"
                          value={entry.date ?? ''}
                          onChange={(e) => setForm((f) => ({
                            ...f,
                            skill_timeline: f.skill_timeline.map((x, j) => j === i ? { ...x, date: e.target.value } : x),
                          }))}
                          placeholder="date"
                        />
                        <input
                          type="text"
                          className="input flex-1 text-xs"
                          value={(entry.skills || []).join(', ')}
                          onChange={(e) => setForm((f) => ({
                            ...f,
                            skill_timeline: f.skill_timeline.map((x, j) => j === i ? { ...x, skills: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) } : x),
                          }))}
                          placeholder="skills (comma separated)"
                        />
                      </div>
                    ))}
                  </div>
                </EditField>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {analysis.summary_text
                ? <p className="text-xs text-ink/70 leading-relaxed whitespace-pre-wrap">{analysis.summary_text}</p>
                : <p className="text-xs text-muted">No summary. Click Edit to add one.</p>
              }
              {analysis.resume_bullets?.length > 0 && (
                <BulletList label="Resume bullets" bullets={analysis.resume_bullets} color="success" />
              )}
              {analysis.ai_bullets?.length > 0 && (
                <BulletList label="AI summary" bullets={analysis.ai_bullets} color="border-hi" warning={analysis.ai_warning} />
              )}
              {[['Languages', analysis.other_languages], ['Tools', analysis.tools], ['Practices', analysis.practices]].map(([label, tags]) =>
                tags?.length > 0 && (
                  <div key={label}>
                    <p className="font-mono text-2xs text-ink/60 uppercase tracking-widest mb-1.5">{label}</p>
                    <div className="flex flex-wrap gap-1">
                      {tags.map((t, i) => (
                        <span key={i} className="rounded border border-border px-2 py-0.5 font-mono text-xs text-ink/70">{t}</span>
                      ))}
                    </div>
                  </div>
                )
              )}
              {analysis.score_breakdown && Object.keys(analysis.score_breakdown).length > 0 && (
                <div>
                  <p className="font-mono text-2xs text-ink/60 uppercase tracking-widest mb-2">Score breakdown</p>
                  <div className="space-y-2">
                    {Object.entries(analysis.score_breakdown).map(([k, v]) => (
                      <MiniScoreBar key={k} label={k.replace(/_/g, ' ')} value={v} />
                    ))}
                  </div>
                </div>
              )}
              {analysis.git?.is_repo && (
                <div>
                  <p className="font-mono text-2xs text-ink/60 uppercase tracking-widest mb-2">Git activity</p>
                  <MiniGit git={analysis.git} />
                </div>
              )}
              {analysis.skill_timeline?.length > 0 && (
                <div>
                  <p className="font-mono text-2xs text-ink/60 uppercase tracking-widest mb-2">Skill timeline</p>
                  <div className="space-y-1.5">
                    {analysis.skill_timeline.map((entry, i) => (
                      <div key={i} className="flex items-start gap-3 text-xs">
                        <span className="shrink-0 w-20 font-mono text-muted">{entry.date}</span>
                        <div className="flex flex-wrap gap-1">
                          {entry.skills?.map((s, j) => (
                            <span key={j} className="rounded border border-border px-1.5 py-0.5 font-mono text-ink/70">{s}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Shared ───────────────────────────────────────────────────────────────────

function Section({ label, children }) {
  return (
    <div className="rounded border border-border">
      <div className="border-b border-border px-3 py-2">
        <span className="font-mono text-2xs text-ink/60 uppercase tracking-widest">{label}</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}

function TagEditor({ tags, onChange }) {
  const [input, setInput] = useState('')
  function add() {
    const val = input.trim()
    if (val && !tags.includes(val)) onChange([...tags, val])
    setInput('')
  }
  return (
    <div>
      <div className="flex flex-wrap gap-1 mb-2">
        {tags.map((t, i) => (
          <span key={i} className="flex items-center gap-1 rounded border border-border px-2 py-0.5 font-mono text-xs text-ink/70">
            {t}
            <button onClick={() => onChange(tags.filter((_, j) => j !== i))} className="text-muted hover:text-danger ml-0.5">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          className="input flex-1 text-xs"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          placeholder="Add tag, press Enter"
        />
        <button onClick={add} className="rounded border border-border-hi px-2 py-1 text-xs text-muted hover:text-ink transition-colors">Add</button>
      </div>
    </div>
  )
}

function EditField({ label, children }) {
  return (
    <div>
      <p className="text-xs text-ink/50 mb-1">{label}</p>
      {children}
    </div>
  )
}

function BulletEditor({ label, bullets, handlers, color }) {
  const markerCls = color === 'success' ? 'text-success/60' : 'text-border-hi'
  return (
    <div>
      <p className="text-xs text-ink/50 mb-2">{label}</p>
      <div className="space-y-2">
        {bullets.map((b, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={`mt-2 shrink-0 text-xs ${markerCls}`}>▸</span>
            <textarea
              className="input flex-1 text-xs resize-none"
              rows={2}
              value={b}
              onChange={(e) => handlers.set(i, e.target.value)}
              placeholder="Bullet point…"
            />
            <button
              onClick={() => handlers.remove(i)}
              className="mt-1.5 rounded p-1 text-muted hover:text-danger transition-colors"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        ))}
        <button onClick={handlers.add} className="text-xs text-muted hover:text-ink transition-colors">
          + Add bullet
        </button>
      </div>
    </div>
  )
}

function BulletList({ label, bullets, color, warning }) {
  const markerCls = color === 'success' ? 'text-success/60' : 'text-ink/40'
  return (
    <div>
      <p className="font-mono text-2xs text-ink/60 uppercase tracking-widest mb-1.5">{label}</p>
      {warning && (
        <p className="mb-1.5 rounded border border-accent/30 bg-accent/10 px-2 py-1 text-xs text-accent/80">{warning}</p>
      )}
      <ul className="space-y-1.5">
        {bullets.map((b, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-ink/80 leading-relaxed">
            <span className={`shrink-0 mt-0.5 ${markerCls}`}>▸</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function MiniScoreBar({ label, value }) {
  const pct = Math.min(100, Math.max(0, Math.round(value)))
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-ink/70 capitalize">{label}</span>
        <span className="font-mono text-xs font-semibold text-ink tabular-nums">{pct}</span>
      </div>
      <div className="h-0.5 w-full rounded-full bg-border">
        <div className="h-0.5 rounded-full bg-ink/40" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function MiniGit({ git }) {
  const mine = git.current_author_contribution
  return (
    <div className="space-y-2">
      {mine && (
        <div className="grid grid-cols-3 gap-3 text-xs">
          {[['Commits', mine.commits], ['Added', mine.added?.toLocaleString()], ['Removed', mine.deleted?.toLocaleString()]].map(([l, v]) => (
            <div key={l}>
              <p className="text-ink/50 mb-0.5">{l}</p>
              <p className="font-medium text-ink">{v ?? '—'}</p>
            </div>
          ))}
        </div>
      )}
      {git.author_contributions?.length > 1 && (
        <div className="space-y-1">
          {git.author_contributions.map((c, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="text-ink truncate max-w-[55%]">{c.author}</span>
              <span className="font-mono text-ink/50 shrink-0">{c.commits}c · +{c.added} / -{c.deleted}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TagRow({ label, tags }) {
  return (
    <div>
      <p className="text-xs text-ink/50 mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1">
        {tags.map((t, i) => (
          <span key={i} className="rounded border border-border px-2 py-0.5 font-mono text-xs text-ink/70">
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
