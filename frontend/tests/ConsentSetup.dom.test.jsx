/**
 * @jest-environment jsdom
 *
 * DOM tests for the ConsentSetup wizard.
 *
 * Flow (new, matching TUI):
 *   auth → file-consent ("Zip2Job Permission" / I Agree) → ai-consent ("AI Features") → done
 *
 * Returning users who already have consent skip the wizard after login.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const AVAILABLE_SERVICES = {
  external_services:      ['GitHub API', 'Gemini', 'LinkedIn API'],
  ai_models:              ['Gemini 2.5 Flash (Google)'],
  common_ignore_patterns: ['.git', 'node_modules'],
}

function setupApi(overrides = {}) {
  window.api = {
    health:               jest.fn().mockResolvedValue({ status: 'ok' }),
    getCurrentUser:       jest.fn().mockResolvedValue({ username: 'alice' }),
    getLatestConsent:     jest.fn().mockResolvedValue(null),
    giveConsent:          jest.fn().mockResolvedValue({ id: 1, consent_given: true }),
    getLLMConfig:         jest.fn().mockResolvedValue({ is_allowed: true }),
    login:                jest.fn().mockResolvedValue({ username: 'alice' }),
    register:             jest.fn().mockResolvedValue({ username: 'alice' }),
    setAuthUsername:      jest.fn(),
    setUsername:          jest.fn(),
    clearCredentials:     jest.fn(),
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
  await userEvent.click(screen.getByTestId('auth-submit'))
}

/** Advance from auth → file-consent step (I Agree button visible). */
async function advanceToFileConsent() {
  await submitAuth()
  await waitFor(() =>
    expect(screen.getByTestId('file-consent-agree')).toBeInTheDocument()
  )
}

/** Advance all the way through file-consent → ai-consent step. */
async function advanceToAiConsent() {
  await advanceToFileConsent()
  await userEvent.click(screen.getByTestId('file-consent-agree'))
  await waitFor(() =>
    expect(screen.getByTestId('consent-use-external')).toBeInTheDocument()
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
  await userEvent.click(screen.getByTestId('auth-tab-register'))
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
test('successful login with NO existing consent advances to file-consent step', async () => {
  setupApi({ getLatestConsent: jest.fn().mockResolvedValue(null) })
  await renderWizard(App)
  await submitAuth()
  expect(window.api.login).toHaveBeenCalledWith({ username: 'alice', password: 'secret' })
  await waitFor(() =>
    expect(screen.getByTestId('file-consent-agree')).toBeInTheDocument()
  )
  // Shows the TUI-matching "Zip2Job Permission" subtitle
  expect(screen.getByText(/zip2job permission/i)).toBeInTheDocument()
})

test('file-consent step shows the correct permission bullets', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToFileConsent()
  expect(screen.getByText(/access and analyze files/i)).toBeInTheDocument()
  expect(screen.getByText(/extract metadata/i)).toBeInTheDocument()
  expect(screen.getByText(/store summaries locally/i)).toBeInTheDocument()
  expect(screen.getByText(/file names\/metadata may appear/i)).toBeInTheDocument()
})

test('file-consent Cancel button returns to auth step', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToFileConsent()
  await userEvent.click(screen.getByTestId('file-consent-cancel'))
  await waitFor(() =>
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
  )
})

test('file-consent I Agree advances to ai-consent step', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  // Shows the TUI-matching "AI Features" subtitle in the header paragraph
  expect(screen.getByTestId('consent-use-external')).toBeInTheDocument()
  expect(screen.getByTestId('consent-submit')).toBeInTheDocument()
})

test('successful login with EXISTING consent skips both consent steps and goes to app', async () => {
  setupApi({ getLatestConsent: jest.fn().mockResolvedValue({ provider: 'openai' }) })
  await renderWizard(App)
  await submitAuth()
  await waitFor(() =>
    expect(screen.getByTestId('consent-success')).toBeInTheDocument()
  )
  expect(screen.queryByTestId('file-consent-agree')).not.toBeInTheDocument()
  expect(screen.queryByTestId('consent-use-external')).not.toBeInTheDocument()
})

