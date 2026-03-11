import { useEffect, useState } from 'react'

export function useAppBootstrap() {
  const [consentReady, setConsentReady] = useState(null)
  const [apiOk, setApiOk] = useState(false)
  const [user, setUser] = useState(null)

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
      } catch {
        localStorage.removeItem('zip2job_username')
        window.api.setUsername(null)

        if (!cancelled) {
          setConsentReady(false)
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
  }
}
