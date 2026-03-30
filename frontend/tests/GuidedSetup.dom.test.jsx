/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext'

// Mock framer-motion
jest.mock('framer-motion', () => {
  const R = require('react')
  const MOTION_PROPS = [
    'initial', 'animate', 'exit', 'transition', 'whileHover', 'whileTap',
    'layoutId', 'layout', 'onHoverStart', 'onHoverEnd',
  ]
  const motion = new Proxy(
    {},
    {
      get: (_, tag) =>
        R.forwardRef((props, ref) => {
          const filtered = {}
          for (const [k, v] of Object.entries(props)) {
            if (!MOTION_PROPS.includes(k)) filtered[k] = v
          }
          return R.createElement(tag, { ...filtered, ref })
        }),
    }
  )
  return {
    motion,
    AnimatePresence: ({ children }) => children,
  }
})

import GuidedSetup from '../renderer/src/components/onboarding/GuidedSetup'

const CTX = { user: { username: 'testuser' }, apiOk: true }

function mockApi() {
  window.api = {
    getSetupStatus: jest.fn().mockResolvedValue({ completed: false, step: 0 }),
    updateSetupStatus: jest.fn().mockResolvedValue({}),
    getProfile: jest.fn().mockRejectedValue(new Error('not found')),
    getWorkExperiences: jest.fn().mockResolvedValue([]),
    getEducations: jest.fn().mockResolvedValue([]),
    getResumes: jest.fn().mockResolvedValue([]),
  }
}

function renderSetup(props = {}) {
  const setPage = props.setPage ?? jest.fn()
  const onComplete = props.onComplete ?? jest.fn()
  const onDismiss = props.onDismiss ?? jest.fn()
  const onSkip = props.onSkip ?? jest.fn()

  render(
    <AppContext.Provider value={CTX}>
      <GuidedSetup
        setPage={setPage}
        onComplete={onComplete}
        onDismiss={onDismiss}
        onSkip={onSkip}
      />
    </AppContext.Provider>
  )

  return { setPage, onComplete, onDismiss, onSkip }
}

beforeEach(() => {
  mockApi()
  jest.clearAllMocks()
})

test('renders step 0 message and navigates to profile page', async () => {
  const { setPage } = renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Let's start with your profile/)).toBeInTheDocument()
  })
  expect(setPage).toHaveBeenCalledWith('profile')
})

test('shows step counter', async () => {
  renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Step 1 of 7/)).toBeInTheDocument()
  })
})

test('dispatching event makes Continue button appear', async () => {
  renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Let's start with your profile/)).toBeInTheDocument()
  })

  // No Continue button initially
  expect(screen.queryByText('Continue →')).not.toBeInTheDocument()

  // Dispatch the profile-saved event
  act(() => {
    window.dispatchEvent(new CustomEvent('z2j:profile-saved'))
  })

  await waitFor(() => {
    expect(screen.getByText('Continue →')).toBeInTheDocument()
  })
})

test('clicking Continue advances to step 1', async () => {
  const { setPage } = renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Let's start with your profile/)).toBeInTheDocument()
  })

  act(() => {
    window.dispatchEvent(new CustomEvent('z2j:profile-saved'))
  })

  await waitFor(() => {
    expect(screen.getByText('Continue →')).toBeInTheDocument()
  })

  fireEvent.click(screen.getByText('Continue →'))

  await waitFor(() => {
    expect(screen.getByText(/work experience/)).toBeInTheDocument()
  })
  expect(setPage).toHaveBeenCalledWith('experience')
})

test('Skip button on skippable step advances to next step', async () => {
  // Start at step 1 (experience) by restoring from backend
  window.api.getSetupStatus.mockResolvedValue({ completed: false, step: 1 })

  renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/work experience/)).toBeInTheDocument()
  })

  fireEvent.click(screen.getByText('Skip'))

  await waitFor(() => {
    expect(screen.getByText(/education/i)).toBeInTheDocument()
  })
})

test('completion step shows Get Started button', async () => {
  // Jump to done step
  window.api.getSetupStatus.mockResolvedValue({ completed: false, step: 6 })

  const { onComplete } = renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/You did it/)).toBeInTheDocument()
  })

  fireEvent.click(screen.getByText('Get Started!'))
  expect(onComplete).toHaveBeenCalledTimes(1)
})

test('Escape calls onDismiss', async () => {
  const { onDismiss } = renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Let's start with your profile/)).toBeInTheDocument()
  })

  fireEvent.keyDown(window, { key: 'Escape' })
  expect(onDismiss).toHaveBeenCalledTimes(1)
})

test('Skip Setup calls onSkip', async () => {
  const { onSkip } = renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Let's start with your profile/)).toBeInTheDocument()
  })

  fireEvent.click(screen.getByText('Skip Setup'))
  expect(onSkip).toHaveBeenCalledTimes(1)
})

test('auto-marks step complete when API check passes', async () => {
  // Profile already exists
  window.api.getProfile.mockResolvedValue({ first_name: 'Jane', last_name: 'Doe' })

  renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/already done this/)).toBeInTheDocument()
  })
  expect(screen.getByText('Continue →')).toBeInTheDocument()
})

test('persists step to backend on advance', async () => {
  renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Let's start with your profile/)).toBeInTheDocument()
  })

  act(() => {
    window.dispatchEvent(new CustomEvent('z2j:profile-saved'))
  })

  await waitFor(() => {
    expect(screen.getByText('Continue →')).toBeInTheDocument()
  })

  fireEvent.click(screen.getByText('Continue →'))

  await waitFor(() => {
    expect(window.api.updateSetupStatus).toHaveBeenCalledWith({ step: 1 })
  })
})

test('restores step from backend on mount', async () => {
  window.api.getSetupStatus.mockResolvedValue({ completed: false, step: 3 })

  const { setPage } = renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Upload Project/)).toBeInTheDocument()
  })
  expect(setPage).toHaveBeenCalledWith('dashboard')
})

test('projects step does not show Continue until analysis-complete event fires', async () => {
  window.api.getSetupStatus.mockResolvedValue({ completed: false, step: 4 })

  renderSetup()
  await waitFor(() => {
    expect(screen.getByText(/Click on it and hit 'Analyze'/)).toBeInTheDocument()
  })

  // Continue should NOT be visible before analysis
  expect(screen.queryByText('Continue →')).not.toBeInTheDocument()

  // Dispatch analysis-complete event
  act(() => {
    window.dispatchEvent(new CustomEvent('z2j:analysis-complete'))
  })

  await waitFor(() => {
    expect(screen.getByText('Continue →')).toBeInTheDocument()
  })
})
