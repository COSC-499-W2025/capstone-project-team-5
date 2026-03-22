import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Zippy from './Zippy'
import { PAGE_DESCRIPTIONS } from './pageDescriptions'
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

const TOUR_STEPS = [
  {
    id: 'welcome',
    target: null,
    expression: 'wave',
    message:
      "Hey there! I'm Zippy, your guide to Zip2Job! I can help you get started in two ways \u2014 take a quick tour of the app, or jump right into setting up your resume. You can always find me in the sidebar to do either one later!",
  },
  { id: 'dashboard', target: 'dashboard', ...PAGE_DESCRIPTIONS.dashboard },
  { id: 'projects', target: 'projects', ...PAGE_DESCRIPTIONS.projects },
  { id: 'analyses', target: 'analyses', ...PAGE_DESCRIPTIONS.analyses },
  { id: 'skills', target: 'skills', ...PAGE_DESCRIPTIONS.skills },
  { id: 'experience', target: 'experience', ...PAGE_DESCRIPTIONS.experience },
  { id: 'education', target: 'education', ...PAGE_DESCRIPTIONS.education },
  { id: 'profile', target: 'profile', ...PAGE_DESCRIPTIONS.profile },
  { id: 'portfolio', target: 'portfolio', ...PAGE_DESCRIPTIONS.portfolio },
  { id: 'resumes', target: 'resumes', ...PAGE_DESCRIPTIONS.resumes },
  { id: 'consents', target: 'consents', ...PAGE_DESCRIPTIONS.consents },
  {
    id: 'done',
    target: 'zippy-tour',
    expression: 'thumbsup',
    message:
      "You're all set! Start by uploading a project on the Dashboard. I'll be right here in the sidebar if you ever want a refresher. Happy job hunting!",
  },
]

const TOTAL_TAB_STEPS = TOUR_STEPS.filter((s) => s.target && s.target !== 'zippy-tour').length

/* ── Per-step Zippy poses (offsets relative to default position) ───── */
const ZIPPY_POSES = [
  { x: 0, y: 0, rotate: 0 },        // welcome: centered
  { x: 40, y: -10, rotate: 5 },      // dashboard: leans right
  { x: -60, y: 0, rotate: -8 },      // projects: peeks from left
  { x: 20, y: -15, rotate: 3 },      // analyses: bounces up-right
  { x: -40, y: 5, rotate: -5 },      // skills: leans left
  { x: 50, y: -5, rotate: 10 },      // experience: far right tilt
  { x: -20, y: -10, rotate: -3 },    // education: slight left up
  { x: 30, y: 0, rotate: 6 },        // profile: right
  { x: -50, y: -8, rotate: -10 },    // portfolio: far left peek
  { x: 10, y: -12, rotate: 2 },      // resumes: center-up
  { x: -30, y: 0, rotate: -4 },      // consents: left
  { x: 0, y: 0, rotate: 0 },         // done: back to center
]

