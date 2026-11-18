import { Link } from 'react-router-dom'
import { ArrowRight, RefreshCw } from 'lucide-react'

import Alert from '../components/common/Alert.jsx'
import AppDataGate from '../components/common/AppDataGate.jsx'
import Badge from '../components/common/Badge.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import ForecastActualChart from '../components/charts/ForecastActualChart.jsx'
import AvailabilityCard from '../components/dashboard/AvailabilityCard.jsx'
import DailySummaryTable from '../components/dashboard/DailySummaryTable.jsx'
import KpiStrip from '../components/dashboard/KpiStrip.jsx'
import LatestForecastCard from '../components/dashboard/LatestForecastCard.jsx'
import OutturnCard from '../components/dashboard/OutturnCard.jsx'
import {
  fetchAccuracySummary,
  fetchActuals,
  fetchActualsDaily,
  fetchDailyAccuracy,
  fetchSelectedForecast,
} from '../api/index.js'
import { useApiResource } from '../hooks/useApiResource.js'
import { useAppData } from '../hooks/useAppData.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'
import { usePolicySelection } from '../hooks/usePolicySelection.js'
import { dailySeries, mergeForecastActual } from '../utils/chartData.js'
import { formatLondonDate, formatLondonDateTime } from '../utils/datetime.js'

function DashboardContent() {
  const {
    status,
    latestDeliveryDate,
    defaultRange,
    metricDefinitions,
    disclaimers,
  } = useAppData()
  const { policy, setPolicy, policies } = usePolicySelection()

  const ready = Boolean(policy && latestDeliveryDate && defaultRange?.from)

  const forecast = useApiResource(
    (signal) => fetchSelectedForecast({ deliveryDate: latestDeliveryDate, policy }, signal),
    [latestDeliveryDate, policy],
    { enabled: ready },
  )

  const dayActuals = useApiResource(
    (signal) => fetchActuals({ from: latestDeliveryDate, to: latestDeliveryDate }, signal),
    [latestDeliveryDate],
    { enabled: Boolean(latestDeliveryDate) },
  )

  const dayActualTotals = useApiResource(
    (signal) => fetchActualsDaily({ from: latestDeliveryDate, to: latestDeliveryDate }, signal),
    [latestDeliveryDate],
    { enabled: Boolean(latestDeliveryDate) },
  )

  const accuracy = useApiResource(
    (signal) =>
      fetchAccuracySummary(
        { from: defaultRange.from, to: defaultRange.to, policy },
        signal,
      ),
    [defaultRange?.from, defaultRange?.to, policy],
    { enabled: ready },
  )

  const daily = useApiResource(
    (signal) =>
      fetchDailyAccuracy({ from: defaultRange.from, to: defaultRange.to, policy }, signal),
    [defaultRange?.from, defaultRange?.to, policy],
    { enabled: ready },
  )

  const chartRows = mergeForecastActual({
    intervals: forecast.data?.intervals ?? [],
    actuals: dayActuals.data ?? [],
  })

  const refreshAll = () => {
    forecast.reload()
    dayActuals.reload()
    dayActualTotals.reload()
    accuracy.reload()
    daily.reload()
  }

  return (
    <>
      <PageHeader
        eyebrow="Operations overview"
        title="Wind forecast dashboard"
        description="Day-ahead wind forecast performance for GB, built from the Elexon FUELHH outturn and the WINDFOR vintage available at your decision cutoff."
        badges={
          <>
            {policy && <Badge tone="brand">Policy · {policy}</Badge>}
            {latestDeliveryDate && (
              <Badge tone="neutral">Latest delivery day · {formatLondonDate(latestDeliveryDate)}</Badge>
            )}
            {status?.latest_vintage_publish_time_utc && (
              <Badge tone="neutral" icon={RefreshCw}>
                Updated {formatLondonDateTime(status.latest_vintage_publish_time_utc)}
              </Badge>
            )}
          </>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="dashboard-policy" className="text-xs font-medium text-slate-600">
              Cutoff policy
            </label>
            <select
              id="dashboard-policy"
              value={policy}
              onChange={(event) => setPolicy(event.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800"
            >
              {policies.length === 0 && <option value="">Default policy</option>}
              {policies.map((entry) => (
                <option key={entry.code} value={entry.code}>
                  {entry.code}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={refreshAll}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Refresh data
            </button>
          </div>
        }
      />

      {status?.stale && (
        <div className="mb-4">
          <Alert tone="warning" title="This view is historical">
            The newest actual settlement date is{' '}
            {formatLondonDate(status.latest_actual_settlement_date)}. Every figure below describes that
            stored period, not the current market.
          </Alert>
        </div>
      )}

      <section aria-labelledby="kpi-heading" className="mb-6">
        <h2 id="kpi-heading" className="mb-2 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Accuracy over the analysis window
        </h2>
        <KpiStrip
          metrics={accuracy.data?.metrics}
          definitions={metricDefinitions}
          range={defaultRange}
          isLoading={accuracy.isLoading || !ready}
          error={accuracy.error}
          onRetry={accuracy.reload}
        />
      </section>

      <section aria-label="Latest forecast, outturn and availability" className="mb-6 grid gap-4 lg:grid-cols-3">
        <LatestForecastCard
          forecast={forecast.data}
          deliveryDate={latestDeliveryDate}
          isLoading={forecast.isLoading}
          error={forecast.error}
          onRetry={forecast.reload}
          footnote={disclaimers?.forecast_resolution}
        />
        <OutturnCard
          daily={dayActualTotals.data}
          deliveryDate={latestDeliveryDate}
          isLoading={dayActualTotals.isLoading}
          error={dayActualTotals.error}
          onRetry={dayActualTotals.reload}
        />
        <AvailabilityCard status={status} />
      </section>

      <div className="mb-6">
        <ForecastActualChart
          rows={chartRows}
          title="Forecast versus actual generation"
          description={
            latestDeliveryDate
              ? `${formatLondonDate(latestDeliveryDate)} · selected day-ahead forecast against metered wind outturn, per settlement period.`
              : 'Selected day-ahead forecast against metered wind outturn.'
          }
          footnote="Hover for the local start time and lead time of each selected vintage."
        />
      </div>

      <DailySummaryTable
        rows={daily.data ?? []}
        isLoading={daily.isLoading}
        error={daily.error}
        onRetry={daily.reload}
      />

      <p className="mt-4 text-xs text-slate-600">
        Need the full detail?{' '}
        <Link to="/forecast" className="font-semibold text-brand-700 hover:underline">
          Explore settlement periods and vintages
        </Link>{' '}
        <ArrowRight className="inline h-3 w-3" aria-hidden="true" />
      </p>
    </>
  )
}

export default function Dashboard() {
  useDocumentTitle('Dashboard')
  return (
    <AppDataGate>
      <DashboardContent />
    </AppDataGate>
  )
}
