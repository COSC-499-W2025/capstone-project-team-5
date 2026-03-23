/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from '../renderer/src/App.jsx'

const MOCK_EDU = {
  id: 1, user_id: 1, institution: 'MIT', degree: 'Bachelor of Science',
  field_of_study: 'Computer Science', gpa: 3.8,
  start_date: '2019-09-01', end_date: '2023-05-15',
  achievements: 'Dean\'s List', is_current: false,
  rank: 0, updated_at: '2023-05-15T00:00:00Z',
}
const MOCK_EDU_CURRENT = {
  id: 2, user_id: 1, institution: 'Stanford', degree: 'Master of Science',
  field_of_study: 'AI', gpa: 3.9,
  start_date: '2023-09-01', end_date: null,
  achievements: null, is_current: true,
  rank: 1, updated_at: '2024-01-01T00:00:00Z',
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
  getEducations: jest.fn().mockResolvedValue([]),
  createEducation: jest.fn().mockResolvedValue(MOCK_EDU),
  updateEducation: jest.fn().mockResolvedValue({ ...MOCK_EDU, degree: 'Bachelor of Arts' }),
  deleteEducation: jest.fn().mockResolvedValue(null),
  getResumes: jest.fn().mockResolvedValue([]),
  getTutorialStatus: jest.fn().mockResolvedValue({ completed: true }),
  updateTutorialStatus: jest.fn().mockResolvedValue({ completed: true }),
}

async function boot(overrides = {}) {
  window.api = { ...BASE_API, ...overrides }
  localStorage.setItem('zip2job_token', 'fake-token')
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  fireEvent.click(screen.getAllByRole('button').find(b => b.textContent.includes('Education')))
  await waitFor(() => expect(screen.getByRole('heading', { name: /^education$/i })).toBeInTheDocument())
}

beforeEach(() => { jest.clearAllMocks(); localStorage.clear() })

test('clicking Education nav shows the heading', async () => {
  await boot()
  expect(screen.getByRole('heading', { name: /^education$/i })).toBeInTheDocument()
})

test('shows empty state when user has no educations', async () => {
  await boot()
  await waitFor(() => expect(screen.getByText(/no education entries yet/i)).toBeInTheDocument())
})

test('displays education cards with Current tag', async () => {
  await boot({ getEducations: jest.fn().mockResolvedValue([MOCK_EDU, MOCK_EDU_CURRENT]) })
  await waitFor(() => expect(screen.getByText('Bachelor of Science')).toBeInTheDocument())
  expect(screen.getByText('MIT')).toBeInTheDocument()
  expect(screen.getByText('Master of Science')).toBeInTheDocument()
  expect(screen.getByText('Stanford')).toBeInTheDocument()
  expect(screen.getByText('Current')).toBeInTheDocument()
})

test('"+ Add Education" reveals form; cancel hides it', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add education/i }))
  expect(screen.getByPlaceholderText(/institution/i)).toBeInTheDocument()
  expect(screen.getByPlaceholderText(/degree/i)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
  expect(screen.queryByPlaceholderText(/institution/i)).not.toBeInTheDocument()
})

test('submitting the create form calls createEducation', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add education/i }))
  fireEvent.change(screen.getByPlaceholderText(/institution/i), { target: { value: 'MIT' } })
  fireEvent.change(screen.getByPlaceholderText(/degree/i), { target: { value: 'Bachelor of Science' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() =>
    expect(window.api.createEducation).toHaveBeenCalledWith('alice', expect.objectContaining({
      institution: 'MIT', degree: 'Bachelor of Science',
    }))
  )
})

test('shows form error when institution and degree are empty', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add education/i }))
  fireEvent.submit(document.querySelector('form'))
  await waitFor(() => expect(screen.getByText(/institution and degree are required/i)).toBeInTheDocument())
})

test('shows GPA validation error for invalid value', async () => {
  await boot()
  fireEvent.click(screen.getByRole('button', { name: /add education/i }))
  fireEvent.change(screen.getByPlaceholderText(/institution/i), { target: { value: 'MIT' } })
  fireEvent.change(screen.getByPlaceholderText(/degree/i), { target: { value: 'BS' } })
  fireEvent.change(screen.getByPlaceholderText(/gpa/i), { target: { value: '6.0' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() => expect(screen.getByText(/gpa must be between/i)).toBeInTheDocument())
})

test('shows API error when createEducation fails', async () => {
  await boot({ createEducation: jest.fn().mockRejectedValue(new Error('Validation error')) })
  fireEvent.click(screen.getByRole('button', { name: /add education/i }))
  fireEvent.change(screen.getByPlaceholderText(/institution/i), { target: { value: 'MIT' } })
  fireEvent.change(screen.getByPlaceholderText(/degree/i), { target: { value: 'BS' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() => expect(screen.getByText('Validation error')).toBeInTheDocument())
})

test('edit populates form and save calls updateEducation', async () => {
  await boot({ getEducations: jest.fn().mockResolvedValue([MOCK_EDU]) })
  await waitFor(() => expect(screen.getByText('Bachelor of Science')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^edit$/i }))
  expect(screen.getByPlaceholderText(/institution/i).value).toBe('MIT')
  fireEvent.change(screen.getByPlaceholderText(/degree/i), { target: { value: 'Bachelor of Arts' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
  await waitFor(() =>
    expect(window.api.updateEducation).toHaveBeenCalledWith('alice', MOCK_EDU.id, expect.objectContaining({
      degree: 'Bachelor of Arts',
    }))
  )
})

test('delete confirmation: confirm removes the card', async () => {
  await boot({ getEducations: jest.fn().mockResolvedValue([MOCK_EDU]) })
  await waitFor(() => expect(screen.getByText('Bachelor of Science')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
  const deleteButtons = screen.getAllByRole('button', { name: /^delete$/i })
  fireEvent.click(deleteButtons[deleteButtons.length - 1])
  await waitFor(() => expect(window.api.deleteEducation).toHaveBeenCalledWith('alice', MOCK_EDU.id))
  await waitFor(() => expect(screen.queryByText('Bachelor of Science')).not.toBeInTheDocument())
})

test('delete confirmation: Cancel cancels without deleting', async () => {
  await boot({ getEducations: jest.fn().mockResolvedValue([MOCK_EDU]) })
  await waitFor(() => expect(screen.getByText('Bachelor of Science')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
  expect(window.api.deleteEducation).not.toHaveBeenCalled()
  expect(screen.getByText('Bachelor of Science')).toBeInTheDocument()
})

test('shows error when getEducations fails', async () => {
  await boot({ getEducations: jest.fn().mockRejectedValue(new Error('Network error')) })
  await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument())
})

test('displays GPA and field of study on cards', async () => {
  await boot({ getEducations: jest.fn().mockResolvedValue([MOCK_EDU]) })
  await waitFor(() => expect(screen.getByText('Bachelor of Science')).toBeInTheDocument())
  expect(screen.getByText('Computer Science')).toBeInTheDocument()
  expect(screen.getByText('GPA 3.8')).toBeInTheDocument()
})
