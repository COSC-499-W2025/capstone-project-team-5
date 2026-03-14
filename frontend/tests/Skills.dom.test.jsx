/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext.jsx'
import SkillsPage from '../renderer/src/pages/skills/SkillsPage.jsx'

function renderSkillsPage({ apiOk = true, skillsPayload = [] } = {}) {
  window.api = {
    getSkills: jest.fn().mockResolvedValue(skillsPayload),
  }

  render(
    <AppContext.Provider
      value={{
        apiOk,
      }}
    >
      <SkillsPage />
    </AppContext.Provider>
  )

  return window.api
}

test('renders skills from paginated payload', async () => {
  const api = renderSkillsPage({
    skillsPayload: {
      items: [
        { id: 2, name: 'React', skill_type: 'tool' },
        { id: 1, name: 'Code Review', skill_type: 'practice' },
      ],
      pagination: { total: 2, limit: 50, offset: 0, has_more: false },
    },
  })

  await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument())
  expect(screen.getByText('Code Review')).toBeInTheDocument()
  expect(screen.getByText('Tool')).toBeInTheDocument()
  expect(screen.getByText('Practice')).toBeInTheDocument()
  expect(api.getSkills).toHaveBeenCalledTimes(1)
})

test('renders empty state when no skills are returned', async () => {
  renderSkillsPage({
    skillsPayload: { items: [], pagination: { total: 0, limit: 50, offset: 0, has_more: false } },
  })

  await waitFor(() =>
    expect(screen.getByText(/No skills detected yet/i)).toBeInTheDocument()
  )
})
