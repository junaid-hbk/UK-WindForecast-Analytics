import { useEffect, useState } from 'react'

import Alert from '../components/common/Alert.jsx'
import AppDataGate from '../components/common/AppDataGate.jsx'
import Badge from '../components/common/Badge.jsx'
import Card from '../components/common/Card.jsx'
import DataTable from '../components/common/DataTable.jsx'
import EmptyState from '../components/common/EmptyState.jsx'
import ErrorState from '../components/common/ErrorState.jsx'
import { DateInput } from '../components/common/FormControls.jsx'
import LoadingState from '../components/common/LoadingState.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import DailyAccuracyChart from '../components/charts/DailyAccuracyChart.jsx'
import DailyErrorChart from '../components/charts/DailyErrorChart.jsx'
import LeadTimeChart from '../components/charts/LeadTimeChart.jsx'
import DefinitionsPanel from '../components/accuracy/DefinitionsPanel.jsx'
import ObservationTable from '../components/accuracy/ObservationTable.jsx'
import KpiStrip from '../components/dashboard/KpiStrip.jsx'
import {
  fetchAccuracySummary,
  fetchDailyAccuracy,
  fetchLeadTimeAccuracy,
} from '../api/index.js'
import { useApiResource } from '../hooks/useApiResource.js'
import { MAX_QUERY_DAYS, useAppData } from '../hooks/useAppData.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'
import { usePolicySelection } from '../hooks/usePolicySelection.js'
import { dailySeries, leadTimeSeries } from '../utils/chartData.js'
import {
  daysBetween,
  formatLondonDate,
  isValidIsoDate,
} from '../utils/datetime.js'
import { formatCount, formatMW, formatPercent } from '../utils/format.js'

const GRANULARITY_OPTIONS = [
  { value: 'sp', label: 'Settlement period (30 min)' },
  { value: 'hourly', label: 'Hourly' },
]

function validateRange(from, to, window) {
  if (!isValidIsoDate(from)) return 'Choose a valid start date.'
  if (!isValidIsoDate(to)) return 'Choose a valid end date.'
  if (from > to) return 'The start date must be on or before the end date.'
  if (daysBetween(from, to) + 1 > MAX_QUERY_DAYS) {
    return `The API limits a query to ${MAX_QUERY_DAYS} days.`
  }
  if (window?.from && from < window.from) {
    return `The loaded data window starts on ${window.from}.`
  }
  if (window?.to && to > window.to) {
    return `The loaded data window ends on ${window.to}.`
  }
  return null
}

function DailyTable({ rows, isLoading, error, onRetry }) {
  const columns = [
    {
      key: 'settlement_date',
      header: 'Settlement day',
      render: (row) => formatLondonDate(row.settlement_date),
    },
    { key: 'accuracy', header: 'Accuracy', align: 'right', numeric: true, render: (row) => formatPercent(row.accuracy_pct) },
    { key: 'mae', header: 'MAE', align: 'right', numeric: true, render: (row) => formatMW(row.metrics?.mae_mw) },
    { key: 'rmse', header: 'RMSE', align: 'right', numeric: true, render: (row) => formatMW(row.metrics?.rmse_mw) },
    { key: 'wape', header: 'WAPE', align: 'right', numeric: true, render: (row) => formatPercent(row.metrics?.wape_pct) },
    { key: 'bias', header: 'Bias', align: 'right', numeric: true, render: (row) => formatMW(row.metrics?.bias_mw) },
    { key: 'n', header: 'n', align: 'right', numeric: true, render: (row) => formatCount(row.metrics?.n_evaluated) },
    { key: 'coverage', header: 'Coverage', align: 'right', numeric: true, render: (row) => formatPercent(row.metrics?.coverage_pct) },
  ]

  return (
    <Card
      title="Daily metrics"
      description="One row per settlement day evaluated by the backend."
      bodyClassName="px-0 py-0"
    >
      {isLoading ? (
        <div className="px-5 py-4">
          <LoadingState label="Loading daily accuracy…" rows={5} compact />
        </div>
      ) : error ? (
        <div className="px-5 py-4">
          <ErrorState error={error} onRetry={onRetry} title="Daily accuracy unavailable" />
        </div>
      ) : rows.length === 0 ? (
        <div className="px-5 py-4">
          <EmptyState
            title="No evaluated days"
            description="The API omitted every day in this range because no interval had both a forecast and an actual."
          />
        </div>
      ) : (
        <DataTable
          caption="Daily forecast metrics: accuracy, MAE, RMSE, WAPE, bias, observations and coverage"
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.settlement_date}
          dense
          maxHeight={420}
        />
      )}
    </Card>
  )
}

