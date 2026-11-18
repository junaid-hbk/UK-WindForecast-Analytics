import { createContext, useContext, useMemo } from 'react'

import { fetchDataStatus, fetchIngestionRuns, fetchMetaConfig } from '../api/index.js'
import {
  addDays,
  daysBetween,
  firstCompleteMonthRange,
  toIsoDate,
  trailingRange,
} from '../utils/datetime.js'
import { useApiResource } from './useApiResource.js'

/** Backend guard: `settings.max_query_days` is 180. */
export const MAX_QUERY_DAYS = 180
const DEFAULT_WINDOW_DAYS = 14

const AppDataContext = createContext(null)

function clampToMaxSpan(from, to) {
  if (!from || !to) return { from, to }
  if (daysBetween(from, to) + 1 <= MAX_QUERY_DAYS) return { from, to }
  return { from: addDays(to, -(MAX_QUERY_DAYS - 1)), to }
}

/**
 * Derive the loaded data window from successful ingestion runs rather than
 * hard-coding dates, then ask /data/status what actually exists.
 */
async function loadAppData(signal) {
  const [metaResult, runsResult] = await Promise.all([
    fetchMetaConfig(signal),
    fetchIngestionRuns({ limit: 200 }, signal),
  ])

  const runs = runsResult.data ?? []
  const successful = runs.filter(
    (run) => run.status === 'succeeded' && run.window_from_utc && run.window_to_utc,
  )

  let window
  if (successful.length > 0) {
    const starts = successful.map((run) => run.window_from_utc.slice(0, 10)).sort()
    const ends = successful.map((run) => run.window_to_utc.slice(0, 10)).sort()
    window = clampToMaxSpan(starts[0], ends[ends.length - 1])
  } else {
    window = clampToMaxSpan(trailingRange(toIsoDate(), DEFAULT_WINDOW_DAYS).from, toIsoDate())
  }

  let status = null
  try {
    status = (await fetchDataStatus(window, signal)).data
  } catch (error) {
    if (error?.isCancelled) throw error
    // Status is supporting context; the rest of the app can still render.
    status = null
  }

  return { data: { meta: metaResult.data, runs, window, status }, meta: metaResult.meta }
}

function deriveAppData(raw) {
  if (!raw) return null
  const { meta, runs, window, status } = raw
  const latestDeliveryDate =
    status?.latest_actual_settlement_date ||
    status?.coverage?.at(-1)?.settlement_date ||
    window.to

  // Only days the backend actually has selections for are selectable. The
  // ingestion-run window is wider than the data (it includes the publishing
  // lead-in), so it must not bound the date pickers.
  const coverageDays = (status?.coverage ?? [])
    .map((day) => day.settlement_date)
    .filter(Boolean)
    .sort()
  const dataWindow =
    coverageDays.length > 0
      ? clampToMaxSpan(coverageDays[0], coverageDays[coverageDays.length - 1])
      : window

  // The selection axis is the delivery date, while the business question is
  // about decision dates. Map delivery coverage back to decision dates through
  // the default policy's offset (D-1 for the shipped policies), take the first
  // complete decision month, then map it forward again: January 2026 decisions
  // therefore cover deliveries 2 Jan – 1 Feb.
  const defaultPolicy =
    meta?.cutoff_policies?.find((entry) => entry.code === meta?.default_cutoff_policy) ?? null
  const offsetDays = Number(defaultPolicy?.offset_days ?? 0)
  const decisionDays = coverageDays.map((day) => addDays(day, offsetDays))
  const decisionMonth = firstCompleteMonthRange(decisionDays)
  const desired = decisionMonth
    ? {
        from: addDays(decisionMonth.from, -offsetDays),
        to: addDays(decisionMonth.to, -offsetDays),
      }
    : trailingRange(latestDeliveryDate, DEFAULT_WINDOW_DAYS)
  const defaultRange = {
    from: desired.from < dataWindow.from ? dataWindow.from : desired.from,
    to: desired.to > dataWindow.to ? dataWindow.to : desired.to,
  }

  return {
    meta,
    runs,
    status,
    window: dataWindow,
    latestDeliveryDate,
    defaultRange,
    policies: meta?.cutoff_policies ?? [],
    defaultPolicy: meta?.default_cutoff_policy ?? '',
    dataSources: meta?.data_sources ?? {},
    metricDefinitions: meta?.metric_definitions ?? {},
    disclaimers: meta?.disclaimers ?? {},
  }
}

export function AppDataProvider({ children }) {
  const resource = useApiResource(() => loadAppData(), [])
  const appData = useMemo(() => deriveAppData(resource.data), [resource.data])

  const value = useMemo(
    () => ({
      isLoading: resource.isLoading,
      error: resource.error,
      reload: resource.reload,
      ...appData,
    }),
    [appData, resource.isLoading, resource.error, resource.reload],
  )

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>
}

export function useAppData() {
  const context = useContext(AppDataContext)
  if (!context) {
    throw new Error('useAppData must be used inside <AppDataProvider>')
  }
  return context
}
