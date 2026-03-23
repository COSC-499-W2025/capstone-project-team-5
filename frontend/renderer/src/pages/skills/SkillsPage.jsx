import { useEffect, useMemo, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'

function getSkillItems(payload) {
  if (Array.isArray(payload)) return payload
  return payload?.items ?? []
}

function normalizeSkillType(skillType) {
  const value = String(skillType || '').toLowerCase()
  if (value === 'tool') return 'Tool'
  if (value === 'practice') return 'Practice'
  return 'Skill'
}

const TYPE_FILTERS = [
  { label: 'All', value: 'all' },
  { label: 'Tools', value: 'tool' },
  { label: 'Practices', value: 'practice' },
]

function SkillCard({ skill }) {
  const typeLabel = normalizeSkillType(skill.skill_type)

  return (
    <div className="card border border-border flex flex-col gap-3 transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-base font-bold truncate" title={skill.name}>
          {skill.name}
        </span>
        <span
          className={`shrink-0 rounded border px-2 py-0.5 font-mono text-xs ${
            typeLabel === 'Tool'
              ? 'border-blue-500/30 bg-blue-500/10 text-blue-400'
              : typeLabel === 'Practice'
              ? 'border-purple-500/30 bg-purple-500/10 text-purple-400'
              : 'border-border-hi bg-elevated text-muted'
          }`}
        >
          {typeLabel}
        </span>
      </div>

    </div>
  )
}

export default function SkillsPage() {
  const { apiOk } = useApp()
  const [skills, setSkills] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')

  useEffect(() => {
    if (!apiOk) return
    let cancelled = false

    async function loadSkills() {
      setLoading(true)
      try {
        const payload = await window.api.getSkills()
        if (!cancelled) {
          setSkills(getSkillItems(payload))
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          setSkills([])
          setError(err?.message || 'Failed to load skills.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadSkills()
    return () => { cancelled = true }
  }, [apiOk])

  const filteredSkills = useMemo(() => {
    const q = query.trim().toLowerCase()
    return [...skills]
      .filter((s) => {
        if (typeFilter !== 'all' && String(s.skill_type || '').toLowerCase() !== typeFilter)
          return false
        if (q && !String(s.name || '').toLowerCase().includes(q)) return false
        return true
      })
      .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
  }, [skills, query, typeFilter])

  const counts = useMemo(() => ({
    all: skills.length,
    tool: skills.filter((s) => String(s.skill_type || '').toLowerCase() === 'tool').length,
    practice: skills.filter((s) => String(s.skill_type || '').toLowerCase() === 'practice').length,
  }), [skills])

  const hasQuery = query.trim() !== ''
  const hasTypeFilter = typeFilter !== 'all'
  const noResults = !loading && !error && skills.length > 0 && filteredSkills.length === 0

  function emptyFilterMessage() {
    if (hasQuery && hasTypeFilter) return 'No skills match your search and filter.'
    if (hasQuery) return 'No skills match your search.'
    return 'No skills match your current filter.'
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Skills"
        description="Detected tools and practices across your uploaded projects."
      />

      <InlineError message={error} />

      {!loading && !error && skills.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative max-w-xs w-full">
            <span className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center text-muted">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="6.5" cy="6.5" r="5" />
                <path d="M10.5 10.5l3.5 3.5" strokeLinecap="round" />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Search skills…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded border border-border bg-black py-1.5 pl-8 pr-3 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute inset-y-0 right-2.5 flex items-center text-muted hover:text-foreground"
                aria-label="Clear search"
              >
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M1 1l10 10M11 1L1 11" />
                </svg>
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 rounded border border-border bg-elevated p-0.5">
            {TYPE_FILTERS.map(({ label, value }) => (
              <button
                key={value}
                onClick={() => setTypeFilter(value)}
                className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
                  typeFilter === value
                    ? 'bg-black text-foreground shadow-sm'
                    : 'text-muted hover:text-foreground'
                }`}
              >
                {label}
                <span className="ml-1.5 font-mono text-xs opacity-60">
                  {counts[value] ?? 0}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && <p className="text-sm text-muted">Loading…</p>}

      {!loading && !error && hasQuery && filteredSkills.length > 0 && (
        <p className="text-sm text-muted">
          Showing {filteredSkills.length} of {skills.length} skill{skills.length !== 1 ? 's' : ''}
        </p>
      )}

      {!loading && !error && filteredSkills.length > 0 && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filteredSkills.map((skill) => (
            <SkillCard key={`${skill.id}-${skill.name}`} skill={skill} />
          ))}
        </div>
      )}

      {!loading && !error && skills.length === 0 && (
        <EmptyState message="No skills detected yet. Analyze projects from the dashboard to populate this page." />
      )}
      {noResults && (
        <EmptyState message={emptyFilterMessage()} />
      )}
    </div>
  )
}