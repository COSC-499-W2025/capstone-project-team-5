import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Zippy from './Zippy'

const SIDEBAR_WIDTH = 220

const TOUR_STEPS = [
  {
    id: 'welcome',
    target: null,
    expression: 'wave',
    message:
      "Hey there! I'm Zippy, your guide to Zip2Job. I'll walk you through everything so you can turn your code into a killer resume. Let's go!",
  },
  {
    id: 'dashboard',
    target: 'dashboard',
    expression: 'pointing',
    message:
      'This is your command center! Upload a .zip of your code repo here to get started. Once uploaded, I\'ll analyze it and pull out the good stuff \u2014 languages, frameworks, and skills.',
  },
  {
    id: 'projects',
    target: 'projects',
    expression: 'excited',
    message:
      'All your uploaded projects show up here. Click on any project to edit its name, add a description, or re-run the analysis. You can also rank your projects by importance.',
  },
  {
    id: 'analyses',
    target: 'analyses',
    expression: 'happy',
    message:
      'This is where the magic happens! See exactly what was detected in your code \u2014 languages used, design patterns, complexity metrics. You can edit or tweak any analysis result.',
  },
  {
    id: 'skills',
    target: 'skills',
    expression: 'pointing',
    message:
      'Your skill inventory! Every technology and framework detected across all your projects gets collected here. These feed directly into your resume and portfolio.',
  },
  {
    id: 'experience',
    target: 'experience',
    expression: 'wave',
    message:
      'Add your work history \u2014 jobs, internships, co-ops. Include bullet points about what you did. These show up on your generated resume alongside your projects.',
  },
  {
    id: 'education',
    target: 'education',
    expression: 'excited',
    message:
      "Add your degrees, certifications, and coursework. Include your GPA if you'd like. This section goes right onto your resume.",
  },
  {
    id: 'profile',
    target: 'profile',
    expression: 'happy',
    message:
      "Fill this in first! Your name, email, phone, LinkedIn, and GitHub go here. Without a profile, resume PDF generation won't work.",
  },
  {
    id: 'portfolio',
    target: 'portfolio',
    expression: 'pointing',
    message:
      'Generate a portfolio website that showcases your top projects with descriptions, skills, and thumbnails. Perfect for sharing with recruiters.',
  },
  {
    id: 'resumes',
    target: 'resumes',
    expression: 'excited',
    message:
      'The grand finale! Pick a template, select your projects, and generate a polished PDF resume. AI can even write your bullet points if you enable it in Consents.',
  },
  {
    id: 'consents',
    target: 'consents',
    expression: 'wave',
    message:
      'Control your privacy here. Toggle AI features on or off, manage which external services can access your data, and set file ignore patterns.',
  },
  {
    id: 'done',
    target: 'zippy-tour',
    expression: 'thumbsup',
    message:
      "You're all set! Start by uploading a project on the Dashboard. I'll be right here in the sidebar if you ever want a refresher. Happy job hunting!",
  },
]

const TOTAL_TAB_STEPS = TOUR_STEPS.filter((s) => s.target && s.target !== 'zippy-tour').length

/* ── Spring presets ─────────────────────────────────────────────────── */
const springSnappy = { type: 'spring', stiffness: 400, damping: 30 }
const springBouncy = { type: 'spring', stiffness: 200, damping: 15 }
const springSmooth = { type: 'spring', stiffness: 300, damping: 25 }
const springPlayful = { type: 'spring', stiffness: 250, damping: 20 }

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

/* ── Hook: track a DOM element's rect ───────────────────────────────── */
function useTargetRect(targetId) {
  const [rect, setRect] = useState(null)

  const update = useCallback(() => {
    if (!targetId) {
      setRect(null)
      return
    }
    const el = document.querySelector(`[data-tour-id="${targetId}"]`)
    if (el) {
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      setRect(el.getBoundingClientRect())
    } else {
      setRect(null)
    }
  }, [targetId])

  useLayoutEffect(() => {
    update()
  }, [update])

  useEffect(() => {
    if (!targetId) return
    const onResize = () => update()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [targetId, update])

  return rect
}

export default function SpotlightTour({ onComplete, onSkip, onDismiss, setPage }) {
  const [step, setStep] = useState(0)
  const bubbleRef = useRef(null)
  const current = TOUR_STEPS[step]
  const rect = useTargetRect(current.target)

  // Track viewport size for centering calculations
  const [winSize, setWinSize] = useState(() => ({
    w: window.innerWidth,
    h: window.innerHeight,
  }))
  useEffect(() => {
    const onResize = () => setWinSize({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

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

  /* ── Positioning: center on content area, slide to sidebar for done ── */
  const WIDGET_W = 440
  const WIDGET_H = 260

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
      <AnimatePresence>
        {(isNavStep || isDone) && (
          <motion.div
            key="sidebar-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed top-0 left-0 z-[9999] pointer-events-none"
            style={{ width: SIDEBAR_WIDTH, height: '100vh' }}
          >
            {/* Light dim */}
            <div className="absolute inset-0 bg-black/30" />

            {/* Glowing highlight ring on nav item */}
            {rect && (
              <motion.div
                layoutId="spotlight-glow"
                className="absolute rounded-lg"
                style={{
                  top: rect.top - spotlightPad,
                  left: rect.left - spotlightPad,
                  width: rect.width + spotlightPad * 2,
                  height: rect.height + spotlightPad * 2,
                  border: '2px solid #f5a623',
                  boxShadow: '0 0 12px 2px rgba(245,166,35,0.5), inset 0 0 8px rgba(245,166,35,0.15)',
                  background: 'rgba(245,166,35,0.08)',
                  zIndex: 1,
                }}
                transition={springSnappy}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>

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

              <button
                type="button"
                onClick={next}
                className="btn-primary px-4 py-1.5 text-xs font-semibold"
              >
                {isLast ? 'Get Started!' : isFirst ? "Let's Go!" : 'Next \u2192'}
              </button>

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
                    Skip Tour
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
