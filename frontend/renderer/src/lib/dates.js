export function formatMonthYear(isoDate) {
  if (!isoDate) {
    return null
  }

  const date = new Date(`${isoDate}T00:00:00`)
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

export function formatDateRange(item) {
  const start = formatMonthYear(item.start_date)
  if (!start) {
    return null
  }

  const end = item.is_current ? 'Present' : formatMonthYear(item.end_date)
  return end ? `${start} – ${end}` : start
}
