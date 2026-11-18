import { http } from './client.js'

/**
 * Thin accessors for the Stage 2 FastAPI endpoints.
 *
 * Every function resolves to `{ data, meta }` — the backend envelope — and
 * rejects with `ApiError`. Abort signals are supported everywhere so callers can
 * cancel in-flight work when a date or filter changes.
 */

function unwrap(response) {
  const body = response?.data ?? {}
  return { data: body.data, meta: body.meta ?? {} }
}

function params(input) {
  return Object.fromEntries(
    Object.entries(input).filter(
      ([, value]) => value !== undefined && value !== null && value !== '',
    ),
  )
}

export async function fetchMetaConfig(signal) {
  return unwrap(await http.get('/meta/config', { signal }))
}

export async function fetchHealth(signal) {
  return unwrap(await http.get('/health', { signal }))
}

export async function fetchDataStatus({ from, to, policy }, signal) {
  return unwrap(
    await http.get('/data/status', { params: params({ from, to, cutoff_policy: policy }), signal }),
  )
}

export async function fetchIngestionRuns({ limit = 25, dataset } = {}, signal) {
  return unwrap(await http.get('/data/runs', { params: params({ limit, dataset }), signal }))
}

export async function fetchDataIssues({ limit = 50, severity } = {}, signal) {
  return unwrap(await http.get('/data/issues', { params: params({ limit, severity }), signal }))
}

export async function fetchSelectedForecast({ deliveryDate, policy }, signal) {
  return unwrap(
    await http.get('/forecast/latest', {
      params: params({ delivery_date: deliveryDate, cutoff_policy: policy }),
      signal,
    }),
  )
}

export async function fetchVintages({ deliveryDate, policy }, signal) {
  return unwrap(
    await http.get('/forecast/vintages', {
      params: params({ delivery_date: deliveryDate, cutoff_policy: policy }),
      signal,
    }),
  )
}

export async function fetchVintage(vintageId, signal) {
  return unwrap(await http.get(`/forecast/vintages/${vintageId}`, { signal }))
}

export async function fetchActuals({ from, to, limit = 1500, offset = 0 }, signal) {
  return unwrap(await http.get('/actuals', { params: params({ from, to, limit, offset }), signal }))
}

export async function fetchActualsDaily({ from, to }, signal) {
  return unwrap(await http.get('/actuals/daily', { params: params({ from, to }), signal }))
}

export async function fetchAccuracySummary({ from, to, policy, granularity = 'sp' }, signal) {
  return unwrap(
    await http.get('/analysis/accuracy', {
      params: params({ from, to, cutoff_policy: policy, granularity }),
      signal,
    }),
  )
}

export async function fetchDailyAccuracy({ from, to, policy, granularity = 'sp' }, signal) {
  return unwrap(
    await http.get('/analysis/accuracy/daily', {
      params: params({ from, to, cutoff_policy: policy, granularity }),
      signal,
    }),
  )
}

export async function fetchLeadTimeAccuracy({ from, to, policy, granularity = 'sp' }, signal) {
  return unwrap(
    await http.get('/analysis/accuracy/by-lead-time', {
      params: params({ from, to, cutoff_policy: policy, granularity }),
      signal,
    }),
  )
}

export async function fetchProcurementScenario(
  { demandMw, dateFrom, dateTo, policy, includeIntervals = true },
  signal,
) {
  return unwrap(
    await http.post(
      '/procurement/scenario',
      {
        demand_mw: demandMw,
        date_from: dateFrom,
        date_to: dateTo,
        ...(policy ? { cutoff_policy: policy } : {}),
        include_intervals: includeIntervals,
      },
      { signal },
    ),
  )
}
