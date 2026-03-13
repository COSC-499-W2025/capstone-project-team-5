import { useEffect, useRef, useState } from 'react'

function getErrorMessage(error, fallbackMessage) {
  let message = error?.message ?? fallbackMessage

  try {
    message = JSON.parse(message).detail ?? message
  } catch {}

  return message
}

export default function ConsentSetup({ onDone }) {
  const [authMode, setAuthMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [availableData, setAvailableData] = useState(null)
  const [useExternal, setUseExternal] = useState(false)
  const [checkedServices, setCheckedServices] = useState({})
  const [step, setStep] = useState('auth')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const doneTimeoutRef = useRef(null)

  useEffect(() => {
    return () => {
      if (doneTimeoutRef.current) {
        clearTimeout(doneTimeoutRef.current)
      }
    }
  }, [])

  async function handleAuthSubmit(event) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const authFn = authMode === 'register' ? window.api.register : window.api.login
      const response = await authFn({ username: username.trim(), password })

      window.api.setAuthUsername(response.username)
      window.api.setUsername(response.username)

      // For returning users who already gave consent, skip the consent step
      // entirely and go straight to the app.
      if (authMode === 'login') {
        const existingConsent = await window.api.getLatestConsent().catch(() => null)
        if (existingConsent !== null) {
          setStep('done')
          doneTimeoutRef.current = setTimeout(() => onDone(response.username), 800)
          return
        }
      }

      const data = await window.api.getAvailableServices()
      const initialCheckedServices = {}

      ;(data.external_services ?? []).forEach((serviceName) => {
        initialCheckedServices[serviceName] = true
      })

      setAvailableData(data)
      setCheckedServices(initialCheckedServices)
      setUseExternal(true)
      setStep('consent')
    } catch (error) {
      setError(getErrorMessage(error, 'Something went wrong.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleConsentSubmit(event) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const externalServicesMap = {}

      Object.entries(checkedServices).forEach(([name, checked]) => {
        externalServicesMap[name] = { allowed: checked }
      })

      await window.api.giveConsent({
        consent_given: true,
        use_external_services: useExternal,
        external_services: externalServicesMap,
        default_ignore_patterns: availableData?.common_ignore_patterns ?? [],
      })

      setStep('done')
      doneTimeoutRef.current = setTimeout(() => onDone(username.trim()), 800)
    } catch (error) {
      setError(getErrorMessage(error, 'Consent submission failed.'))
    } finally {
      setLoading(false)
    }
  }

  function toggleService(name) {
    setCheckedServices((current) => ({ ...current, [name]: !current[name] }))
  }

  return (
    <div className="flex h-screen items-center justify-center bg-bg text-ink">
      <div className="w-[480px] space-y-6">
        <div>
          <div className="text-2xl font-extrabold tracking-tight">
            Zip<span className="text-accent">2</span>Job
          </div>
          <p className="mt-1 text-sm text-muted">
            {step === 'auth'
              ? authMode === 'login'
                ? 'Welcome back.'
                : 'Create your account.'
              : 'Review data permissions for your workspace.'}
          </p>
        </div>

        {step === 'done' && (
          <div data-testid="consent-success" className="font-mono text-sm text-green-400">
            ✓ All set — loading your workspace…
          </div>
        )}

        {step === 'auth' && (
          <div className="space-y-5">
            <div className="flex gap-1 rounded-lg border border-border bg-surface p-1">
              {['login', 'register'].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => {
                    setAuthMode(mode)
                    setError(null)
                  }}
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
                  onChange={(event) => setUsername(event.target.value)}
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
                  onChange={(event) => setPassword(event.target.value)}
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
                {loading ? 'Please wait…' : authMode === 'login' ? 'Log In' : 'Create Account'}
              </button>
            </form>
          </div>
        )}

        {step === 'consent' && (
          <form onSubmit={handleConsentSubmit} className="space-y-5">
            <div className="font-mono text-xs text-muted">
              Signed in as <span className="font-semibold text-ink">{username}</span>
            </div>

            <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 hover:border-accent">
              <input
                type="checkbox"
                checked={useExternal}
                onChange={(event) => setUseExternal(event.target.checked)}
                className="h-4 w-4 accent-accent"
                data-testid="consent-use-external"
              />
              <div>
                <div className="text-sm font-semibold">Allow external service access</div>
                <div className="text-xs text-muted">Enables GitHub, LinkedIn, and AI integrations</div>
              </div>
            </label>

            {useExternal && availableData?.external_services?.length > 0 && (
              <fieldset className="space-y-1.5">
                <legend className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted">
                  External Services
                </legend>
                {availableData.external_services.map((serviceName) => (
                  <label
                    key={serviceName}
                    className="flex cursor-pointer items-center gap-3 rounded-lg border border-border px-3 py-2 text-sm hover:border-accent"
                  >
                    <input
                      type="checkbox"
                      checked={!!checkedServices[serviceName]}
                      onChange={() => toggleService(serviceName)}
                      className="h-3.5 w-3.5 accent-accent"
                      data-testid={`consent-service-${serviceName.replace(/\s+/g, '-').toLowerCase()}`}
                    />
                    {serviceName}
                  </label>
                ))}
              </fieldset>
            )}

            {error && (
              <p data-testid="consent-error" className="font-mono text-xs text-red-400">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary disabled:cursor-not-allowed disabled:opacity-40"
              data-testid="consent-submit"
            >
              {loading ? 'Saving…' : 'Save & Continue →'}
            </button>

            <p className="text-center text-xs text-muted">
              You can update these settings at any time from the Dashboard.
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