function LeadTimeTable({ rows, isLoading, error, onRetry }) {
  const columns = [
    { key: 'label', header: 'Lead-time bucket' },
    {
      key: 'range',
      header: 'Range (minutes)',
      render: (row) =>
        row.lower_minutes === null || row.lower_minutes === undefined
          ? '—'
          : `${formatCount(row.lower_minutes)} – ${formatCount(row.upper_minutes)}`,
    },
    {
      key: 'n',
      header: 'Observations (n)',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.metrics?.n_evaluated),
    },
    {
      key: 'mae',
      header: 'MAE',
      align: 'right',
      numeric: true,
      render: (row) => formatMW(row.metrics?.mae_mw),
    },
    {
      key: 'wape',
      header: 'WAPE',
      align: 'right',
      numeric: true,
      render: (row) => formatPercent(row.metrics?.wape_pct),
    },
    {
      key: 'coverage',
      header: 'Coverage',
      align: 'right',
      numeric: true,
      render: (row) => formatPercent(row.metrics?.coverage_pct),
    },
  ]

  return (
    <Card
      title="Lead-time buckets"
      description="Empty buckets are returned by the API with n = 0 so the table and chart keep a stable shape."
      bodyClassName="px-0 py-0"
    >
      {isLoading ? (
        <div className="px-5 py-4">
          <LoadingState label="Loading lead-time accuracy…" rows={4} compact />
        </div>
      ) : error ? (
        <div className="px-5 py-4">
          <ErrorState error={error} onRetry={onRetry} title="Lead-time accuracy unavailable" />
        </div>
      ) : rows.length === 0 ? (
        <div className="px-5 py-4">
          <EmptyState title="No lead-time buckets" description="The API returned no buckets for this range." />
        </div>
      ) : (
        <DataTable
          caption="Accuracy by lead-time bucket, with observation counts"
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.label}
          dense
        />
      )}
    </Card>
  )
}

