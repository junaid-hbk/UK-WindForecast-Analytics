/**
 * Test fixtures mirroring the real Stage 2 response envelopes.
 * These are used only with mocked API functions — never in the app.
 */

export const policy = {
  code: 'EPEX_GB_DA_1H_0920',
  name: 'EPEX GB day-ahead (09:20)',
  local_time: '09:20:00',
  timezone_id: 'Europe/London',
  offset_days: -1,
  is_default: true,
  source_reference: 'EPEX SPOT GB day-ahead auction',
  notes: null,
}

export const metaConfig = {
  app_version: '0.2.0',
  environment: 'development',
  timezone_display: 'Europe/London',
  timezone_storage: 'UTC',
  cutoff_policies: [
    policy,
    {
      code: 'N2EX_GB_DA_1H_0950',
      name: 'N2EX GB day-ahead (09:50)',
      local_time: '09:50:00',
      timezone_id: 'Europe/London',
      offset_days: -1,
      is_default: false,
      source_reference: null,
      notes: null,
    },
  ],
  default_cutoff_policy: policy.code,
  windfor_sp_mapping: 'HOUR_SP_REPEAT',
  forecast_resolution_minutes: 60,
  settlement_period_minutes: 30,
  metric_definitions: {
    error: 'e = forecast_mw - actual_mw. Positive means the forecast was too high.',
    mae: 'Mean absolute error in MW over evaluated intervals.',
    rmse: 'Square root of the mean squared error in MW.',
    wape: '100 * sum(|e|) / sum(|actual|).',
    bias: 'Mean signed error in MW; positive means systematic over-forecast.',
    bias_pct: '100 * sum(e) / sum(actual).',
    coverage: 'Evaluated intervals / expected intervals, expressed as a percentage.',
    n: 'Number of intervals with both a forecast and an actual.',
  },
  data_sources: {
    actual_generation: {
      dataset: 'FUELHH',
      provider: 'Elexon BMRS Insights API',
      endpoint: '/datasets/FUELHH/stream',
      filter: 'fuelType=WIND',
      fields: ['startTime', 'generation'],
      resolution_minutes: 30,
    },
    forecast_generation: {
      dataset: 'WINDFOR',
      provider: 'Elexon BMRS Insights API',
      endpoint: '/datasets/WINDFOR/stream',
      fields: ['startTime', 'publishTime', 'generation'],
      resolution_minutes: 60,
      note: 'Published hourly; vintages are preserved individually.',
    },
  },
  disclaimers: {
    procurement: 'Illustrative estimate only. Not a purchasing recommendation.',
    forecast_resolution: 'WINDFOR is hourly; half-hourly values are a documented mapping.',
    comparability: 'FUELHH WIND and WINDFOR are the only permitted pair.',
  },
}

export const ingestionRuns = [
  {
    run_id: 3,
    dataset: 'WINDFOR',
    run_type: 'manual',
    status: 'succeeded',
    window_from_utc: '2025-12-29T00:00:00Z',
    window_to_utc: '2026-03-02T00:00:00Z',
    rows_fetched: 36792,
    rows_inserted: 36792,
    rows_updated: 0,
    rows_rejected: 0,
    http_requests: 63,
    http_status: 200,
    error_code: null,
    error_message: null,
    started_at_utc: '2026-01-01T00:00:00Z',
    finished_at_utc: '2026-01-01T00:02:00Z',
  },
  {
    run_id: 2,
    dataset: 'FUELHH',
    run_type: 'backfill',
    status: 'succeeded',
    window_from_utc: '2025-12-29T00:00:00Z',
    window_to_utc: '2026-03-01T00:00:00Z',
    rows_fetched: 2832,
    rows_inserted: 2832,
    rows_updated: 0,
    rows_rejected: 0,
    http_requests: 63,
    http_status: 200,
    error_code: null,
    error_message: null,
    started_at_utc: '2026-01-01T00:00:00Z',
    finished_at_utc: '2026-01-01T00:01:00Z',
  },
]

