import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Zippy from './Zippy'
import { PAGE_DESCRIPTIONS, DEFAULT_DESCRIPTION } from './pageDescriptions'

const springSnappy = { type: 'spring', stiffness: 400, damping: 30 }

export default function ZippyMenu({ currentPage, onStartTour, onStartSetup }) {
  const [isOpen, setIsOpen] = useState(false)
  const [view, setView] = useState('menu') // 'menu' | 'explain'
  const [isHovered, setIsHovered] = useState(false)
  const popoverRef = useRef(null)
  const triggerRef = useRef(null)

  const close = useCallback(() => {
    setIsOpen(false)
    setView('menu')
  }, [])

  const toggle = useCallback(() => {
    // If GuidedSetup is minimized, restore it instead of opening popover
    if (window.__guidedSetupMinimized && window.__guidedSetupRestore) {
      window.__guidedSetupRestore()
      return
    }
    setIsOpen((prev) => {
      if (prev) setView('menu')
      return !prev
    })
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    function handleMouseDown(e) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target)
      ) {
        close()
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [isOpen, close])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    function handleKey(e) {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, close])

  const handleStartTour = useCallback(() => {
    close()
    onStartTour()
  }, [close, onStartTour])

  const handleStartSetup = useCallback(() => {
    close()
    onStartSetup?.()
  }, [close, onStartSetup])

  const handleExplain = useCallback(() => {
    setView('explain')
  }, [])

  const desc = PAGE_DESCRIPTIONS[currentPage] ?? DEFAULT_DESCRIPTION

  return (
    <div className="relative">
      {/* Trigger — slides right on hover */}
      <motion.button
        ref={triggerRef}
        type="button"
        data-tour-id="zippy-tour"
        onClick={toggle}
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        className={`mt-1 flex w-full items-center gap-1.5 font-mono text-2xs text-muted hover:text-ink transition-colors ${isHovered || isOpen ? 'justify-end' : 'justify-start'}`}
      >
        <motion.span layout className="flex items-center gap-1.5">
          <Zippy size="sm" /> {isHovered || isOpen ? 'How can I help :)' : 'Zippy'}
        </motion.span>
      </motion.button>

      {/* Popover flyout */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={popoverRef}
            initial={{ opacity: 0, x: -8, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -8, scale: 0.95 }}
            transition={springSnappy}
            className="fixed z-[9000] rounded-lg border border-border-hi bg-surface shadow-xl"
            style={{ left: 228, bottom: 48 }}
            role="menu"
            aria-label="Zippy menu"
          >
            <AnimatePresence mode="wait">
              {view === 'menu' ? (
                <motion.div
                  key="menu"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.15 }}
                  className="p-2"
                >
                  <button
                    type="button"
                    onClick={handleExplain}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-ink whitespace-nowrap hover:bg-border transition-colors"
                  >
                    <span className="flex w-5 items-center justify-center">
                      <Zippy size="sm" expression={desc.expression} />
                    </span>
                    Explain this page
                  </button>
                  {onStartSetup && (
                    <button
                      type="button"
                      onClick={handleStartSetup}
                      className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-ink whitespace-nowrap hover:bg-border transition-colors"
                    >
                      <span className="flex w-5 items-center justify-center text-accent text-xs">&#9881;</span>
                      Recommended Setup
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleStartTour}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-ink whitespace-nowrap hover:bg-border transition-colors"
                  >
                    <span className="flex w-5 items-center justify-center text-accent text-xs">&#9654;</span>
                    Start tour
                  </button>
                </motion.div>
              ) : (
                <motion.div
                  key="explain"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.15 }}
                  className="w-72 p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 pt-1">
                      <motion.div
                        animate={{ y: [0, -4, 0] }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                      >
                        <Zippy size="sm" expression={desc.expression} />
                      </motion.div>
                    </div>
                    <p className="text-sm leading-relaxed text-ink">{desc.message}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setView('menu')}
                    className="mt-3 btn-ghost px-3 py-1.5 text-xs"
                  >
                    &larr; Back
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