test('login with existing consent does NOT call giveConsent', async () => {
  setupApi({ getLatestConsent: jest.fn().mockResolvedValue({ provider: 'openai' }) })
  await renderWizard(App)
  await submitAuth()
  await waitFor(() => expect(screen.getByTestId('consent-success')).toBeInTheDocument())
  expect(window.api.giveConsent).not.toHaveBeenCalled()
})

test('register always shows file-consent step regardless of existing consent', async () => {
  setupApi({ getLatestConsent: jest.fn().mockResolvedValue({ provider: 'openai' }) })
  await renderWizard(App)
  await userEvent.click(screen.getByTestId('auth-tab-register'))
  await submitAuth('newuser', 'password123')
  await waitFor(() =>
    expect(screen.getByTestId('file-consent-agree')).toBeInTheDocument()
  )
})

test('setUsername is called with returned username after login', async () => {
  setupApi()
  await renderWizard(App)
  await submitAuth()
  await waitFor(() => expect(window.api.setUsername).toHaveBeenCalledWith('alice'))
})

test('setAuthUsername is called with returned username after login', async () => {
  setupApi()
  await renderWizard(App)
  await submitAuth()
  await waitFor(() => expect(window.api.setAuthUsername).toHaveBeenCalledWith('alice'))
})

test('successful register calls window.api.register and advances to file-consent', async () => {
  setupApi()
  await renderWizard(App)
  await userEvent.click(screen.getByTestId('auth-tab-register'))
  await submitAuth('newuser', 'password123')
  expect(window.api.register).toHaveBeenCalledWith({ username: 'newuser', password: 'password123' })
  await waitFor(() =>
    expect(screen.getByTestId('file-consent-agree')).toBeInTheDocument()
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

// ── Step 3: ai-consent UI ─────────────────────────────────────────────────
test('ai-consent shows AI features description text', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  expect(screen.getByText(/automated bullet points/i)).toBeInTheDocument()
})

test('master external toggle starts unchecked on ai-consent step', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  expect(screen.getByTestId('consent-use-external')).not.toBeChecked()
})

test('submit button label changes to "Enable AI →" when toggle is checked', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  expect(screen.getByTestId('consent-submit')).toHaveTextContent(/skip/i)
  await userEvent.click(screen.getByTestId('consent-use-external'))
  expect(screen.getByTestId('consent-submit')).toHaveTextContent(/enable ai/i)
})

test('consent submit button is enabled by default', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  expect(screen.getByTestId('consent-submit')).not.toBeDisabled()
})

// ── Step 3: successful consent ────────────────────────────────────────────
test('calls giveConsent with correct payload when AI is skipped', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  await userEvent.click(screen.getByTestId('consent-submit'))
  await waitFor(() =>
    expect(screen.getByTestId('consent-success')).toBeInTheDocument()
  )
  expect(window.api.giveConsent).toHaveBeenCalledWith({
    consent_given:          true,
    use_external_services:  false,
    external_services:      {},
    default_ignore_patterns: [],
  })
})

test('calls giveConsent with AI services payload when AI is enabled', async () => {
  setupApi()
  await renderWizard(App)
  await advanceToAiConsent()
  await userEvent.click(screen.getByTestId('consent-use-external'))
  await userEvent.click(screen.getByTestId('consent-submit'))
  await waitFor(() =>
    expect(screen.getByTestId('consent-success')).toBeInTheDocument()
  )
  expect(window.api.giveConsent).toHaveBeenCalledWith({
    consent_given:          true,
    use_external_services:  true,
    external_services: {
      Gemini: { allowed: true },
      llm:    { allowed: true, model_preferences: ['Gemini 2.5 Flash (Google)'] },
    },
    default_ignore_patterns: [],
  })
})

// ── Step 3: failed consent ────────────────────────────────────────────────
test('shows error when giveConsent rejects', async () => {
  setupApi({
    giveConsent: jest.fn().mockRejectedValue(new Error('Server error')),
  })
  await renderWizard(App)
  await advanceToAiConsent()
  await userEvent.click(screen.getByTestId('consent-submit'))
  await waitFor(() =>
    expect(screen.getByTestId('consent-error')).toHaveTextContent('Server error')
  )
})
