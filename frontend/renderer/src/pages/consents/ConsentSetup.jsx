import { useEffect, useRef, useState } from 'react'

function getErrorMessage(error, fallbackMessage) {
  let message = error?.message ?? fallbackMessage

  try {
    message = JSON.parse(message).detail ?? message
  } catch {}

  return message
}

// ── Copy sourced from ConsentTool in tui.py / consent_tool.py ──────────────

const FILE_ACCESS_BULLETS = [
  'Access and analyze files in your selected directories',
  'Extract metadata and generate summaries',
  'Store summaries locally and optionally share with external services',
]

const AI_FEATURES_DESCRIPTION =
  'AI features include automated bullet points, project descriptions, and skill recommendations. Requires API keys.'

// ── Component ──────────────────────────────────────────────────────────────

// When the user enables AI, we auto-configure these services (matches TUI behaviour).
const AI_SERVICES_PAYLOAD = {
  Gemini: { allowed: true },
  llm:    { allowed: true, model_preferences: ['Gemini 2.5 Flash (Google)'] },
}

export default function ConsentSetup({ onDone }) {
  const [authMode, setAuthMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [useExternal, setUseExternal] = useState(false)
  // step: 'auth' | 'file-consent' | 'ai-consent' | 'done'
  const [step, setStep] = useState('auth')
  const [statusMsg, setStatusMsg] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const doneTimeoutRef = useRef(null)

  useEffect(() => {
    return () => {
      if (doneTimeoutRef.current) clearTimeout(doneTimeoutRef.current)
    }
  }, [])

  // ── Auth ────────────────────────────────────────────────────────────────

  async function handleAuthSubmit(event) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const authFn = authMode === 'register' ? window.api.register : window.api.login
      const response = await authFn({ username: username.trim(), password })

      window.api.setAuthUsername(response.username)
      window.api.setUsername(response.username)

      if (authMode === 'login') {
        setStatusMsg(`Logged in as ${response.username}.`)

        // Returning users who already gave consent skip the wizard entirely.
        const existingConsent = await window.api.getLatestConsent().catch(() => null)
        if (existingConsent !== null) {
          setStep('done')
          doneTimeoutRef.current = setTimeout(() => onDone(response.username), 800)
          return
        }
      } else {
        setStatusMsg(`Account created. Logged in as ${response.username}.`)
      }

      // First-time user (or login with no prior consent) → file access consent
      setStep('file-consent')
    } catch (err) {
      setError(getErrorMessage(err, 'Something went wrong.'))
    } finally {
      setLoading(false)
    }
  }

  // ── File-access consent → advance to AI consent ─────────────────────────

  function handleFileConsentAgree() {
    setError(null)
    setUseExternal(false)
    setStep('ai-consent')
  }

  // ── AI / external services consent → submit everything ──────────────────

  async function handleAiConsentSubmit(event) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await window.api.giveConsent({
        consent_given: true,
        use_external_services: useExternal,
        external_services: useExternal ? AI_SERVICES_PAYLOAD : {},
        default_ignore_patterns: [],
      })

      setStep('done')
      doneTimeoutRef.current = setTimeout(() => onDone(username.trim()), 800)
    } catch (err) {
      setError(getErrorMessage(err, 'Consent submission failed.'))
    } finally {
      setLoading(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen items-center justify-center bg-bg text-ink">
      <div className="w-[480px] space-y-6">

        {/* ── Brand header ── */}
        <div>
          <div className="text-2xl font-extrabold tracking-tight">
            Zip<span className="text-accent">2</span>Job<span className="ml-2 font-mono text-xs font-normal text-muted uppercase tracking-widest">Analyzer</span>
          </div>
          <p className="mt-1 text-sm text-muted">
            {step === 'auth' && (authMode === 'login' ? 'Welcome back.' : 'Create your account.')}
            {step === 'file-consent' && 'Zip2Job Permission'}
            {step === 'ai-consent' && 'AI Features'}
            {step === 'done' && 'All set.'}
          </p>
        </div>

        {/* ── Status message (mirrors TUI status bar) ── */}
        {statusMsg && step !== 'auth' && (
          <p className="font-mono text-xs text-muted">{statusMsg}</p>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            STEP: auth
        ══════════════════════════════════════════════════════════════════ */}
        {step === 'auth' && (
          <div className="space-y-5">
            {/* Tab toggle — Login / Sign Up */}
            <div className="flex gap-1 rounded-lg border border-border bg-surface p-1">
              {['login', 'register'].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => { setAuthMode(mode); setError(null) }}
                  className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition-colors ${
                    authMode === mode ? 'bg-accent text-bg' : 'text-muted hover:text-ink'
                  }`}
                  data-testid={`auth-tab-${mode}`}
                >
                  {mode === 'login' ? 'Log In' : 'Sign Up'}
                </button>
              ))}
            </div>

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-muted">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. alice"
                  required
                  autoFocus
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm focus:border-accent focus:outline-none"
                  data-testid="auth-username"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-muted">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm focus:border-accent focus:outline-none"
                  data-testid="auth-password"
                />
              </div>

              {error && (
                <p data-testid="consent-error" className="font-mono text-xs text-red-400">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={!username.trim() || !password || loading}
                className="w-full btn-primary disabled:cursor-not-allowed disabled:opacity-40"
                data-testid="auth-submit"
              >
                {loading
                  ? 'Please wait…'
                  : authMode === 'login'
                  ? 'Log In'
                  : 'Create Account'}
              </button>
            </form>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            STEP: file-consent  (mirrors ConsentTool.consent_text)
        ══════════════════════════════════════════════════════════════════ */}
        {step === 'file-consent' && (
          <div className="space-y-5">
            <p className="text-sm text-ink leading-relaxed">
              I agree to let Zip2Job:
            </p>
            <ul className="space-y-2">
              {FILE_ACCESS_BULLETS.map((bullet) => (
                <li key={bullet} className="flex items-start gap-2 text-sm text-ink">
                  <span className="mt-0.5 text-accent">•</span>
                  {bullet}
                </li>
              ))}
            </ul>
            <p className="rounded-lg border border-border bg-surface px-3 py-2 font-mono text-xs text-muted">
              ⚠️ File names/metadata may appear in summaries. You can revoke permission anytime.
            </p>

            {error && (
              <p data-testid="consent-error" className="font-mono text-xs text-red-400">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleFileConsentAgree}
                className="flex-1 btn-primary"
                data-testid="file-consent-agree"
              >
                I Agree
              </button>
              <button
                type="button"
                onClick={() => { setError(null); setStep('auth') }}
                className="flex-1 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                data-testid="file-consent-cancel"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            STEP: ai-consent  (mirrors ConsentTool.external_services_consent_text)
        ══════════════════════════════════════════════════════════════════ */}
        {step === 'ai-consent' && (
          <form onSubmit={handleAiConsentSubmit} className="space-y-5">
            <p className="text-sm text-ink leading-relaxed">
              {AI_FEATURES_DESCRIPTION}
            </p>

            <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 hover:border-accent">
              <input
                type="checkbox"
                checked={useExternal}
                onChange={(e) => setUseExternal(e.target.checked)}
                className="h-4 w-4 accent-accent"
                data-testid="consent-use-external"
              />
              <div>
                <div className="text-sm font-semibold">Enable AI features</div>
                <div className="text-xs text-muted">Enables Gemini AI for bullet points, summaries, and skill recommendations</div>
              </div>
            </label>

            {error && (
              <p data-testid="consent-error" className="font-mono text-xs text-red-400">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 btn-primary disabled:cursor-not-allowed disabled:opacity-40"
                data-testid="consent-submit"
              >
                {loading ? 'Saving…' : useExternal ? 'Enable AI →' : 'Skip →'}
              </button>
            </div>

            <p className="text-center text-xs text-muted">
              You can update these settings at any time from the Dashboard.
            </p>
          </form>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            STEP: done
        ══════════════════════════════════════════════════════════════════ */}
        {step === 'done' && (
          <div data-testid="consent-success" className="font-mono text-sm text-green-400">
            ✓ All set — loading your workspace…
          </div>
        )}

      </div>
    </div>
  )
}
