import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

/* ── Constants ─────────────────────────────────────────────────────── */
export const SIDEBAR_WIDTH = 220
export const WIDGET_W = 440
export const WIDGET_H = 260

/* ── Spring presets ────────────────────────────────────────────────── */
export const springSnappy = { type: 'spring', stiffness: 400, damping: 30 }
export const springBouncy = { type: 'spring', stiffness: 200, damping: 15 }
export const springSmooth = { type: 'spring', stiffness: 300, damping: 25 }
export const springPlayful = { type: 'spring', stiffness: 250, damping: 20 }

/* ── Hook: track a DOM element's rect by data-tour-id ──────────────── */
export function useTargetRect(targetId) {
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

/* ── Hook: track viewport size ─────────────────────────────────────── */
export function useWindowSize() {
  const [winSize, setWinSize] = useState(() => ({
    w: window.innerWidth,
    h: window.innerHeight,
  }))
  useEffect(() => {
    const onResize = () => setWinSize({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return winSize
}

/* ── SidebarOverlay: dim sidebar + glowing highlight ring ──────────── */
export function SidebarOverlay({ rect, spotlightPad = 6, visible }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="sidebar-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed top-0 left-0 z-[9999] pointer-events-none"
          style={{ width: SIDEBAR_WIDTH, height: '100vh' }}
        >
          <div className="absolute inset-0 bg-black/30" />

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
  )
}
