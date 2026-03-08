/**
 * @jest-environment jsdom
 *
 * DOM tests for the ConsentSetup wizard (Login/Register → Consent).
 * Consent step uses checkboxes for external services, not a provider picker.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const AVAILABLE_SERVICES = {
  external_services:     ['GitHub API', 'Gemini', 'LinkedIn API'],
  ai_models:             ['Gemini 2.5 Flash (Google)'],
  common_ignore_patterns: ['.git', 'node_modules'],
}

function setupApi(overrides = {}) {
  window.api = {
    health:               jest.fn().mockResolvedValue({ status: 'ok' }),
    getCurrentUser:       jest.fn().mockResolvedValue({ username: 'alice' }),
    getLatestConsent:     jest.fn().mockResolvedValue(null),
    getAvailableServices: jest.fn().mockResolvedValue(AVAILABLE_SERVICES),
    giveConsent:          jest.fn().mockResolvedValue({ id: 1, consent_given: true }),
    getLLMConfig:         jest.fn().mockResolvedValue({ is_allowed: true }),
    login:                jest.fn().mockResolvedValue({ username: 'alice' }),
    register:             jest.fn().mockResolvedValue({ username: 'alice' }),
    setUsername:          jest.fn(),
    getUsername:          jest.fn().mockReturnValue(null),
    getProjects:          jest.fn().mockResolvedValue([]),
    getSkills:            jest.fn().mockResolvedValue([]),
    getWorkExperiences:   jest.fn().mockResolvedValue([]),
    getResumes:           jest.fn().mockResolvedValue([]),
    ...overrides,
  }
}

async function renderWizard(App) {
  render(<App />)
  await waitFor(() =>
    expect(screen.getByText(/welcome back|create your account/i)).toBeInTheDocument()
  )
}

async function submitAuth(username = 'alice', password = 'secret') {
  await userEvent.type(screen.getByTestId('auth-username'), username)
  await userEvent.type(screen.getByTestId('auth-password'), password)
  fireEvent.click(screen.getByTestId('auth-submit'))
}

async function advanceToConsent() {
  await submitAuth()
  await waitFor(() =>
    expect(screen.getByText(/review data permissions/i)).toBeInTheDocument()
  )
}

let App
beforeAll(async () => {
  App = (await import('../renderer/src/App.jsx')).default
})
beforeEach(() => jest.clearAllMocks())

// ── Step 1: auth tab UI ────────────────────────────────────────────────────
test('shows Login tab by default with Welcome back subtitle', async () => {
  setupApi()
  await renderWizard(App)
  expect(screen.getByTestId('auth-tab-login')).toBeInTheDocument()
  expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
})

test('switching to Sign Up tab updates subtitle', async () => {
  setupApi()
  await renderWizard(App)
  fireEvent.click(screen.getByTestId('auth-tab-register'))
  expect(screen.getByText(/create your account/i)).toBeInTheDocument()
})

test('submit button disabled until username and password filled', async () => {
  setupApi()
  await renderWizard(App)
  const btn = screen.getByTestId('auth-submit')
  expect(btn).toBeDisabled()
  await userEvent.type(screen.getByTestId('auth-username'), 'alice')
  expect(btn).toBeDisabled()
  await userEvent.type(screen.getByTestId('auth-password'), 'secret')
  expect(btn).not.toBeDisabled()
})

// ── Step 1: login / register success ──────────────────────────────────────
test('successful login calls window.api.login and advances to consent step', async () => {
  setupApi()
  await renderWizard(App)
  await submitAuth()
  expect(window.api.login).toHaveBeenCalledWith({ username: 'alice', password: 'secret' })
  await waitFor(() =>
    expect(screen.getByText(/review data permissions/i)).toBeInTheDocument()
  )
})

test('setUsername is called with returned username after login', async () => {
  setupApi()
  await renderWizard(App)
  await submitAuth()
  await waitFor(() => expect(window.api.setUsername).toHaveBeenCalledWith('alice'))
})

test('successful register calls window.api.register and advances to consent', async () => {
  setupApi()
  await renderWizard(App)
  fireEvent.click(screen.getByTestId('auth-tab-register'))
  await submitAuth('newuser', 'password123')
  expect(window.api.register).toHaveBeenCalledWith({ username: 'newuser', password: 'password123' })
  await waitFor(() =>
    expect(screen.getByText(/review data permissions/i)).toBeInTheDocument()
  )
})

// ── Step 1: failed auth ────────────────────────────────────────────────────
test('failed login shows error message', async () => {
  setupApi({
    login: jest.fn().mockRejectedValue(new Error('Invalid username or password.')),
  })
  await renderWizard(App)
  await submitAuth()
  await waitFor(() =>
    expect(screen.getByTestId('consent-error')).toHaveTextContent('Invalid username or password.')
  )
})

// ── Step 2: consent UI ────────────────────────────────────────────────────
test('shows external services checkboxes on consent step', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToConsent()
  expect(screen.getByText('GitHub API')).toBeInTheDocument()
  expect(screen.getByText('Gemini')).toBeInTheDocument()
  expect(screen.getByText('LinkedIn API')).toBeInTheDocument()
})

test('shows signed-in username on consent step', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToConsent()
  expect(screen.getByText('alice')).toBeInTheDocument()
})

test('master external toggle is checked by default', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToConsent()
  expect(screen.getByTestId('consent-use-external')).toBeChecked()
})

test('unchecking master toggle hides per-service list', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToConsent()
  fireEvent.click(screen.getByTestId('consent-use-external'))
  expect(screen.queryByText('GitHub API')).not.toBeInTheDocument()
})

test('consent submit button is enabled by default (no required fields)', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToConsent()
  expect(screen.getByTestId('consent-submit')).not.toBeDisabled()
})

// ── Step 2: successful consent ────────────────────────────────────────────
test('calls giveConsent with correct payload and shows success splash', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToConsent()
  fireEvent.click(screen.getByTestId('consent-submit'))
  await waitFor(() =>
    expect(screen.getByTestId('consent-success')).toBeInTheDocument()
  )
  expect(window.api.giveConsent).toHaveBeenCalledWith(
    expect.objectContaining({
      consent_given:         true,
      use_external_services: true,
    })
  )
})

// ── Step 2: failed consent ────────────────────────────────────────────────
test('shows error when giveConsent rejects', async () => {
  setupApi({
    giveConsent: jest.fn().mockRejectedValue(new Error('Server error')),
  })
  await renderWizard(App)
  await advanceToConsent()
  fireEvent.click(screen.getByTestId('consent-submit'))
  await waitFor(() =>
    expect(screen.getByTestId('consent-error')).toHaveTextContent('Server error')
  )
})
