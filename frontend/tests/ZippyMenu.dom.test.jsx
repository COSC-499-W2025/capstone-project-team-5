/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock framer-motion for jsdom
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

import ZippyMenu from '../renderer/src/components/onboarding/ZippyMenu'
import { PAGE_DESCRIPTIONS, DEFAULT_DESCRIPTION } from '../renderer/src/components/onboarding/pageDescriptions'

// ── Render helper ──────────────────────────────────────────────────────────
function renderMenu({ currentPage = 'dashboard', onStartTour, onStartSetup } = {}) {
  const startTour = onStartTour ?? jest.fn()
  const startSetup = onStartSetup ?? jest.fn()
  render(<ZippyMenu currentPage={currentPage} onStartTour={startTour} onStartSetup={startSetup} />)
  return { startTour, startSetup }
}

// ── Tests ──────────────────────────────────────────────────────────────────

test('renders the Zippy trigger button', () => {
  renderMenu()
  expect(screen.getByText('Zippy')).toBeInTheDocument()
})

test('popover is hidden initially', () => {
  renderMenu()
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('clicking trigger opens the popover with all options', () => {
  renderMenu()
  fireEvent.click(screen.getByText('Zippy'))
  expect(screen.getByRole('menu')).toBeInTheDocument()
  expect(screen.getByText('Explain this page')).toBeInTheDocument()
  expect(screen.getByText('Recommended Setup')).toBeInTheDocument()
  expect(screen.getByText('Start tour')).toBeInTheDocument()
})

test('"Start tour" calls onStartTour and closes the popover', () => {
  const { startTour } = renderMenu()
  fireEvent.click(screen.getByText('Zippy'))
  fireEvent.click(screen.getByText('Start tour'))
  expect(startTour).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('"Recommended Setup" calls onStartSetup and closes the popover', () => {
  const { startSetup } = renderMenu()
  fireEvent.click(screen.getByText('Zippy'))
  fireEvent.click(screen.getByText('Recommended Setup'))
  expect(startSetup).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('"Explain this page" shows the page description', () => {
  renderMenu({ currentPage: 'dashboard' })
  fireEvent.click(screen.getByText('Zippy'))
  fireEvent.click(screen.getByText('Explain this page'))
  expect(screen.getByText(PAGE_DESCRIPTIONS.dashboard.message)).toBeInTheDocument()
})

test('Back button returns to menu view', () => {
  renderMenu({ currentPage: 'projects' })
  fireEvent.click(screen.getByText('Zippy'))
  fireEvent.click(screen.getByText('Explain this page'))
  expect(screen.getByText(PAGE_DESCRIPTIONS.projects.message)).toBeInTheDocument()

  fireEvent.click(screen.getByText(/Back/))
  expect(screen.getByText('Explain this page')).toBeInTheDocument()
  expect(screen.getByText('Recommended Setup')).toBeInTheDocument()
  expect(screen.getByText('Start tour')).toBeInTheDocument()
})

test('Escape key closes the popover', () => {
  renderMenu()
  fireEvent.click(screen.getByText('Zippy'))
  expect(screen.getByRole('menu')).toBeInTheDocument()

  fireEvent.keyDown(window, { key: 'Escape' })
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('outside click closes the popover', () => {
  renderMenu()
  fireEvent.click(screen.getByText('Zippy'))
  expect(screen.getByRole('menu')).toBeInTheDocument()

  fireEvent.mouseDown(document.body)
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('shows fallback description for unknown page', () => {
  renderMenu({ currentPage: 'nonexistent' })
  fireEvent.click(screen.getByText('Zippy'))
  fireEvent.click(screen.getByText('Explain this page'))
  expect(screen.getByText(DEFAULT_DESCRIPTION.message)).toBeInTheDocument()
})

test('closing and reopening resets to menu view', () => {
  renderMenu()
  // Open and navigate to explain view
  fireEvent.click(screen.getByText('Zippy'))
  fireEvent.click(screen.getByText('Explain this page'))
  expect(screen.getByText(PAGE_DESCRIPTIONS.dashboard.message)).toBeInTheDocument()

  // Close via Escape
  fireEvent.keyDown(window, { key: 'Escape' })
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()

  // Reopen — should show menu, not explain
  fireEvent.click(screen.getByText('Zippy'))
  expect(screen.getByText('Explain this page')).toBeInTheDocument()
  expect(screen.getByText('Recommended Setup')).toBeInTheDocument()
  expect(screen.getByText('Start tour')).toBeInTheDocument()
})
