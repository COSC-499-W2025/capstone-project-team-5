/**
 * @jest-environment jsdom
 *
 * DOM tests for the ConsentSetup first-run wizard:
 *   - renders provider options from getAvailableServices
 *   - API key input appears only after a provider is selected
 *   - submit button is disabled until both provider + key are filled
 *   - successful submission calls giveConsent and triggers onDone
 *   - failed submission shows an error message
 *   - error from getAvailableServices shows a fallback message
 */

import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// We render App with consent = null so ConsentSetup is shown
function setupApi(overrides = {}) {
  window.api = {
    health:               jest.fn().mockResolvedValue({ status: 'ok' }),
    getCurrentUser:       jest.fn().mockResolvedValue({ username: 'alice' }),
    getLatestConsent:     jest.fn().mockResolvedValue(null),   // triggers ConsentSetup
    getAvailableServices: jest.fn().mockResolvedValue([
      { service_name: 'openai',    display_name: 'OpenAI',    description: 'GPT models'    },
      { service_name: 'anthropic', display_name: 'Anthropic', description: 'Claude models' },
    ]),
    giveConsent:  jest.fn().mockResolvedValue({ status: 'ok' }),
    getLLMConfig: jest.fn().mockResolvedValue({ provider: 'openai' }),
    getProjects:          jest.fn().mockResolvedValue([]),
    getSkills:            jest.fn().mockResolvedValue([]),
    getWorkExperiences:   jest.fn().mockResolvedValue([]),
    getResumes:           jest.fn().mockResolvedValue([]),
    ...overrides,
  }
}

// Helper: render App and wait for ConsentSetup to appear
async function renderConsent(App) {
  render(<App />)
  await waitFor(() =>
    expect(screen.getByText(/choose an AI provider/i)).toBeInTheDocument()
  )
}

let App
beforeAll(async () => {
  App = (await import('../renderer/src/App.jsx')).default
})

beforeEach(() => jest.clearAllMocks())

// ── Provider list ──────────────────────────────────────────────────────────
test('renders available service options', async () => {
  setupApi()
  await renderConsent(App)
  await waitFor(() => expect(screen.getByText('OpenAI')).toBeInTheDocument())
  expect(screen.getByText('Anthropic')).toBeInTheDocument()
  expect(screen.getByText('GPT models')).toBeInTheDocument()
})

test('shows loading text while services are fetching', async () => {
  setupApi({
    getAvailableServices: jest.fn(() => new Promise(() => {})), // never resolves
  })
  await renderConsent(App)
  expect(screen.getByText(/loading providers/i)).toBeInTheDocument()
})

test('shows error when getAvailableServices rejects', async () => {
  setupApi({
    getAvailableServices: jest.fn().mockRejectedValue(new Error('network')),
  })
  await renderConsent(App)
  await waitFor(() =>
    expect(screen.getByText(/could not load available services/i)).toBeInTheDocument()
  )
})

// ── API key field ──────────────────────────────────────────────────────────
test('API key input is not shown before a provider is selected', async () => {
  setupApi()
  await renderConsent(App)
  await waitFor(() => expect(screen.getByText('OpenAI')).toBeInTheDocument())
  expect(screen.queryByTestId('consent-api-key')).not.toBeInTheDocument()
})

test('API key input appears after selecting a provider', async () => {
  setupApi()
  await renderConsent(App)
  await waitFor(() => expect(screen.getByText('OpenAI')).toBeInTheDocument())

  const openaiRadio = screen.getByDisplayValue('openai')
  fireEvent.click(openaiRadio)

  expect(screen.getByTestId('consent-api-key')).toBeInTheDocument()
})

// ── Submit button state ────────────────────────────────────────────────────
test('submit button is disabled until provider and key are both filled', async () => {
  setupApi()
  await renderConsent(App)
  await waitFor(() => expect(screen.getByText('OpenAI')).toBeInTheDocument())

  const submitBtn = screen.getByTestId('consent-submit')
  expect(submitBtn).toBeDisabled()

  // Select provider
  fireEvent.click(screen.getByDisplayValue('openai'))
  expect(submitBtn).toBeDisabled()  // still disabled — no key

  // Type a key
  await userEvent.type(screen.getByTestId('consent-api-key'), 'sk-testkey')
  expect(submitBtn).not.toBeDisabled()
})

// ── Successful submission ──────────────────────────────────────────────────
test('calls giveConsent with correct payload and shows success', async () => {
  setupApi()
  await renderConsent(App)
  await waitFor(() => expect(screen.getByText('OpenAI')).toBeInTheDocument())

  fireEvent.click(screen.getByDisplayValue('openai'))
  await userEvent.type(screen.getByTestId('consent-api-key'), 'sk-mykey')
  fireEvent.click(screen.getByTestId('consent-submit'))

  await waitFor(() =>
    expect(screen.getByTestId('consent-success')).toBeInTheDocument()
  )

  expect(window.api.giveConsent).toHaveBeenCalledWith(
    expect.objectContaining({
      llm_provider: 'openai',
      api_key: 'sk-mykey',
    })
  )
})

// ── Failed submission ──────────────────────────────────────────────────────
test('shows error message when giveConsent rejects', async () => {
  setupApi({
    giveConsent: jest.fn().mockRejectedValue(new Error('Invalid API key')),
  })
  await renderConsent(App)
  await waitFor(() => expect(screen.getByText('OpenAI')).toBeInTheDocument())

  fireEvent.click(screen.getByDisplayValue('openai'))
  await userEvent.type(screen.getByTestId('consent-api-key'), 'bad-key')
  fireEvent.click(screen.getByTestId('consent-submit'))

  await waitFor(() =>
    expect(screen.getByTestId('consent-error')).toHaveTextContent('Invalid API key')
  )
})
