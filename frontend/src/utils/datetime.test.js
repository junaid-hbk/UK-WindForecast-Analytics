import { describe, expect, it } from 'vitest'

import {
  addDays,
  daysBetween,
  firstCompleteMonthRange,
  formatDurationMinutes,
  formatIntervalLabel,
  formatLondonDate,
  formatLondonDateTime,
  formatUtcTimestamp,
  isValidIsoDate,
  toIsoDate,
  trailingRange,
} from './datetime.js'

describe('Europe/London formatting', () => {
  it('renders winter timestamps as GMT', () => {
    expect(formatLondonDateTime('2026-01-15T09:20:00Z')).toMatch(/15 Jan 2026.*09:20.*GMT/)
  })

  it('shifts summer timestamps to BST', () => {
    // 12:00 UTC on 2026-07-01 is 13:00 BST.
    expect(formatLondonDateTime('2026-07-01T12:00:00Z')).toMatch(/13:00.*BST/)
  })

  it('formats plain dates', () => {
    expect(formatLondonDate('2026-02-28')).toBe('28 Feb 2026')
  })

  it('passes through API-local labels that already carry a zone', () => {
    expect(formatIntervalLabel('2026-01-15 00:00 GMT')).toBe('2026-01-15 00:00 GMT')
  })

  it('renders an em dash for missing values', () => {
    expect(formatLondonDateTime(null)).toBe('—')
    expect(formatUtcTimestamp('not-a-date')).toBe('—')
  })

  it('normalises ISO strings for audit display', () => {
    expect(formatUtcTimestamp('2026-01-15T00:00:00Z')).toBe('2026-01-15T00:00:00Z')
  })
})

describe('date arithmetic', () => {
  it('adds and subtracts days across month boundaries', () => {
    expect(addDays('2026-01-31', 1)).toBe('2026-02-01')
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28')
  })

  it('counts whole days between dates', () => {
    expect(daysBetween('2026-01-01', '2026-01-31')).toBe(30)
    expect(daysBetween('2026-01-01', '2026-01-01')).toBe(0)
  })

  it('builds inclusive trailing ranges', () => {
    expect(trailingRange('2026-02-28', 14)).toEqual({ from: '2026-02-15', to: '2026-02-28' })
  })

  it('derives the earliest complete calendar month from coverage days', () => {
    const january = Array.from(
      { length: 31 },
      (_, index) => `2026-01-${String(index + 1).padStart(2, '0')}`,
    )
    expect(firstCompleteMonthRange(january)).toEqual({ from: '2026-01-01', to: '2026-01-31' })
    // A leading partial month (December, from the Jan-1 delivery's D-1
    // decision) is skipped in favour of the first complete month.
    expect(firstCompleteMonthRange(['2025-12-31', ...january])).toEqual({
      from: '2026-01-01',
      to: '2026-01-31',
    })
    // A partial month is not a valid default analysis period.
    expect(firstCompleteMonthRange(january.slice(0, 30))).toBeNull()
    expect(firstCompleteMonthRange([])).toBeNull()
  })

  it('validates ISO date strings strictly', () => {
    expect(isValidIsoDate('2026-02-28')).toBe(true)
    expect(isValidIsoDate('2026-02-30')).toBe(false)
    expect(isValidIsoDate('28/02/2026')).toBe(false)
    expect(isValidIsoDate('')).toBe(false)
  })

  it('derives today in the display time zone', () => {
    expect(toIsoDate(new Date('2026-02-28T23:30:00Z'))).toBe('2026-02-28')
  })
})

describe('duration formatting', () => {
  it('renders hours and minutes', () => {
    expect(formatDurationMinutes(990)).toBe('16 h 30 min')
    expect(formatDurationMinutes(120)).toBe('2 h')
    expect(formatDurationMinutes(45)).toBe('45 min')
    expect(formatDurationMinutes(null)).toBe('—')
  })
})
