import { useCallback, useEffect, useMemo, useState } from 'react'
import { Search } from 'lucide-react'

import Alert from '../components/common/Alert.jsx'
import AppDataGate from '../components/common/AppDataGate.jsx'
import Badge from '../components/common/Badge.jsx'
import { DateInput } from '../components/common/FormControls.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import ForecastActualChart from '../components/charts/ForecastActualChart.jsx'
import IntervalErrorChart from '../components/charts/IntervalErrorChart.jsx'
import CutoffBanner from '../components/forecast/CutoffBanner.jsx'
import IntervalTable from '../components/forecast/IntervalTable.jsx'
import VintageComparisonChart from '../components/forecast/VintageComparisonChart.jsx'
import VintageTable from '../components/forecast/VintageTable.jsx'
import {
  fetchActuals,
  fetchSelectedForecast,
  fetchVintage,
  fetchVintages,
} from '../api/index.js'
import { useApiResource } from '../hooks/useApiResource.js'
import { useAppData } from '../hooks/useAppData.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'
import { usePolicySelection } from '../hooks/usePolicySelection.js'
import { mergeForecastActual, mergeVintageSeries } from '../utils/chartData.js'
import {
  formatDurationMinutes,
  formatLondonDate,
  isValidIsoDate,
} from '../utils/datetime.js'
import { formatCount, formatMW, formatMWh } from '../utils/format.js'

function validateDate(value, window) {
  if (!value) return 'Choose a delivery date.'
  if (!isValidIsoDate(value)) return 'Enter a valid date (YYYY-MM-DD).'
  if (window?.from && value < window.from) {
    return `The loaded data window starts on ${window.from}.`
  }
  if (window?.to && value > window.to) {
    return `The loaded data window ends on ${window.to}.`
  }
  return null
}

