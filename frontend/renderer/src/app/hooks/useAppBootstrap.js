import { useCallback, useEffect, useState } from 'react'

/**
 * Returns true only for HTTP responses that definitively mean the stored
 * credentials are no longer valid (401 Unauthorized / 403 Forbidden).
 * Network errors, 5xx, timeouts, etc. are treated as transient and must NOT
 * clear the persisted login.
 *
 * Relies on the numeric `status` property that preload's `httpError()` helper
 * attaches to every API error — no string parsing required.
 */
function isAuthError(err) {
  return err?.status === 401 || err?.status === 403
}

/** Clears all persisted credentials from both localStorage and the preload bridge. */
function clearSession() {
  localStorage.removeItem('zip2job_token')
  localStorage.removeItem('zip2job_username')
  window.api.clearCredentials()
}

export function useAppBootstrap() {
  const [consentReady, setConsentReady] = useState(null)
  const [apiOk, setApiOk] = useState(false)
  const [user, setUser] = useState(null)

  /** Imperatively clear credentials and return to the consent/login gate. */
  const logout = useCallback(() => {
    clearSession()
    setUser(null)
    setConsentReady(false)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function boot() {
      try {
        await window.api.health()
        if (!cancelled) {
          setApiOk(true)
        }
      } catch {
        if (!cancelled) {
          setApiOk(false)
          setConsentReady(false)
        }
        return
      }

      const savedToken    = localStorage.getItem('zip2job_token')
      const savedUsername = localStorage.getItem('zip2job_username')

      if (savedToken)    window.api.setAuthToken(savedToken)
      if (savedUsername) window.api.setUsername(savedUsername)

      if (!savedToken) {
        if (!cancelled) {
          setConsentReady(false)
        }
        return
      }

      try {
        const [currentUser, consent] = await Promise.all([
          window.api.getCurrentUser(),
          window.api.getLatestConsent(),
        ])

        if (!cancelled) {
          setUser(currentUser)
          setConsentReady(consent !== null)
        }
      } catch (err) {
        // Only evict the stored session when the server explicitly rejects the
        // credentials (401/403).  Transient errors (network down, 5xx, timeout)
        // must not log the user out.
        if (isAuthError(err)) {
          clearSession()

          if (!cancelled) {
            setUser(null)
            setConsentReady(false)
          }
        } else {
          // Transient error – keep credentials, show the offline / error state
          if (!cancelled) {
            setConsentReady(false)
          }
        }
      }
    }

    boot()

    const id = setInterval(async () => {
      try {
        await window.api.health()
        if (!cancelled) {
          setApiOk(true)
        }
      } catch {
        if (!cancelled) {
          setApiOk(false)
        }
      }
    }, 10_000)

    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  return {
    consentReady,
    setConsentReady,
    apiOk,
    user,
    setUser,
    logout,
  }
}
