import { useState } from 'react'
import { AppContext } from './context/AppContext'
import { useAppBootstrap } from './hooks/useAppBootstrap'
import ConsentSetup from '../pages/consents/ConsentSetup'
import AppShell from '../layouts/AppShell'
import LoadingScreen from '../components/LoadingScreen'

const INITIAL_UPLOAD_HIGHLIGHTS = {
  created: [],
  merged: [],
}

export default function AppRoot() {
  const [page, setPage] = useState('dashboard')
  const [uploadHighlights, setUploadHighlights] = useState(INITIAL_UPLOAD_HIGHLIGHTS)
  const {
    consentReady,
    setConsentReady,
    apiOk,
    user,
    setUser,
    logout,
  } = useAppBootstrap()

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
        logout,
      }}
    >
      <AppShell page={page} setPage={setPage} apiOk={apiOk} user={user} logout={logout} />
    </AppContext.Provider>
  )
}
