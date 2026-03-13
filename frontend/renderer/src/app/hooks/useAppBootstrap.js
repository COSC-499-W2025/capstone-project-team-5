import { useCallback, useEffect, useState } from 'react'

/**
 * Returns true only for HTTP responses that definitively mean the stored
 * credentials are no longer valid (401 Unauthorized / 403 Forbidden).
 * Network errors, 5xx, timeouts, etc. are treated as transient and must NOT
 * clear the persisted login.
 */
function isAuthError(err) {
  if (!err || typeof err.message !== 'string') return false
  const msg = err.message.trim()
  // The preload request() helper throws with the message "HTTP <status>" when
  // no detail field is available, so we match on the status code prefix.
  return /^HTTP (401|403)\b/.test(msg) || /unauthorized|forbidden/i.test(msg)
}

export function useAppBootstrap() {
  const [consentReady, setConsentReady] = useState(null)
  const [apiOk, setApiOk] = useState(false)
  const [user, setUser] = useState(null)

  /** Imperatively clear credentials and return to the consent/login gate. */
  const logout = useCallback(() => {
    localStorage.removeItem('zip2job_username')
    window.api.clearCredentials()
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

      const savedUsername = localStorage.getItem('zip2job_username')
      if (savedUsername) {
        window.api.setAuthUsername(savedUsername)
        window.api.setUsername(savedUsername)
      }

      if (!savedUsername) {
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
          localStorage.removeItem('zip2job_username')
          window.api.clearCredentials()

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
