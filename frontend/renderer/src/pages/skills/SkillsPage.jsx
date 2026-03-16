import { useEffect, useMemo, useState } from 'react'
import { useApp } from '../../app/context/AppContext'
import EmptyState from '../../components/EmptyState'
import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'

function getSkillItems(payload) {
  if (Array.isArray(payload)) {
    return payload
  }

  return payload?.items ?? []
}

function normalizeSkillType(skillType) {
  const value = String(skillType || '').toLowerCase()
  if (value === 'tool') {
    return 'Tool'
  }
  if (value === 'practice') {
    return 'Practice'
  }
  return 'Skill'
}

export default function SkillsPage() {
  const { apiOk } = useApp()
  const [skills, setSkills] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!apiOk) {
      return
    }

    let cancelled = false

    async function loadSkills() {
      setLoading(true)
      try {
        const payload = await window.api.getSkills()
        if (!cancelled) {
          setSkills(getSkillItems(payload))
          setError('')
        }
      } catch (loadError) {
        if (!cancelled) {
          setSkills([])
          setError(loadError?.message || 'Failed to load skills.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadSkills()

    return () => {
      cancelled = true
    }
  }, [apiOk])

  const sortedSkills = useMemo(
    () => [...skills].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''))),
    [skills]
  )

  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Skills"
        description="Detected tools and practices across your uploaded projects."
      />

      <InlineError message={error} />

      {loading && <p className="text-xs text-muted">Loading…</p>}

      {!loading && !error && sortedSkills.length > 0 && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {sortedSkills.map((skill) => (
            <div key={`${skill.id}-${skill.name}`} className="card border border-border">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-bold">{skill.name}</div>
                <span className="rounded border border-border-hi bg-elevated px-2 py-0.5 font-mono text-2xs text-muted">
                  {normalizeSkillType(skill.skill_type)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && sortedSkills.length === 0 && (
        <EmptyState message="No skills detected yet. Analyze projects from the dashboard to populate this page." />
      )}
    </div>
  )
}