function coverageForMonth(year, month, missingByDay = {}) {
  const totalDays = new Date(Date.UTC(year, month, 0)).getUTCDate()
  return Array.from({ length: totalDays }, (_, index) => {
    const day = index + 1
    const missing = missingByDay[day] ?? 0
    return {
      settlement_date: `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
      intervals: 48,
      selected_intervals: 48 - missing,
      missing_intervals: missing,
      earliest_used_vintage: null,
      latest_used_vintage: null,
      min_lead_minutes: null,
      max_lead_minutes: null,
    }
  })
}

export const dataStatus = {
  policy_code: policy.code,
  date_from: '2026-01-01',
  date_to: '2026-02-28',
  stale: false,
  selection_intervals: 2832,
  coverage_days_with_gaps: 1,
  latest_vintage_publish_time_utc: '2026-03-01T22:30:00Z',
  latest_actual_settlement_date: '2026-02-28',
  actual_rows: 2832,
  actual_settlement_periods: 2832,
  forecast_vintages: 504,
  forecast_points: 36792,
  issue_counts: {},
  coverage: [...coverageForMonth(2026, 1, { 2: 2 }), ...coverageForMonth(2026, 2)],
  recent_runs: ingestionRuns,
  notes: ['Latest actual settlement date is 2026-02-28.'],
}

const intervalBase = {
  settlement_date: '2026-02-28',
  interval_start_utc: '2026-02-28T00:00:00Z',
  local_start: '2026-02-28 00:00 GMT',
  vintage_id: 401,
  vintage_publish_time_utc: '2026-02-27T07:30:00Z',
  lead_time_minutes: 990,
  fallback_depth: 0,
  selection_status: 'selected',
}

export const selectedDay = {
  delivery_date: '2026-02-28',
  policy_code: policy.code,
  cutoff_definition: '09:20 Europe/London on delivery_date-1 day',
  cutoff_utc: '2026-02-27T09:20:00Z',
  mapping: 'HOUR_SP_REPEAT',
  summary: {
    intervals: 3,
    selected: 3,
    missing: 0,
    total_forecast_mwh: 15000.5,
    mean_forecast_mw: 10000.333,
    min_lead_minutes: 990,
    max_lead_minutes: 1140,
  },
  intervals: [
    { ...intervalBase, settlement_period: 1, forecast_mw: 12000 },
    {
      ...intervalBase,
      settlement_period: 2,
      interval_start_utc: '2026-02-28T00:30:00Z',
      local_start: '2026-02-28 00:30 GMT',
      forecast_mw: 9000,
      lead_time_minutes: 1060,
    },
    {
      ...intervalBase,
      settlement_period: 3,
      interval_start_utc: '2026-02-28T01:00:00Z',
      local_start: '2026-02-28 01:00 GMT',
      forecast_mw: null,
      vintage_id: null,
      vintage_publish_time_utc: null,
      lead_time_minutes: null,
      selection_status: 'missing',
    },
  ],
}

export const actualIntervals = [
  {
    settlement_date: '2026-02-28',
    settlement_period: 1,
    start_time_utc: '2026-02-28T00:00:00Z',
    local_start: '2026-02-28 00:00 GMT',
    generation_mw: 11000,
    source_publish_time_utc: '2026-02-28T01:00:00Z',
  },
  {
    settlement_date: '2026-02-28',
    settlement_period: 2,
    start_time_utc: '2026-02-28T00:30:00Z',
    local_start: '2026-02-28 00:30 GMT',
    generation_mw: 9500,
    source_publish_time_utc: '2026-02-28T01:00:00Z',
  },
]

export const dailyActuals = [
  {
    settlement_date: '2026-02-28',
    periods_with_data: 48,
    mean_mw: 10250.75,
    total_mwh: 492036,
  },
]

export const vintages = {
  delivery_date: '2026-02-28',
  policy_code: policy.code,
  cutoff_utc: '2026-02-27T09:20:00Z',
  vintages: [
    {
      vintage_id: 401,
      publish_time_utc: '2026-02-27T07:30:00Z',
      local_publish_time: '2026-02-27 07:30 GMT',
      point_count: 73,
      resolution_minutes: 60,
      horizon_start_utc: '2026-02-27T08:00:00Z',
      horizon_end_utc: '2026-03-02T08:00:00Z',
      is_after_cutoff: false,
      is_used_at_cutoff: true,
      hours_in_delivery_day: 24,
    },
    {
      vintage_id: 402,
      publish_time_utc: '2026-02-27T12:30:00Z',
      local_publish_time: '2026-02-27 12:30 GMT',
      point_count: 73,
      resolution_minutes: 60,
      horizon_start_utc: '2026-02-27T13:00:00Z',
      horizon_end_utc: '2026-03-02T13:00:00Z',
      is_after_cutoff: true,
      is_used_at_cutoff: false,
      hours_in_delivery_day: 24,
    },
  ],
  note: 'Vintages published after cutoff_utc are historical only.',
}

export const vintageDetail = {
  vintage_id: 401,
  dataset: 'WINDFOR',
  publish_time_utc: '2026-02-27T07:30:00Z',
  local_publish_time: '2026-02-27 07:30 GMT',
  resolution_minutes: 60,
  horizon_start_utc: '2026-02-27T08:00:00Z',
  horizon_end_utc: '2026-03-02T08:00:00Z',
  point_count: 3,
  points: [
    {
      valid_from_utc: '2026-02-28T00:00:00Z',
      local_valid_from: '2026-02-28 00:00 GMT',
      generation_mw: 12000,
    },
    {
      valid_from_utc: '2026-02-28T01:00:00Z',
      local_valid_from: '2026-02-28 01:00 GMT',
      generation_mw: 11500,
    },
  ],
}

export const accuracyMetrics = {
  mae_mw: 2145.166,
  rmse_mw: 2615.812,
  wape_pct: 18.524,
  bias_mw: 1851.904,
  bias_pct: 15.991,
  n_evaluated: 1488,
  n_expected: 1488,
  n_missing_forecast: 0,
  n_missing_actual: 0,
  n_no_vintage_before_cutoff: 0,
  n_duplicate_intervals: 0,
  n_invalid_timestamps: 0,
  coverage_pct: 100.0,
  insufficient_data: false,
  wape_note: null,
}

export const accuracySummary = {
  policy_code: policy.code,
  date_from: '2026-01-01',
  date_to: '2026-01-31',
  granularity: 'sp',
  metrics: accuracyMetrics,
  notes: ['Metrics use the stored as-of selection for the requested policy.'],
}

export const dailyAccuracy = [
  {
    settlement_date: '2026-01-01',
    metrics: { ...accuracyMetrics, mae_mw: 4207.542, n_evaluated: 48, n_expected: 48 },
    accuracy_pct: 72.628,
  },
  {
    settlement_date: '2026-01-02',
    metrics: { ...accuracyMetrics, mae_mw: 1900.2, n_evaluated: 47, n_expected: 48, coverage_pct: 97.917 },
    accuracy_pct: 88.1,
  },
]

export const leadTimeAccuracy = [
  {
    label: '0-6h',
    lower_minutes: 0,
    upper_minutes: 360,
    is_empty: true,
    metrics: {
      mae_mw: null,
      rmse_mw: null,
      wape_pct: null,
      bias_mw: null,
      bias_pct: null,
      n_evaluated: 0,
      n_expected: 0,
      coverage_pct: null,
      insufficient_data: true,
      wape_note: 'No interval has both a forecast and an actual.',
    },
  },
  {
    label: '12-18h',
    lower_minutes: 720,
    upper_minutes: 1080,
    is_empty: false,
    metrics: {
      mae_mw: 1750.5,
      rmse_mw: 2100.1,
      wape_pct: 15.2,
      bias_mw: 900.4,
      bias_pct: 7.8,
      n_evaluated: 720,
      n_expected: 720,
      coverage_pct: 100,
      insufficient_data: false,
      wape_note: null,
    },
  },
]

export const procurementScenario = {
  policy_code: policy.code,
  date_from: '2026-02-28',
  date_to: '2026-02-28',
  demand_mw: 15000,
  totals: {
    intervals: 48,
    evaluated_intervals: 48,
    unavailable_intervals: 0,
    shortfall_intervals: 42,
    surplus_intervals: 6,
    balanced_intervals: 0,
    total_demand_mwh: 360000,
    total_forecast_mwh: 278630,
    total_delta_mwh: 81370,
    shortfall_mwh: 82748,
    surplus_mwh: 1378,
  },
  intervals: [
    {
      settlement_date: '2026-02-28',
      settlement_period: 1,
      interval_start_utc: '2026-02-28T00:00:00Z',
      local_start: '2026-02-28 00:00 GMT',
      demand_mw: 15000,
      forecast_mw: 12000,
      delta_mw: 3000,
      classification: 'shortfall',
      vintage_publish_time_utc: '2026-02-27T07:30:00Z',
      lead_time_minutes: 990,
    },
    {
      settlement_date: '2026-02-28',
      settlement_period: 2,
      interval_start_utc: '2026-02-28T00:30:00Z',
      local_start: '2026-02-28 00:30 GMT',
      demand_mw: 15000,
      forecast_mw: 16000,
      delta_mw: -1000,
      classification: 'surplus',
      vintage_publish_time_utc: '2026-02-27T07:30:00Z',
      lead_time_minutes: 1050,
    },
  ],
  disclaimer: 'Illustrative estimate only. This is not a purchasing recommendation.',
}

export const dataIssues = []

export const envelope = (data, meta = {}) => Promise.resolve({ data, meta })
