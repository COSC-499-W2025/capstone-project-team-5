import { useState, useEffect } from 'react'
import { useApp } from '../App'

const EMPTY_FORM = {
  institution: '', degree: '', field_of_study: '', gpa: '',
  start_date: '', end_date: '', achievements: '', is_current: false,
}

export default function EducationPage() {
  const { user, apiOk } = useApp()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  // form state
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  // delete confirmation
  const [confirmId, setConfirmId] = useState(null)

  useEffect(() => {
    if (!apiOk || !user?.username) return
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const data = await window.api.getEducations(user.username)
        if (!cancelled) { setItems(data ?? []); setError('') }
      } catch (err) {
        if (!cancelled) { setError(err?.message || 'Failed to load'); setItems([]) }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
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

  async function handleSave(e) {
    e.preventDefault()
    if (!form.institution.trim() || !form.degree.trim()) {
      setFormError('Institution and degree are required.')
      return
    }

    const gpaVal = form.gpa.trim() ? parseFloat(form.gpa) : null
    if (gpaVal !== null && (isNaN(gpaVal) || gpaVal < 0 || gpaVal > 5)) {
      setFormError('GPA must be between 0.0 and 5.0.')
      return
    }

    setSaving(true)
    setFormError('')

    const payload = {
      institution: form.institution.trim(),
      degree: form.degree.trim(),
      field_of_study: form.field_of_study.trim() || null,
      gpa: gpaVal,
      start_date: form.start_date || null,
      end_date: form.is_current ? null : (form.end_date || null),
      achievements: form.achievements.trim() || null,
      is_current: form.is_current,
    }

    try {
      if (editingId) {
        const updated = await window.api.updateEducation(user.username, editingId, payload)
        setItems(prev => prev.map(it => it.id === editingId ? updated : it))
      } else {
        const created = await window.api.createEducation(user.username, payload)
        setItems(prev => [...prev, created])
      }
      cancelForm()
    } catch (err) {
      setFormError(err?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id) {
    try {
      await window.api.deleteEducation(user.username, id)
      setItems(prev => prev.filter(it => it.id !== id))
      setConfirmId(null)
    } catch (err) {
      setError(err?.message || 'Delete failed')
    }
  }

  function setField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  function formatDate(iso) {
    if (!iso) return null
    const d = new Date(iso + 'T00:00:00')
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  }

  function dateRange(item) {
    const start = formatDate(item.start_date)
    if (!start) return null
    const end = item.is_current ? 'Present' : formatDate(item.end_date)
    return end ? `${start} – ${end}` : start
  }

  return (
    <div className="animate-fade-up space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Education</h1>
          <p className="text-sm text-muted mt-1">Manage your education entries.</p>
        </div>
        {!showForm && (
          <button className="btn-primary text-xs" onClick={openCreate}>
            + Add Education
          </button>
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {/* Create / Edit form */}
      {showForm && (
        <form onSubmit={handleSave} className="card space-y-4 p-5">
          <h2 className="text-sm font-bold">
            {editingId ? 'Edit Education' : 'New Education'}
          </h2>

          {formError && <p className="text-xs text-red-400">{formError}</p>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              className="input" placeholder="Institution *" required
              value={form.institution}
              onChange={e => setField('institution', e.target.value)}
            />
            <input
              className="input" placeholder="Degree *" required
              value={form.degree}
              onChange={e => setField('degree', e.target.value)}
            />
            <input
              className="input" placeholder="Field of Study"
              value={form.field_of_study}
              onChange={e => setField('field_of_study', e.target.value)}
            />
            <input
              className="input" placeholder="GPA (0.0 – 5.0)"
              value={form.gpa}
              onChange={e => setField('gpa', e.target.value)}
            />
            <div className="flex items-center gap-2">
              <input
                type="date" className="input flex-1"
                value={form.start_date}
                onChange={e => setField('start_date', e.target.value)}
              />
              <span className="text-2xs text-muted">to</span>
              {form.is_current ? (
                <span className="input flex-1 text-muted text-center cursor-default">Present</span>
              ) : (
                <input
                  type="date" className="input flex-1"
                  value={form.end_date}
                  onChange={e => setField('end_date', e.target.value)}
                />
              )}
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-ink cursor-pointer">
            <input
              type="checkbox" checked={form.is_current}
              onChange={e => setField('is_current', e.target.checked)}
            />
            I currently attend here
          </label>

          <textarea
            className="input w-full" rows={3} placeholder="Achievements"
            value={form.achievements}
            onChange={e => setField('achievements', e.target.value)}
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

      {/* Loading */}
      {loading && <div className="flex justify-center py-12"><span className="spinner" /></div>}

      {/* Cards */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-1 gap-3">
          {items.map(item => (
            <div key={item.id} className="card p-5 space-y-2">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="text-sm font-bold truncate">{item.degree}</h3>
                  <p className="text-xs text-muted truncate">{item.institution}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button className="btn-ghost text-xs" onClick={() => openEdit(item)}>
                    Edit
                  </button>
                  {confirmId === item.id ? (
                    <>
                      <span className="text-xs text-red-400">Delete?</span>
                      <button className="btn-ghost text-xs text-red-400" onClick={() => handleDelete(item.id)}>
                        Yes
                      </button>
                      <button className="btn-ghost text-xs" onClick={() => setConfirmId(null)}>
                        No
                      </button>
                    </>
                  ) : (
                    <button className="btn-ghost text-xs" onClick={() => setConfirmId(item.id)}>
                      Delete
                    </button>
                  )}
                </div>
              </div>

              {(item.field_of_study || item.gpa != null || item.start_date) && (
                <div className="flex items-center gap-3 text-2xs text-muted font-mono">
                  {item.field_of_study && <span>{item.field_of_study}</span>}
                  {item.gpa != null && <span>GPA {item.gpa}</span>}
                  {dateRange(item) && <span>{dateRange(item)}</span>}
                  {item.is_current && <span className="tag">Current</span>}
                </div>
              )}

              {item.achievements && (
                <p className="text-xs text-ink/70 leading-relaxed">{item.achievements}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !showForm && items.length === 0 && (
        <p className="text-xs text-muted">No education entries yet. Add one to get started.</p>
      )}
    </div>
  )
}
