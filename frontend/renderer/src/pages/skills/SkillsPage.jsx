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
  { key: 'beginner', label: 'Beginner', short: 'B', color: '#4e5668', bar: 1 },
  { key: 'intermediate', label: 'Intermediate', short: 'I', color: '#f5a623', bar: 2 },
  { key: 'proficient', label: 'Proficient', short: 'P', color: '#3dd68c', bar: 3 },
  { key: 'expert', label: 'Expert', short: 'E', color: '#60a5fa', bar: 4 },
]

const PROFICIENCY_FILTERS = [
  { label: 'All Levels', value: 'all' },
  { label: 'Expert', value: 'expert' },
  { label: 'Proficient', value: 'proficient' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Beginner', value: 'beginner' },
  { label: 'Unrated', value: 'unrated' },
]

/* ─── Level bar: 4 small segments that fill up to the current level ─── */
function LevelBar({ level }) {
  const activeIndex = LEVELS.findIndex((l) => l.key === level)
  return (
    <div className="flex gap-1">
      {LEVELS.map((l, i) => (
        <div
          key={l.key}
          className="h-1 rounded-full transition-all duration-300"
          style={{
            width: '16px',
            backgroundColor: i <= activeIndex ? l.color : '#1e2229',
          }}
        />
      ))}
    </div>
  )
}

/* ─── Segmented proficiency picker ─── */
function LevelPicker({ current, onChange }) {
  return (
    <div className="flex gap-px rounded bg-elevated p-px">
      {LEVELS.map((l) => {
        const active = current === l.key
        return (
          <button
            key={l.key}
            onClick={() => onChange(active ? null : l.key)}
            title={active ? `Clear ${l.label}` : l.label}
            className="relative flex-1 py-1.5 font-mono text-2xs uppercase tracking-wider rounded transition-all duration-150 cursor-pointer"
            style={{
              color: active ? '#0a0b0d' : '#4e5668',
              backgroundColor: active ? l.color : 'transparent',
              fontWeight: active ? 600 : 400,
            }}
          >
            {l.short}
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
  const levelMeta = LEVELS.find((l) => l.key === currentLevel)

  return (
    <div className="card flex flex-col gap-3" style={style}>
      {/* Top row: name + type badge */}
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

      {/* Level indicator bar + label */}
      <div className="flex items-center justify-between gap-2">
        <LevelBar level={currentLevel} />
        {levelMeta ? (
          <span
            className="font-mono text-2xs tracking-wide"
            style={{ color: levelMeta.color }}
          >
            {levelMeta.label}
          </span>
        ) : (
          <span className="font-mono text-2xs text-muted italic">unrated</span>
        )}
      </div>

      {/* Segmented picker */}
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

  const ratedCount = skills.filter((s) => s.proficiency_level).length

  const hasQuery = query.trim() !== ''
  const noResults = !loading && !error && skills.length > 0 && filteredSkills.length === 0

  function emptyFilterMessage() {
    if (hasQuery) return 'No skills match your search.'
    return 'No skills match your current filters.'
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
          {/* Stats row */}
          <div className="flex items-center gap-4">
            <div className="stat-card flex items-center gap-3 px-4 py-2.5">
              <span className="font-mono text-2xs text-muted uppercase tracking-widest">Total</span>
              <span className="font-mono text-sm font-bold text-ink">{skills.length}</span>
            </div>
            <div className="stat-card flex items-center gap-3 px-4 py-2.5">
              <span className="font-mono text-2xs text-muted uppercase tracking-widest">Rated</span>
              <span className="font-mono text-sm font-bold" style={{ color: '#3dd68c' }}>{ratedCount}</span>
            </div>
            <div className="stat-card flex items-center gap-3 px-4 py-2.5">
              <span className="font-mono text-2xs text-muted uppercase tracking-widest">Unrated</span>
              <span className="font-mono text-sm font-bold text-muted">{skills.length - ratedCount}</span>
            </div>
          </div>

          {/* Filters row */}
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
          </div>

          {/* Proficiency filter */}
          <div className="flex items-center gap-px rounded border border-border bg-elevated p-0.5 w-fit">
            {PROFICIENCY_FILTERS.map(({ label, value }) => (
              <button
                key={value}
                onClick={() => setProficiencyFilter(value)}
                className={`rounded px-3 py-1 font-mono text-2xs uppercase tracking-wider transition-colors cursor-pointer ${
                  proficiencyFilter === value
                    ? 'bg-surface text-ink shadow-sm'
                    : 'text-muted hover:text-ink'
                }`}
              >
                {label}
              </button>
            ))}
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
