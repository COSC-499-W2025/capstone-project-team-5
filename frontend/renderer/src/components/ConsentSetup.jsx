import { useState } from 'react'

export default function ConsentSetup({ onDone }) {
  const [authMode,        setAuthMode]        = useState('login')   // 'login' | 'register'
  const [username,        setUsername]        = useState('')
  const [password,        setPassword]        = useState('')
  const [authToken,       setAuthToken]       = useState(null)
  const [availableData,   setAvailableData]   = useState(null)      // raw API response
  const [useExternal,     setUseExternal]     = useState(false)     // use_external_services
  const [checkedServices, setCheckedServices] = useState({})        // { serviceName: bool }
  const [step,            setStep]            = useState('auth')
  const [error,           setError]           = useState(null)
  const [loading,         setLoading]         = useState(false)

  // ── Step 1: auth ──────────────────────────────────────────────────────
  async function handleAuthSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const fn = authMode === 'register' ? window.api.register : window.api.login
      const res = await fn({ username: username.trim(), password })
      window.api.setAuthToken(res.token)
      window.api.setAuthUsername(res.username)
      window.api.setUsername(res.username)
      setAuthToken(res.token)
      // Load available services list for the consent step
      const data = await window.api.getAvailableServices()
      setAvailableData(data)
      // Pre-tick all external services by default
      const initial = {}
      ;(data.external_services ?? []).forEach(s => { initial[s] = true })
      setCheckedServices(initial)
      setUseExternal(true)
      setStep('consent')
    } catch (err) {
      let msg = err.message ?? 'Something went wrong.'
      try { msg = JSON.parse(msg).detail ?? msg } catch {}
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: consent ───────────────────────────────────────────────────
  async function handleConsentSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      // Build the external_services map: { serviceName: { allowed: bool } }
      const externalServicesMap = {}
      Object.entries(checkedServices).forEach(([name, checked]) => {
        externalServicesMap[name] = { allowed: checked }
      })
      await window.api.giveConsent({
        consent_given:         true,
        use_external_services: useExternal,
        external_services:     externalServicesMap,
        default_ignore_patterns: availableData?.common_ignore_patterns ?? [],
      })
      setStep('done')
      setTimeout(() => onDone(username.trim(), authToken), 800)
    } catch (err) {
      let msg = err.message ?? 'Consent submission failed.'
      try { msg = JSON.parse(msg).detail ?? msg } catch {}
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function toggleService(name) {
    setCheckedServices(prev => ({ ...prev, [name]: !prev[name] }))
  }

  return (
    <div className="flex h-screen items-center justify-center bg-bg text-ink">
      <div className="w-[480px] space-y-6">

        {/* Brand */}
        <div>
          <div className="text-2xl font-extrabold tracking-tight">
            Zip<span className="text-accent">2</span>Job
          </div>
          <p className="text-sm text-muted mt-1">
            {step === 'auth'
              ? authMode === 'login' ? 'Welcome back.' : 'Create your account.'
              : 'Review data permissions for your workspace.'}
          </p>
        </div>

        {/* ── Done splash ── */}
        {step === 'done' && (
          <div data-testid="consent-success" className="text-green-400 font-mono text-sm">
            ✓ All set — loading your workspace…
          </div>
        )}

        {/* ── Step 1: Login / Register ── */}
        {step === 'auth' && (
          <div className="space-y-5">
            {/* Mode tabs */}
            <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
              {['login', 'register'].map(mode => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => { setAuthMode(mode); setError(null) }}
                  className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-colors ${
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
                  onChange={e => setUsername(e.target.value)}
                  placeholder="e.g. alice"
                  required
                  autoFocus
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent"
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
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent"
                  data-testid="auth-password"
                />
              </div>

              {error && (
                <p data-testid="consent-error" className="text-xs text-red-400 font-mono">{error}</p>
              )}

              <button
                type="submit"
                disabled={!username.trim() || !password || loading}
                className="w-full btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
                data-testid="auth-submit"
              >
                {loading ? 'Please wait…' : authMode === 'login' ? 'Log In' : 'Create Account'}
              </button>
            </form>
          </div>
        )}

        {/* ── Step 2: Consent ── */}
        {step === 'consent' && (
          <form onSubmit={handleConsentSubmit} className="space-y-5">

            {/* Who's logged in */}
            <div className="font-mono text-xs text-muted">
              Signed in as <span className="text-ink font-semibold">{username}</span>
            </div>

            {/* Master toggle */}
            <label className="flex items-center gap-3 p-3 rounded-lg border border-border cursor-pointer hover:border-accent">
              <input
                type="checkbox"
                checked={useExternal}
                onChange={e => setUseExternal(e.target.checked)}
                className="accent-accent w-4 h-4"
                data-testid="consent-use-external"
              />
              <div>
                <div className="font-semibold text-sm">Allow external service access</div>
                <div className="text-xs text-muted">Enables GitHub, LinkedIn, and AI integrations</div>
              </div>
            </label>

            {/* Per-service list */}
            {useExternal && availableData?.external_services?.length > 0 && (
              <fieldset className="space-y-1.5">
                <legend className="text-xs font-semibold uppercase tracking-widest text-muted mb-2">
                  External Services
                </legend>
                {availableData.external_services.map(svc => (
                  <label
                    key={svc}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border cursor-pointer hover:border-accent text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={!!checkedServices[svc]}
                      onChange={() => toggleService(svc)}
                      className="accent-accent w-3.5 h-3.5"
                      data-testid={`consent-service-${svc.replace(/\s+/g, '-').toLowerCase()}`}
                    />
                    {svc}
                  </label>
                ))}
              </fieldset>
            )}

            {error && (
              <p data-testid="consent-error" className="text-xs text-red-400 font-mono">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
              data-testid="consent-submit"
            >
              {loading ? 'Saving…' : 'Save & Continue →'}
            </button>

            <p className="text-xs text-muted text-center">
              You can update these settings at any time from the Dashboard.
            </p>
          </form>
        )}

      </div>
    </div>
  )
}
