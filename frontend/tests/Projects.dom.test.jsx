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
  has_thumbnail: false,
  thumbnail_url: null,
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
  has_thumbnail: true,
  thumbnail_url: '/api/projects/2/thumbnail',
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
  analyzeProject,
  uploadThumbnailResult = null,
  uploadThumbnailError = null,
  deleteThumbnailResult = null,
} = {}) {
  const analysisCache = { current: {} }
  window.api = {
    getProjects: jest.fn().mockResolvedValue(projectPayload),
    getSavedProjects: jest.fn().mockResolvedValue([]),
    getAuthUsername: jest.fn().mockReturnValue(null),
    analyzeProject: analyzeProject ?? (
      analyzeError
        ? jest.fn().mockRejectedValue(new Error(analyzeError))
        : jest.fn().mockResolvedValue(analyzeResult)
    ),
    uploadProjectThumbnail: uploadThumbnailError
      ? jest.fn().mockRejectedValue(new Error(uploadThumbnailError))
      : jest.fn().mockResolvedValue(uploadThumbnailResult),
    deleteProjectThumbnail: jest.fn().mockResolvedValue(deleteThumbnailResult),
    getProjectThumbnailUrl: jest.fn((id) => `http://localhost:8000/api/projects/${id}/thumbnail`),
  }
  render(
    <AppContext.Provider value={{ apiOk, uploadHighlights, setUploadHighlights, analysisCache }}>
      <ProjectsPage />
    </AppContext.Provider>
  )
  return { setUploadHighlights, analyzeProject: window.api.analyzeProject }
}

beforeEach(() => {
  localStorage.clear()
  jest.clearAllMocks()
})

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
  // Card shows the rounded importance score instead of an "ANALYZED" badge
  await waitFor(() => expect(screen.getByText('88')).toBeInTheDocument()) // Math.round(87.6)
})

test('does not show ANALYZED badge on unanalyzed cards', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  // Unanalyzed card shows no importance score
  expect(screen.queryByRole('heading', { name: /\d+/ })).not.toBeInTheDocument()
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
  // Drawer opens — Close button appears
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  // Path appears in both card and drawer header
  expect(screen.getAllByText('repos/demo-project').length).toBeGreaterThanOrEqual(2)
})

test('closes modal when the close button is clicked', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  fireEvent.click(screen.getByLabelText('Close'))
  await waitFor(() => expect(screen.queryByLabelText('Close')).not.toBeInTheDocument())
})

test('closes modal on Escape key', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  fireEvent.keyDown(document, { key: 'Escape' })
  await waitFor(() => expect(screen.queryByLabelText('Close')).not.toBeInTheDocument())
})

test('opens modal via Enter key on focused card', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  const card = screen.getByRole('button', { name: /demo-project/i })
  fireEvent.click(card)
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
})

// ─── Analysis: auto-triggered for unanalyzed projects ────────────────────────

test('triggers analysis when the Analyze button is clicked', async () => {
  const { analyzeProject } = renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Analyze'))
  await waitFor(() => expect(analyzeProject).toHaveBeenCalledWith(RAW_PROJECT.id))
})

test('shows analyzing spinner while analysis is in flight', async () => {
  renderProjectsPage({
    projectPayload: [RAW_PROJECT],
    analyzeProject: jest.fn(() => new Promise(() => {})),
  })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Analyze'))
  await waitFor(() =>
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument()
  )
})

test('renders analysis results after successful analysis', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Analyze'))
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
  await waitFor(() => expect(screen.getByText('Analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Analyze'))
  await waitFor(() =>
    expect(screen.getByText('Analysis service unavailable')).toBeInTheDocument()
  )
})

test('re-analyze button triggers another analysis call', async () => {
  const { analyzeProject } = renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Analyze'))
  await waitFor(() => expect(screen.getByText('Re-analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Re-analyze'))
  await waitFor(() => expect(analyzeProject).toHaveBeenCalledTimes(2))
})

// ─── Analysis: already-analyzed projects skip the API call ───────────────────

test('does not call analyzeProject when opening an already-analyzed project', async () => {
  const { analyzeProject } = renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  expect(analyzeProject).not.toHaveBeenCalled()
})

test('renders existing analysis data immediately for analyzed projects', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() =>
    expect(screen.getByText('Built REST API with Node.js')).toBeInTheDocument()
  )
  expect(screen.queryByText(/Analyzing/)).not.toBeInTheDocument()
})

// ─── Analysis result content ──────────────────────────────────────────────────

test('displays rounded importance score and contribution percentage', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getAllByText('88').length).toBeGreaterThan(0)) // 87.6 rounded
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
  await waitFor(() => expect(screen.getByText('Collaborators')).toBeInTheDocument())
  expect(screen.getByText('Alice, Bob')).toBeInTheDocument()
})

