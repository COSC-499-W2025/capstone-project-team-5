import { useCallback, useEffect, useRef, useState } from 'react'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

const ZOOM_STEPS = [0.5, 0.65, 0.75, 0.85, 1, 1.25, 1.5, 2]
const DEFAULT_ZOOM_INDEX = 2 // 0.75

export default function PdfViewer({ pdfBytes, className = '' }) {
  const containerRef = useRef(null)
  const pdfDocRef = useRef(null)
  const [rendering, setRendering] = useState(false)
  const [error, setError] = useState('')
  const [zoomIndex, setZoomIndex] = useState(DEFAULT_ZOOM_INDEX)
  const [pageCount, setPageCount] = useState(0)

  const zoomLevel = ZOOM_STEPS[zoomIndex]

  const renderPages = useCallback(async (signal) => {
    const doc = pdfDocRef.current
    const container = containerRef.current
    if (!doc || !container) return

    setRendering(true)
    setError('')
    container.innerHTML = ''

    try {
      for (let i = 1; i <= doc.numPages; i++) {
        if (signal.cancelled) break

        const page = await doc.getPage(i)
        const unscaledViewport = page.getViewport({ scale: 1 })
        const containerWidth = container.clientWidth - 32
        const fitScale = containerWidth / unscaledViewport.width
        const scale = fitScale * zoomLevel
        const viewport = page.getViewport({ scale })

        const canvas = document.createElement('canvas')
        canvas.width = viewport.width * window.devicePixelRatio
        canvas.height = viewport.height * window.devicePixelRatio
        canvas.style.width = `${viewport.width}px`
        canvas.style.height = `${viewport.height}px`
        canvas.className = 'mx-auto'

        if (i > 1) {
          const spacer = document.createElement('div')
          spacer.className = 'h-4'
          container.appendChild(spacer)
        }

        container.appendChild(canvas)

        const ctx = canvas.getContext('2d')
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

        await page.render({ canvasContext: ctx, viewport }).promise
      }
    } catch (err) {
      if (!signal.cancelled) {
        setError(err?.message || 'Failed to render PDF.')
      }
    } finally {
      if (!signal.cancelled) setRendering(false)
    }
  }, [zoomLevel])

  // Load PDF document when bytes change
  useEffect(() => {
    if (!pdfBytes) return

    let cancelled = false

    async function load() {
      setRendering(true)
      setError('')

      try {
        if (pdfDocRef.current) {
          pdfDocRef.current.destroy()
          pdfDocRef.current = null
        }

        const source = pdfBytes instanceof ArrayBuffer ? pdfBytes : pdfBytes.buffer ?? pdfBytes
        const data = new Uint8Array(source.slice(0))
        const doc = await pdfjsLib.getDocument({ data }).promise

        if (cancelled) {
          doc.destroy()
          return
        }

        pdfDocRef.current = doc
        setPageCount(doc.numPages)

        await renderPages({ cancelled: false })
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Failed to render PDF.')
          setRendering(false)
        }
      }
    }

    load()

    return () => {
      cancelled = true
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy()
        pdfDocRef.current = null
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdfBytes])

  // Re-render when zoom changes (but not on initial load)
  useEffect(() => {
    if (!pdfDocRef.current) return

    const signal = { cancelled: false }
    renderPages(signal)

    return () => {
      signal.cancelled = true
    }
  }, [zoomLevel, renderPages])

  if (!pdfBytes) return null

  const canZoomOut = zoomIndex > 0
  const canZoomIn = zoomIndex < ZOOM_STEPS.length - 1
  const zoomPercent = Math.round(zoomLevel * 100)

  return (
    <div className={className}>
      {/* Zoom toolbar */}
      <div className="mb-3 flex items-center gap-2 rounded-lg border border-border bg-elevated/70 px-3 py-1.5">
        <button
          type="button"
          onClick={() => setZoomIndex((i) => Math.max(0, i - 1))}
          disabled={!canZoomOut || rendering}
          className="btn-ghost px-2 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Zoom out"
        >
          −
        </button>
        <span className="min-w-[3.5rem] text-center font-mono text-2xs text-ink">
          {zoomPercent}%
        </span>
        <button
          type="button"
          onClick={() => setZoomIndex((i) => Math.min(ZOOM_STEPS.length - 1, i + 1))}
          disabled={!canZoomIn || rendering}
          className="btn-ghost px-2 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => setZoomIndex(DEFAULT_ZOOM_INDEX)}
          disabled={zoomIndex === DEFAULT_ZOOM_INDEX || rendering}
          className="btn-ghost px-2 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40"
        >
          Reset
        </button>
        {pageCount > 0 && (
          <span className="ml-auto font-mono text-2xs text-muted">
            {pageCount} {pageCount === 1 ? 'page' : 'pages'}
          </span>
        )}
      </div>

      {rendering && (
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="spinner" />
            Rendering PDF…
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300">
          {error}
        </div>
      )}

      <div
        ref={containerRef}
        className="overflow-auto rounded-lg border border-border bg-white p-4"
        style={{ minHeight: rendering ? 0 : 200 }}
      />
    </div>
  )
}
