/**
 * @jest-environment jsdom
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext.jsx'
import ProjectsPage from '../renderer/src/pages/projects/ProjectsPage.jsx'

function renderProjectsPage({
  apiOk = true,
  uploadHighlights = { created: [], merged: [] },
  setUploadHighlights = jest.fn(),
  projectPayload = [],
} = {}) {
  window.api = {
    getProjects: jest.fn().mockResolvedValue(projectPayload),
  }

  render(
    <AppContext.Provider
      value={{
        apiOk,
        uploadHighlights,
        setUploadHighlights,
      }}
    >
      <ProjectsPage />
    </AppContext.Provider>
  )

  return { setUploadHighlights }
}

test('clears project highlight when highlighted card is hovered', async () => {
  const { setUploadHighlights } = renderProjectsPage({
    uploadHighlights: { created: [1], merged: [] },
    projectPayload: [{ id: 1, name: 'demo-project', rel_path: 'demo-project', file_count: 4 }],
  })

  await waitFor(() => expect(screen.getAllByText('demo-project').length).toBeGreaterThan(0))

  const [projectTitle] = screen.getAllByText('demo-project')
  fireEvent.mouseEnter(projectTitle.closest('.card'))

  expect(setUploadHighlights).toHaveBeenCalledTimes(1)

  const updateHighlights = setUploadHighlights.mock.calls[0][0]
  expect(updateHighlights({ created: [1], merged: [] })).toEqual({
    created: [],
    merged: [],
  })
})

test('normalizes object payloads with items arrays', async () => {
  renderProjectsPage({
    projectPayload: {
      items: [{ id: 2, name: 'wrapped-project', rel_path: 'wrapped', file_count: 2 }],
    },
  })

  await waitFor(() => expect(screen.getByText('wrapped-project')).toBeInTheDocument())
})
