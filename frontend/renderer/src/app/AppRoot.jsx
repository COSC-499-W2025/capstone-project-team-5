import { useCallback, useEffect, useRef, useState } from 'react'
import { AppContext } from './context/AppContext'
import { useAppBootstrap } from './hooks/useAppBootstrap'
import ConsentSetup from '../pages/consents/ConsentSetup'
import AppShell from '../layouts/AppShell'
import LoadingScreen from '../components/LoadingScreen'
import SpotlightTour from '../components/onboarding/SpotlightTour'
import GuidedSetup from '../components/onboarding/GuidedSetup'

const INITIAL_UPLOAD_HIGHLIGHTS = {
  created: [],
  merged: [],
}

export default function AppRoot() {
  const [page, setPage] = useState('dashboard')
  const [uploadHighlights, setUploadHighlights] = useState(INITIAL_UPLOAD_HIGHLIGHTS)
  const [showTour, setShowTour] = useState(false)
  const [tourInitialStep, setTourInitialStep] = useState(0)
  const [showSetup, setShowSetup] = useState(false)

  const startSetup = useCallback(() => {
    setShowTour(false)
    window.api.updateTutorialStatus({ completed: true }).catch(() => {})
    window.api.updateSetupStatus({ completed: false, step: 0 }).catch(() => {})
    setShowSetup(true)
  }, [])

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
      <AppShell page={page} setPage={setPage} apiOk={apiOk} user={user} logout={logout} onStartTour={() => { setTourInitialStep(1); setShowTour(true) }} onStartSetup={startSetup} />
      {showTour && (
        <SpotlightTour
          setPage={setPage}
          initialStep={tourInitialStep}
          onStartSetup={startSetup}
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
      {showSetup && (
        <GuidedSetup
          setPage={setPage}
          onComplete={() => {
            window.api.updateSetupStatus({ completed: true, step: 6 }).catch(() => {})
            setShowSetup(false)
          }}
          onDismiss={() => setShowSetup(false)}
          onSkip={() => {
            window.api.updateSetupStatus({ completed: true, step: 0 }).catch(() => {})
            setShowSetup(false)
          }}
        />
      )}
    </AppContext.Provider>
  )
}