function AccuracyContent() {
  const { defaultRange, window, metricDefinitions } = useAppData()
  const { policy, setPolicy, policies } = usePolicySelection()

  const [from, setFrom] = useState(defaultRange?.from ?? '')
  const [to, setTo] = useState(defaultRange?.to ?? '')
  const [granularity, setGranularity] = useState('sp')

  useEffect(() => {
    if (!from && defaultRange?.from) setFrom(defaultRange.from)
    if (!to && defaultRange?.to) setTo(defaultRange.to)
  }, [defaultRange?.from, defaultRange?.to, from, to])

  const rangeError = validateRange(from, to, window)
  const enabled = Boolean(policy && !rangeError)

  const summary = useApiResource(
    (signal) => fetchAccuracySummary({ from, to, policy, granularity }, signal),
    [from, to, policy, granularity],
    { enabled },
  )

  const daily = useApiResource(
    (signal) => fetchDailyAccuracy({ from, to, policy, granularity }, signal),
    [from, to, policy, granularity],
    { enabled },
  )

  const leadTime = useApiResource(
    (signal) => fetchLeadTimeAccuracy({ from, to, policy, granularity }, signal),
    [from, to, policy, granularity],
    { enabled },
  )

  const dailyRows = daily.data ?? []
  const leadRows = leadTime.data ?? []
  const metrics = summary.data?.metrics

  return (
    <>
      <PageHeader
        eyebrow="Forecast quality"
        title="Forecast accuracy"
        description="Authoritative accuracy metrics calculated by the backend over the intervals that have both a selected day-ahead forecast and a metered actual."
        badges={
          <>
            {policy && <Badge tone="brand">Policy · {policy}</Badge>}
            {granularity && <Badge tone="neutral">Granularity · {granularity === 'sp' ? '30 min' : 'hourly'}</Badge>}
          </>
        }
      />

      <div className="mb-4 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="accuracy-from" className="block text-xs font-semibold text-slate-700">
            From
          </label>
          <DateInput
            id="accuracy-from"
            value={from}
            min={window?.from}
            max={window?.to}
            onChange={(event) => setFrom(event.target.value)}
            className="mt-1"
          />
        </div>
        <div>
          <label htmlFor="accuracy-to" className="block text-xs font-semibold text-slate-700">
            To
          </label>
          <DateInput
            id="accuracy-to"
            value={to}
            min={window?.from}
            max={window?.to}
            onChange={(event) => setTo(event.target.value)}
            className="mt-1"
          />
        </div>
        <div>
          <label htmlFor="accuracy-policy" className="block text-xs font-semibold text-slate-700">
            Cutoff policy
          </label>
          <select
            id="accuracy-policy"
            value={policy}
            onChange={(event) => setPolicy(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            {policies.length === 0 && <option value="">Default policy</option>}
            {policies.map((entry) => (
              <option key={entry.code} value={entry.code}>
                {entry.code}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="accuracy-granularity" className="block text-xs font-semibold text-slate-700">
            Granularity
          </label>
          <select
            id="accuracy-granularity"
            value={granularity}
            onChange={(event) => setGranularity(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            {GRANULARITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {rangeError && (
        <div className="mb-4">
          <Alert tone="warning" title="Adjust the date range">
            {rangeError}
          </Alert>
        </div>
      )}

      <div className="space-y-5">
        <KpiStrip
          metrics={metrics}
          definitions={metricDefinitions}
          range={{ from, to }}
          isLoading={summary.isLoading}
          error={summary.error}
          onRetry={summary.reload}
        />

        <div className="grid gap-5 xl:grid-cols-2">
          <Card title="Summary notes" description="Returned with the accuracy response.">
            {summary.isLoading ? (
              <LoadingState label="Loading notes…" rows={3} compact />
            ) : summary.error ? (
              <ErrorState error={summary.error} onRetry={summary.reload} />
            ) : (
              <ul className="space-y-2 text-xs leading-relaxed text-slate-700">
                {(summary.data?.notes ?? []).map((note) => (
                  <li key={note} className="rounded-md bg-slate-50 px-3 py-2">
                    {note}
                  </li>
                ))}
                {(summary.data?.notes ?? []).length === 0 && (
                  <li className="text-slate-500">The API returned no additional notes.</li>
                )}
              </ul>
            )}
          </Card>

          <ObservationTable metrics={metrics} />
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <DailyAccuracyChart
            rows={dailySeries(dailyRows)}
            footnote="Sentence to remember: accuracy = 100 − WAPE, a convenience derived by the backend, not a separate KPI."
          />
          <DailyErrorChart rows={dailySeries(dailyRows)} />
        </div>

        <LeadTimeChart rows={leadTimeSeries(leadRows)} />

        <div className="grid gap-5 xl:grid-cols-2">
          <DailyTable
            rows={dailyRows}
            isLoading={daily.isLoading}
            error={daily.error}
            onRetry={daily.reload}
          />
          <LeadTimeTable
            rows={leadRows}
            isLoading={leadTime.isLoading}
            error={leadTime.error}
            onRetry={leadTime.reload}
          />
        </div>

        <DefinitionsPanel
          definitions={metricDefinitions}
          notes={summary.data?.notes ?? []}
          metaNotes={[
            daily.meta?.note,
            daily.meta?.accuracy_pct,
            leadTime.meta?.lead_time_definition,
            summary.meta?.missing_data_policy,
          ].filter(Boolean)}
        />
      </div>
    </>
  )
}

export default function ForecastAccuracy() {
  useDocumentTitle('Forecast Accuracy')
  return (
    <AppDataGate>
      <AccuracyContent />
    </AppDataGate>
  )
}
