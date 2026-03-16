import { useEffect, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'

// When the user enables AI, we auto-configure these services (matches ConsentSetup behaviour).
const AI_SERVICES_PAYLOAD = {
  Gemini: { allowed: true },
  llm:    { allowed: true, model_preferences: ['Gemini 2.5 Flash (Google)'] },
}

const AI_FEATURES_DESCRIPTION =
  'AI features include automated bullet points, project descriptions, and skill recommendations. Requires API keys.'

function StatusBadge({ active }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-2xs font-semibold ${
        active
          ? 'bg-success/10 text-success'
          : 'bg-border text-muted'
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-success' : 'bg-muted'}`}
      />
      {active ? 'Enabled' : 'Disabled'}
    </span>
  )
}

function SectionCard({ title, children }) {
  return (
    <div className="card space-y-4 p-5">
      <h2 className="text-sm font-bold">{title}</h2>
      {children}
    </div>
  )
}

export default function ConsentsPage() {
  const { apiOk } = useApp()

  const [consent, setConsent] = useState(null)        // null = not yet loaded
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(false)

  // edit form state
  const [showForm, setShowForm] = useState(false)
  const [useExternal, setUseExternal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  // ── Load latest consent ────────────────────────────────────────────────

  useEffect(() => {
    if (!apiOk) return
    let cancelled = false

    async function load() {
      setLoading(true)
      setLoadError('')
      try {
        const data = await window.api.getLatestConsent()
        if (!cancelled) setConsent(data)
      } catch (err) {
        if (!cancelled) setLoadError(err?.message || 'Failed to load consent settings.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [apiOk])

  // ── Derived flags from loaded consent ─────────────────────────────────

  const consentGiven      = consent?.consent_given ?? false
  const aiEnabled         = consent?.use_external_services ?? false
  const externalServices  = consent?.external_services ?? {}
  const geminiEnabled     = externalServices?.Gemini?.allowed === true
  const llmEnabled        = externalServices?.llm?.allowed === true
  const llmModels         = externalServices?.llm?.model_preferences ?? []

  // ── Open edit form, pre-populate from current consent ─────────────────

  function openEdit() {
    setUseExternal(aiEnabled)
    setSaveError('')
    setSaveSuccess(false)
    setShowForm(true)
  }

  function cancelEdit() {
    setShowForm(false)
    setSaveError('')
    setSaveSuccess(false)
  }

  // ── Submit updated consent ─────────────────────────────────────────────

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setSaveError('')
    setSaveSuccess(false)

    try {
      const updated = await window.api.giveConsent({
        consent_given:           true,
        use_external_services:   useExternal,
        external_services:       useExternal ? AI_SERVICES_PAYLOAD : {},
        default_ignore_patterns: consent?.default_ignore_patterns ?? [],
      })
      setConsent(updated)
      setSaveSuccess(true)
      setShowForm(false)
    } catch (err) {
      setSaveError(err?.message || 'Failed to save consent settings.')
    } finally {
      setSaving(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Consents"
        description="Review and update your data-access and AI service permissions."
        action={
          !showForm && consent !== null && (
            <button
              type="button"
              className="btn-primary text-xs"
              onClick={openEdit}
            >
              Edit
            </button>
          )
        }
      />

      <InlineError message={loadError} />

      {loading && <p className="text-xs text-muted">Loading…</p>}

      {!loading && !loadError && consent === null && (
        <p className="text-xs text-muted">No consent record found.</p>
      )}

      {/* ── Current consent summary ── */}
      {!loading && !loadError && consent !== null && !showForm && (
        <div className="space-y-4">
          {/* File access card */}
          <SectionCard title="File Access">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm text-muted">
                Zip2Job can access and analyze files in your selected directories, extract metadata,
                generate summaries, and store them locally.
              </p>
              <StatusBadge active={consentGiven} />
            </div>
            {consentGiven && (
              <ul className="mt-1 space-y-1">
                {[
                  'Access and analyze files in your selected directories',
                  'Extract metadata and generate summaries',
                  'Store summaries locally and optionally share with external services',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-muted">
                    <span className="mt-0.5 text-accent">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>

          {/* AI / external services card */}
          <SectionCard title="AI Features">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm text-muted">{AI_FEATURES_DESCRIPTION}</p>
              <StatusBadge active={aiEnabled} />
            </div>

            {aiEnabled && (
              <div className="mt-2 space-y-2 border-t border-border pt-3">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted">
                  Active services
                </p>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2">
                    <span className="text-xs font-semibold">Gemini</span>
                    <StatusBadge active={geminiEnabled} />
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2">
                    <span className="text-xs font-semibold">LLM</span>
                    <StatusBadge active={llmEnabled} />
                  </div>
                </div>
                {llmModels.length > 0 && (
                  <p className="font-mono text-2xs text-muted">
                    Model preferences: {llmModels.join(', ')}
                  </p>
                )}
              </div>
            )}
          </SectionCard>

          {saveSuccess && (
            <p className="font-mono text-xs text-green-400">✓ Consent settings updated.</p>
          )}
        </div>
      )}

      {/* ── Edit form ── */}
      {showForm && (
        <form onSubmit={handleSave} className="card space-y-5 p-5">
          <h2 className="text-sm font-bold">Update Consent Settings</h2>

          {/* File access is always granted (matches wizard behaviour) */}
          <div className="rounded-lg border border-border bg-surface px-4 py-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">File Access</div>
                <div className="text-xs text-muted">
                  Required for the app to function. Always enabled.
                </div>
              </div>
              <StatusBadge active />
            </div>
          </div>

          {/* AI toggle */}
          <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 hover:border-accent transition-colors">
            <input
              type="checkbox"
              checked={useExternal}
              onChange={(e) => setUseExternal(e.target.checked)}
              className="h-4 w-4 accent-accent"
              data-testid="consents-use-external"
            />
            <div>
              <div className="text-sm font-semibold">Enable AI features</div>
              <div className="text-xs text-muted">
                {AI_FEATURES_DESCRIPTION}
              </div>
            </div>
          </label>

          <InlineError message={saveError} />

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="btn-primary text-xs disabled:cursor-not-allowed disabled:opacity-40"
              data-testid="consents-save"
            >
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
            <button
              type="button"
              onClick={cancelEdit}
              className="rounded-lg border border-border bg-surface px-4 py-2 text-xs font-semibold text-muted hover:text-ink transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
