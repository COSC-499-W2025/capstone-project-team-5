import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Zippy from './Zippy'
import { SETUP_STEPS, TOTAL_SETUP_STEPS } from './setupSteps'
import {
  SIDEBAR_WIDTH,
  WIDGET_W,
  WIDGET_H,
  springSmooth,
  springPlayful,
  useTargetRect,
  useWindowSize,
  SidebarOverlay,
} from './tourPrimitives'
import { useApp } from '../../app/context/AppContext'

export default function GuidedSetup({ setPage, onComplete, onDismiss, onSkip }) {
  const { user } = useApp()
  const [step, setStep] = useState(0)
  const [stepComplete, setStepComplete] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [alreadyDone, setAlreadyDone] = useState(false)
  const bubbleRef = useRef(null)

  const current = SETUP_STEPS[step]
  const rect = useTargetRect(current.page)
  const winSize = useWindowSize()
  const isDone = current.id === 'done'
  const isInfoStep = current.hasScrim
  const spotlightPad = 6

  // Restore saved step from backend on mount
  useEffect(() => {
    window.api.getSetupStatus().then((status) => {
      if (status?.step > 0 && status.step < TOTAL_SETUP_STEPS) {
        setStep(status.step)
      }
    }).catch(() => {})
  }, [])

  // Navigate to the step's page
  useEffect(() => {
    if (current.page && setPage) {
      setPage(current.page)
    }
  }, [current.page, setPage])

  // Check if step is already complete on entry
  useEffect(() => {
    setStepComplete(false)
    setAlreadyDone(false)

    if (current.checkComplete && user?.username) {
      current.checkComplete(user.username).then((done) => {
        if (done) {
          setStepComplete(true)
          setAlreadyDone(true)
        }
      })
    }
  }, [step, current, user?.username])

  // Listen for CustomEvent completion
  useEffect(() => {
    if (!current.event) return

    const handler = () => {
      // Auto-advance on upload complete since the app navigates away
      if (current.id === 'upload') {
        setStep((s) => s + 1)
      } else {
        setStepComplete(true)
      }
    }
    window.addEventListener(current.event, handler)
    return () => window.removeEventListener(current.event, handler)
  }, [current.event, current.id])

  // Persist step to backend
  useEffect(() => {
    window.api.updateSetupStatus({ step }).catch(() => {})
  }, [step])

  // Focus bubble on step change
  useEffect(() => {
    if (!minimized) bubbleRef.current?.focus()
  }, [step, minimized])

  // Keyboard handler
  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape') onDismiss()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onDismiss])

  const advance = useCallback(() => {
    if (step >= TOTAL_SETUP_STEPS - 1) {
      onComplete()
    } else {
      setStep((s) => s + 1)
    }
  }, [step, onComplete])

  const skipStep = useCallback(() => {
    setStep((s) => s + 1)
  }, [])

  // Position: bottom-right for interactive steps, centered for completion
  const bubbleL = isDone
    ? SIDEBAR_WIDTH + (winSize.w - SIDEBAR_WIDTH) / 2 - WIDGET_W / 2
    : winSize.w - WIDGET_W - 32
  const bubbleT = isDone
    ? winSize.h / 2 - WIDGET_H / 2
    : winSize.h - WIDGET_H - 32

  const message = alreadyDone
    ? "Looks like you've already done this! Let's move on."
    : current.message

  // Expose minimized state for parent to pass to ZippyMenu
  useEffect(() => {
    window.__guidedSetupMinimized = minimized
    window.__guidedSetupRestore = () => setMinimized(false)
    return () => {
      delete window.__guidedSetupMinimized
      delete window.__guidedSetupRestore
    }
  }, [minimized])

  if (minimized) return null

  return (
    <>
      {/* Sidebar overlay */}
      <SidebarOverlay rect={rect} spotlightPad={spotlightPad} visible />

      {/* Scrim for info-only steps */}
      <AnimatePresence>
        {isInfoStep && (
          <motion.div
            key="setup-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9998] bg-black/30 pointer-events-none"
            style={{ left: SIDEBAR_WIDTH }}
          />
        )}
      </AnimatePresence>

      {/* Zippy + Speech bubble */}
      <motion.div
        ref={bubbleRef}
        tabIndex={-1}
        className="outline-none pointer-events-auto"
        style={{ position: 'fixed', zIndex: 10000, maxWidth: WIDGET_W }}
        initial={{ left: bubbleL, top: bubbleT, opacity: 0, scale: 0.9 }}
        animate={{ left: bubbleL, top: bubbleT, opacity: 1, scale: 1 }}
        transition={springSmooth}
        role="dialog"
        aria-label="Guided setup"
      >
        {/* Speech bubble */}
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={springSmooth}
            className="rounded-lg border border-border-hi bg-surface p-5 shadow-xl mb-3"
          >
            {/* Header with step counter + minimize */}
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-2xs uppercase tracking-widest text-muted">
                Step {step + 1} of {TOTAL_SETUP_STEPS}
              </span>
              <button
                type="button"
                onClick={() => setMinimized(true)}
                className="text-muted hover:text-ink text-xs transition-colors"
                title="Minimize"
              >
                &mdash;
              </button>
            </div>

            {/* Message */}
            <p className="text-sm leading-relaxed text-ink">{message}</p>

            {/* Controls */}
            <div className="mt-4 flex items-center gap-3">
              {/* Continue / Next button — visible when step is complete or info step */}
              {(stepComplete || isInfoStep) && (
                <button
                  type="button"
                  onClick={advance}
                  className="btn-primary px-4 py-1.5 text-xs font-semibold"
                >
                  {isDone ? 'Get Started!' : 'Continue \u2192'}
                </button>
              )}

              {/* Skip button for skippable steps */}
              {current.skippable && !stepComplete && (
                <button
                  type="button"
                  onClick={skipStep}
                  className="btn-ghost px-3 py-1.5 text-xs"
                >
                  Skip
                </button>
              )}

              <div className="ml-auto flex gap-3">
                <button
                  type="button"
                  onClick={onDismiss}
                  className="text-xs text-muted hover:text-ink transition-colors"
                >
                  Show Again Later
                </button>
                <button
                  type="button"
                  onClick={onSkip}
                  className="text-xs text-muted hover:text-ink transition-colors"
                >
                  Skip Setup
                </button>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Zippy character */}
        <motion.div
          className="flex justify-end pr-4"
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={springPlayful}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          <motion.div
            animate={{ y: [0, -6, 0], rotate: [0, 2, -2, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Zippy size="lg" expression={current.expression} />
          </motion.div>
        </motion.div>
      </motion.div>
    </>
  )
}
