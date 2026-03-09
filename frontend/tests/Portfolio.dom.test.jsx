/**
 * @jest-environment jsdom
 *
 * DOM tests for the PortfolioPage component:
 *   - navigating to Portfolio shows the list view
 *   - empty state message when no portfolios exist
 *   - "New Portfolio" button reveals the create form
 *   - submitting the form calls createPortfolio and adds card to list
 *   - clicking "View →" enters the detail view
 *   - detail view shows empty state when no items exist
 *   - detail view shows item cards when items exist
 *   - delete confirmation flow (Delete → Yes removes card)
 *   - API error is displayed in list view
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from '../renderer/src/App.jsx'

const MOCK_PORTFOLIO = { id: 1, name: 'My Portfolio', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }
const MOCK_ITEM = { id: 10, project_id: 5, title: 'Cool Project', markdown: '# Cool Project\n\nDoes cool things.', is_user_edited: false, source_analysis_id: null, portfolio_id: 1, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }
const MOCK_PROJECT = { id: 5, name: 'cool-project', rel_path: 'cool-project', file_count: 3 }

function setupApi(overrides = {}) {
  window.api = {
    health:                jest.fn().mockResolvedValue({ status: 'ok' }),
    getCurrentUser:        jest.fn().mockResolvedValue({ username: 'alice' }),
    getLatestConsent:      jest.fn().mockResolvedValue({ provider: 'openai' }),
    getAvailableServices:  jest.fn().mockResolvedValue([]),
    giveConsent:           jest.fn().mockResolvedValue({ status: 'ok' }),
    getLLMConfig:          jest.fn().mockResolvedValue({ provider: 'openai' }),
    setAuthUsername:       jest.fn(),
    setUsername:           jest.fn(),
    getUsername:           jest.fn().mockReturnValue('alice'),
    getProjects:           jest.fn().mockResolvedValue([]),
    getSkills:             jest.fn().mockResolvedValue([]),
    getWorkExperiences:    jest.fn().mockResolvedValue([]),
    getResumes:            jest.fn().mockResolvedValue([]),
    // Portfolio API
    getPortfolioByUser:    jest.fn().mockResolvedValue([]),
    getPortfolio:          jest.fn().mockResolvedValue([]),
    createPortfolio:       jest.fn().mockResolvedValue(MOCK_PORTFOLIO),
    deletePortfolio:       jest.fn().mockResolvedValue(null),
    addPortfolioItem:      jest.fn().mockResolvedValue(MOCK_ITEM),
    ...overrides,
  }
}

async function bootToPortfolioPage(overrides = {}) {
  setupApi(overrides)
  localStorage.setItem('zip2job_username', 'alice')
  render(<App />)
  // Wait for the shell to appear
  await waitFor(() => expect(screen.getByText('Portfolio Engine')).toBeInTheDocument())
  // Click Portfolio nav item
  const navButtons = screen.getAllByRole('button')
  const portfolioBtn = navButtons.find(b => b.textContent.includes('Portfolio'))
  fireEvent.click(portfolioBtn)
  // Wait for the portfolio page heading
  await waitFor(() => expect(screen.getByRole('heading', { name: /^portfolio$/i })).toBeInTheDocument())
}

beforeEach(() => {
  jest.clearAllMocks()
  localStorage.clear()
})

// ── Navigation ──────────────────────────────────────────────────────────────
test('clicking Portfolio nav shows the Portfolio list heading', async () => {
  await bootToPortfolioPage()
  expect(screen.getByRole('heading', { name: /^portfolio$/i })).toBeInTheDocument()
})

// ── Empty state ─────────────────────────────────────────────────────────────
test('shows empty state when user has no portfolios', async () => {
  await bootToPortfolioPage({ getPortfolioByUser: jest.fn().mockResolvedValue([]) })
  await waitFor(() =>
    expect(screen.getByText(/no portfolios yet/i)).toBeInTheDocument()
  )
})

// ── Create form ──────────────────────────────────────────────────────────────
test('"+ New Portfolio" button reveals the name input', async () => {
  await bootToPortfolioPage()
  const newBtn = screen.getByRole('button', { name: /new portfolio/i })
  fireEvent.click(newBtn)
  expect(screen.getByPlaceholderText(/portfolio name/i)).toBeInTheDocument()
})

test('submitting the create form calls createPortfolio and shows the new card', async () => {
  await bootToPortfolioPage()

  fireEvent.click(screen.getByRole('button', { name: /new portfolio/i }))

  const input = screen.getByPlaceholderText(/portfolio name/i)
  fireEvent.change(input, { target: { value: 'My Portfolio' } })

  const createBtn = screen.getByRole('button', { name: /^create$/i })
  fireEvent.click(createBtn)

  await waitFor(() =>
    expect(window.api.createPortfolio).toHaveBeenCalledWith({
      username: 'alice',
      name: 'My Portfolio',
    })
  )
  await waitFor(() =>
    expect(screen.getByText('My Portfolio')).toBeInTheDocument()
  )
})

test('shows form error when createPortfolio fails', async () => {
  await bootToPortfolioPage({
    createPortfolio: jest.fn().mockRejectedValue(new Error('Name too short')),
  })

  fireEvent.click(screen.getByRole('button', { name: /new portfolio/i }))
  fireEvent.change(screen.getByPlaceholderText(/portfolio name/i), { target: { value: 'X' } })
  fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

  await waitFor(() =>
    expect(screen.getByText('Name too short')).toBeInTheDocument()
  )
})

// ── Portfolio list ───────────────────────────────────────────────────────────
test('displays existing portfolios as cards', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
  })
  await waitFor(() =>
    expect(screen.getByText('My Portfolio')).toBeInTheDocument()
  )
  expect(screen.getByRole('button', { name: /view →/i })).toBeInTheDocument()
})

// ── Delete confirmation ──────────────────────────────────────────────────────
test('delete confirmation flow: Delete → Yes removes the card', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
  })
  await waitFor(() => expect(screen.getByText('My Portfolio')).toBeInTheDocument())

  // Click Delete to enter confirmation state
  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  expect(screen.getByText(/delete\?/i)).toBeInTheDocument()

  // Confirm with Yes
  fireEvent.click(screen.getByRole('button', { name: /^yes$/i }))

  await waitFor(() =>
    expect(window.api.deletePortfolio).toHaveBeenCalledWith(MOCK_PORTFOLIO.id)
  )
  await waitFor(() =>
    expect(screen.queryByText('My Portfolio')).not.toBeInTheDocument()
  )
})

test('delete confirmation: No cancels without deleting', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
  })
  await waitFor(() => expect(screen.getByText('My Portfolio')).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  fireEvent.click(screen.getByRole('button', { name: /^no$/i }))

  expect(window.api.deletePortfolio).not.toHaveBeenCalled()
  expect(screen.getByText('My Portfolio')).toBeInTheDocument()
})

// ── Detail view ──────────────────────────────────────────────────────────────
test('clicking "View →" enters the detail view with portfolio name as heading', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
    getPortfolio:       jest.fn().mockResolvedValue([]),
  })
  await waitFor(() => expect(screen.getByRole('button', { name: /view →/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /view →/i }))

  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /my portfolio/i })).toBeInTheDocument()
  )
})

test('detail view shows empty state when portfolio has no items', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
    getPortfolio:       jest.fn().mockResolvedValue([]),
  })
  await waitFor(() => expect(screen.getByRole('button', { name: /view →/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /view →/i }))

  await waitFor(() =>
    expect(screen.getByText(/no items yet/i)).toBeInTheDocument()
  )
})

test('detail view renders item cards', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
    getPortfolio:       jest.fn().mockResolvedValue([MOCK_ITEM]),
    getProjects:        jest.fn().mockResolvedValue([MOCK_PROJECT]),
  })
  await waitFor(() => expect(screen.getByRole('button', { name: /view →/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /view →/i }))

  await waitFor(() =>
    expect(screen.getByText('Cool Project')).toBeInTheDocument()
  )
})

test('back button returns to list view', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockResolvedValue([MOCK_PORTFOLIO]),
    getPortfolio:       jest.fn().mockResolvedValue([]),
  })
  await waitFor(() => expect(screen.getByRole('button', { name: /view →/i })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /view →/i }))
  await waitFor(() => expect(screen.getByRole('heading', { name: /my portfolio/i })).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /← back/i }))

  await waitFor(() =>
    expect(screen.getByRole('heading', { name: /^portfolio$/i })).toBeInTheDocument()
  )
})

// ── API error ────────────────────────────────────────────────────────────────
test('shows error message when getPortfolioByUser fails', async () => {
  await bootToPortfolioPage({
    getPortfolioByUser: jest.fn().mockRejectedValue(new Error('Network error')),
  })
  await waitFor(() =>
    expect(screen.getByText('Network error')).toBeInTheDocument()
  )
})
