import { describe, expect, it } from 'vitest'

import {
  dailySeries,
  leadTimeSeries,
  mergeForecastActual,
  mergeVintageSeries,
  procurementSeries,
} from './chartData.js'
import {
  actualIntervals,
  dailyAccuracy,
  leadTimeAccuracy,
  procurementScenario,
  selectedDay,
  vintageDetail,
} from '../test/fixtures.js'

describe('mergeForecastActual', () => {
  const rows = mergeForecastActual({
    intervals: selectedDay.intervals,
    actuals: actualIntervals,
  })

  it('joins on settlement date and period', () => {
    expect(rows).toHaveLength(3)
    expect(rows[0]).toMatchObject({
      settlement_period: 1,
      forecast_mw: 12000,
      actual_mw: 11000,
      difference_mw: 1000,
    })
    expect(rows[0].label).toBe('00:00')
  })

  it('keeps a missing forecast null instead of treating it as zero', () => {
    expect(rows[2].forecast_mw).toBeNull()
    expect(rows[2].difference_mw).toBeNull()
    expect(rows[2].selection_status).toBe('missing')
  })

  it('keeps a missing actual null', () => {
    // Period 3 has no actual in the fixture.
    expect(rows[2].actual_mw).toBeNull()
  })
})

describe('mergeVintageSeries', () => {
  it('aligns vintages on their own publish timestamps and leaves gaps', () => {
    const second = { ...vintageDetail, vintage_id: 402, points: [vintageDetail.points[0]] }
    const { rows, series } = mergeVintageSeries([vintageDetail, second])

    expect(series.map((entry) => entry.key)).toEqual(['vintage_401', 'vintage_402'])
    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({ vintage_401: 12000, vintage_402: 12000 })
    // The second vintage has no 01:00 point, so that key stays absent (a gap).
    expect(rows[1].vintage_401).toBe(11500)
    expect(rows[1].vintage_402).toBeUndefined()
  })

  it('returns empty structures for no vintages', () => {
    expect(mergeVintageSeries([])).toEqual({ rows: [], series: [] })
  })
})

describe('dailySeries', () => {
  it('copies backend metrics without recomputing them', () => {
    const rows = dailySeries(dailyAccuracy)
    expect(rows[0]).toMatchObject({
      date: '2026-01-01',
      accuracy_pct: 72.6,
      mae_mw: 4207.5,
      n_evaluated: 48,
    })
    expect(rows).toHaveLength(2)
  })
})

describe('leadTimeSeries', () => {
  it('marks empty buckets as null so charts show no bar', () => {
    const rows = leadTimeSeries(leadTimeAccuracy)
    expect(rows[0]).toMatchObject({ label: '0-6h', mae_mw: null, is_empty: true, n_evaluated: 0 })
    expect(rows[1].mae_mw).toBe(1750.5)
    expect(rows[1].is_empty).toBe(false)
  })
})

describe('procurementSeries', () => {
  it('maps intervals to labelled chart rows', () => {
    const rows = procurementSeries(procurementScenario.intervals)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({ label: '00:00', delta_mw: 3000, classification: 'shortfall' })
    expect(rows[1].delta_mw).toBe(-1000)
  })
})