function SummaryStrip({ forecast }) {
  const summary = forecast?.summary
  if (!summary) return null

  const items = [
    { label: 'Intervals', value: `${formatCount(summary.intervals)}` },
    { label: 'Selected', value: `${formatCount(summary.selected)}` },
    { label: 'Missing', value: `${formatCount(summary.missing)}` },
    { label: 'Mean forecast', value: formatMW(summary.mean_forecast_mw) },
    { label: 'Forecast energy', value: formatMWh(summary.total_forecast_mwh) },
    {
      label: 'Lead time',
      value:
        summary.min_lead_minutes === null || summary.min_lead_minutes === undefined
          ? '—'
          : `${formatDurationMinutes(summary.min_lead_minutes)} – ${formatDurationMinutes(
              summary.max_lead_minutes,
            )}`,
    },
  ]

  return (
    <dl className="grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-3 xl:grid-cols-6">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
            {item.label}
          </dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-slate-900">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function ForecastExplorerContent() {
  const { window, latestDeliveryDate } = useAppData()
  const { policy, setPolicy, policies } = usePolicySelection()

  const [deliveryDate, setDeliveryDate] = useState(latestDeliveryDate ?? '')
  const [selectedVintageIds, setSelectedVintageIds] = useState([])

  useEffect(() => {
    if (!deliveryDate && latestDeliveryDate) setDeliveryDate(latestDeliveryDate)
  }, [deliveryDate, latestDeliveryDate])

  const dateError = validateDate(deliveryDate, window)
  const enabled = Boolean(policy && !dateError)

  const forecast = useApiResource(
    (signal) => fetchSelectedForecast({ deliveryDate, policy }, signal),
    [deliveryDate, policy],
    { enabled },
  )

  const vintages = useApiResource(
    (signal) => fetchVintages({ deliveryDate, policy }, signal),
    [deliveryDate, policy],
    { enabled },
  )

  const actuals = useApiResource(
    (signal) => fetchActuals({ from: deliveryDate, to: deliveryDate }, signal),
    [deliveryDate],
    { enabled: Boolean(!dateError) },
  )

  const vintageDetails = useApiResource(
    (signal) =>
      Promise.all(selectedVintageIds.map((id) => fetchVintage(id, signal))).then((results) => ({
        data: results.map((result) => result.data),
        meta: { loaded: results.length },
      })),
    [selectedVintageIds.join(',')],
    { enabled: selectedVintageIds.length > 0 },
  )

  const usedVintageIds = useMemo(
    () => (vintages.data?.vintages ?? []).filter((row) => row.is_used_at_cutoff).map((row) => row.vintage_id),
    [vintages.data],
  )

  useEffect(() => {
    setSelectedVintageIds((current) => (current.length > 0 ? current : usedVintageIds.slice(0, 3)))
  }, [usedVintageIds])

  useEffect(() => {
    setSelectedVintageIds([])
  }, [deliveryDate, policy])

  const toggleVintage = useCallback((vintageId) => {
    setSelectedVintageIds((current) =>
      current.includes(vintageId)
        ? current.filter((id) => id !== vintageId)
        : [...current, vintageId].slice(0, 3),
    )
  }, [])

  const intervalRows = mergeForecastActual({
    intervals: forecast.data?.intervals ?? [],
    actuals: actuals.data ?? [],
  })

  const vintageChart = mergeVintageSeries(vintageDetails.data ?? [])
  const selectedVintageCount = usedVintageIds.length

  return (
    <>
      <PageHeader
        eyebrow="Forecast lineage"
        title="Forecast explorer"
        description="Inspect the half-hourly day-ahead selection, the metered outturn, and exactly which WINDFOR vintage was available when the decision had to be made."
        badges={
          <>
            {policy && <Badge tone="brand">Policy · {policy}</Badge>}
            <Badge tone="neutral">Loaded window {window?.from} → {window?.to}</Badge>
          </>
        }
      />

      <div className="mb-4 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-end sm:gap-4">
        <div className="sm:w-48">
          <label htmlFor="delivery-date" className="block text-xs font-semibold text-slate-700">
            Delivery date
          </label>
          <DateInput
            id="delivery-date"
            value={deliveryDate}
            min={window?.from}
            max={window?.to}
            invalid={Boolean(dateError)}
            describedBy={dateError ? 'delivery-date-error' : 'delivery-date-hint'}
            onChange={(event) => setDeliveryDate(event.target.value)}
            className="mt-1"
          />
          {dateError ? (
            <p id="delivery-date-error" className="mt-1 text-[11px] font-medium text-rose-700">
              {dateError}
            </p>
          ) : (
            <p id="delivery-date-hint" className="mt-1 text-[11px] text-slate-500">
              GB settlement date, Europe/London.
            </p>
          )}
        </div>

        <div className="sm:w-72">
          <label htmlFor="explorer-policy" className="block text-xs font-semibold text-slate-700">
            Decision cutoff policy
          </label>
          <select
            id="explorer-policy"
            value={policy}
            onChange={(event) => setPolicy(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            {policies.length === 0 && <option value="">Default policy</option>}
            {policies.map((entry) => (
              <option key={entry.code} value={entry.code}>
                {entry.name} ({entry.local_time} {entry.timezone_id})
              </option>
            ))}
          </select>
          <p className="mt-1 text-[11px] text-slate-500">
            Changing the policy re-selects vintages; stored selections may differ.
          </p>
        </div>

        <div className="flex items-center gap-2 pb-1 text-xs text-slate-600">
          <Search className="h-3.5 w-3.5" aria-hidden="true" />
          {formatLondonDate(deliveryDate)} · {selectedVintageCount} vintage
          {selectedVintageCount === 1 ? '' : 's'} used at cutoff
        </div>
      </div>

      <div className="space-y-4">
        <CutoffBanner
          cutoffUtc={forecast.data?.cutoff_utc ?? vintages.data?.cutoff_utc}
          cutoffDefinition={forecast.data?.cutoff_definition}
          policyCode={forecast.data?.policy_code ?? vintages.data?.policy_code ?? policy}
          mapping={forecast.data?.mapping}
          note={vintages.data?.note}
        />

        {dateError && (
          <Alert tone="warning" title="Adjust the delivery date">
            {dateError} No request is sent while the date is outside the loaded window.
          </Alert>
        )}

        <SummaryStrip forecast={forecast.data} />

        <ForecastActualChart
          rows={intervalRows}
          title="As-of selected forecast versus actual"
          description={`${formatLondonDate(deliveryDate)} · the interval-level selection available at the cutoff, next to FUELHH outturn.`}
          footnote="Nulls stay null: an interval with no eligible vintage is a gap, not a zero."
        />

        <IntervalErrorChart rows={intervalRows} />

        <VintageTable
          vintages={vintages.data?.vintages}
          cutoffUtc={vintages.data?.cutoff_utc}
          selectedIds={selectedVintageIds}
          onToggle={toggleVintage}
          isLoading={vintages.isLoading}
          error={vintages.error}
          onRetry={vintages.reload}
          note={vintages.meta?.used !== undefined ? `${formatCount(vintages.meta.used)} vintage(s) used at this cutoff.` : undefined}
        />

        <VintageComparisonChart rows={vintageChart.rows} series={vintageChart.series} />

        <IntervalTable
          rows={intervalRows}
          isLoading={forecast.isLoading || actuals.isLoading}
          error={forecast.error ?? actuals.error}
          onRetry={() => {
            forecast.reload()
            actuals.reload()
          }}
        />
      </div>
    </>
  )
}

export default function ForecastExplorer() {
  useDocumentTitle('Forecast Explorer')
  return (
    <AppDataGate>
      <ForecastExplorerContent />
    </AppDataGate>
  )
}
