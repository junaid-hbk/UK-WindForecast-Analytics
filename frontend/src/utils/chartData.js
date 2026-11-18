import { formatLondonShortDate, formatLondonTime } from './datetime.js'
import { toChartNumber } from './format.js'

/**
 * Pure transforms that turn API payloads into Recharts row arrays.
 *
 * These functions only reshape and round values the backend already computed.
 * Accuracy metrics (MAE, RMSE, WAPE, bias, coverage) are never recalculated
 * here — they are copied from the API responses.
 */

export function mergeForecastActual({ intervals = [], actuals = [] } = {}) {
  const actualByKey = new Map(
    actuals.map((row) => [`${row.settlement_date}#${row.settlement_period}`, row]),
  )

  return intervals.map((interval) => {
    const key = `${interval.settlement_date}#${interval.settlement_period}`
    const actual = actualByKey.get(key)
    const forecast = toChartNumber(interval.forecast_mw)
    const actualValue = toChartNumber(actual?.generation_mw)

    return {
      key,
      settlement_period: interval.settlement_period,
      settlement_date: interval.settlement_date,
      label: formatLondonTime(interval.interval_start_utc),
      local_start: interval.local_start,
      interval_start_utc: interval.interval_start_utc,
      forecast_mw: forecast,
      actual_mw: actualValue,
      // Signed difference plotted for inspection only; the authoritative
      // aggregate metrics come from /analysis/accuracy.
      difference_mw:
        forecast === null || actualValue === null
          ? null
          : Math.round((forecast - actualValue) * 10) / 10,
      vintage_id: interval.vintage_id,
      vintage_publish_time_utc: interval.vintage_publish_time_utc,
      lead_time_minutes: interval.lead_time_minutes,
      selection_status: interval.selection_status,
      actual_local_start: actual?.local_start ?? null,
    }
  })
}

/**
 * Merge the native hourly points of several vintages onto one time axis.
 * Missing hours stay `undefined` so lines break instead of implying a value.
 */
export function mergeVintageSeries(vintages = []) {
  const series = vintages.map((vintage) => ({
    id: vintage.vintage_id,
    key: `vintage_${vintage.vintage_id}`,
    publishTime: vintage.publish_time_utc,
  }))

  const byTime = new Map()
  vintages.forEach((vintage, index) => {
    const key = series[index].key
    for (const point of vintage.points ?? []) {
      if (!point.valid_from_utc) continue
      const row =
        byTime.get(point.valid_from_utc) ?? {
          time: point.valid_from_utc,
          label: formatLondonTime(point.valid_from_utc),
        }
      const value = toChartNumber(point.generation_mw)
      if (value !== null) row[key] = value
      byTime.set(point.valid_from_utc, row)
    }
  })

  const rows = [...byTime.values()].sort((a, b) => a.time.localeCompare(b.time))
  return { rows, series }
}

export function dailySeries(rows = []) {
  return rows
    .filter((row) => row?.metrics)
    .map((row) => ({
      key: row.settlement_date,
      date: row.settlement_date,
      label: formatLondonShortDate(row.settlement_date),
      accuracy_pct: toChartNumber(row.accuracy_pct),
      mae_mw: toChartNumber(row.metrics.mae_mw),
      bias_mw: toChartNumber(row.metrics.bias_mw),
      wape_pct: toChartNumber(row.metrics.wape_pct),
      n_evaluated: row.metrics.n_evaluated ?? 0,
      coverage_pct: toChartNumber(row.metrics.coverage_pct),
    }))
}

export function leadTimeSeries(rows = []) {
  return rows.map((row) => {
    const insufficient = !row.metrics || row.metrics.insufficient_data
    return {
      key: row.label,
      label: row.label,
      lower_minutes: row.lower_minutes,
      upper_minutes: row.upper_minutes,
      // Empty buckets return null so the chart shows a gap rather than a zero.
      mae_mw: insufficient ? null : toChartNumber(row.metrics?.mae_mw),
      wape_pct: insufficient ? null : toChartNumber(row.metrics?.wape_pct),
      n_evaluated: row.metrics?.n_evaluated ?? 0,
      is_empty: Boolean(row.is_empty) || insufficient,
    }
  })
}

export function procurementSeries(intervals = []) {
  return intervals.map((interval) => ({
    key: `${interval.settlement_date}#${interval.settlement_period}`,
    label: formatLondonTime(interval.interval_start_utc),
    settlement_date: interval.settlement_date,
    settlement_period: interval.settlement_period,
    demand_mw: toChartNumber(interval.demand_mw),
    forecast_mw: toChartNumber(interval.forecast_mw),
    delta_mw: toChartNumber(interval.delta_mw),
    classification: interval.classification,
  }))
}
