import { useState, useEffect } from 'react'
import { useApp } from '../App'

const EMPTY_FORM = {
  company: '', title: '', location: '', description: '',
  start_date: '', end_date: '', is_current: false,
}

export default function ExperiencePage() {
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
        const data = await window.api.getWorkExperiences(user.username)
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
      company: item.company ?? '',
      title: item.title ?? '',
      location: item.location ?? '',
      description: item.description ?? '',
      start_date: item.start_date ?? '',
      end_date: item.end_date ?? '',
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
    if (!form.company.trim() || !form.title.trim()) {
      setFormError('Company and title are required.')
      return
    }
    setSaving(true)
    setFormError('')

    const payload = {
      company: form.company.trim(),
      title: form.title.trim(),
      location: form.location.trim() || null,
      description: form.description.trim() || null,
      start_date: form.start_date || null,
      end_date: form.is_current ? null : (form.end_date || null),
      is_current: form.is_current,
    }

    try {
      if (editingId) {
        const updated = await window.api.updateWorkExperience(user.username, editingId, payload)
        setItems(prev => prev.map(it => it.id === editingId ? updated : it))
      } else {
        const created = await window.api.createWorkExperience(user.username, payload)
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
      await window.api.deleteWorkExperience(user.username, id)
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
          <h1 className="text-2xl font-extrabold tracking-tight">Experience</h1>
          <p className="text-sm text-muted mt-1">Manage your work experience entries.</p>
        </div>
        {!showForm && (
          <button className="btn-primary text-xs" onClick={openCreate}>
            + Add Experience
          </button>
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {/* Create / Edit form */}
      {showForm && (
        <form onSubmit={handleSave} className="card space-y-4 p-5">
          <h2 className="text-sm font-bold">
            {editingId ? 'Edit Experience' : 'New Experience'}
          </h2>

          {formError && <p className="text-xs text-red-400">{formError}</p>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              className="input" placeholder="Company *" required
              value={form.company}
              onChange={e => setField('company', e.target.value)}
            />
            <input
              className="input" placeholder="Title *" required
              value={form.title}
              onChange={e => setField('title', e.target.value)}
            />
            <input
              className="input" placeholder="Location"
              value={form.location}
              onChange={e => setField('location', e.target.value)}
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
            I currently work here
          </label>

          <textarea
            className="input w-full" rows={3} placeholder="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
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
                  <h3 className="text-sm font-bold truncate">{item.title}</h3>
                  <p className="text-xs text-muted truncate">{item.company}</p>
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

              {(item.location || item.start_date) && (
                <div className="flex items-center gap-3 text-2xs text-muted font-mono">
                  {item.location && <span>{item.location}</span>}
                  {dateRange(item) && <span>{dateRange(item)}</span>}
                  {item.is_current && <span className="tag">Current</span>}
                </div>
              )}

              {item.description && (
                <p className="text-xs text-ink/70 leading-relaxed">{item.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !showForm && items.length === 0 && (
        <p className="text-xs text-muted">No experience entries yet. Add one to get started.</p>
      )}
    </div>
  )
}
