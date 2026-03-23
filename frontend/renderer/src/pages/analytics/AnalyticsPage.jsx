import { useEffect, useMemo, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'

// Interpolates from border color (#1e2229 = rgb 30,34,41)
// to accent color (#f5a623 = rgb 245,166,35) at t ∈ [0,1]
function heatColor(value, max = 100) {
  const t = Math.min(1, Math.max(0, value / max))
  const r = Math.round(30  + 215 * t)
  const g = Math.round(34  + 132 * t)
  const b = Math.round(41  -   6 * t)
  return `rgb(${r},${g},${b})`
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { apiOk, user } = useApp()
  const [projects, setProjects] = useState([])
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  useEffect(() => {
    if (!apiOk || !user?.username) return
    const username = user.username
    setLoading(true)

    async function load() {
      try {
        const [allProjects, savedUploads] = await Promise.all([
          window.api.getProjects('?limit=100'),
          window.api.getSavedProjects(username).catch(() => []),
        ])

        // Build projectId → enriched data map from saved upload history
        const savedMap = {}
        for (const upload of (savedUploads || [])) {
          for (const sp of (upload.projects || [])) {
            const latest = sp.analyses?.length > 0
              ? sp.analyses[sp.analyses.length - 1]
              : null
            savedMap[sp.id] = {
              importance_score:             sp.importance_score,
              user_contribution_percentage: sp.user_contribution_percentage,
              tools:           sp.tools     ?? [],
              practices:       sp.practices ?? [],
              other_languages: sp.languages ?? [],
              score_breakdown: latest?.score_breakdown ?? {},
            }
          }
        }

        const analyzed = (allProjects?.items || [])
          .filter((p) => p.importance_score != null || p.user_role)
          .map((p) => ({
            ...p,
            ...(savedMap[p.id] ?? {}),
            name:     p.name,
            rel_path: p.rel_path,
          }))

        setProjects(analyzed)
        setError('')
      } catch (err) {
        setError(err?.message || 'Failed to load analytics data.')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [apiOk, user?.username])

  return (
    <div className="animate-fade-up space-y-8">
      <PageHeader
        title="Analytics"
        description="Visual breakdown across your analyzed projects."
      />
      <InlineError message={error} />

      {loading && <p className="text-xs text-muted">Loading…</p>}

      {!loading && !error && projects.length === 0 && (
        <p className="text-sm text-muted">
          No analyzed projects yet. Analyze projects to see visualizations here.
        </p>
      )}

      {!loading && projects.length > 0 && (
        <>
          <ScoreHeatmap projects={projects} />
          <SkillsMatrix projects={projects} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ImportanceChart projects={projects} />
            <ContribChart   projects={projects} />
          </div>
        </>
      )}
    </div>
  )
}

// ─── Score Breakdown Heatmap ──────────────────────────────────────────────────
// Rows = projects, columns = score dimensions, cells = color-coded score values

function ScoreHeatmap({ projects }) {
  const scored = projects.filter(
    (p) => p.score_breakdown && Object.keys(p.score_breakdown).length > 0,
  )

  const dimensions = useMemo(() => {
    const seen = new Set()
    scored.forEach((p) => Object.keys(p.score_breakdown).forEach((k) => seen.add(k)))
    return [...seen].sort()
  }, [scored])

  if (!scored.length || !dimensions.length) return null

  return (
    <Panel label="Score breakdown heatmap · project × dimension">
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="text-left font-normal text-ink/40 pb-2 pr-6 min-w-[140px]">
                Project
              </th>
              {dimensions.map((d) => (
                <th
                  key={d}
                  className="pb-2 px-1 font-mono text-2xs text-ink/40 capitalize text-center whitespace-nowrap"
                >
                  {d.replace(/_/g, '\u00a0')}
                </th>
              ))}
              <th className="pb-2 pl-4 font-mono text-2xs text-ink/40 text-right whitespace-nowrap">
                total
              </th>
            </tr>
          </thead>
          <tbody>
            {scored.map((p) => (
              <tr key={p.id}>
                <td
                  className="pr-6 py-0.5 font-mono text-2xs text-ink/70 whitespace-nowrap"
                  style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis' }}
                  title={p.name}
                >
                  {p.name}
                </td>
                {dimensions.map((d) => {
                  const val = p.score_breakdown[d] ?? 0
                  return (
                    <td key={d} className="px-0.5 py-0.5 text-center">
                      <div
                        className="w-9 h-6 rounded-sm mx-auto flex items-center justify-center font-mono text-2xs tabular-nums"
                        style={{
                          backgroundColor: heatColor(val),
                          color: val > 55 ? 'rgba(10,11,13,0.9)' : 'rgba(221,227,238,0.55)',
                        }}
                        title={`${p.name} · ${d.replace(/_/g, ' ')}: ${Math.round(val)}`}
                      >
                        {Math.round(val)}
                      </div>
                    </td>
                  )
                })}
                <td className="pl-4 py-0.5 font-mono text-xs font-semibold text-ink text-right tabular-nums">
                  {p.importance_score != null ? Math.round(p.importance_score) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

// ─── Skills Presence Matrix ───────────────────────────────────────────────────
// Rows = top skills, columns = projects, cells = colored square (present/absent)

function SkillsMatrix({ projects }) {
  const { topSkills, skillSets } = useMemo(() => {
    const freq = {}
    const sets = {}
    for (const p of projects) {
      const s = new Set([
        ...(p.other_languages ?? []),
        ...(p.tools           ?? []),
        ...(p.practices       ?? []),
      ])
      sets[p.id] = s
      for (const name of s) freq[name] = (freq[name] || 0) + 1
    }
    // Top 20 skills, minimum 2 projects to be interesting
    const topSkills = Object.entries(freq)
      .filter(([, c]) => c > 1)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([name, count]) => ({ name, count }))
    return { topSkills, skillSets: sets }
  }, [projects])

  if (!topSkills.length) return null

  const cols = projects.slice(0, 12) // cap columns for readability

  return (
    <Panel
      label={`Skills matrix · top ${topSkills.length} skills × ${projects.length} project${projects.length !== 1 ? 's' : ''}`}
    >
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="text-left font-normal text-ink/40 pb-3 pr-4 min-w-[120px]">
                Skill
              </th>
              {cols.map((p) => (
                <th key={p.id} className="pb-3 px-0.5 min-w-[28px]">
                  <div
                    className="font-mono text-2xs text-ink/40 text-center"
                    style={{
                      writingMode: 'vertical-rl',
                      transform:   'rotate(180deg)',
                      height:      '60px',
                      overflow:    'hidden',
                    }}
                    title={p.name}
                  >
                    {p.name.length > 12 ? `${p.name.slice(0, 10)}…` : p.name}
                  </div>
                </th>
              ))}
              <th className="pb-3 pl-3 font-mono text-2xs text-ink/40 text-right">×</th>
            </tr>
          </thead>
          <tbody>
            {topSkills.map(({ name, count }) => (
              <tr key={name}>
                <td className="pr-4 py-0.5 font-mono text-2xs text-ink/70 whitespace-nowrap">
                  {name}
                </td>
                {cols.map((p) => {
                  const has = skillSets[p.id]?.has(name) ?? false
                  return (
                    <td key={p.id} className="px-0.5 py-0.5 text-center">
                      <div
                        className="w-5 h-5 rounded-sm mx-auto"
                        style={{
                          backgroundColor: has ? 'rgba(245,166,35,0.85)' : '#181b22',
                        }}
                        title={`${p.name}: ${has ? '✓' : '✗'} ${name}`}
                      />
                    </td>
                  )
                })}
                <td className="pl-3 py-0.5 font-mono text-2xs text-ink/30 text-right tabular-nums">
                  {count}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {projects.length > 12 && (
        <p className="mt-2 font-mono text-2xs text-muted">
          Showing first 12 of {projects.length} projects.
        </p>
      )}
    </Panel>
  )
}

// ─── Importance Score Chart ───────────────────────────────────────────────────
// Horizontal bars sorted by score, colored using the same heat gradient

function ImportanceChart({ projects }) {
  const items = projects
    .filter((p) => p.importance_score != null)
    .sort((a, b) => b.importance_score - a.importance_score)
    .slice(0, 12)

  if (!items.length) return null

  const max = Math.max(...items.map((p) => p.importance_score), 1)

  return (
    <Panel label="Importance scores">
      <div className="space-y-2.5">
        {items.map((p) => {
          const pct = (p.importance_score / max) * 100
          return (
            <div key={p.id}>
              <div className="flex items-center justify-between gap-2 mb-1">
                <span
                  className="font-mono text-2xs text-ink/70 truncate flex-1 min-w-0"
                  title={p.name}
                >
                  {p.name}
                </span>
                <span className="font-mono text-2xs font-semibold text-ink shrink-0 tabular-nums">
                  {Math.round(p.importance_score)}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-border">
                <div
                  className="h-1.5 rounded-full transition-all"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: heatColor(p.importance_score),
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

// ─── Contribution % Chart ─────────────────────────────────────────────────────
// Horizontal bars sorted by contribution percentage

function ContribChart({ projects }) {
  const items = projects
    .filter((p) => p.user_contribution_percentage != null)
    .sort((a, b) => b.user_contribution_percentage - a.user_contribution_percentage)
    .slice(0, 12)

  if (!items.length) return null

  return (
    <Panel label="Contribution %">
      <div className="space-y-2.5">
        {items.map((p) => {
          const pct = Math.min(100, Math.max(0, p.user_contribution_percentage))
          return (
            <div key={p.id}>
              <div className="flex items-center justify-between gap-2 mb-1">
                <span
                  className="font-mono text-2xs text-ink/70 truncate flex-1 min-w-0"
                  title={p.name}
                >
                  {p.name}
                </span>
                <span className="font-mono text-2xs font-semibold text-ink shrink-0 tabular-nums">
                  {Math.round(pct)}%
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-border">
                <div
                  className="h-1.5 rounded-full bg-success transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

// ─── Shared ───────────────────────────────────────────────────────────────────

function Panel({ label, children }) {
  return (
    <div className="rounded border border-border">
      <div className="border-b border-border px-4 py-2.5">
        <span className="font-mono text-2xs text-ink/60 uppercase tracking-widest">{label}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}
