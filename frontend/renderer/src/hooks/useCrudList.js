import { useEffect, useState } from 'react'
import { useApp } from '../app/context/AppContext'

export default function useCrudList({
  emptyForm,
  api,
  itemToForm,
  validate,
  buildPayload,
}) {
  const { user, apiOk } = useApp()

  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyForm)
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
        const data = await api.list(user.username)
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
  }, [apiOk, user?.username, api])

  function defaultItemToForm(item) {
    const result = {}
    for (const key of Object.keys(emptyForm)) {
      const value = item[key]
      result[key] = value != null ? (typeof emptyForm[key] === 'string' ? String(value) : value) : emptyForm[key]
    }
    return result
  }

  const toForm = itemToForm ?? defaultItemToForm

  function openCreate() {
    setForm(emptyForm)
    setEditingId(null)
    setFormError('')
    setShowForm(true)
  }

  function openEdit(item) {
    setForm(toForm(item))
    setEditingId(item.id)
    setFormError('')
    setShowForm(true)
  }

  function cancelForm() {
    setShowForm(false)
    setEditingId(null)
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
      if (editingId) {
        const updated = await api.update(user.username, editingId, payload)
        setItems((current) => current.map((item) => (item.id === editingId ? updated : item)))
      } else {
        const created = await api.create(user.username, payload)
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
      await api.remove(user.username, id)
      setItems((current) => current.filter((item) => item.id !== id))
      setConfirmId(null)
    } catch (error) {
      setError(error?.message || 'Delete failed')
    }
  }

  return {
    user,
    items,
    error,
    loading,
    showForm,
    editingId,
    form,
    formError,
    saving,
    confirmId,
    setConfirmId,
    openCreate,
    openEdit,
    cancelForm,
    setField,
    handleSave,
    handleDelete,
  }
}
