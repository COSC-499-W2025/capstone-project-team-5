import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import useCrudList from '../../hooks/useCrudList'
import { formatDateRange } from '../../lib/dates'

const EMPTY_FORM = {
  institution: '',
  degree: '',
  field_of_study: '',
  gpa: '',
  start_date: '',
  end_date: '',
  achievements: '',
  is_current: false,
}

const API = {
  list: (username) => window.api.getEducations(username),
  create: (username, data) => window.api.createEducation(username, data),
  update: (username, id, data) => window.api.updateEducation(username, id, data),
  remove: (username, id) => window.api.deleteEducation(username, id),
}

function validate(form) {
  if (!form.institution.trim() || !form.degree.trim()) {
    return 'Institution and degree are required.'
  }
  const gpaValue = form.gpa.trim() ? parseFloat(form.gpa) : null
  if (gpaValue !== null && (Number.isNaN(gpaValue) || gpaValue < 0 || gpaValue > 5)) {
    return 'GPA must be between 0.0 and 5.0.'
  }
  return null
}

function buildPayload(form) {
  const gpaValue = form.gpa.trim() ? parseFloat(form.gpa) : null
  return {
    institution: form.institution.trim(),
    degree: form.degree.trim(),
    field_of_study: form.field_of_study.trim() || null,
    gpa: gpaValue,
    start_date: form.start_date || null,
    end_date: form.is_current ? null : form.end_date || null,
    achievements: form.achievements.trim() || null,
    is_current: form.is_current,
  }
}

export default function EducationPage() {
  const {
    items, error, loading, showForm, editingId, form,
    formError, saving, confirmId, setConfirmId,
    openCreate, openEdit, cancelForm, setField, handleSave, handleDelete,
  } = useCrudList({ emptyForm: EMPTY_FORM, api: API, validate, buildPayload })

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Education"
        description="Manage your education entries."
        action={!showForm && (
          <button type="button" className="btn-primary text-xs" onClick={openCreate}>
            + Add Education
          </button>
        )}
      />

      <InlineError message={error} />

      {showForm && (
        <form onSubmit={handleSave} className="card space-y-4 p-5">
          <h2 className="text-sm font-bold">{editingId ? 'Edit Education' : 'New Education'}</h2>
          <InlineError message={formError} />

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              className="input"
              placeholder="Institution *"
              required
              value={form.institution}
              onChange={(event) => setField('institution', event.target.value)}
            />
            <input
              className="input"
              placeholder="Degree *"
              required
              value={form.degree}
              onChange={(event) => setField('degree', event.target.value)}
            />
            <input
              className="input"
              placeholder="Field of Study"
              value={form.field_of_study}
              onChange={(event) => setField('field_of_study', event.target.value)}
            />
            <input
              className="input"
              placeholder="GPA (0.0 – 5.0)"
              value={form.gpa}
              onChange={(event) => setField('gpa', event.target.value)}
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
            I currently attend here
          </label>

          <textarea
            className="input w-full"
            rows={3}
            placeholder="Achievements"
            value={form.achievements}
            onChange={(event) => setField('achievements', event.target.value)}
          />

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
                  <h3 className="truncate text-sm font-bold">{item.degree}</h3>
                  <p className="truncate text-xs text-muted">{item.institution}</p>
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

              {(item.field_of_study || item.gpa != null || item.start_date) && (
                <div className="flex items-center gap-3 font-mono text-2xs text-muted">
                  {item.field_of_study && <span>{item.field_of_study}</span>}
                  {item.gpa != null && <span>GPA {item.gpa}</span>}
                  {formatDateRange(item) && <span>{formatDateRange(item)}</span>}
                  {item.is_current && <span className="tag">Current</span>}
                </div>
              )}

              {item.achievements && (
                <p className="text-xs leading-relaxed text-ink/70">{item.achievements}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && !showForm && items.length === 0 && (
        <EmptyState message="No education entries yet. Add one to get started." />
      )}
    </div>
  )
}
