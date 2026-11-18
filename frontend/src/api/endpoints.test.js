import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client.js', () => ({
  http: { get: vi.fn(), post: vi.fn() },
  apiBaseUrl: 'http://api.test/api/v1',
  apiTimeoutMs: 1000,
}))

import { http } from './client.js'
import {
  fetchAccuracySummary,
  fetchActuals,
  fetchDailyAccuracy,
  fetchDataStatus,
  fetchProcurementScenario,
  fetchSelectedForecast,
  fetchVintage,
  fetchVintages,
} from './endpoints.js'

const ok = (data, meta = {}) => ({ data: { data, meta } })

beforeEach(() => {
  http.get.mockReset()
  http.post.mockReset()
})

describe('GET endpoints', () => {
  it('unwraps the envelope and sends the as-of forecast query', async () => {
    http.get.mockResolvedValue(ok({ delivery_date: '2026-01-15' }, { note: 'x' }))

    const result = await fetchSelectedForecast({ deliveryDate: '2026-01-15', policy: 'P1' })

    expect(http.get).toHaveBeenCalledTimes(1)
    const [url, config] = http.get.mock.calls[0]
    expect(url).toBe('/forecast/latest')
    expect(config.params).toEqual({ delivery_date: '2026-01-15', cutoff_policy: 'P1' })
    expect(result).toEqual({ data: { delivery_date: '2026-01-15' }, meta: { note: 'x' } })
  })

  it('omits an unset cutoff policy instead of sending an empty string', async () => {
    http.get.mockResolvedValue(ok({}))

    await fetchVintages({ deliveryDate: '2026-01-15', policy: '' })

    const [, config] = http.get.mock.calls[0]
    expect(config.params).toEqual({ delivery_date: '2026-01-15' })
  })

  it('encodes the vintage id in the path', async () => {
    http.get.mockResolvedValue(ok({}))
    await fetchVintage(42)
    expect(http.get.mock.calls[0][0]).toBe('/forecast/vintages/42')
  })

  it('passes the date range and pagination to actuals', async () => {
    http.get.mockResolvedValue(ok([]))
    await fetchActuals({ from: '2026-01-01', to: '2026-01-02' })
    const [url, config] = http.get.mock.calls[0]
    expect(url).toBe('/actuals')
    expect(config.params).toEqual({ from: '2026-01-01', to: '2026-01-02', limit: 1500, offset: 0 })
  })

  it('requests accuracy with granularity', async () => {
    http.get.mockResolvedValue(ok({}))
    await fetchAccuracySummary({
      from: '2026-01-01',
      to: '2026-01-31',
      policy: 'P1',
      granularity: 'hourly',
    })
    const [url, config] = http.get.mock.calls[0]
    expect(url).toBe('/analysis/accuracy')
    expect(config.params).toEqual({
      from: '2026-01-01',
      to: '2026-01-31',
      cutoff_policy: 'P1',
      granularity: 'hourly',
    })
  })

  it('requests daily accuracy and data status from their paths', async () => {
    http.get.mockResolvedValue(ok([]))
    await fetchDailyAccuracy({ from: '2026-01-01', to: '2026-01-02', policy: 'P1' })
    await fetchDataStatus({ from: '2026-01-01', to: '2026-01-02' })

    expect(http.get.mock.calls[0][0]).toBe('/analysis/accuracy/daily')
    expect(http.get.mock.calls[1][0]).toBe('/data/status')
    expect(http.get.mock.calls[1][1].params).toEqual({ from: '2026-01-01', to: '2026-01-02' })
  })

  it('forwards the abort signal', async () => {
    http.get.mockResolvedValue(ok({}))
    const controller = new AbortController()
    await fetchSelectedForecast({ deliveryDate: '2026-01-15' }, controller.signal)
    expect(http.get.mock.calls[0][1].signal).toBe(controller.signal)
  })
})

describe('POST procurement scenario', () => {
  it('sends the backend field names and includes intervals by default', async () => {
    http.post.mockResolvedValue(ok({ totals: {} }))

    const result = await fetchProcurementScenario({
      demandMw: 15000,
      dateFrom: '2026-01-15',
      dateTo: '2026-01-15',
      includeIntervals: true,
    })

    const [url, body, config] = http.post.mock.calls[0]
    expect(url).toBe('/procurement/scenario')
    expect(body).toEqual({
      demand_mw: 15000,
      date_from: '2026-01-15',
      date_to: '2026-01-15',
      include_intervals: true,
    })
    expect(config.signal).toBeUndefined()
    expect(result.data).toEqual({ totals: {} })
  })

  it('omits an empty policy but keeps an explicit one', async () => {
    http.post.mockResolvedValue(ok({}))
    await fetchProcurementScenario({
      demandMw: 1,
      dateFrom: '2026-01-15',
      dateTo: '2026-01-15',
      policy: 'P1',
    })
    expect(http.post.mock.calls[0][1].cutoff_policy).toBe('P1')
  })
})
