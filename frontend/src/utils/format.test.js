import { describe, expect, it } from 'vitest'

import {
  formatCount,
  formatMW,
  formatMWh,
  formatPercent,
  formatSignedMW,
  formatSignedMWh,
  formatSignedPercent,
  toChartNumber,
} from './format.js'

describe('energy formatting', () => {
  it('formats MW with thousands separators', () => {
    expect(formatMW(2145.166)).toBe('2,145 MW')
    expect(formatMW(15834, 1)).toBe('15,834.0 MW')
  })

  it('formats energy in MW·h', () => {
    expect(formatMWh(81370)).toBe('81,370 MW·h')
  })

  it('formats percentages with the backend space convention', () => {
    expect(formatPercent(18.524, 1)).toBe('18.5 %')
  })

  it('marks signed values explicitly', () => {
    expect(formatSignedMW(1851.904)).toBe('+1,852 MW')
    expect(formatSignedMW(-420)).toBe('-420 MW')
    expect(formatSignedMWh(81370)).toBe('+81,370 MW·h')
    expect(formatSignedPercent(-15.991)).toBe('-16.0 %')
  })

  it('returns an em dash for null or non-numeric input', () => {
    expect(formatMW(null)).toBe('—')
    expect(formatMW(undefined)).toBe('—')
    expect(formatMW('not-a-number')).toBe('—')
    expect(formatPercent(null)).toBe('—')
    expect(formatSignedMW(null)).toBe('—')
    expect(formatCount(undefined)).toBe('—')
  })

  it('treats zero as a real value, not missing', () => {
    expect(formatMW(0)).toBe('0 MW')
    expect(formatPercent(0)).toBe('0.0 %')
    expect(formatSignedMW(0)).toBe('0 MW')
  })

  it('rounds chart values to one decimal without inventing precision', () => {
    expect(toChartNumber(1234.5678)).toBe(1234.6)
    expect(toChartNumber(null)).toBe(null)
  })
})
