/**
 * @jest-environment jsdom
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext.jsx'
import ProjectsPage from '../renderer/src/pages/projects/ProjectsPage.jsx'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const RAW_PROJECT = {
  id: 1,
  name: 'demo-project',
  rel_path: 'repos/demo-project',
  file_count: 4,
}

const ANALYZED_PROJECT = {
  ...RAW_PROJECT,
  id: 2,
  name: 'analyzed-project',
  rel_path: 'projects/analyzed-project',
  importance_score: 87.6,
  user_role: 'Full Stack Developer',
  user_contribution_percentage: 92.4,
  user_role_types: {
    primary_role: 'Full Stack Developer',
    secondary_roles: 'DevOps Engineer',
  },
  role_justification: 'Primary contributor across all layers.',
  score_breakdown: { complexity: 80, impact: 95 },
  resume_bullets: ['Built REST API with Node.js', 'Deployed to AWS'],
  ai_bullets: ['Led full-stack development'],
  ai_warning: null,
  language: 'JavaScript',
  framework: 'React',
  duration: '6 months',
  collaborators_display: 'Alice, Bob',
  created_at: '2024-01-15T00:00:00.000Z',
  skill_timeline: [{ date: '2024-01', skills: ['React', 'Node.js'] }],
}

const ANALYSIS_RESULT = {
  ...ANALYZED_PROJECT,
  id: 1,
  name: 'demo-project',
  rel_path: 'repos/demo-project',
}

// ─── Helper ───────────────────────────────────────────────────────────────────

function renderProjectsPage({
  apiOk = true,
  uploadHighlights = { created: [], merged: [] },
  setUploadHighlights = jest.fn(),
  projectPayload = [],
  analyzeResult = ANALYSIS_RESULT,
  analyzeError = null,
} = {}) {
  window.api = {
    getProjects: jest.fn().mockResolvedValue(projectPayload),
    analyzeProject: analyzeError
      ? jest.fn().mockRejectedValue(new Error(analyzeError))
      : jest.fn().mockResolvedValue(analyzeResult),
  }
  render(
    <AppContext.Provider value={{ apiOk, uploadHighlights, setUploadHighlights }}>
      <ProjectsPage />
    </AppContext.Provider>
  )
  return { setUploadHighlights, analyzeProject: window.api.analyzeProject }
}

test('clears project highlight when highlighted card is hovered', async () => {
  const { setUploadHighlights } = renderProjectsPage({
    uploadHighlights: { created: [1], merged: [] },
    projectPayload: [RAW_PROJECT],
  })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  const card = screen.getByText('demo-project').closest('.card')
  fireEvent.mouseEnter(card)
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

// ─── Card badge rendering ─────────────────────────────────────────────────────

test('shows ANALYZED badge on cards that already have analysis data', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('ANALYZED')).toBeInTheDocument())
})

test('does not show ANALYZED badge on unanalyzed cards', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  expect(screen.queryByText('ANALYZED')).not.toBeInTheDocument()
})

test('shows user_role in card footer when present', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() =>
    expect(screen.getByText('Full Stack Developer')).toBeInTheDocument()
  )
})

// ─── Modal opens and closes ───────────────────────────────────────────────────

test('opens modal when a project card is clicked', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() =>
    expect(screen.getByText('Project Path: repos/demo-project')).toBeInTheDocument()
  )
})

test('closes modal when the close button is clicked', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  fireEvent.click(screen.getByLabelText('Close'))
  await waitFor(() =>
    expect(screen.queryByText('Project Path: repos/demo-project')).not.toBeInTheDocument()
  )
})

test('closes modal on Escape key', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  fireEvent.keyDown(document, { key: 'Escape' })
  await waitFor(() =>
    expect(screen.queryByText('Project Path: repos/demo-project')).not.toBeInTheDocument()
  )
})

test('opens modal via Enter key on focused card', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  const card = screen.getByRole('button', { name: /demo-project/i })
  fireEvent.keyDown(card, { key: 'Enter' })
  await waitFor(() =>
    expect(screen.getByText('Project Path: repos/demo-project')).toBeInTheDocument()
  )
})

// ─── Analysis: auto-triggered for unanalyzed projects ────────────────────────

test('auto-triggers analysis when opening an unanalyzed project', async () => {
  const { analyzeProject } = renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(analyzeProject).toHaveBeenCalledWith(RAW_PROJECT.id))
})

test('shows analyzing spinner while analysis is in flight', async () => {
  // Never resolves during the test so we can assert the loading state
  window.api.analyzeProject = jest.fn(() => new Promise(() => {}))
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() =>
    expect(screen.getByText(/analyzing project/i)).toBeInTheDocument()
  )
})

test('renders analysis results after successful analysis', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() =>
    expect(screen.getByText('Built REST API with Node.js')).toBeInTheDocument()
  )
  expect(screen.getByText('Led full-stack development')).toBeInTheDocument()
})

test('shows error message when analysis fails', async () => {
  renderProjectsPage({
    projectPayload: [RAW_PROJECT],
    analyzeError: 'Analysis service unavailable',
  })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() =>
    expect(screen.getByText('Analysis service unavailable')).toBeInTheDocument()
  )
})

test('re-analyze button triggers another analysis call', async () => {
  const { analyzeProject } = renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Re-analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Re-analyze'))
  await waitFor(() => expect(analyzeProject).toHaveBeenCalledTimes(2))
})

// ─── Analysis: already-analyzed projects skip the API call ───────────────────

test('does not call analyzeProject when opening an already-analyzed project', async () => {
  const { analyzeProject } = renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() =>
    expect(screen.getByText('Project Path: projects/analyzed-project')).toBeInTheDocument()
  )
  expect(analyzeProject).not.toHaveBeenCalled()
})

test('renders existing analysis data immediately for analyzed projects', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() =>
    expect(screen.getByText('Built REST API with Node.js')).toBeInTheDocument()
  )
  expect(screen.queryByText(/analyzing project/i)).not.toBeInTheDocument()
})

// ─── Analysis result content ──────────────────────────────────────────────────

test('displays rounded importance score and contribution percentage', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByText('88')).toBeInTheDocument()) // 87.6 rounded
  expect(screen.getByText('92%')).toBeInTheDocument() // 92.4 rounded
})

test('displays primary and secondary roles', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  // primary_role also appears in the card footer so multiple matches are expected
  await waitFor(() =>
    expect(screen.getAllByText('Full Stack Developer').length).toBeGreaterThan(0)
  )
  // secondary_roles is rendered as the full string from the fixture
  expect(screen.getByText('DevOps Engineer')).toBeInTheDocument()
})

test('displays skill timeline entries', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  // 'React' also appears as the framework meta value, so multiple matches are valid
  await waitFor(() => expect(screen.getAllByText('React').length).toBeGreaterThan(0))
  expect(screen.getByText('Node.js')).toBeInTheDocument()
})

// ─── ProjectMeta layout ───────────────────────────────────────────────────────

test('renders collaborators_display in its own full-width row', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByText('COLLABORATORS')).toBeInTheDocument())
  expect(screen.getByText('Alice, Bob')).toBeInTheDocument()
})

// ─── Post-analysis card sync ──────────────────────────────────────────────────

test('card gains ANALYZED badge after successful analysis', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  expect(screen.queryByText('ANALYZED')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  // Wait for analysis to complete then close the modal
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  fireEvent.click(screen.getByLabelText('Close'))
  await waitFor(() => expect(screen.getByText('ANALYZED')).toBeInTheDocument())
})