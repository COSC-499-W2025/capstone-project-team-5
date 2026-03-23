/**
 * @jest-environment jsdom
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext.jsx'
import ResumesPage from '../renderer/src/pages/resumes/ResumesPage.jsx'

const PROFILE = {
  id: 9,
  user_id: 3,
  first_name: 'Alice',
  last_name: 'Nguyen',
  email: 'alice@example.com',
}

const PROJECT_ONE = {
  id: 1,
  name: 'Portfolio Engine',
  rel_path: 'portfolio-engine',
  file_count: 12,
}

const PROJECT_TWO = {
  id: 2,
  name: 'Signal Board',
  rel_path: 'signal-board',
  file_count: 8,
}

const EXISTING_RESUME = {
  id: 77,
  resume_id: 5,
  project_id: 1,
  project_name: 'Portfolio Engine',
  rel_path: 'portfolio-engine',
  title: 'Portfolio Engine',
  description: 'Built with React, FastAPI.',
  analysis_snapshot: ['React', 'FastAPI'],
  bullet_points: ['Built a desktop portfolio workspace.'],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-05T00:00:00Z',
}

const ANALYSIS_RESULT = {
  name: 'Signal Board',
  language: 'TypeScript',
  framework: 'React',
  tools: ['Vite', 'Jest'],
  other_languages: ['SQL'],
  practices: ['Testing'],
  resume_bullets: ['Built a real-time board for monitoring deploy health.'],
  ai_bullets: [],
}

function createApi(overrides = {}) {
  return {
    getResumes: jest.fn().mockResolvedValue([]),
    getProfile: jest.fn().mockResolvedValue(PROFILE),
    getWorkExperiences: jest.fn().mockResolvedValue([{ id: 1 }]),
    getEducations: jest.fn().mockResolvedValue([{ id: 1 }]),
    getProjects: jest.fn().mockResolvedValue([PROJECT_ONE, PROJECT_TWO]),
    getLLMConfig: jest.fn().mockResolvedValue({ is_allowed: false, model_preferences: [] }),
    analyzeProject: jest.fn().mockResolvedValue(ANALYSIS_RESULT),
    createResume: jest.fn().mockResolvedValue({
      ...EXISTING_RESUME,
      project_id: 2,
      project_name: 'Signal Board',
      title: 'Signal Board',
      rel_path: 'signal-board',
      analysis_snapshot: ['TypeScript', 'React', 'Vite'],
      bullet_points: ['Built a real-time board for monitoring deploy health.'],
    }),
    updateResume: jest.fn().mockResolvedValue({
      ...EXISTING_RESUME,
      title: 'Updated Resume Entry',
      bullet_points: ['Updated bullet'],
    }),
    deleteResume: jest.fn().mockResolvedValue(null),
    downloadResumePdf: jest.fn().mockResolvedValue({
      bytes: new Uint8Array([1, 2, 3]).buffer,
      contentType: 'application/pdf',
      filename: 'alice_resume.pdf',
    }),
    ...overrides,
  }
}

function renderResumesPage(apiOverrides = {}) {
  window.api = createApi(apiOverrides)

  render(
    <AppContext.Provider
      value={{
        apiOk: true,
        user: { username: 'alice' },
      }}
    >
      <ResumesPage />
    </AppContext.Provider>
  )
}

function getProjectSelect() {
  return screen.getAllByRole('combobox')[0]
}

beforeEach(() => {
  jest.clearAllMocks()
  global.URL.createObjectURL = jest.fn(() => 'blob:resume-preview')
  global.URL.revokeObjectURL = jest.fn()
  localStorage.clear()
})

test('shows the empty state and keeps preview disabled until data is ready', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([]),
    getProfile: jest.fn().mockResolvedValue(null),
  })

  await waitFor(() =>
    expect(screen.getByText(/no resume entries yet/i)).toBeInTheDocument()
  )

  expect(screen.getByRole('button', { name: /preview pdf/i })).toBeDisabled()
  expect(screen.getByText(/create your profile before generating the pdf/i)).toBeInTheDocument()
})

test('creates a resume entry from project analysis with ai assist enabled', async () => {
  renderResumesPage({
    getLLMConfig: jest.fn().mockResolvedValue({
      is_allowed: true,
      model_preferences: ['Gemini 2.5 Flash (Google)'],
    }),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /\+ add resume entry/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /\+ add resume entry/i }))

  fireEvent.change(getProjectSelect(), { target: { value: '2' } })

  await waitFor(() =>
    expect(window.api.analyzeProject).toHaveBeenCalledWith(2, { useAi: true })
  )

  await waitFor(() =>
    expect(screen.getAllByDisplayValue('Signal Board').length).toBeGreaterThan(0)
  )

  fireEvent.click(screen.getByRole('button', { name: /save resume entry/i }))

  await waitFor(() =>
    expect(window.api.createResume).toHaveBeenCalledWith('alice', {
      project_id: 2,
      title: 'Signal Board',
      description: 'Built with TypeScript, React, Vite, Jest.',
      bullet_points: ['Built a real-time board for monitoring deploy health.'],
      analysis_snapshot: ['TypeScript', 'React', 'Vite', 'Jest', 'SQL', 'Testing'],
    })
  )

  await waitFor(() =>
    expect(screen.getAllByText('Signal Board').length).toBeGreaterThan(0)
  )
})

test('falls back to local analysis when ai assist fails', async () => {
  renderResumesPage({
    getLLMConfig: jest.fn().mockResolvedValue({ is_allowed: true, model_preferences: ['Gemini'] }),
    analyzeProject: jest
      .fn()
      .mockRejectedValueOnce(new Error('Provider unavailable'))
      .mockResolvedValueOnce(ANALYSIS_RESULT),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /\+ add resume entry/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /\+ add resume entry/i }))
  fireEvent.change(getProjectSelect(), { target: { value: '2' } })

  await waitFor(() =>
    expect(window.api.analyzeProject).toHaveBeenNthCalledWith(1, 2, { useAi: true })
  )
  await waitFor(() =>
    expect(window.api.analyzeProject).toHaveBeenNthCalledWith(2, 2, { useAi: false })
  )

  await waitFor(() =>
    expect(screen.getByText(/ai assist failed\. local analysis loaded instead\./i)).toBeInTheDocument()
  )
})

test('edits an existing resume entry', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /^edit$/i }))

  const titleInput = screen.getByDisplayValue('Portfolio Engine')
  fireEvent.change(titleInput, { target: { value: 'Updated Resume Entry' } })

  const bulletTextarea = screen.getByDisplayValue('Built a desktop portfolio workspace.')
  fireEvent.change(bulletTextarea, { target: { value: 'Updated bullet' } })

  fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

  await waitFor(() =>
    expect(window.api.updateResume).toHaveBeenCalledWith('alice', 1, {
      title: 'Updated Resume Entry',
      description: 'Built with React, FastAPI.',
      bullet_points: ['Updated bullet'],
      analysis_snapshot: ['React', 'FastAPI'],
    })
  )
})

test('deletes an existing resume entry after confirmation', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  fireEvent.click(screen.getByRole('button', { name: /^yes$/i }))

  await waitFor(() =>
    expect(window.api.deleteResume).toHaveBeenCalledWith('alice', 1)
  )
  await waitFor(() =>
    expect(screen.queryByText('Portfolio Engine')).not.toBeInTheDocument()
  )
})

test('hides already-used projects from the create form', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /\+ add resume entry/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /\+ add resume entry/i }))

  expect(screen.queryByRole('option', { name: 'Portfolio Engine' })).not.toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Signal Board' })).toBeInTheDocument()
})

test('generates and previews a pdf from saved entries', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /preview pdf/i })).toBeEnabled()
  )

  fireEvent.click(screen.getByRole('button', { name: /preview pdf/i }))

  await waitFor(() =>
    expect(window.api.downloadResumePdf).toHaveBeenCalledWith('alice', {
      template_name: 'jake',
    })
  )

  await waitFor(() =>
    expect(screen.getByText(/full preview of the generated resume document/i)).toBeInTheDocument()
  )
  expect(
    screen.getByRole('button', { name: /download pdf/i })
  ).toBeEnabled()
})

test('tab switcher toggles between entries and preview views', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByText('Built a desktop portfolio workspace.')).toBeInTheDocument()
  )

  // Entries tab is active by default — resume bullet visible
  expect(screen.getByRole('button', { name: /^entries$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^preview$/i })).toBeInTheDocument()

  // Switch to Preview tab
  fireEvent.click(screen.getByRole('button', { name: /^preview$/i }))

  // Resume cards should be gone, preview CTA visible
  expect(screen.queryByText('Built a desktop portfolio workspace.')).not.toBeInTheDocument()
  expect(screen.getByText(/no preview generated yet/i)).toBeInTheDocument()

  // Switch back to Entries tab
  fireEvent.click(screen.getByRole('button', { name: /^entries$/i }))
  expect(screen.getByText('Built a desktop portfolio workspace.')).toBeInTheDocument()
})

test('preview pdf auto-switches to the preview tab', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /preview pdf/i })).toBeEnabled()
  )

  // Should start on entries tab — bullet visible
  expect(screen.getByText('Built a desktop portfolio workspace.')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: /preview pdf/i }))

  // Should auto-switch to preview tab — bullet hidden
  await waitFor(() =>
    expect(screen.getByText(/full preview of the generated resume document/i)).toBeInTheDocument()
  )
  expect(screen.queryByText('Built a desktop portfolio workspace.')).not.toBeInTheDocument()
})

test('download pdf button works without previewing first', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /download pdf/i })).toBeEnabled()
  )

  fireEvent.click(screen.getByRole('button', { name: /download pdf/i }))

  await waitFor(() =>
    expect(window.api.downloadResumePdf).toHaveBeenCalledWith('alice', {
      template_name: 'jake',
    })
  )

  // Should have triggered a blob download
  expect(global.URL.createObjectURL).toHaveBeenCalled()
})

test('caches preview to localStorage and restores on remount', async () => {
  const { unmount } = render(
    <AppContext.Provider value={{ apiOk: true, user: { username: 'alice' } }}>
      <ResumesPage />
    </AppContext.Provider>
  )
  window.api = createApi({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  // Generate preview in a fresh render
  unmount()
  const { unmount: unmount2 } = render(
    <AppContext.Provider value={{ apiOk: true, user: { username: 'alice' } }}>
      <ResumesPage />
    </AppContext.Provider>
  )

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /preview pdf/i })).toBeEnabled()
  )

  fireEvent.click(screen.getByRole('button', { name: /preview pdf/i }))

  await waitFor(() =>
    expect(window.api.downloadResumePdf).toHaveBeenCalled()
  )

  // Verify something was cached
  expect(localStorage.getItem('resume_preview_alice')).not.toBeNull()

  // Unmount and remount to simulate navigation
  unmount2()
  render(
    <AppContext.Provider value={{ apiOk: true, user: { username: 'alice' } }}>
      <ResumesPage />
    </AppContext.Provider>
  )

  // Switch to preview tab — cached preview should show stale badge
  fireEvent.click(screen.getByRole('button', { name: /^preview$/i }))

  await waitFor(() =>
    expect(screen.getByText(/stale/i)).toBeInTheDocument()
  )
})

test('displays AI-generated badge when bullet_source is AI', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([
      { ...EXISTING_RESUME, bullet_source: 'AI' },
    ]),
  })

  await waitFor(() =>
    expect(screen.getByText('AI-generated')).toBeInTheDocument()
  )
})

test('displays Local analysis badge when bullet_source is Local', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([
      { ...EXISTING_RESUME, bullet_source: 'Local' },
    ]),
  })

  await waitFor(() =>
    expect(screen.getByText('Local analysis')).toBeInTheDocument()
  )
})

test('does not display bullet source badge when bullet_source is null', async () => {
  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getAllByText('Portfolio Engine').length).toBeGreaterThan(0)
  )

  expect(screen.queryByText('AI-generated')).not.toBeInTheDocument()
  expect(screen.queryByText('Local analysis')).not.toBeInTheDocument()
})

test('save payload includes bullet_source from analysis', async () => {
  renderResumesPage({
    analyzeProject: jest.fn().mockResolvedValue({
      ...ANALYSIS_RESULT,
      resume_bullet_source: 'Local',
    }),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /\+ add resume entry/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /\+ add resume entry/i }))
  fireEvent.change(getProjectSelect(), { target: { value: '2' } })

  await waitFor(() =>
    expect(window.api.analyzeProject).toHaveBeenCalled()
  )

  await waitFor(() =>
    expect(screen.getAllByDisplayValue('Signal Board').length).toBeGreaterThan(0)
  )

  fireEvent.click(screen.getByRole('button', { name: /save resume entry/i }))

  await waitFor(() =>
    expect(window.api.createResume).toHaveBeenCalledWith(
      'alice',
      expect.objectContaining({
        bullet_source: 'Local',
      })
    )
  )
})

test('full flow: analysis bullet_source flows to saved card display', async () => {
  const apiOverrides = {
    analyzeProject: jest.fn().mockResolvedValue({
      ...ANALYSIS_RESULT,
      resume_bullet_source: 'AI',
    }),
    createResume: jest.fn().mockResolvedValue({
      ...EXISTING_RESUME,
      project_id: 2,
      project_name: 'Signal Board',
      title: 'Signal Board',
      bullet_source: 'AI',
      bullet_points: ['Built a real-time board for monitoring deploy health.'],
    }),
  }

  renderResumesPage(apiOverrides)

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /\+ add resume entry/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /\+ add resume entry/i }))
  fireEvent.change(getProjectSelect(), { target: { value: '2' } })

  await waitFor(() =>
    expect(screen.getAllByDisplayValue('Signal Board').length).toBeGreaterThan(0)
  )

  fireEvent.click(screen.getByRole('button', { name: /save resume entry/i }))

  await waitFor(() =>
    expect(screen.getByText('AI-generated')).toBeInTheDocument()
  )
})

test('deleting all resume entries clears the cached preview', async () => {
  localStorage.setItem('resume_preview_alice', JSON.stringify({
    base64: btoa('fakepdf'),
    filename: 'test.pdf',
    contentType: 'application/pdf',
  }))

  renderResumesPage({
    getResumes: jest.fn().mockResolvedValue([EXISTING_RESUME]),
  })

  await waitFor(() =>
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument()
  )

  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
  fireEvent.click(screen.getByRole('button', { name: /^yes$/i }))

  await waitFor(() =>
    expect(window.api.deleteResume).toHaveBeenCalledWith('alice', 1)
  )

  // Cache should be cleared since all entries are gone
  expect(localStorage.getItem('resume_preview_alice')).toBeNull()
})
