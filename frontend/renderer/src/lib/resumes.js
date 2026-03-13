export const EMPTY_RESUME_FORM = {
  project_id: '',
  project_name: '',
  title: '',
  description: '',
  analysis_snapshot: '',
  bullet_points: [''],
}

function compact(values) {
  return values
    .map((value) => String(value ?? '').trim())
    .filter(Boolean)
}

function unique(values) {
  return [...new Set(compact(values))]
}

export function normalizeResumeItems(payload) {
  if (Array.isArray(payload)) {
    return payload
  }

  return payload ?? []
}

export function sortResumesByUpdatedAt(items) {
  return [...items].sort((left, right) => {
    const leftTime = left?.updated_at ? new Date(left.updated_at).getTime() : 0
    const rightTime = right?.updated_at ? new Date(right.updated_at).getTime() : 0
    return rightTime - leftTime
  })
}

export function hasResumeProfile(profile) {
  return Boolean(profile)
}

export function formatResumeDate(value) {
  if (!value) {
    return 'No timestamp'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'No timestamp'
  }

  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function parseSnapshotInput(value) {
  return unique(String(value ?? '').split(',')).slice(0, 8)
}

export function prepareBulletPoints(values) {
  return compact(values)
}

export function getAvailableResumeProjects(projects, resumes, currentProjectId = null) {
  const usedProjectIds = new Set(
    resumes
      .map((resume) => resume?.project_id)
      .filter(
        (projectId) =>
          projectId !== null && projectId !== undefined && projectId !== currentProjectId
      )
  )

  return projects.filter((project) => !usedProjectIds.has(project.id))
}

export function buildResumeDraft(project, analysis) {
  const snapshot = unique([
    analysis?.language,
    analysis?.framework,
    ...(analysis?.tools ?? []),
    ...(analysis?.other_languages ?? []),
    ...(analysis?.practices ?? []),
  ]).slice(0, 8)

  const bulletPoints = prepareBulletPoints(
    (analysis?.resume_bullets?.length ? analysis.resume_bullets : analysis?.ai_bullets) ?? []
  )

  const summaryPrefix = snapshot.length > 0 ? `Built with ${snapshot.slice(0, 4).join(', ')}.` : ''

  return {
    project_id: String(project?.id ?? ''),
    project_name: analysis?.name ?? project?.name ?? '',
    title: analysis?.name ?? project?.name ?? '',
    description: summaryPrefix,
    analysis_snapshot: snapshot.join(', '),
    bullet_points: bulletPoints.length > 0 ? bulletPoints : [''],
  }
}
