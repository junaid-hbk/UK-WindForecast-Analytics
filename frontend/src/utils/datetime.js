/**
 * Date helpers.
 *
 * The API stores UTC and displays Europe/London. All user-facing timestamps go
 * through `Intl.DateTimeFormat` with an explicit time zone so the browser's own
 * locale never silently changes the meaning of a timestamp.
 */

export const DISPLAY_TIME_ZONE = 'Europe/London'

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: DISPLAY_TIME_ZONE,
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZoneName: 'short',
})

const dateFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: DISPLAY_TIME_ZONE,
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const shortDateFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: DISPLAY_TIME_ZONE,
  day: '2-digit',
  month: 'short',
})

const timeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: DISPLAY_TIME_ZONE,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

function parse(value) {
  if (value === null || value === undefined || value === '') return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/** "15 Jan 2026, 14:30 GMT" — an em dash when the value is missing. */
export function formatLondonDateTime(value) {
  const date = parse(value)
  return date ? dateTimeFormatter.format(date) : '—'
}

/** "15 Jan 2026" */
export function formatLondonDate(value) {
  const date = parse(value)
  return date ? dateFormatter.format(date) : '—'
}

/** "15 Jan" — compact axis ticks. */
export function formatLondonShortDate(value) {
  const date = parse(value)
  return date ? shortDateFormatter.format(date) : '—'
}

/** "14:30" */
export function formatLondonTime(value) {
  const date = parse(value)
  return date ? timeFormatter.format(date) : '—'
}

/** "2026-01-15T07:30:00Z" — tooltips and audit details. */
export function formatUtcTimestamp(value) {
  const date = parse(value)
  if (!date) return '—'
  return date.toISOString().replace('.000Z', 'Z')
}

/** "2026-01-15" for a Date or ISO string, in Europe/London. */
export function toIsoDate(value = new Date()) {
  const date = parse(value)
  if (!date) return ''
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: DISPLAY_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const lookup = (type) => parts.find((part) => part.type === type)?.value ?? ''
  return `${lookup('year')}-${lookup('month')}-${lookup('day')}`
}

export function addDays(isoDate, days) {
  if (!isoDate) return ''
  const [year, month, day] = isoDate.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function daysBetween(fromIso, toIso) {
  if (!fromIso || !toIso) return 0
  const from = Date.parse(`${fromIso}T00:00:00Z`)
  const to = Date.parse(`${toIso}T00:00:00Z`)
  if (Number.isNaN(from) || Number.isNaN(to)) return 0
  return Math.round((to - from) / 86400000)
}

/** Last `days` days (inclusive) ending on `endIso`. */
export function trailingRange(endIso, days) {
  return { from: addDays(endIso, -(days - 1)), to: endIso }
}

/** First and last ISO date of the calendar month containing `isoDate`. */
export function monthRange(isoDate) {
  if (!isValidIsoDate(isoDate)) return null
  const [year, month] = isoDate.split('-').map(Number)
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate()
  const prefix = isoDate.slice(0, 7)
  return { from: `${prefix}-01`, to: `${prefix}-${String(lastDay).padStart(2, '0')}` }
}

/**
 * The earliest complete calendar month present in `days` (ISO settlement dates).
 *
 * The analysis window is derived from what the backend actually holds, so the
 * default period is never a hard-coded date and never a partial month.
 */
export function firstCompleteMonthRange(days = []) {
  const valid = [...new Set((days ?? []).filter(isValidIsoDate))].sort()
  if (valid.length === 0) return null
  const present = new Set(valid)
  const months = [...new Set(valid.map((day) => day.slice(0, 7)))]
  for (const month of months) {
    const [year, monthNumber] = month.split('-').map(Number)
    const totalDays = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate()
    let complete = true
    for (let day = 1; day <= totalDays; day += 1) {
      if (!present.has(`${month}-${String(day).padStart(2, '0')}`)) {
        complete = false
        break
      }
    }
    if (complete) return { from: `${month}-01`, to: `${month}-${String(totalDays).padStart(2, '0')}` }
  }
  return null
}

export function clampIsoDate(value, min, max) {
  if (!value) return value
  if (min && value < min) return min
  if (max && value > max) return max
  return value
}

export const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

export function isValidIsoDate(value) {
  if (typeof value !== 'string' || !ISO_DATE_PATTERN.test(value)) return false
  const date = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}

/** Human-readable lead time, e.g. 990 minutes → "16 h 30 min". */
export function formatDurationMinutes(minutes) {
  if (minutes === null || minutes === undefined || Number.isNaN(Number(minutes))) return '—'
  const total = Math.round(Number(minutes))
  const hours = Math.floor(total / 60)
  const mins = total % 60
  if (hours === 0) return `${mins} min`
  if (mins === 0) return `${hours} h`
  return `${hours} h ${mins} min`
}

/** "2026-01-15 00:00 GMT" (as returned by the API) or any ISO string. */
export function formatIntervalLabel(value) {
  if (typeof value === 'string' && /(GMT|BST)$/.test(value.trim())) return value
  return formatLondonDateTime(value)
}
