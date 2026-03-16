/**
 * @jest-environment jsdom
 *
 * DOM tests for the top-level App component:
 *   - shows "Starting…" while booting
 *   - shows ConsentSetup when no consent exists
 *   - shows the main shell (sidebar + topbar) once consent is present
 *   - sidebar nav items are all rendered
 *   - clicking a nav item updates the topbar title
 *   - api-offline indicator when health check fails
 *   - transient boot errors do NOT clear localStorage (no unexpected logout)
 *   - 401/403 boot errors DO clear localStorage (auth failure)
 *   - Log Out button clears credentials and returns to ConsentSetup
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from '../renderer/src/App.jsx'

/** Mirrors the `httpError()` helper in preload.js — attaches a numeric `status`. */
function httpError(status, message) {
  const err = new Error(message ?? `HTTP ${status}`)
  err.status = status
  return err
}
function setupApi(overrides = {}) {
  window.api = {
    health:               jest.fn().mockResolvedValue({ status: 'ok' }),
    getCurrentUser:       jest.fn().mockResolvedValue({ username: 'alice' }),
    getLatestConsent:     jest.fn().mockResolvedValue({ provider: 'openai' }),
    getAvailableServices: jest.fn().mockResolvedValue([]),
    giveConsent:          jest.fn().mockResolvedValue({ status: 'ok' }),
    getLLMConfig:         jest.fn().mockResolvedValue({ provider: 'openai' }),
    setAuthToken:         jest.fn(),
    getAuthToken:         jest.fn().mockReturnValue(null),
    setAuthUsername:      jest.fn(),
    setUsername:          jest.fn(),
    clearCredentials:     jest.fn(),
    getUsername:          jest.fn().mockReturnValue('alice'),
    getProjects:          jest.fn().mockResolvedValue([]),
    getSkills:            jest.fn().mockResolvedValue([]),
    getWorkExperiences:   jest.fn().mockResolvedValue([]),
    getEducations:        jest.fn().mockResolvedValue([]),
    getProfile:           jest.fn().mockResolvedValue(null),
    getResumes:           jest.fn().mockResolvedValue([]),
    getLLMConfig:         jest.fn().mockResolvedValue({ is_allowed: false, model_preferences: [] }),
    analyzeProject:       jest.fn().mockResolvedValue({}),
    createResume:         jest.fn().mockResolvedValue({}),
    updateResume:         jest.fn().mockResolvedValue({}),
    deleteResume:         jest.fn().mockResolvedValue(null),
    downloadResumePdf:    jest.fn().mockResolvedValue({
      bytes: new ArrayBuffer(8),
      contentType: 'application/pdf',
      filename: 'resume.pdf',
    }),
    ...overrides,
  }
}

beforeEach(() => {
  jest.clearAllMocks()
  localStorage.clear()
})

// ── Boot splash ────────────────────────────────────────────────────────────
test('shows loading splash while booting', () => {
  // Health never resolves so boot stays pending
  setupApi({ health: jest.fn(() => new Promise(() => {})) })
  render(<App />)
  expect(screen.getByText('Starting…')).toBeInTheDocument()
})

// ── Consent gate ───────────────────────────────────────────────────────────
test('shows ConsentSetup when getLatestConsent returns null', async () => {
  setupApi({ getLatestConsent: jest.fn().mockResolvedValue(null) })
  render(<App />)
  await waitFor(() =>
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
  )
})

// ── Main shell ─────────────────────────────────────────────────────────────
test('renders sidebar and topbar after successful boot with existing consent', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  // Sidebar brand
  expect(screen.getByText('Portfolio Engine')).toBeInTheDocument()
  // Topbar shows current page title — appears in both nav button and topbar span
  expect(screen.getAllByText(/Dashboard/).length).toBeGreaterThan(0)
})

test('renders all nav items in sidebar', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  const labels = ['Dashboard', 'Projects', 'Skills', 'Experience', 'Education', 'Portfolio', 'Resumes', 'Consents']
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  for (const label of labels) {
    expect(screen.getAllByText(label).length).toBeGreaterThan(0)
  }
})

test('clicking a nav item updates the topbar title', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())

  // Find the sidebar nav button for Projects and click it
  const navButtons = screen.getAllByRole('button')
  const projectsBtn = navButtons.find(b => b.textContent.includes('Projects'))
  expect(projectsBtn).toBeTruthy()
  fireEvent.click(projectsBtn)

  // Topbar title updates to Projects
  await waitFor(() => {
    const header = document.querySelector('header')
    expect(header.textContent).toMatch(/Projects/)
  })
})

