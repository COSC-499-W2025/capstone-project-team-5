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

const LEVELS = [
  { key: 'beginner', label: 'Beginner', color: '#f87171' },
  { key: 'intermediate', label: 'Intermediate', color: '#f5a623' },
  { key: 'proficient', label: 'Proficient', color: '#3dd68c' },
  { key: 'expert', label: 'Expert', color: '#60a5fa' },
]

const PROFICIENCY_FILTERS = [
  { label: 'All Levels', value: 'all' },
  { label: 'Expert', value: 'expert' },
  { label: 'Proficient', value: 'proficient' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Beginner', value: 'beginner' },
  { label: 'Unrated', value: 'unrated' },
]

/* ─── Segmented level picker ─── */
function LevelPicker({ current, onChange }) {
  return (
    <div className="flex gap-px rounded border border-border bg-elevated p-0.5">
      {LEVELS.map((l) => {
        const isActive = l.key === current
        return (
          <button
            key={l.key}
            onClick={() => onChange(isActive ? null : l.key)}
            title={isActive ? `Clear ${l.label}` : l.label}
            className="flex-1 rounded py-1 font-mono text-2xs uppercase tracking-wider transition-all duration-150 cursor-pointer"
            style={{
              color: isActive ? '#0a0b0d' : '#4e5668',
              backgroundColor: isActive ? l.color : 'transparent',
              fontWeight: isActive ? 600 : 400,
            }}
          >
            {l.label}
          </button>
        )
      })}
    </div>
  )
}

/* ─── Skill card ─── */
function SkillCard({ skill, onLevelChange, style }) {
  const typeLabel = normalizeSkillType(skill.skill_type)
  const currentLevel = skill.proficiency_level || ''

  return (
    <div className="card flex flex-col gap-3" style={style}>
      {/* Header: name + type */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-bold truncate leading-tight" title={skill.name}>
          {skill.name}
        </span>
        <span
          className="shrink-0 font-mono text-2xs uppercase tracking-wider px-1.5 py-0.5 rounded"
          style={{
            color: typeLabel === 'Tool' ? '#60a5fa' : '#c084fc',
            backgroundColor: typeLabel === 'Tool' ? 'rgba(96,165,250,0.1)' : 'rgba(192,132,252,0.1)',
            border: `1px solid ${typeLabel === 'Tool' ? 'rgba(96,165,250,0.2)' : 'rgba(192,132,252,0.2)'}`,
          }}
        >
          {typeLabel}
        </span>
      </div>

      {/* Level picker */}
      <LevelPicker
        current={currentLevel}
        onChange={(level) => onLevelChange(skill.id, level)}
      />
    </div>
  )
}

/* ─── Main page ─── */
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

  async function handleLevelChange(skillId, level) {
    setSkills((prev) =>
      prev.map((s) =>
        s.id === skillId ? { ...s, proficiency_level: level } : s
      )
    )
    try {
      const updated = await window.api.updateSkillProficiency(skillId, level)
      setSkills((prev) =>
        prev.map((s) => (s.id === skillId ? { ...s, ...updated } : s))
      )
    } catch {
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
    if (hasQuery && (hasTypeFilter || hasProficiencyFilter)) return 'No skills match your search and filter.'
    if (hasQuery) return 'No skills match your search.'
    return 'No skills match your current filter.'
  }

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Skills"
        description="Rate your proficiency across detected tools and practices."
      />

      <InlineError message={error} />

      {!loading && !error && skills.length > 0 && (
        <>
          {/* Filters */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {/* Search */}
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
                className="input pl-8 pr-8"
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  className="absolute inset-y-0 right-2.5 flex items-center text-muted hover:text-ink cursor-pointer"
                  aria-label="Clear search"
                >
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M1 1l10 10M11 1L1 11" />
                  </svg>
                </button>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Type filter */}
              <div className="flex items-center gap-px rounded border border-border bg-elevated p-0.5">
                {TYPE_FILTERS.map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() => setTypeFilter(value)}
                    className={`rounded px-3 py-1 font-mono text-2xs uppercase tracking-wider transition-colors cursor-pointer ${
                      typeFilter === value
                        ? 'bg-surface text-ink shadow-sm'
                        : 'text-muted hover:text-ink'
                    }`}
                  >
                    {label}
                    <span className="ml-1.5 opacity-50">{counts[value] ?? 0}</span>
                  </button>
                ))}
              </div>

              {/* Proficiency filter dropdown */}
              <select
                value={proficiencyFilter}
                onChange={(e) => setProficiencyFilter(e.target.value)}
                className="input w-auto py-1.5 px-3 text-2xs uppercase tracking-wider"
              >
                {PROFICIENCY_FILTERS.map(({ label, value }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>
        </>
      )}

      {loading && (
        <div className="flex items-center gap-3 py-8">
          <div className="spinner" />
          <span className="font-mono text-2xs text-muted uppercase tracking-widest">Loading skills…</span>
        </div>
      )}

      {!loading && !error && (hasQuery || proficiencyFilter !== 'all') && filteredSkills.length > 0 && (
        <p className="font-mono text-2xs text-muted uppercase tracking-widest">
          Showing {filteredSkills.length} of {skills.length} skill{skills.length !== 1 ? 's' : ''}
        </p>
      )}

      {!loading && !error && filteredSkills.length > 0 && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filteredSkills.map((skill, i) => (
            <SkillCard
              key={`${skill.id}-${skill.name}`}
              skill={skill}
              onLevelChange={handleLevelChange}
              style={{ animationDelay: `${Math.min(i * 30, 300)}ms` }}
            />
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
