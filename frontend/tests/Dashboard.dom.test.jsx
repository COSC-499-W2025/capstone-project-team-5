/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext.jsx'
import DashboardPage from '../renderer/src/pages/dashboard/DashboardPage.jsx'

function renderDashboard({
  user = null,
  apiOk = true,
  projectPayload = [],
  skillsPayload = [],
  experiencePayload = [],
  resumesPayload = [],
} = {}) {
  window.api = {
    getProjects: jest.fn().mockResolvedValue(projectPayload),
    getSkills: jest.fn().mockResolvedValue(skillsPayload),
    getWorkExperiences: jest.fn().mockResolvedValue(experiencePayload),
    getResumes: jest.fn().mockResolvedValue(resumesPayload),
    getUsername: jest.fn().mockReturnValue('alice'),
  }

  render(
    <AppContext.Provider
      value={{
        user,
        apiOk,
        setPage: jest.fn(),
        setUploadHighlights: jest.fn(),
      }}
    >
      <DashboardPage />
    </AppContext.Provider>
  )

  return window.api
}

test('shows project count on dashboard stats card', async () => {
  const api = renderDashboard({
    user: { username: 'alice' },
    projectPayload: { items: [{ id: 1 }, { id: 2 }, { id: 3 }] },
  })

  await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument())
  expect(api.getProjects).toHaveBeenCalledTimes(1)
})

test('shows project count even when user is not loaded yet', async () => {
  const api = renderDashboard({
    user: null,
    projectPayload: { items: [{ id: 1 }, { id: 2 }] },
  })

  await waitFor(() => expect(screen.getByText('2')).toBeInTheDocument())
  expect(api.getProjects).toHaveBeenCalledTimes(1)
})

test('still shows projects count when user-scoped APIs are unavailable', async () => {
  window.api = {
    getProjects: jest.fn().mockResolvedValue({ items: [{ id: 1 }] }),
    getSkills: jest.fn().mockResolvedValue([]),
    getUsername: jest.fn().mockReturnValue('alice'),
  }

  render(
    <AppContext.Provider
      value={{
        user: null,
        apiOk: true,
        setPage: jest.fn(),
        setUploadHighlights: jest.fn(),
      }}
    >
      <DashboardPage />
    </AppContext.Provider>
  )

  await waitFor(() => expect(screen.getByText('1')).toBeInTheDocument())
})

test('uses pagination total for projects card count', async () => {
  renderDashboard({
    user: { username: 'alice' },
    projectPayload: {
      items: [{ id: 1 }, { id: 2 }],
      pagination: { total: 5, limit: 2, offset: 0, has_more: true },
    },
  })

  await waitFor(() => expect(screen.getByText('5')).toBeInTheDocument())
})

test('uses pagination total for skills card count', async () => {
  renderDashboard({
    user: { username: 'alice' },
    projectPayload: { items: [], pagination: { total: 0, limit: 50, offset: 0, has_more: false } },
    skillsPayload: {
      items: [{ id: 1 }, { id: 2 }],
      pagination: { total: 6, limit: 2, offset: 0, has_more: true },
    },
  })

  await waitFor(() => expect(screen.getByText('6')).toBeInTheDocument())
})

test('shows experience card count from work experiences list', async () => {
  renderDashboard({
    user: { username: 'alice' },
    projectPayload: { items: [], pagination: { total: 0, limit: 50, offset: 0, has_more: false } },
    experiencePayload: [{ id: 1 }, { id: 2 }],
  })

  await waitFor(() => expect(screen.getByText('2')).toBeInTheDocument())
})

test('falls back to dash when projects API fails', async () => {
  window.api = {
    getProjects: jest.fn().mockRejectedValue(new Error('boom')),
    getSkills: jest.fn().mockResolvedValue([]),
    getWorkExperiences: jest.fn().mockResolvedValue([]),
    getResumes: jest.fn().mockResolvedValue([]),
    getUsername: jest.fn().mockReturnValue('alice'),
  }

  render(
    <AppContext.Provider
      value={{
        user: { username: 'alice' },
        apiOk: true,
        setPage: jest.fn(),
        setUploadHighlights: jest.fn(),
      }}
    >
      <DashboardPage />
    </AppContext.Provider>
  )

  await waitFor(() => expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1))
})

test('shows dashes for all cards when all counts are zero', async () => {
  renderDashboard({
    user: { username: 'alice' },
    projectPayload: { items: [], pagination: { total: 0, limit: 50, offset: 0, has_more: false } },
  })

  await waitFor(() => expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(4))
})

test('renders projects count under React StrictMode', async () => {
  window.api = {
    getProjects: jest.fn().mockResolvedValue({
      items: [{ id: 1 }, { id: 2 }, { id: 3 }],
      pagination: { total: 3, limit: 50, offset: 0, has_more: false },
    }),
    getSkills: jest.fn().mockResolvedValue([]),
    getWorkExperiences: jest.fn().mockResolvedValue([]),
    getResumes: jest.fn().mockResolvedValue([]),
    getUsername: jest.fn().mockReturnValue('alice'),
  }

  render(
    <React.StrictMode>
      <AppContext.Provider
        value={{
          user: { username: 'alice' },
          apiOk: true,
          setPage: jest.fn(),
          setUploadHighlights: jest.fn(),
        }}
      >
        <DashboardPage />
      </AppContext.Provider>
    </React.StrictMode>
  )

  await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument())
})
