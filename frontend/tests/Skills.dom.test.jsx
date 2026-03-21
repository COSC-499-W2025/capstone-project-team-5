/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext.jsx'
import SkillsPage from '../renderer/src/pages/skills/SkillsPage.jsx'

const SKILLS = [
  { id: 1, name: 'React', skill_type: 'tool' },
  { id: 2, name: 'Code Review', skill_type: 'practice' },
  { id: 3, name: 'TypeScript', skill_type: 'tool' },
]

function renderSkillsPage({ apiOk = true, skillsPayload = [] } = {}) {
  window.api = {
    getSkills: jest.fn().mockResolvedValue(skillsPayload),
  }
  render(
    <AppContext.Provider value={{ apiOk }}>
      <SkillsPage />
    </AppContext.Provider>
  )
  return window.api
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

test('renders skills from paginated payload', async () => {
  const api = renderSkillsPage({
    skillsPayload: {
      items: SKILLS,
      pagination: { total: 3, limit: 50, offset: 0, has_more: false },
    },
  })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())
  expect(screen.getByText('Code Review')).toBeInTheDocument()
  expect(screen.getByText('TypeScript')).toBeInTheDocument()
  expect(api.getSkills).toHaveBeenCalledTimes(1)
})

test('renders skills from flat array payload', async () => {
  renderSkillsPage({ skillsPayload: SKILLS })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())
  expect(screen.getByText('TypeScript')).toBeInTheDocument()
})

test('renders empty state when no skills are returned', async () => {
  renderSkillsPage({
    skillsPayload: { items: [], pagination: { total: 0, limit: 50, offset: 0, has_more: false } },
  })
  await waitFor(() =>
    expect(screen.getByText(/No skills detected yet/i)).toBeInTheDocument()
  )
})

test('renders error message when api call fails', async () => {
  window.api = { getSkills: jest.fn().mockRejectedValue(new Error('Network error')) }
  render(
    <AppContext.Provider value={{ apiOk: true }}>
      <SkillsPage />
    </AppContext.Provider>
  )
  await waitFor(() => expect(screen.getByText(/Network error/i)).toBeInTheDocument())
})

test('does not call getSkills when apiOk is false', () => {
  const api = renderSkillsPage({ apiOk: false })
  expect(api.getSkills).not.toHaveBeenCalled()
})

// ---------------------------------------------------------------------------
// Type badges
// ---------------------------------------------------------------------------

test('displays correct type badges', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())
  // Two tools + one practice
  expect(screen.getAllByText('Tool')).toHaveLength(2)
  expect(screen.getAllByText('Practice')).toHaveLength(1)
})

// ---------------------------------------------------------------------------
// Sorting
// ---------------------------------------------------------------------------

test('renders skills sorted alphabetically', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())
  const cards = screen.getAllByText(/React|TypeScript|Code Review/)
  expect(cards.map((el) => el.textContent)).toEqual(['Code Review', 'React', 'TypeScript'])
})

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

test('filters skills by search query using includes', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.change(screen.getByPlaceholderText('Search skills…'), {
    target: { value: 'script' },
  })

  expect(screen.getByText('TypeScript')).toBeInTheDocument()
  expect(screen.queryByText('React')).not.toBeInTheDocument()
  expect(screen.queryByText('Code Review')).not.toBeInTheDocument()
})

test('search is case-insensitive', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.change(screen.getByPlaceholderText('Search skills…'), {
    target: { value: 'REACT' },
  })

  expect(screen.getByText('React')).toBeInTheDocument()
  expect(screen.queryByText('TypeScript')).not.toBeInTheDocument()
})

test('shows no-results empty state when search matches nothing', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.change(screen.getByPlaceholderText('Search skills…'), {
    target: { value: 'zzznomatch' },
  })

  expect(screen.getByText(/No skills match your search\./i)).toBeInTheDocument()
})

test('clear button resets search and restores all skills', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.change(screen.getByPlaceholderText('Search skills…'), {
    target: { value: 'react' },
  })
  expect(screen.queryByText('TypeScript')).not.toBeInTheDocument()

  fireEvent.click(screen.getByLabelText('Clear search'))
  expect(screen.getByText('TypeScript')).toBeInTheDocument()
  expect(screen.getByText('React')).toBeInTheDocument()
})

// ---------------------------------------------------------------------------
// Type filter tabs
// ---------------------------------------------------------------------------

test('type filter tabs show correct counts', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  // counts rendered as siblings inside each tab button — grab by role
  const allBtn = screen.getByRole('button', { name: /^All/ })
  const toolBtn = screen.getByRole('button', { name: /^Tools/ })
  const practiceBtn = screen.getByRole('button', { name: /^Practices/ })

  expect(allBtn.textContent).toMatch('3')
  expect(toolBtn.textContent).toMatch('2')
  expect(practiceBtn.textContent).toMatch('1')
})

test('filtering by Tools hides practices', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /^Tools/ }))

  expect(screen.getByText('React')).toBeInTheDocument()
  expect(screen.getByText('TypeScript')).toBeInTheDocument()
  expect(screen.queryByText('Code Review')).not.toBeInTheDocument()
})

test('filtering by Practices hides tools', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /^Practices/ }))

  expect(screen.getByText('Code Review')).toBeInTheDocument()
  expect(screen.queryByText('React')).not.toBeInTheDocument()
  expect(screen.queryByText('TypeScript')).not.toBeInTheDocument()
})

test('combined search and type filter shows correct empty message', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: /^Practices/ }))
  fireEvent.change(screen.getByPlaceholderText('Search skills…'), {
    target: { value: 'react' },
  })

  expect(screen.getByText(/No skills match your search and filter\./i)).toBeInTheDocument()
})

test('shows result count summary when search is active', async () => {
  renderSkillsPage({ skillsPayload: { items: SKILLS } })
  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())

  fireEvent.change(screen.getByPlaceholderText('Search skills…'), {
    target: { value: 'react' },
  })

  expect(screen.getByText(/Showing 1 of 3 skills/i)).toBeInTheDocument()
})