export function getProjectItems(payload) {
  if (Array.isArray(payload)) {
    return payload
  }

  return payload?.items ?? []
}
