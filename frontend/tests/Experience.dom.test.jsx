/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from '../renderer/src/App.jsx'

const MOCK_EXP = {
  id: 1, user_id: 1, company: 'Acme Corp', title: 'Software Engineer',
  location: 'New York', start_date: '2023-01-15', end_date: '2024-06-01',
  description: 'Built cool things', bullets: null, is_current: false,
  rank: 0, updated_at: '2024-06-01T00:00:00Z',
}
const MOCK_EXP_CURRENT = {
  id: 2, user_id: 1, company: 'Globex', title: 'Senior Engineer',
  location: 'Remote', start_date: '2024-07-01', end_date: null,
  description: null, bullets: null, is_current: true,
  rank: 1, updated_at: '2024-07-01T00:00:00Z',
}

const BASE_API = {
  health: jest.fn().mockResolvedValue({ status: 'ok' }),
  getCurrentUser: jest.fn().mockResolvedValue({ username: 'alice' }),
  getLatestConsent: jest.fn().mockResolvedValue({ provider: 'openai' }),
  getAvailableServices: jest.fn().mockResolvedValue([]),
  giveConsent: jest.fn().mockResolvedValue({ status: 'ok' }),
  getLLMConfig: jest.fn().mockResolvedValue({ provider: 'openai' }),
  setAuthUsername: jest.fn(), setUsername: jest.fn(),
  getUsername: jest.fn().mockReturnValue('alice'),
  getProjects: jest.fn().mockResolvedValue([]),
  getSkills: jest.fn().mockResolvedValue([]),
  getWorkExperiences: jest.fn().mockResolvedValue([]),
  createWorkExperience: jest.fn().mockResolvedValue(MOCK_EXP),
  updateWorkExperience: jest.fn().mockResolvedValue({ ...MOCK_EXP, title: 'Lead Engineer' }),
  deleteWorkExperience: jest.fn().mockResolvedValue(null),
  getResumes: jest.fn().mockResolvedValue([]),
}

async function boot(overrides = {}) {
  window.api = { ...BASE_API, ...overrides }
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  fireEvent.click(screen.getAllByRole('button').find(b => b.textContent.includes('Experience')))
  await waitFor(() => expect(screen.getByRole('heading', { name: /^experience$/i })).toBeInTheDocument())
}

beforeEach(() => { jest.clearAllMocks(); localStorage.clear() })

test('clicking Experience nav shows the heading', async () => {
  await boot()
  expect(screen.getByRole('heading', { name: /^experience$/i })).toBeInTheDocument()
})

test('shows empty state when user has no experiences', async () => {
  await boot()
  await waitFor(() => expect(screen.getByText(/no experience entries yet/i)).toBeInTheDocument())
})

test('displays experience cards with Current tag', async () => {
  await boot({ getWorkExperiences: jest.fn().mockResolvedValue([MOCK_EXP, MOCK_EXP_CURRENT]) })
  await waitFor(() => expect(screen.getByText('Software Engineer')).toBeInTheDocument())
  expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  expect(screen.getByText('Senior Engineer')).toBeInTheDocument()
  expect(screen.getByText('Globex')).toBeInTheDocument()
  expect(screen.getByText('Current')).toBeInTheDocument()
})

test('"+ Add Experience" reveals form; cancel hides it', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add experience/i }))
  expect(screen.getByPlaceholderText(/company/i)).toBeInTheDocument()
  expect(screen.getByPlaceholderText(/title/i)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
  expect(screen.queryByPlaceholderText(/company/i)).not.toBeInTheDocument()
})

test('submitting the create form calls createWorkExperience', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add experience/i }))
  fireEvent.change(screen.getByPlaceholderText(/company/i), { target: { value: 'Acme Corp' } })
  fireEvent.change(screen.getByPlaceholderText(/title/i), { target: { value: 'Software Engineer' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() =>
    expect(window.api.createWorkExperience).toHaveBeenCalledWith('alice', expect.objectContaining({
      company: 'Acme Corp', title: 'Software Engineer',
    }))
  )
})

test('shows form error when company and title are empty', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add experience/i }))
  fireEvent.submit(document.querySelector('form'))
  await waitFor(() => expect(screen.getByText(/company and title are required/i)).toBeInTheDocument())
})

test('shows API error when createWorkExperience fails', async () => {
  await boot({ createWorkExperience: jest.fn().mockRejectedValue(new Error('Validation error')) })
  fireEvent.click(screen.getByRole('button', { name: /add experience/i }))
  fireEvent.change(screen.getByPlaceholderText(/company/i), { target: { value: 'Acme' } })
  fireEvent.change(screen.getByPlaceholderText(/title/i), { target: { value: 'Dev' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() => expect(screen.getByText('Validation error')).toBeInTheDocument())
})

test('edit populates form and save calls updateWorkExperience', async () => {
  await boot({ getWorkExperiences: jest.fn().mockResolvedValue([MOCK_EXP]) })
  await waitFor(() => expect(screen.getByText('Software Engineer')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^edit$/i }))
  expect(screen.getByPlaceholderText(/company/i).value).toBe('Acme Corp')
  fireEvent.change(screen.getByPlaceholderText(/title/i), { target: { value: 'Lead Engineer' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() =>
    expect(window.api.updateWorkExperience).toHaveBeenCalledWith('alice', MOCK_EXP.id, expect.objectContaining({
      title: 'Lead Engineer',
    }))
  )
})

test('delete confirmation: confirm removes the card', async () => {
  await boot({ getWorkExperiences: jest.fn().mockResolvedValue([MOCK_EXP]) })
  await waitFor(() => expect(screen.getByText('Software Engineer')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
  const deleteButtons = screen.getAllByRole('button', { name: /^delete$/i })
  fireEvent.click(deleteButtons[deleteButtons.length - 1])
  await waitFor(() => expect(window.api.deleteWorkExperience).toHaveBeenCalledWith('alice', MOCK_EXP.id))
  await waitFor(() => expect(screen.queryByText('Software Engineer')).not.toBeInTheDocument())
})

test('delete confirmation: Cancel cancels without deleting', async () => {
  await boot({ getWorkExperiences: jest.fn().mockResolvedValue([MOCK_EXP]) })
  await waitFor(() => expect(screen.getByText('Software Engineer')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
  expect(window.api.deleteWorkExperience).not.toHaveBeenCalled()
  expect(screen.getByText('Software Engineer')).toBeInTheDocument()
})

test('shows error when getWorkExperiences fails', async () => {
  await boot({ getWorkExperiences: jest.fn().mockRejectedValue(new Error('Network error')) })
  await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument())
})
