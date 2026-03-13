import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import useCrudList from '../../hooks/useCrudList'
import { formatDateRange } from '../../lib/dates'

const EMPTY_FORM = {
  company: '',
  title: '',
  location: '',
  description: '',
  bullets: [''],
  start_date: '',
  end_date: '',
  is_current: false,
}

const API = {
  list: (username) => window.api.getWorkExperiences(username),
  create: (username, data) => window.api.createWorkExperience(username, data),
  update: (username, id, data) => window.api.updateWorkExperience(username, id, data),
  remove: (username, id) => window.api.deleteWorkExperience(username, id),
}

function validate(form) {
  if (!form.company.trim() || !form.title.trim()) {
    return 'Company and title are required.'
  }
  return null
}

function parseBullets(raw) {
  if (!raw) return ['']
  if (Array.isArray(raw)) return raw.length ? raw : ['']
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.length ? parsed.map(String) : ['']
  } catch {
    return [raw]
  }
}

function itemToForm(item) {
  return {
    company: item.company ?? '',
    title: item.title ?? '',
    location: item.location ?? '',
    description: item.description ?? '',
    bullets: parseBullets(item.bullets),
    start_date: item.start_date ?? '',
    end_date: item.end_date ?? '',
    is_current: item.is_current ?? false,
  }
}

function buildPayload(form) {
  const cleaned = form.bullets.map((b) => b.trim()).filter(Boolean)
  return {
    company: form.company.trim(),
    title: form.title.trim(),
    location: form.location.trim() || null,
    description: form.description.trim() || null,
    bullets: cleaned.length ? JSON.stringify(cleaned) : null,
    start_date: form.start_date || null,
    end_date: form.is_current ? null : form.end_date || null,
    is_current: form.is_current,
  }
}

export default function ExperiencePage() {
  const {
    items, error, loading, showForm, editingId, form,
    formError, saving, confirmId, setConfirmId,
    openCreate, openEdit, cancelForm, setField, handleSave, handleDelete,
  } = useCrudList({ emptyForm: EMPTY_FORM, api: API, itemToForm, validate, buildPayload })

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Experience"
        description="Manage your work experience entries."
        action={!showForm && (
          <button type="button" className="btn-primary text-xs" onClick={openCreate}>
            + Add Experience
          </button>
        )}
      />

      <InlineError message={error} />

      {showForm && (
        <form onSubmit={handleSave} className="card space-y-4 p-5">
          <h2 className="text-sm font-bold">{editingId ? 'Edit Experience' : 'New Experience'}</h2>
          <InlineError message={formError} />

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              className="input"
              placeholder="Company *"
              required
              value={form.company}
              onChange={(event) => setField('company', event.target.value)}
            />
            <input
              className="input"
              placeholder="Title *"
              required
              value={form.title}
              onChange={(event) => setField('title', event.target.value)}
            />
            <input
              className="input"
              placeholder="Location"
              value={form.location}
              onChange={(event) => setField('location', event.target.value)}
            />
            <div className="flex items-center gap-2">
              <input
                type="date"
                className="input flex-1"
                value={form.start_date}
                onChange={(event) => setField('start_date', event.target.value)}
              />
              <span className="text-2xs text-muted">to</span>
              {form.is_current ? (
                <span className="input flex-1 cursor-default text-center text-muted">Present</span>
              ) : (
                <input
                  type="date"
                  className="input flex-1"
                  value={form.end_date}
                  onChange={(event) => setField('end_date', event.target.value)}
                />
              )}
            </div>
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-xs text-ink">
            <input
              type="checkbox"
              checked={form.is_current}
              onChange={(event) => setField('is_current', event.target.checked)}
            />
            I currently work here
          </label>

          <textarea
            className="input w-full"
            rows={3}
            placeholder="Description"
            value={form.description}
            onChange={(event) => setField('description', event.target.value)}
          />

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">Bullet Points</label>
            {form.bullets.map((bullet, index) => (
              <div key={index} className="flex items-center gap-2">
                <span className="text-xs text-muted">•</span>
                <input
                  className="input flex-1"
                  placeholder={`Bullet point ${index + 1}`}
                  value={bullet}
                  onChange={(event) => {
                    const updated = [...form.bullets]
                    updated[index] = event.target.value
                    setField('bullets', updated)
                  }}
                />
                {form.bullets.length > 1 && (
                  <button
                    type="button"
                    className="btn-ghost text-xs text-red-400"
                    onClick={() => setField('bullets', form.bullets.filter((_, i) => i !== index))}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              className="btn-ghost text-xs"
              onClick={() => setField('bullets', [...form.bullets, ''])}
            >
              + Add bullet
            </button>
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-xs" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className="btn-ghost text-xs" onClick={cancelForm}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <span className="spinner" />
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="grid grid-cols-1 gap-3">
          {items.filter((item) => item.id !== editingId).map((item) => (
            <div key={item.id} className="card space-y-2 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-bold">{item.title}</h3>
                  <p className="truncate text-xs text-muted">{item.company}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" className="btn-ghost text-xs" onClick={() => openEdit(item)}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    onClick={() => setConfirmId(confirmId === item.id ? null : item.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>

              {confirmId === item.id && (
                <div className="flex items-center justify-between rounded-md border border-red-500/30 bg-red-500/10 px-4 py-2">
                  <span className="text-xs text-red-400">Are you sure you want to delete this entry?</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
                      onClick={() => handleDelete(item.id)}
                    >
                      Delete
                    </button>
                    <button
                      type="button"
                      className="btn-ghost text-xs"
                      onClick={() => setConfirmId(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {(item.location || item.start_date) && (
                <div className="flex items-center gap-3 font-mono text-2xs text-muted">
                  {item.location && <span>{item.location}</span>}
                  {formatDateRange(item) && <span>{formatDateRange(item)}</span>}
                  {item.is_current && <span className="tag">Current</span>}
                </div>
              )}

              {item.description && (
                <p className="text-xs leading-relaxed text-ink/70">{item.description}</p>
              )}

              {(() => {
                const bullets = parseBullets(item.bullets)
                const nonEmpty = bullets.filter((b) => b.trim())
                return nonEmpty.length > 0 && (
                  <ul className="list-disc pl-4 text-xs leading-relaxed text-ink/70">
                    {nonEmpty.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                )
              })()}
            </div>
          ))}
        </div>
      )}

      {!loading && !showForm && items.length === 0 && (
        <EmptyState message="No experience entries yet. Add one to get started." />
      )}
    </div>
  )
}
