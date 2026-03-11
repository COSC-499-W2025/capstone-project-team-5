import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { formatDateRange } from '../../lib/dates'

const EMPTY_FORM = {
  company: '',
  title: '',
  location: '',
  description: '',
  start_date: '',
  end_date: '',
  is_current: false,
}

export default function ExperiencePage() {
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
        const data = await window.api.getWorkExperiences(user.username)
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

  async function handleSave(event) {
    event.preventDefault()
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
      end_date: form.is_current ? null : form.end_date || null,
      is_current: form.is_current,
    }

    try {
      if (editingId) {
        const updated = await window.api.updateWorkExperience(user.username, editingId, payload)
        setItems((current) => current.map((item) => (item.id === editingId ? updated : item)))
      } else {
        const created = await window.api.createWorkExperience(user.username, payload)
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
      await window.api.deleteWorkExperience(user.username, id)
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
                  <h3 className="truncate text-sm font-bold">{item.title}</h3>
                  <p className="truncate text-xs text-muted">{item.company}</p>
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
