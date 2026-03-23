/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from '../renderer/src/App.jsx'

const MOCK_PROFILE = {
  id: 1, user_id: 1,
  first_name: 'Alice', last_name: 'Smith',
  email: 'alice@example.com', phone: '555-0100',
  address: '123 Main St', city: 'Springfield',
  state: 'IL', zip_code: '62701',
  linkedin_url: 'https://linkedin.com/in/alice',
  github_username: 'alice',
  website: 'https://alice.dev',
  updated_at: '2024-01-01T00:00:00Z',
}

const BASE_API = {
  health: jest.fn().mockResolvedValue({ status: 'ok' }),
  getCurrentUser: jest.fn().mockResolvedValue({ username: 'alice' }),
  getLatestConsent: jest.fn().mockResolvedValue({ provider: 'openai' }),
  getAvailableServices: jest.fn().mockResolvedValue([]),
  giveConsent: jest.fn().mockResolvedValue({ status: 'ok' }),
  getLLMConfig: jest.fn().mockResolvedValue({ provider: 'openai' }),
  setAuthToken: jest.fn(), setAuthUsername: jest.fn(), setUsername: jest.fn(),
  clearCredentials: jest.fn(),
  getUsername: jest.fn().mockReturnValue('alice'),
  getProjects: jest.fn().mockResolvedValue([]),
  getSkills: jest.fn().mockResolvedValue([]),
  getWorkExperiences: jest.fn().mockResolvedValue([]),
  getResumes: jest.fn().mockResolvedValue([]),
  getProfile: jest.fn().mockRejectedValue(new Error('Profile not found (404)')),
  createProfile: jest.fn().mockResolvedValue(MOCK_PROFILE),
  updateProfile: jest.fn().mockResolvedValue(MOCK_PROFILE),
  getTutorialStatus: jest.fn().mockResolvedValue({ completed: true }),
  updateTutorialStatus: jest.fn().mockResolvedValue({ completed: true }),
}

async function boot(overrides = {}) {
  window.api = { ...BASE_API, ...overrides }
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  fireEvent.click(screen.getAllByRole('button').find(b => b.textContent.includes('Profile')))
  await waitFor(() => expect(screen.getByRole('heading', { name: /^profile$/i })).toBeInTheDocument())
}

beforeEach(() => { jest.clearAllMocks(); localStorage.clear() })

test('clicking Profile nav shows the heading', async () => {
  await boot()
  expect(screen.getByRole('heading', { name: /^profile$/i })).toBeInTheDocument()
})

test('shows empty state with Add button when no profile exists', async () => {
  await boot()
  await waitFor(() => expect(screen.getByText(/no profile yet/i)).toBeInTheDocument())
  expect(screen.getByRole('button', { name: /add profile/i })).toBeInTheDocument()
})

test('displays profile card when profile exists', async () => {
  await boot({ getProfile: jest.fn().mockResolvedValue(MOCK_PROFILE) })
  await waitFor(() => expect(screen.getByText('Alice Smith')).toBeInTheDocument())
  expect(screen.getByText('alice@example.com')).toBeInTheDocument()
  expect(screen.getByText('555-0100')).toBeInTheDocument()
  expect(screen.getByText('Springfield')).toBeInTheDocument()
  expect(screen.getByText('IL')).toBeInTheDocument()
})

test('"+ Add Profile" opens form; cancel hides it', async () => {
  await boot()
  await waitFor(() => expect(screen.getByRole('button', { name: /add profile/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /add profile/i }))
  expect(screen.getByPlaceholderText(/first name/i)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
  expect(screen.queryByPlaceholderText(/first name/i)).not.toBeInTheDocument()
})

test('Edit button opens form populated with data; cancel returns to card', async () => {
  await boot({ getProfile: jest.fn().mockResolvedValue(MOCK_PROFILE) })
  await waitFor(() => expect(screen.getByText('Alice Smith')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^edit$/i }))
  expect(screen.getByPlaceholderText(/first name/i).value).toBe('Alice')
  expect(screen.getByPlaceholderText(/last name/i).value).toBe('Smith')
  expect(screen.getByPlaceholderText(/email/i).value).toBe('alice@example.com')
  fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
  expect(screen.queryByPlaceholderText(/first name/i)).not.toBeInTheDocument()
  expect(screen.getByText('Alice Smith')).toBeInTheDocument()
})

test('submitting create form calls createProfile and shows card', async () => {
  await boot()
  await waitFor(() => expect(screen.getByRole('button', { name: /add profile/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /add profile/i }))
  fireEvent.change(screen.getByPlaceholderText(/first name/i), { target: { value: 'Alice' } })
  fireEvent.change(screen.getByPlaceholderText(/last name/i), { target: { value: 'Smith' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() =>
    expect(window.api.createProfile).toHaveBeenCalledWith('alice', expect.objectContaining({
      first_name: 'Alice', last_name: 'Smith',
    }))
  )
  await waitFor(() => expect(screen.getByText('Alice Smith')).toBeInTheDocument())
})

test('submitting edit form calls updateProfile and returns to card', async () => {
  const updated = { ...MOCK_PROFILE, first_name: 'Bob' }
  await boot({
    getProfile: jest.fn().mockResolvedValue(MOCK_PROFILE),
    updateProfile: jest.fn().mockResolvedValue(updated),
  })
  await waitFor(() => expect(screen.getByText('Alice Smith')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^edit$/i }))
  fireEvent.change(screen.getByPlaceholderText(/first name/i), { target: { value: 'Bob' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() =>
    expect(window.api.updateProfile).toHaveBeenCalledWith('alice', expect.objectContaining({
      first_name: 'Bob',
    }))
  )
  await waitFor(() => expect(screen.getByText('Bob Smith')).toBeInTheDocument())
})

test('shows validation error when first and last name are empty', async () => {
  await boot()
  await waitFor(() => expect(screen.getByRole('button', { name: /add profile/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /add profile/i }))
  fireEvent.submit(document.querySelector('form'))
  await waitFor(() => expect(screen.getByText(/first name and last name are required/i)).toBeInTheDocument())
})

test('shows API error when createProfile fails', async () => {
  await boot({ createProfile: jest.fn().mockRejectedValue(new Error('Server error')) })
  await waitFor(() => expect(screen.getByRole('button', { name: /add profile/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /add profile/i }))
  fireEvent.change(screen.getByPlaceholderText(/first name/i), { target: { value: 'Alice' } })
  fireEvent.change(screen.getByPlaceholderText(/last name/i), { target: { value: 'Smith' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() => expect(screen.getByText('Server error')).toBeInTheDocument())
})

test('shows error when getProfile fails with non-404 error', async () => {
  await boot({ getProfile: jest.fn().mockRejectedValue(new Error('Network error')) })
  await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument())
})

test('does not show error for 404 (no profile yet)', async () => {
  await boot()
  await waitFor(() => expect(screen.getByText(/no profile yet/i)).toBeInTheDocument())
  expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument()
})