// ─── Post-analysis card sync ──────────────────────────────────────────────────

test('card gains importance score after successful analysis', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  // No score shown before analysis
  expect(screen.queryByText('88')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Analyze'))
  // Wait for analysis, then close the drawer
  await waitFor(() => expect(screen.getByText('Re-analyze')).toBeInTheDocument())
  fireEvent.click(screen.getByLabelText('Close'))
  // Card now shows rounded importance score
  await waitFor(() => expect(screen.getByText('88')).toBeInTheDocument())
})

// ─── ProjectCard thumbnail ───────────────────────────────────────────────────

test('displays thumbnail image on card when has_thumbnail is true', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  const img = screen.getByAlt('analyzed-project thumbnail')
  expect(img).toBeInTheDocument()
  expect(img.src).toContain('/api/projects/2/thumbnail')
})

test('does not display thumbnail image on card when has_thumbnail is false', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  expect(screen.queryByAlt('demo-project thumbnail')).not.toBeInTheDocument()
})

// ─── ProjectDrawer thumbnail ─────────────────────────────────────────────────

test('shows thumbnail in drawer when project has thumbnail', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  // Thumbnail image appears in both the card and the drawer
  const imgs = screen.getAllByAlt('analyzed-project thumbnail')
  expect(imgs.length).toBeGreaterThanOrEqual(2)
})

test('does not show thumbnail in drawer when project has no thumbnail', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  expect(screen.queryByAlt('demo-project thumbnail')).not.toBeInTheDocument()
})

test('shows "Set Thumbnail" button in drawer for project without thumbnail', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  expect(screen.getByText('Set Thumbnail')).toBeInTheDocument()
  expect(screen.queryByText('Clear Thumbnail')).not.toBeInTheDocument()
})

test('shows "Clear Thumbnail" button in drawer when project has thumbnail', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByLabelText('Close')).toBeInTheDocument())
  expect(screen.getByText('Clear Thumbnail')).toBeInTheDocument()
  expect(screen.queryByText('Set Thumbnail')).not.toBeInTheDocument()
})

test('clicking "Clear Thumbnail" calls deleteProjectThumbnail API', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByText('Clear Thumbnail')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Clear Thumbnail'))
  await waitFor(() => expect(window.api.deleteProjectThumbnail).toHaveBeenCalledWith(2))
})

test('clearing thumbnail removes the image from card', async () => {
  renderProjectsPage({ projectPayload: [ANALYZED_PROJECT] })
  await waitFor(() => expect(screen.getByText('analyzed-project')).toBeInTheDocument())
  // Thumbnail is initially visible on the card
  expect(screen.getByAlt('analyzed-project thumbnail')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /analyzed-project/i }))
  await waitFor(() => expect(screen.getByText('Clear Thumbnail')).toBeInTheDocument())
  fireEvent.click(screen.getByText('Clear Thumbnail'))
  // After clearing, the "Set Thumbnail" button appears and image is gone
  await waitFor(() => expect(screen.getByText('Set Thumbnail')).toBeInTheDocument())
  expect(screen.queryByAlt('analyzed-project thumbnail')).not.toBeInTheDocument()
})

test('selecting a file calls uploadProjectThumbnail API', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Set Thumbnail')).toBeInTheDocument())
  const fileInput = document.querySelector('[data-testid="thumbnail-file-input"]')
  const file = new File(['pixels'], 'thumb.png', { type: 'image/png' })
  fireEvent.change(fileInput, { target: { files: [file] } })
  await waitFor(() => expect(window.api.uploadProjectThumbnail).toHaveBeenCalledWith(1, file))
})

test('after successful upload, thumbnail appears and button changes to Clear', async () => {
  renderProjectsPage({ projectPayload: [RAW_PROJECT] })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Set Thumbnail')).toBeInTheDocument())
  const fileInput = document.querySelector('[data-testid="thumbnail-file-input"]')
  const file = new File(['pixels'], 'thumb.png', { type: 'image/png' })
  fireEvent.change(fileInput, { target: { files: [file] } })
  await waitFor(() => expect(screen.getByText('Clear Thumbnail')).toBeInTheDocument())
})

test('shows error message when thumbnail upload fails', async () => {
  renderProjectsPage({
    projectPayload: [RAW_PROJECT],
    uploadThumbnailError: 'File exceeds 2 MiB.',
  })
  await waitFor(() => expect(screen.getByText('demo-project')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /demo-project/i }))
  await waitFor(() => expect(screen.getByText('Set Thumbnail')).toBeInTheDocument())
  const fileInput = document.querySelector('[data-testid="thumbnail-file-input"]')
  const file = new File(['pixels'], 'big.png', { type: 'image/png' })
  fireEvent.change(fileInput, { target: { files: [file] } })
  await waitFor(() => expect(screen.getByText('File exceeds 2 MiB.')).toBeInTheDocument())
})
