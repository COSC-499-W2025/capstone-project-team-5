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

const PROFICIENCY_LEVELS = [
  { label: 'Expert', value: 'expert', color: 'border-green-500/30 bg-green-500/10 text-green-400' },
  { label: 'Proficient', value: 'proficient', color: 'border-blue-500/30 bg-blue-500/10 text-blue-400' },
  { label: 'Intermediate', value: 'intermediate', color: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400' },
  { label: 'Beginner', value: 'beginner', color: 'border-gray-500/30 bg-gray-500/10 text-gray-400' },
]

const PROFICIENCY_FILTERS = [
  { label: 'All Levels', value: 'all' },
  { label: 'Expert', value: 'expert' },
  { label: 'Proficient', value: 'proficient' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Beginner', value: 'beginner' },
  { label: 'Unrated', value: 'unrated' },
]

function SkillCard({ skill, onProficiencyChange }) {
  const typeLabel = normalizeSkillType(skill.skill_type)
  const currentLevel = skill.proficiency_level || ''

  function handleChange(e) {
    const value = e.target.value || null
    onProficiencyChange(skill.id, value)
  }

  const levelInfo = PROFICIENCY_LEVELS.find((l) => l.value === currentLevel)

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

      {/* Proficiency dropdown */}
      <div className="flex items-center gap-2">
        <select
          value={currentLevel}
          onChange={handleChange}
          className="w-full rounded border border-border bg-black px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="">Auto-detect</option>
          {PROFICIENCY_LEVELS.map(({ label, value }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        {levelInfo && (
          <span className={`shrink-0 rounded border px-2 py-0.5 text-xs ${levelInfo.color}`}>
            {levelInfo.label}
          </span>
        )}
        {skill.is_manual_override === false && currentLevel && (
          <span className="text-xs text-muted italic">auto</span>
        )}
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
  const [proficiencyFilter, setProficiencyFilter] = useState('all')

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

  async function handleProficiencyChange(skillId, level) {
    // Optimistic update
    setSkills((prev) =>
      prev.map((s) =>
        s.id === skillId
          ? { ...s, proficiency_level: level, is_manual_override: level !== null }
          : s
      )
    )
    try {
      const updated = await window.api.updateSkillProficiency(skillId, level)
      setSkills((prev) =>
        prev.map((s) => (s.id === skillId ? { ...s, ...updated } : s))
      )
    } catch {
      // Revert on error — reload all skills
      const payload = await window.api.getSkills()
      setSkills(getSkillItems(payload))
    }
  }

  const filteredSkills = useMemo(() => {
    const q = query.trim().toLowerCase()
    return [...skills]
      .filter((s) => {
        if (typeFilter !== 'all' && String(s.skill_type || '').toLowerCase() !== typeFilter)
          return false
        if (proficiencyFilter !== 'all') {
          const level = s.proficiency_level || ''
          if (proficiencyFilter === 'unrated' && level !== '') return false
          if (proficiencyFilter !== 'unrated' && level !== proficiencyFilter) return false
        }
        if (q && !String(s.name || '').toLowerCase().includes(q)) return false
        return true
      })
      .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
  }, [skills, query, typeFilter, proficiencyFilter])

  const counts = useMemo(() => ({
    all: skills.length,
    tool: skills.filter((s) => String(s.skill_type || '').toLowerCase() === 'tool').length,
    practice: skills.filter((s) => String(s.skill_type || '').toLowerCase() === 'practice').length,
  }), [skills])

  const hasQuery = query.trim() !== ''
  const hasTypeFilter = typeFilter !== 'all'
  const hasProficiencyFilter = proficiencyFilter !== 'all'
  const noResults = !loading && !error && skills.length > 0 && filteredSkills.length === 0

  function emptyFilterMessage() {
    if (hasQuery && (hasTypeFilter || hasProficiencyFilter)) return 'No skills match your search and filters.'
    if (hasQuery) return 'No skills match your search.'
    return 'No skills match your current filters.'
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Skills"
        description="Detected tools and practices across your uploaded projects."
      />

      <InlineError message={error} />

      {!loading && !error && skills.length > 0 && (
        <div className="flex flex-col gap-3">
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

          <div className="flex items-center gap-1 rounded border border-border bg-elevated p-0.5 w-fit">
            {PROFICIENCY_FILTERS.map(({ label, value }) => (
              <button
                key={value}
                onClick={() => setProficiencyFilter(value)}
                className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
                  proficiencyFilter === value
                    ? 'bg-black text-foreground shadow-sm'
                    : 'text-muted hover:text-foreground'
                }`}
              >
                {label}
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
            <SkillCard key={`${skill.id}-${skill.name}`} skill={skill} onProficiencyChange={handleProficiencyChange} />
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
