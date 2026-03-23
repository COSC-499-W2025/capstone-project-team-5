import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

export default function PortfolioPage() {
  const { user, apiOk } = useApp()
  const [view, setView] = useState('list')
  const [portfolios, setPortfolios] = useState([])
  const [selectedPortfolio, setSelectedPortfolio] = useState(null)
  const [items, setItems] = useState([])
  const [projects, setProjects] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState('')
  const [addProjectId, setAddProjectId] = useState('')
  const [addLoading, setAddLoading] = useState(false)
  const [addError, setAddError] = useState('')
  const [pendingDelete, setPendingDelete] = useState(null)

  useEffect(() => {
    if (!apiOk || !user?.username) {
      return
    }

    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')

      try {
        const data = await window.api.getPortfolioByUser(user.username)
        if (!cancelled) {
          setPortfolios(data ?? [])
        }
      } catch (error) {
        if (!cancelled) {
          setError(error?.message || 'Failed to load portfolios.')
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
  }, [apiOk, user])

  useEffect(() => {
    if (view !== 'detail' || !selectedPortfolio) {
      return
    }

    let cancelled = false

    async function loadDetail() {
      setLoading(true)
      setError('')
      setItems([])

      try {
        const [itemData, projectData] = await Promise.all([
          window.api.getPortfolio(selectedPortfolio.id),
          window.api.getProjects(),
        ])

        if (!cancelled) {
          setItems(itemData ?? [])
          setProjects(getProjectItems(projectData))
        }
      } catch (error) {
        if (!cancelled) {
          setError(error?.message || 'Failed to load portfolio.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadDetail()

    return () => {
      cancelled = true
    }
  }, [view, selectedPortfolio])

  async function handleCreatePortfolio(event) {
    event.preventDefault()
    if (!newName.trim()) {
      return
    }

    setFormLoading(true)
    setFormError('')

    try {
      const created = await window.api.createPortfolio({
        username: user.username,
        name: newName.trim(),
      })
      setPortfolios((current) => [created, ...current])
      setNewName('')
      setShowForm(false)
    } catch (error) {
      setFormError(error?.message || 'Failed to create portfolio.')
    } finally {
      setFormLoading(false)
    }
  }

  async function handleDelete(portfolioId) {
    try {
      await window.api.deletePortfolio(portfolioId)
      setPortfolios((current) => current.filter((portfolio) => portfolio.id !== portfolioId))
    } catch (error) {
      setError(error?.message || 'Failed to delete portfolio.')
    } finally {
      setPendingDelete(null)
    }
  }

  async function handleAddProject(event) {
    event.preventDefault()
    if (!addProjectId) {
      return
    }

    setAddLoading(true)
    setAddError('')

    try {
      const item = await window.api.addPortfolioItem(selectedPortfolio.id, {
        username: user.username,
        project_id: parseInt(addProjectId, 10),
      })

      setItems((current) => {
        const exists = current.some((existingItem) => existingItem.id === item.id)
        return exists ? current : [item, ...current]
      })
      setAddProjectId('')
    } catch (error) {
      setAddError(error?.message || 'Failed to add project.')
    } finally {
      setAddLoading(false)
    }
  }

  function openPortfolio(portfolio) {
    setSelectedPortfolio(portfolio)
    setAddProjectId('')
    setAddError('')
    setError('')
    setView('detail')
  }

  function goBack() {
    setView('list')
    setSelectedPortfolio(null)
    setItems([])
    setError('')
  }

  if (view === 'detail' && selectedPortfolio) {
    const addableProjects = projects.filter(
      (project) => !items.some((item) => item.project_id === project.id)
    )

    return (
      <div className="animate-fade-up space-y-6">
        <div className="flex items-center gap-3">
          <button type="button" onClick={goBack} className="btn-ghost px-3 py-1.5 text-xs">
            ← Back
          </button>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight">{selectedPortfolio.name}</h1>
            <p className="mt-0.5 text-sm text-muted">
              {items.length} item{items.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        <InlineError message={error} />

        {addableProjects.length > 0 && (
          <form onSubmit={handleAddProject} className="flex items-center gap-2">
            <select
              value={addProjectId}
              onChange={(event) => setAddProjectId(event.target.value)}
              className="input max-w-xs flex-1 text-sm"
            >
              <option value="">Add a project…</option>
              {addableProjects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={!addProjectId || addLoading}
              className="btn-primary px-4 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40"
            >
              {addLoading ? 'Adding…' : 'Add'}
            </button>
          </form>
        )}
        <InlineError message={addError} />

        {loading && <p className="text-xs text-muted">Loading…</p>}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const preview = item.markdown?.slice(0, 150)
            const truncated = (item.markdown?.length ?? 0) > 150

            return (
              <div key={item.id} className="card space-y-2">
                <div className="text-sm font-bold">{item.title}</div>
                {preview && (
                  <p className="line-clamp-3 font-mono text-2xs leading-relaxed text-muted">
                    {preview}
                    {truncated ? '…' : ''}
                  </p>
                )}
                <div className="border-t border-border pt-1 font-mono text-2xs text-muted">
                  project #{item.project_id}
                </div>
              </div>
            )
          })}
        </div>

        {!loading && items.length === 0 && (
          <EmptyState message="No items yet. Add a project above." />
        )}
      </div>
    )
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Portfolio"
        description="Curate and share your best work."
        action={(
          <button
            type="button"
            onClick={() => {
              setShowForm((current) => !current)
              setFormError('')
            }}
            className="btn-primary px-4 py-2 text-xs"
          >
            {showForm ? 'Cancel' : '+ New Portfolio'}
          </button>
        )}
      />

      {showForm && (
        <form onSubmit={handleCreatePortfolio} className="flex items-center gap-2">
          <input
            type="text"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="Portfolio name…"
            required
            autoFocus
            className="input max-w-xs flex-1 text-sm"
          />
          <button
            type="submit"
            disabled={!newName.trim() || formLoading}
            className="btn-primary px-4 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40"
          >
            {formLoading ? 'Creating…' : 'Create'}
          </button>
          <InlineError message={formError} />
        </form>
      )}

      <InlineError message={error} />
      {loading && <p className="text-xs text-muted">Loading…</p>}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {portfolios.map((portfolio) => (
          <div key={portfolio.id} className="card space-y-3">
            <div className="text-sm font-bold">{portfolio.name}</div>
            <div className="font-mono text-2xs text-muted">
              {new Date(portfolio.created_at).toLocaleDateString()}
            </div>
            <div className="flex items-center gap-2 border-t border-border pt-1">
              <button
                type="button"
                onClick={() => openPortfolio(portfolio)}
                className="btn-ghost px-3 py-1 text-xs"
              >
                View →
              </button>
              {pendingDelete === portfolio.id ? (
                <>
                  <span className="text-xs text-muted">Delete?</span>
                  <button
                    type="button"
                    onClick={() => handleDelete(portfolio.id)}
                    className="text-xs font-semibold text-red-400 hover:text-red-300"
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    onClick={() => setPendingDelete(null)}
                    className="text-xs text-muted hover:text-ink"
                  >
                    No
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setPendingDelete(portfolio.id)}
                  className="ml-auto text-xs text-muted hover:text-red-400"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {!loading && portfolios.length === 0 && (
        <EmptyState message="No portfolios yet. Create one to get started." />
      )}
    </div>
  )
}
