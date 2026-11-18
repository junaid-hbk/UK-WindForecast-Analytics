/**
 * Number formatting for energy units.
 *
 * The API returns MW (power) and MW·h (energy). Values are formatted for
 * display only — no metric is recomputed here.
 */

const EMPTY = '—'

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function formatNumber(value, digits = 0) {
  const number = toNumber(value)
  if (number === null) return EMPTY
  return number.toLocaleString('en-GB', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function formatMW(value, digits = 0) {
  const number = toNumber(value)
  return number === null ? EMPTY : `${formatNumber(number, digits)} MW`
}

export function formatMWh(value, digits = 0) {
  const number = toNumber(value)
  return number === null ? EMPTY : `${formatNumber(number, digits)} MW·h`
}

/** Backend convention: a space before the percent sign. */
export function formatPercent(value, digits = 1) {
  const number = toNumber(value)
  return number === null ? EMPTY : `${formatNumber(number, digits)} %`
}

export function formatSignedMW(value, digits = 0) {
  const number = toNumber(value)
  if (number === null) return EMPTY
  return `${number > 0 ? '+' : ''}${formatNumber(number, digits)} MW`
}

export function formatSignedMWh(value, digits = 0) {
  const number = toNumber(value)
  if (number === null) return EMPTY
  return `${number > 0 ? '+' : ''}${formatNumber(number, digits)} MW·h`
}

export function formatSignedPercent(value, digits = 1) {
  const number = toNumber(value)
  if (number === null) return EMPTY
  return `${number > 0 ? '+' : ''}${formatNumber(number, digits)} %`
}

export function formatCount(value) {
  const number = toNumber(value)
  return number === null ? EMPTY : number.toLocaleString('en-GB')
}

/** Rounds for chart tooltips without introducing fake precision. */
export function toChartNumber(value) {
  const number = toNumber(value)
  return number === null ? null : Math.round(number * 10) / 10
}

export function isNumeric(value) {
  return toNumber(value) !== null
}
