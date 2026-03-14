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
