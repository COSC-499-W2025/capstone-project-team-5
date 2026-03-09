/**
 * @jest-environment jsdom
 */

import { formatDateRange, formatMonthYear } from '../renderer/src/lib/dates'
import { getProjectItems } from '../renderer/src/lib/projects'

test('getProjectItems returns array payloads unchanged', () => {
  const payload = [{ id: 1 }]
  expect(getProjectItems(payload)).toBe(payload)
})

test('getProjectItems unwraps item collections', () => {
  expect(getProjectItems({ items: [{ id: 2 }] })).toEqual([{ id: 2 }])
})

test('formatMonthYear keeps the existing month year format', () => {
  expect(formatMonthYear('2024-01-15')).toBe('Jan 2024')
})

test('formatDateRange returns Present for current entries', () => {
  expect(
    formatDateRange({
      start_date: '2024-01-01',
      end_date: null,
      is_current: true,
    })
  ).toBe('Jan 2024 – Present')
})

test('formatDateRange returns bounded ranges for completed entries', () => {
  expect(
    formatDateRange({
      start_date: '2023-09-01',
      end_date: '2024-05-15',
      is_current: false,
    })
  ).toBe('Sep 2023 – May 2024')
})