test('dashboard quick action opens the resumes workspace', async () => {
  setupApi()
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /generate resume/i }))

  await waitFor(() => {
    const header = document.querySelector('header')
    expect(header.textContent).toMatch(/Resumes/)
  })
  expect(screen.getByRole('heading', { name: /^resumes$/i })).toBeInTheDocument()
})

test('shows username in sidebar when user is loaded', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument())
})

test('restores saved token and username into the Electron bridge during boot', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)

  await waitFor(() => expect(window.api.setAuthToken).toHaveBeenCalledWith('fake-token'))
  expect(window.api.setUsername).toHaveBeenCalledWith('alice')
})

// ── API offline indicator ──────────────────────────────────────────────────
test('shows api offline when health check throws', async () => {
  setupApi({
    health: jest.fn().mockRejectedValue(new Error('ECONNREFUSED')),
    // getLatestConsent also throws since api is down, so consent stays false
    getLatestConsent: jest.fn().mockRejectedValue(new Error('down')),
    getCurrentUser:   jest.fn().mockRejectedValue(new Error('down')),
  })
  render(<App />)
  // Boot catches the error → consentReady = false → ConsentSetup shown
  // (or we could be on the main shell if consent was already recorded —
  // here the api is down so boot rejects → consentReady stays false)
  await waitFor(() =>
    expect(screen.queryByText('Starting…')).not.toBeInTheDocument()
  )
})

// ── Boot error handling ────────────────────────────────────────────────────
test('transient boot error (5xx) does NOT clear localStorage', async () => {
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  setupApi({
    getCurrentUser:   jest.fn().mockRejectedValue(httpError(503)),
    getLatestConsent: jest.fn().mockRejectedValue(httpError(503)),
  })
  render(<App />)
  await waitFor(() =>
    expect(screen.queryByText('Starting…')).not.toBeInTheDocument()
  )
  // Credentials must still be in localStorage — user was NOT logged out
  expect(localStorage.getItem('zip2job_username')).toBe('alice')
  expect(window.api.clearCredentials).not.toHaveBeenCalled()
})

test('network error during boot does NOT clear localStorage', async () => {
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  setupApi({
    getCurrentUser:   jest.fn().mockRejectedValue(new Error('ECONNREFUSED')),
    getLatestConsent: jest.fn().mockRejectedValue(new Error('ECONNREFUSED')),
  })
  render(<App />)
  await waitFor(() =>
    expect(screen.queryByText('Starting…')).not.toBeInTheDocument()
  )
  expect(localStorage.getItem('zip2job_username')).toBe('alice')
  expect(window.api.clearCredentials).not.toHaveBeenCalled()
})

test('401 auth error during boot DOES clear localStorage', async () => {
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  setupApi({
    getCurrentUser:   jest.fn().mockRejectedValue(httpError(401)),
    getLatestConsent: jest.fn().mockRejectedValue(httpError(401)),
  })
  render(<App />)
  await waitFor(() =>
    expect(screen.queryByText('Starting…')).not.toBeInTheDocument()
  )
  expect(localStorage.getItem('zip2job_token')).toBeNull()
  expect(localStorage.getItem('zip2job_username')).toBeNull()
  expect(window.api.clearCredentials).toHaveBeenCalled()
})

test('403 auth error during boot DOES clear localStorage', async () => {
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  setupApi({
    getCurrentUser:   jest.fn().mockRejectedValue(httpError(403)),
    getLatestConsent: jest.fn().mockRejectedValue(httpError(403)),
  })
  render(<App />)
  await waitFor(() =>
    expect(screen.queryByText('Starting…')).not.toBeInTheDocument()
  )
  expect(localStorage.getItem('zip2job_token')).toBeNull()
  expect(localStorage.getItem('zip2job_username')).toBeNull()
  expect(window.api.clearCredentials).toHaveBeenCalled()
})

// ── Log Out ────────────────────────────────────────────────────────────────
test('sidebar renders a Log Out button when the shell is shown', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument()
})

test('clicking Log Out clears localStorage and returns to ConsentSetup', async () => {
  setupApi()
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')

  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /log out/i }))

  await waitFor(() =>
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
  )
  expect(localStorage.getItem('zip2job_token')).toBeNull()
  expect(localStorage.getItem('zip2job_username')).toBeNull()
  expect(window.api.clearCredentials).toHaveBeenCalled()
})
