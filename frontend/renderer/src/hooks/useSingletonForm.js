import { useEffect, useState } from 'react'
import { useApp } from '../app/context/AppContext'

/**
 * Hook for singleton-form pages (e.g. user profile, settings).
 *
 * Unlike useCrudList which manages a list of items, this hook manages
 * a single resource that is loaded, created, or updated per user.
 */
export default function useSingletonForm({
  emptyForm,
  api,
  validate,
  buildPayload,
  isNotFound,
}) {
  const { user, apiOk } = useApp()

  const [data, setData] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [exists, setExists] = useState(false)
  const [showForm, setShowForm] = useState(false)

  const notFoundCheck = isNotFound ?? ((err) => {
    const msg = err?.message || ''
    return msg.includes('404') || msg.toLowerCase().includes('not found')
  })

  function dataToForm(raw) {
    const loaded = {}
    for (const key of Object.keys(emptyForm)) {
      loaded[key] = raw[key] != null ? String(raw[key]) : ''
    }
    return loaded
  }

  useEffect(() => {
    if (!apiOk || !user?.username) return

    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const raw = await api.get(user.username)
        if (!cancelled && raw) {
          setData(raw)
          setForm(dataToForm(raw))
          setExists(true)
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          if (notFoundCheck(err)) {
            setError('')
          } else {
            setError(err?.message || 'Failed to load')
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [apiOk, user?.username, api])

  function openCreate() {
    setForm(emptyForm)
    setFormError('')
    setShowForm(true)
  }

  function openEdit() {
    if (data) setForm(dataToForm(data))
    setFormError('')
    setShowForm(true)
  }

  function cancelForm() {
    setShowForm(false)
    setFormError('')
  }

  function setField(key, value) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSave(event) {
    event.preventDefault()

    if (validate) {
      const msg = validate(form)
      if (msg) {
        setFormError(msg)
        return
      }
    }

    setSaving(true)
    setFormError('')

    const payload = buildPayload ? buildPayload(form) : form

    try {
      let result
      if (exists) {
        result = await api.update(user.username, payload)
      } else {
        result = await api.create(user.username, payload)
        setExists(true)
      }
      if (result) {
        setData(result)
        setForm(dataToForm(result))
      }
      setError('')
      setFormError('')
      setShowForm(false)
    } catch (err) {
      setFormError(err?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return {
    data,
    form,
    error,
    formError,
    loading,
    saving,
    exists,
    showForm,
    openCreate,
    openEdit,
    cancelForm,
    setField,
    handleSave,
  }
}
