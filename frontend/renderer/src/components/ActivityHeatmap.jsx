import { useEffect, useMemo, useState } from 'react'
import { useApp } from '../app/context/AppContext'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Local-time YYYY-MM-DD key
function toKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

// Build array of weeks (each week = 7 date keys, Sun→Sat).
// Covers ~52 weeks ending today. Future cells in the last week are null.
function buildGrid() {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const start = new Date(today)
  start.setDate(today.getDate() - 364)
  start.setDate(start.getDate() - start.getDay()) // roll back to Sunday

  const weeks = []
  const cur = new Date(start)

  while (cur <= today) {
    const week = []
    for (let i = 0; i < 7; i++) {
      week.push(cur <= today ? toKey(new Date(cur)) : null)
      cur.setDate(cur.getDate() + 1)
    }
    weeks.push(week)
  }

  return weeks
}

function levelColor(count) {
  if (count === 0) return '#1e2229'
  if (count === 1) return 'rgba(245,166,35,0.28)'
  if (count === 2) return 'rgba(245,166,35,0.52)'
  if (count === 3) return 'rgba(245,166,35,0.76)'
  return '#f5a623'
}

function formatDate(key) {
  if (!key) return ''
  const d = new Date(key + 'T00:00:00')
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

function Tooltip({ x, y, date, count }) {
  return (
    <div
      style={{
        position: 'fixed',
        left: x + 12,
        top: y - 36,
        pointerEvents: 'none',
        zIndex: 100,
      }}
      className="rounded border border-border-hi bg-elevated px-2.5 py-1.5 shadow-lg"
    >
      <span className="font-mono text-2xs text-ink">
        {count > 0 ? (
          <><span className="text-accent font-semibold">{count}</span> commit{count !== 1 ? 's' : ''} · </>
        ) : 'No commits · '}
        {formatDate(date)}
      </span>
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

const CELL = 9   // px: cell size
const GAP  = 2   // px: gap between cells
const STEP = CELL + GAP  // 11px per column

export default function ActivityHeatmap() {
  const { apiOk, user, analysisCache } = useApp()
  const [activityMap, setActivityMap] = useState({})
  const [total, setTotal] = useState(0)
  const [tooltip, setTooltip] = useState(null)

  useEffect(() => {
    if (!apiOk) return
    let cancelled = false

    async function load() {
      const username =
        user?.username ||
        (typeof window.api?.getAuthUsername === 'function' ? window.api.getAuthUsername() : null) ||
        (typeof window.api?.getUsername === 'function' ? window.api.getUsername() : null) ||
        localStorage.getItem('zip2job_username')

      // Build a per-project-ID map of commit_frequency so the same project
      // is never double-counted even if it appears in both the saved API
      // response and the in-memory analysis cache.
      // projectFreq: { [projectId]: { [YYYY-MM-DD]: count } }
      const projectFreq = {}

      // Source 1: saved analyses from the server (persisted git data).
      if (username && typeof window.api?.getSavedProjects === 'function') {
        try {
          const savedUploads = await window.api.getSavedProjects(username)
          if (!cancelled) {
            for (const upload of (savedUploads || [])) {
              for (const sp of (upload.projects || [])) {
                const latest = sp.analyses?.length > 0
                  ? sp.analyses[sp.analyses.length - 1]
                  : null
                const freq = latest?.git?.commit_frequency
                if (freq && typeof freq === 'object') {
                  projectFreq[sp.id] = freq
                }
              }
            }
          }
        } catch {}
      }

      if (cancelled) return

      // Source 2: in-memory cache for projects analyzed live this session.
      // Only fills in projects not already present from the server.
      const cache = analysisCache?.current ?? {}
      for (const [projectId, result] of Object.entries(cache)) {
        if (projectFreq[projectId]) continue  // server data takes precedence
        const freq = result?.git?.commit_frequency
        if (freq && typeof freq === 'object') {
          projectFreq[projectId] = freq
        }
      }

      // Aggregate across all projects by date.
      const map = {}
      let commitCount = 0

      for (const freq of Object.values(projectFreq)) {
        for (const [date, count] of Object.entries(freq)) {
          if (typeof count === 'number' && count > 0 && date.length === 10) {
            map[date] = (map[date] || 0) + count
            commitCount += count
          }
        }
      }

      setActivityMap(map)
      setTotal(commitCount)
    }

    load().catch(() => {})
    return () => { cancelled = true }
  }, [apiOk, user?.username])

  const weeks = useMemo(() => buildGrid(), [])

  const monthLabels = useMemo(() => {
    const labels = []
    let lastMonth = -1
    weeks.forEach((week, wi) => {
      const first = week.find(Boolean)
      if (!first) return
      const month = new Date(first + 'T00:00:00').getMonth()
      if (month !== lastMonth) {
        labels.push({ wi, label: MONTHS[month] })
        lastMonth = month
      }
    })
    return labels
  }, [weeks])

  const labelMap = useMemo(() => {
    const m = {}
    for (const { wi, label } of monthLabels) m[wi] = label
    return m
  }, [monthLabels])

  return (
    <div>
      <div className="divider-label">Activity</div>

      <div className="stat-card">
        <div className="mb-4 flex items-center justify-between">
          <span className="font-mono text-2xs uppercase tracking-widest text-muted">
            {total} commit{total !== 1 ? 's' : ''} in the last year
          </span>
          {/* Legend */}
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-2xs text-muted">Less</span>
            {[0, 1, 2, 3, 4].map((lvl) => (
              <div
                key={lvl}
                style={{ width: CELL, height: CELL, borderRadius: 2, backgroundColor: levelColor(lvl) }}
              />
            ))}
            <span className="font-mono text-2xs text-muted">More</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          {/* Month labels row */}
          <div style={{ display: 'flex', marginLeft: 28, marginBottom: 4 }}>
            {weeks.map((_, wi) => (
              <div
                key={wi}
                style={{ width: STEP, flexShrink: 0 }}
                className="font-mono text-2xs text-muted"
              >
                {labelMap[wi] ?? ''}
              </div>
            ))}
          </div>

          {/* Day labels + grid */}
          <div style={{ display: 'flex' }}>
            {/* Day-of-week labels */}
            <div
              style={{ display: 'flex', flexDirection: 'column', gap: GAP, width: 24, marginRight: 4, paddingTop: 1 }}
            >
              {['', 'Mon', '', 'Wed', '', 'Fri', ''].map((label, i) => (
                <div
                  key={i}
                  style={{ height: CELL, lineHeight: `${CELL}px` }}
                  className="font-mono text-2xs text-muted text-right leading-none"
                >
                  {label}
                </div>
              ))}
            </div>

            {/* Heatmap columns */}
            <div style={{ display: 'flex', gap: GAP }}>
              {weeks.map((week, wi) => (
                <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: GAP }}>
                  {week.map((dateKey, di) => {
                    if (!dateKey) {
                      return <div key={di} style={{ width: CELL, height: CELL }} />
                    }
                    const count = activityMap[dateKey] ?? 0
                    return (
                      <div
                        key={di}
                        style={{
                          width: CELL,
                          height: CELL,
                          borderRadius: 2,
                          backgroundColor: levelColor(count),
                          cursor: 'default',
                          transition: 'opacity 120ms',
                        }}
                        onMouseEnter={(e) =>
                          setTooltip({ x: e.clientX, y: e.clientY, date: dateKey, count })
                        }
                        onMouseMove={(e) =>
                          setTooltip((t) => t ? { ...t, x: e.clientX, y: e.clientY } : t)
                        }
                        onMouseLeave={() => setTooltip(null)}
                      />
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {total === 0 && (
          <p className="mt-4 text-xs text-muted">
            Analyze a project to populate commit history.
          </p>
        )}
      </div>

      {tooltip && (
        <Tooltip x={tooltip.x} y={tooltip.y} date={tooltip.date} count={tooltip.count} />
      )}
    </div>
  )
}
