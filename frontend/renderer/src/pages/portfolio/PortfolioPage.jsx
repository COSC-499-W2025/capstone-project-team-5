import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import { getProjectItems } from '../../lib/projects'

const API_BASE = 'http://localhost:8000'

const TEMPLATES = [
  { value: 'grid', label: 'Grid' },
  { value: 'showcase', label: 'Showcase' },
  { value: 'timeline', label: 'Timeline' },
]

function stripMd(text) {
  return (text || '')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/`[^`]*`/g, '')
    .replace(/[*_~]/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\n+/g, ' ')
    .trim()
}

const COLOR_THEMES = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'slate', label: 'Slate' },
]

function TextBlockCard({ item, onSave, onRemove }) {
  const [title, setTitle] = useState(item.title === 'Text block' ? '' : item.title)
  const [markdown, setMarkdown] = useState(item.markdown)
  const [editing, setEditing] = useState(!item.markdown)

  function handleBlur() {
    setEditing(false)
    onSave({ title: title || 'Text block', markdown })
  }

  return (
    <div className="card group relative space-y-2 border-dashed border-accent/20">
      <div className="flex items-start justify-between gap-2">
        <span className="text-2xs font-mono text-accent/60 uppercase tracking-widest">Text</span>
        <button
          type="button"
          onClick={onRemove}
          className="text-muted opacity-0 group-hover:opacity-100 hover:text-red-400 text-sm leading-none transition-opacity"
        >
          ×
        </button>
      </div>
      {editing ? (
        <>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Heading (optional)"
            className="input w-full text-sm font-bold"
            autoFocus
          />
          <textarea
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            onBlur={handleBlur}
            placeholder="Write markdown here…"
            rows={4}
            className="input w-full resize-none text-xs"
          />
        </>
      ) : (
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="w-full text-left"
        >
          {title && <div className="text-sm font-bold">{title}</div>}
          {markdown
            ? <p className="line-clamp-3 text-xs text-muted mt-1">{stripMd(markdown)}</p>
            : <p className="text-xs text-muted/50 italic">Click to edit…</p>}
        </button>
      )}
    </div>
  )
}

function CustomSelect({ label, value, options, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const current = options.find((o) => o.value === value)

  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2 py-1 text-xs text-ink hover:border-accent/40"
      >
        <span className="text-2xs text-muted">{label}</span>
        <span>{current?.label}</span>
        <span className="text-2xs text-muted">▾</span>
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 min-w-full overflow-hidden rounded-lg border border-border bg-surface shadow-lg">
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => { onChange(o.value); setOpen(false) }}
              className={`block w-full px-3 py-1.5 text-left text-xs transition-colors hover:bg-white/5 ${o.value === value ? 'text-accent font-medium' : 'text-ink'}`}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ShareModal({ portfolio, onClose, onShare, onRevoke }) {
  const [shareToken, setShareToken] = useState(portfolio.share_token ?? null)
  const [loading, setLoading] = useState(false)
  const [revoking, setRevoking] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  const shareUrl = shareToken ? `${API_BASE}/api/portfolio/shared/${shareToken}` : null

  async function handleGenerate() {
    setLoading(true)
    setError('')
    try {
      const result = await window.api.sharePortfolio(portfolio.id)
      setShareToken(result.share_token)
      onShare?.(result.share_token)
    } catch (err) {
      setError(err?.message || 'Failed to generate share link.')
    } finally {
      setLoading(false)
    }
  }

  async function handleCopy() {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Failed to copy to clipboard.')
    }
  }

  async function handleRevoke() {
    setRevoking(true)
    setError('')
    try {
      await window.api.revokePortfolioShare(portfolio.id)
      setShareToken(null)
      onRevoke?.()
    } catch (err) {
      setError(err?.message || 'Failed to revoke link.')
    } finally {
      setRevoking(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="card w-full max-w-md space-y-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold">Share "{portfolio.name}"</h2>
          <button type="button" onClick={onClose} className="text-muted hover:text-ink text-lg leading-none">
            ×
          </button>
        </div>

        {shareToken ? (
          <div className="space-y-3">
            <p className="text-xs text-muted">Anyone with this link can view this portfolio.</p>
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={shareUrl}
                className="input flex-1 text-xs font-mono"
                onFocus={(e) => e.target.select()}
              />
              <button
                type="button"
                onClick={handleCopy}
                className="btn-primary px-3 py-2 text-xs"
              >
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <button
              type="button"
              onClick={handleRevoke}
              disabled={revoking}
              className="text-xs text-red-400 hover:text-red-300 disabled:opacity-40"
            >
              {revoking ? 'Revoking…' : 'Revoke link'}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted">
              Generate a shareable link for this portfolio. Anyone with the link can view it.
            </p>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              className="btn-primary px-4 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? 'Generating…' : 'Generate Link'}
            </button>
          </div>
        )}

        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    </div>
  )
}

export default function PortfolioPage() {
  const { user, apiOk } = useApp()
  const [view, setView] = useState('list')
  const [portfolios, setPortfolios] = useState([])
  const [selectedPortfolio, setSelectedPortfolio] = useState(null)
  const [items, setItems] = useState([])
  const [dragIdx, setDragIdx] = useState(null)
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
  const [shareModalPortfolio, setShareModalPortfolio] = useState(null)

  // Description inline editing
  const [editingDesc, setEditingDesc] = useState(false)
  const [descValue, setDescValue] = useState('')
  const descRef = useRef(null)

  useEffect(() => {
    if (!apiOk || !user?.username) return

    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await window.api.getPortfolioByUser(user.username)
        if (!cancelled) setPortfolios(data ?? [])
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load portfolios.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [apiOk, user])

  useEffect(() => {
    if (view !== 'detail' || !selectedPortfolio) return

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
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load portfolio.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadDetail()
    return () => { cancelled = true }
  }, [view, selectedPortfolio])

  async function handleCreatePortfolio(event) {
    event.preventDefault()
    if (!newName.trim()) return
    setFormLoading(true)
    setFormError('')
    try {
      const created = await window.api.createPortfolio({ username: user.username, name: newName.trim() })
      setPortfolios((current) => [created, ...current])
      setNewName('')
      setShowForm(false)
    } catch (err) {
      setFormError(err?.message || 'Failed to create portfolio.')
    } finally {
      setFormLoading(false)
    }
  }

  async function handleDelete(portfolioId) {
    try {
      await window.api.deletePortfolio(portfolioId)
      setPortfolios((current) => current.filter((p) => p.id !== portfolioId))
    } catch (err) {
      setError(err?.message || 'Failed to delete portfolio.')
    } finally {
      setPendingDelete(null)
    }
  }

  async function handleAddProject(event) {
    event.preventDefault()
    if (!addProjectId) return
    setAddLoading(true)
    setAddError('')
    try {
      const item = await window.api.addPortfolioItem(selectedPortfolio.id, {
        username: user.username,
        project_id: parseInt(addProjectId, 10),
      })
      setItems((current) => {
        const exists = current.some((i) => i.id === item.id)
        return exists ? current : [item, ...current]
      })
      setAddProjectId('')
    } catch (err) {
      setAddError(err?.message || 'Failed to add project.')
    } finally {
      setAddLoading(false)
    }
  }

  function syncPortfolioList(id, patch) {
    setPortfolios((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)))
  }

  async function handleTemplateChange(newTemplate) {
    try {
      await window.api.updatePortfolio(selectedPortfolio.id, { template: newTemplate })
      setSelectedPortfolio((prev) => ({ ...prev, template: newTemplate }))
      syncPortfolioList(selectedPortfolio.id, { template: newTemplate })
    } catch {
      // silently ignore — not critical
    }
  }

  async function handleThemeChange(newTheme) {
    try {
      await window.api.updatePortfolio(selectedPortfolio.id, { color_theme: newTheme })
      setSelectedPortfolio((prev) => ({ ...prev, color_theme: newTheme }))
      syncPortfolioList(selectedPortfolio.id, { color_theme: newTheme })
    } catch {
      // silently ignore — not critical
    }
  }

  function handleDragStart(e, idx) {
    setDragIdx(idx)
    e.dataTransfer.effectAllowed = 'move'
  }

  function handleDragOver(e, idx) {
    e.preventDefault()
    if (idx === dragIdx || dragIdx === null) return
    const next = [...items]
    const [dragged] = next.splice(dragIdx, 1)
    next.splice(idx, 0, dragged)
    setItems(next)
    setDragIdx(idx)
  }

  function handleDragEnd() {
    setDragIdx(null)
    window.api.reorderPortfolioItems(selectedPortfolio.id, items.map((i) => i.id)).catch(() => {})
  }

  async function handleAddTextBlock() {
    try {
      const block = await window.api.addTextBlock(selectedPortfolio.id, { title: '', markdown: '' })
      setItems((prev) => [...prev, block])
    } catch (err) {
      setError(err?.message || 'Failed to add text block.')
    }
  }

  async function handleUpdateItem(itemId, patch) {
    try {
      const updated = await window.api.updatePortfolioItem(selectedPortfolio.id, itemId, patch)
      setItems((prev) => prev.map((i) => (i.id === itemId ? updated : i)))
    } catch (err) {
      setError(err?.message || 'Failed to save.')
    }
  }

  async function handleRemoveItem(itemId) {
    try {
      await window.api.removePortfolioItem(selectedPortfolio.id, itemId)
      setItems((prev) => prev.filter((i) => i.id !== itemId))
    } catch (err) {
      setError(err?.message || 'Failed to remove item.')
    }
  }

  async function handleDescSave() {
    setEditingDesc(false)
    if (descValue === (selectedPortfolio.description || '')) return
    try {
      await window.api.updatePortfolio(selectedPortfolio.id, { description: descValue })
      setSelectedPortfolio((prev) => ({ ...prev, description: descValue }))
      syncPortfolioList(selectedPortfolio.id, { description: descValue })
    } catch {
      // silently ignore
    }
  }

  async function openPortfolio(portfolio) {
    setSelectedPortfolio(portfolio)
    setDescValue(portfolio.description || '')
    setEditingDesc(false)
    setAddProjectId('')
    setAddError('')
    setError('')
    setView('detail')
    // Fetch fresh metadata in case it changed since the list was loaded
    try {
      const fresh = await window.api.getPortfolioInfo(portfolio.id)
      setSelectedPortfolio(fresh)
      setDescValue(fresh.description || '')
    } catch {
      // Fall back to list data — not critical
    }
  }

  function goBack() {
    setView('list')
    setSelectedPortfolio(null)
    setItems([])
    setError('')
    setEditingDesc(false)
  }

  // ── Portfolio Dashboard (detail view) ─────────────────────────────────────
  if (view === 'detail' && selectedPortfolio) {
    const addableProjects = projects.filter(
      (project) => !items.some((item) => item.project_id === project.id)
    )
    const shareUrl = selectedPortfolio.share_token
      ? `${API_BASE}/api/portfolio/shared/${selectedPortfolio.share_token}`
      : null
    const currentTemplate = selectedPortfolio.template || 'grid'

    return (
      <div className="animate-fade-up space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <button type="button" onClick={goBack} className="btn-ghost px-3 py-1.5 text-xs">
              ← Back
            </button>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">{selectedPortfolio.name}</h1>
              <p className="mt-0.5 flex items-center gap-2 text-sm text-muted">
                {items.length} item{items.length !== 1 ? 's' : ''}
                <span className={`flex items-center gap-1 font-mono text-2xs ${selectedPortfolio.share_token ? 'text-green-400' : 'text-muted'}`}>
                  <span className={`inline-block h-1.5 w-1.5 rounded-full ${selectedPortfolio.share_token ? 'bg-green-400' : 'bg-neutral-600'}`} />
                  {selectedPortfolio.share_token ? 'Published' : 'Unpublished'}
                </span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <CustomSelect
              label="Layout"
              value={currentTemplate}
              options={TEMPLATES}
              onChange={handleTemplateChange}
            />
            <CustomSelect
              label="Theme"
              value={selectedPortfolio.color_theme || 'dark'}
              options={COLOR_THEMES}
              onChange={handleThemeChange}
            />
            <button
              type="button"
              disabled={!shareUrl}
              onClick={() => shareUrl && window.open(shareUrl, '_blank')}
              title={shareUrl ? 'Open shared page in browser' : 'Publish first to preview'}
              className="btn-ghost px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-30"
            >
              Preview ↗
            </button>
            <button
              type="button"
              onClick={() => setShareModalPortfolio(selectedPortfolio)}
              className="btn-ghost px-3 py-1.5 text-xs"
            >
              Share ↗
            </button>
          </div>
        </div>

        {/* Description editor */}
        <div className="rounded-lg border border-border bg-surface px-4 py-3">
          {editingDesc ? (
            <textarea
              ref={descRef}
              value={descValue}
              onChange={(e) => setDescValue(e.target.value)}
              onBlur={handleDescSave}
              rows={3}
              autoFocus
              placeholder="Describe this portfolio… (shown on the shared page)"
              className="input w-full resize-none text-sm"
            />
          ) : (
            <button
              type="button"
              onClick={() => { setEditingDesc(true); setTimeout(() => descRef.current?.focus(), 0) }}
              className="w-full text-left text-sm"
            >
              {selectedPortfolio.description
                ? <span className="text-ink">{selectedPortfolio.description}</span>
                : <span className="text-muted">Add a description for your portfolio… (click to edit)</span>}
            </button>
          )}
        </div>

        {/* Shared link banner */}
        {shareUrl && (
          <div className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3">
            <span className="text-xs text-muted">Share link:</span>
            <span className="flex-1 truncate font-mono text-2xs text-ink">{shareUrl}</span>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(shareUrl)}
              className="text-xs text-muted hover:text-ink"
            >
              Copy
            </button>
          </div>
        )}

        <InlineError message={error} />

        {/* Add project */}
        {addableProjects.length > 0 && (
          <form onSubmit={handleAddProject} className="flex items-center gap-2">
            <select
              value={addProjectId}
              onChange={(e) => setAddProjectId(e.target.value)}
              className="input max-w-xs flex-1 text-sm"
            >
              <option value="">Add a project…</option>
              {addableProjects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
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


        {/* Items list — draggable */}
        <div className="flex flex-col gap-2">
          {items.map((item, idx) => {
            const dragProps = {
              draggable: true,
              onDragStart: (e) => handleDragStart(e, idx),
              onDragOver:  (e) => handleDragOver(e, idx),
              onDragEnd:   handleDragEnd,
            }
            const handle = (
              <span
                className="mt-3 cursor-grab select-none text-lg text-muted opacity-0 transition-opacity group-hover:opacity-100 active:cursor-grabbing"
                title="Drag to reorder"
              >⠿</span>
            )

            if (item.is_text_block) {
              return (
                <div key={item.id} {...dragProps} className="group flex items-start gap-2">
                  {handle}
                  <div className="flex-1">
                    <TextBlockCard
                      item={item}
                      onSave={(patch) => handleUpdateItem(item.id, patch)}
                      onRemove={() => handleRemoveItem(item.id)}
                    />
                  </div>
                </div>
              )
            }

            const clean = stripMd(item.markdown)
            const preview = clean.slice(0, 160)
            const truncated = clean.length > 160
            return (
              <div key={item.id} {...dragProps} className="group flex items-start gap-2">
                {handle}
                <div className="card flex-1 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm font-bold">{item.title}</div>
                    <div className="flex items-center gap-1.5">
                      {item.is_user_edited && (
                        <span className="shrink-0 rounded-full bg-blue-500/10 px-1.5 py-0.5 text-2xs text-blue-400">
                          edited
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(item.id)}
                        title="Remove from portfolio"
                        className="shrink-0 text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400 text-sm leading-none"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  {preview && (
                    <p className="line-clamp-2 text-xs leading-relaxed text-muted">
                      {preview}{truncated ? '…' : ''}
                    </p>
                  )}
                  <div className="border-t border-border pt-1 font-mono text-2xs text-muted">
                    project #{item.project_id}
                  </div>
                </div>
              </div>
            )
          })}
          <button
            type="button"
            onClick={handleAddTextBlock}
            className="card ml-6 flex min-h-[52px] items-center justify-center gap-2 border-dashed text-xs text-muted transition-colors hover:border-accent/40 hover:text-ink"
          >
            <span className="text-base leading-none">+</span> Add text block
          </button>
        </div>

        {!loading && items.length === 0 && (
          <EmptyState message="No items yet. Add a project above." />
        )}

        {shareModalPortfolio && (
          <ShareModal
            portfolio={shareModalPortfolio}
            onClose={() => setShareModalPortfolio(null)}
            onShare={(token) => {
              setSelectedPortfolio((prev) => ({ ...prev, share_token: token }))
              syncPortfolioList(shareModalPortfolio.id, { share_token: token })
            }}
            onRevoke={() => {
              setSelectedPortfolio((prev) => ({ ...prev, share_token: null }))
              syncPortfolioList(shareModalPortfolio.id, { share_token: null })
            }}
          />
        )}
      </div>
    )
  }

  // ── Portfolio list view ────────────────────────────────────────────────────
  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Portfolio"
        description="Curate and share your best work."
        action={(
          <button
            type="button"
            onClick={() => { setShowForm((c) => !c); setFormError('') }}
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
            onChange={(e) => setNewName(e.target.value)}
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
          <div
            key={portfolio.id}
            className="card flex cursor-pointer flex-col gap-3 transition-colors hover:border-accent/40"
            onClick={() => openPortfolio(portfolio)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-bold">{portfolio.name}</div>
              {/* Published / unpublished dot */}
              <span className={`mt-0.5 flex items-center gap-1 shrink-0 font-mono text-2xs ${portfolio.share_token ? 'text-green-400' : 'text-muted'}`}>
                <span className={`inline-block h-1.5 w-1.5 rounded-full ${portfolio.share_token ? 'bg-green-400' : 'bg-neutral-600'}`} />
                {portfolio.share_token ? 'Published' : 'Unpublished'}
              </span>
            </div>
            {portfolio.description && (
              <p className="text-xs text-muted line-clamp-2">{portfolio.description}</p>
            )}
            <div className="flex items-center gap-1 font-mono text-2xs text-muted">
              <span>{new Date(portfolio.created_at).toLocaleDateString()}</span>
              <span>·</span>
              <span className="capitalize">{portfolio.template || 'grid'}</span>
            </div>
            <div
              className="flex items-center gap-2 border-t border-border pt-1"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                onClick={() => openPortfolio(portfolio)}
                className="btn-ghost px-3 py-1 text-xs"
              >
                View →
              </button>
              <button
                type="button"
                onClick={() => setShareModalPortfolio(portfolio)}
                className="btn-ghost px-3 py-1 text-xs"
              >
                Share
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

      {shareModalPortfolio && (
        <ShareModal
          portfolio={shareModalPortfolio}
          onClose={() => setShareModalPortfolio(null)}
          onRevoke={() => syncPortfolioList(shareModalPortfolio.id, { share_token: null })}
        />
      )}
    </div>
  )
}
