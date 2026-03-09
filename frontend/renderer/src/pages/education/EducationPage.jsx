import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
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

export default function EducationPage() {
  const { user, apiOk } = useApp()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmId, setConfirmId] = useState(null)

  useEffect(() => {
    if (!apiOk || !user?.username) {
      return
    }

    let cancelled = false

    async function load() {
      setLoading(true)

      try {
        const data = await window.api.getEducations(user.username)
        if (!cancelled) {
          setItems(data ?? [])
          setError('')
        }
      } catch (error) {
        if (!cancelled) {
          setError(error?.message || 'Failed to load')
          setItems([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()

    return () => {
      cancelled = true
    }
  }, [apiOk, user?.username])

  function openCreate() {
    setForm(EMPTY_FORM)
    setEditingId(null)
    setFormError('')
    setShowForm(true)
  }

  function openEdit(item) {
    setForm({
      institution: item.institution ?? '',
      degree: item.degree ?? '',
      field_of_study: item.field_of_study ?? '',
      gpa: item.gpa != null ? String(item.gpa) : '',
      start_date: item.start_date ?? '',
      end_date: item.end_date ?? '',
      achievements: item.achievements ?? '',
      is_current: item.is_current ?? false,
    })
    setEditingId(item.id)
    setFormError('')
    setShowForm(true)
  }

  function cancelForm() {
    setShowForm(false)
    setEditingId(null)
    setFormError('')
  }

  async function handleSave(event) {
    event.preventDefault()
    if (!form.institution.trim() || !form.degree.trim()) {
      setFormError('Institution and degree are required.')
      return
    }

    const gpaValue = form.gpa.trim() ? parseFloat(form.gpa) : null
    if (gpaValue !== null && (Number.isNaN(gpaValue) || gpaValue < 0 || gpaValue > 5)) {
      setFormError('GPA must be between 0.0 and 5.0.')
      return
    }

    setSaving(true)
    setFormError('')

    const payload = {
      institution: form.institution.trim(),
      degree: form.degree.trim(),
      field_of_study: form.field_of_study.trim() || null,
      gpa: gpaValue,
      start_date: form.start_date || null,
      end_date: form.is_current ? null : form.end_date || null,
      achievements: form.achievements.trim() || null,
      is_current: form.is_current,
    }

    try {
      if (editingId) {
        const updated = await window.api.updateEducation(user.username, editingId, payload)
        setItems((current) => current.map((item) => (item.id === editingId ? updated : item)))
      } else {
        const created = await window.api.createEducation(user.username, payload)
        setItems((current) => [...current, created])
      }

      cancelForm()
    } catch (error) {
      setFormError(error?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id) {
    try {
      await window.api.deleteEducation(user.username, id)
      setItems((current) => current.filter((item) => item.id !== id))
      setConfirmId(null)
    } catch (error) {
      setError(error?.message || 'Delete failed')
    }
  }

  function setField(key, value) {
    setForm((current) => ({ ...current, [key]: value }))
  }

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
          {items.map((item) => (
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
                  {confirmId === item.id ? (
                    <>
                      <span className="text-xs text-red-400">Delete?</span>
                      <button
                        type="button"
                        className="btn-ghost text-xs text-red-400"
                        onClick={() => handleDelete(item.id)}
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
                      onClick={() => setConfirmId(item.id)}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>

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