export default function SpotlightTour({ onComplete, onSkip, onDismiss, onStartSetup, setPage, initialStep = 0 }) {
  const [step, setStep] = useState(initialStep)
  const bubbleRef = useRef(null)
  const current = TOUR_STEPS[step]
  const rect = useTargetRect(current.target)
  const winSize = useWindowSize()

  const isFirst = step === 0
  const isLast = step === TOUR_STEPS.length - 1
  const isDone = current.id === 'done'
  const isNavStep = current.target && !isDone

  const tabIndex = TOUR_STEPS.slice(0, step + 1).filter((s) => s.target && s.target !== 'zippy-tour').length
  const showCounter = isNavStep

  // Navigate to the page for the current step (skip for done/welcome)
  useEffect(() => {
    if (current.target && current.target !== 'zippy-tour' && setPage) {
      setPage(current.target)
    }
  }, [current.target, setPage])

  const next = useCallback(() => {
    if (isLast) {
      setPage('dashboard')
      onComplete()
    } else {
      setStep((s) => s + 1)
    }
  }, [isLast, onComplete, setPage])

  const prev = useCallback(() => {
    if (step > 0) setStep((s) => s - 1)
  }, [step])

  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape') {
        onSkip()
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault()
        next()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        prev()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [next, prev, onSkip])

  // Focus the bubble on step change for accessibility
  useEffect(() => {
    bubbleRef.current?.focus()
  }, [step])

  const spotlightPad = 6

  // Center of the content area (right of sidebar)
  const contentCenterL = SIDEBAR_WIDTH + (winSize.w - SIDEBAR_WIDTH) / 2 - WIDGET_W / 2
  const contentCenterT = winSize.h / 2 - WIDGET_H / 2

  // Welcome: bottom-right (before sliding to center)
  const welcomeL = winSize.w - WIDGET_W - 24
  const welcomeT = winSize.h - WIDGET_H - 24

  // Done: next to sidebar button
  const doneL = rect ? rect.right + 16 : SIDEBAR_WIDTH + 16
  const doneT = rect ? Math.max(16, rect.top - 220) : 100

  const getContainerAnimate = () => {
    if (isFirst) return { left: welcomeL, top: welcomeT }
    if (isDone) return { left: doneL, top: doneT }
    return { left: contentCenterL, top: contentCenterT }
  }

  return (
    <>
      {/* Sidebar overlay with accent glow on nav item */}
      <SidebarOverlay rect={rect} spotlightPad={spotlightPad} visible={isNavStep || isDone} />

      {/* Subtle scrim for welcome step only */}
      <AnimatePresence>
        {isFirst && (
          <motion.div
            key="welcome-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9998] bg-black/30"
          />
        )}
      </AnimatePresence>

      {/* Zippy + Speech bubble container */}
      <motion.div
        ref={bubbleRef}
        tabIndex={-1}
        className="outline-none"
        style={{ position: 'fixed', zIndex: 10000, maxWidth: WIDGET_W }}
        initial={{ left: welcomeL, top: welcomeT }}
        animate={getContainerAnimate()}
        transition={springSmooth}
        aria-modal="true"
        role="dialog"
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
            {/* Step counter */}
            {showCounter && (
              <div className="mb-2 font-mono text-2xs uppercase tracking-widest text-muted">
                {tabIndex} of {TOTAL_TAB_STEPS}
              </div>
            )}

            {/* Message */}
            <p className="text-sm leading-relaxed text-ink">{current.message}</p>

            {/* Controls */}
            <div className="mt-4 flex items-center gap-3">
              {step > 0 && (
                <button
                  type="button"
                  onClick={prev}
                  className="btn-ghost px-3 py-1.5 text-xs"
                >
                  &larr; Back
                </button>
              )}

              {isFirst ? (
                <>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="btn-primary px-4 py-1.5 text-xs font-semibold"
                  >
                    Take a Tour
                  </button>
                  {onStartSetup && (
                    <button
                      type="button"
                      onClick={onStartSetup}
                      className="btn-primary px-4 py-1.5 text-xs font-semibold"
                    >
                      Recommended Setup
                    </button>
                  )}
                </>
              ) : (
                <button
                  type="button"
                  onClick={next}
                  className="btn-primary px-4 py-1.5 text-xs font-semibold"
                >
                  {isLast ? 'Get Started!' : 'Next \u2192'}
                </button>
              )}

              <div className="ml-auto flex gap-3">
                {!isLast && (
                  <button
                    type="button"
                    onClick={onDismiss}
                    className="text-xs text-muted hover:text-ink transition-colors"
                  >
                    Show Again Later
                  </button>
                )}
                {!isLast && (
                  <button
                    type="button"
                    onClick={onSkip}
                    className="text-xs text-muted hover:text-ink transition-colors"
                  >
                    Skip
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Zippy character — hops around like a pet */}
        <motion.div
          className="flex justify-end pr-4"
          initial={{ scale: 0, rotate: -180 }}
          animate={{
            scale: 1,
            rotate: 0,
            x: ZIPPY_POSES[step]?.x ?? 0,
            y: ZIPPY_POSES[step]?.y ?? 0,
          }}
          transition={springPlayful}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          {/* Idle floating bob */}
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
