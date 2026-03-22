import { useEffect, useRef, useState } from 'react'
import { AppContext } from './context/AppContext'
import { useAppBootstrap } from './hooks/useAppBootstrap'
import ConsentSetup from '../pages/consents/ConsentSetup'
import AppShell from '../layouts/AppShell'
import LoadingScreen from '../components/LoadingScreen'
import SpotlightTour from '../components/onboarding/SpotlightTour'

const INITIAL_UPLOAD_HIGHLIGHTS = {
  created: [],
  merged: [],
}

export default function AppRoot() {
  const [page, setPage] = useState('dashboard')
  const [uploadHighlights, setUploadHighlights] = useState(INITIAL_UPLOAD_HIGHLIGHTS)
  const [showTour, setShowTour] = useState(false)

  const analysisCache = useRef({})

  const {
    consentReady,
    setConsentReady,
    apiOk,
    user,
    setUser,
    logout,
  } = useAppBootstrap()

  useEffect(() => {
    if (consentReady) {
      window.api
        .getTutorialStatus()
        .then((res) => {
          if (!res.completed) setShowTour(true)
        })
        .catch(() => {})
    }
  }, [consentReady])

  if (consentReady === null) {
    return <LoadingScreen message="Starting…" />
  }

  if (!consentReady) {
    return (
      <ConsentSetup
        onDone={(username, token) => {
          localStorage.setItem('zip2job_token', token)
          localStorage.setItem('zip2job_username', username)
          window.api.setAuthToken(token)
          window.api.setUsername(username)
          window.api.getCurrentUser().then(setUser).catch(() => {})
          setConsentReady(true)
        }}
      />
    )
  }

  return (
    <AppContext.Provider
      value={{
        user,
        apiOk,
        page,
        setPage,
        uploadHighlights,
        setUploadHighlights,
        analysisCache,
        logout,
      }}
    >
      <AppShell page={page} setPage={setPage} apiOk={apiOk} user={user} logout={logout} onStartTour={() => setShowTour(true)} />
      {showTour && (
        <SpotlightTour
          setPage={setPage}
          onComplete={() => {
            window.api.updateTutorialStatus({ completed: true }).catch(() => {})
            setShowTour(false)
          }}
          onSkip={() => {
            window.api.updateTutorialStatus({ completed: true }).catch(() => {})
            setShowTour(false)
          }}
          onDismiss={() => setShowTour(false)}
        />
      )}
    </AppContext.Provider>
  )
}
