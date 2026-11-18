import { useCallback, useEffect, useRef, useState } from 'react'
import { Calculator, Play } from 'lucide-react'

import Alert from '../components/common/Alert.jsx'
import AppDataGate from '../components/common/AppDataGate.jsx'
import Badge from '../components/common/Badge.jsx'
import Card from '../components/common/Card.jsx'
import DataTable from '../components/common/DataTable.jsx'
import ErrorState from '../components/common/ErrorState.jsx'
import { Checkbox, DateInput, Field, TextInput } from '../components/common/FormControls.jsx'
import LoadingState from '../components/common/LoadingState.jsx'
import MetricCard from '../components/common/MetricCard.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import ProcurementChart from '../components/charts/ProcurementChart.jsx'
import { fetchProcurementScenario, isCancelledError, toApiError } from '../api/index.js'
import { useAppData } from '../hooks/useAppData.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'
import { usePolicySelection } from '../hooks/usePolicySelection.js'
import { procurementSeries } from '../utils/chartData.js'
import { daysBetween, formatLondonDate, isValidIsoDate } from '../utils/datetime.js'
import {
  formatCount,
  formatMW,
  formatMWh,
  formatSignedMWh,
} from '../utils/format.js'

const MAX_DEMAND_MW = 100000

function validate({ demand, from, to, window }) {
  const errors = {}

  if (demand === '' || demand === null) {
    errors.demand = 'Enter a demand scenario in MW.'
  } else {
    const value = Number(demand)
    if (!Number.isFinite(value)) errors.demand = 'Demand must be a number.'
    else if (value <= 0) errors.demand = 'Demand must be greater than zero.'
    else if (value > MAX_DEMAND_MW) errors.demand = `Demand must be ${MAX_DEMAND_MW.toLocaleString('en-GB')} MW or less.`
  }

  if (!isValidIsoDate(from)) errors.from = 'Choose a valid start date.'
  if (!isValidIsoDate(to)) errors.to = 'Choose a valid end date.'
  if (!errors.from && !errors.to && from > to) errors.to = 'The end date must be on or after the start date.'
  if (!errors.from && window?.from && from < window.from) errors.from = `The loaded window starts on ${window.from}.`
  if (!errors.to && window?.to && to > window.to) errors.to = `The loaded window ends on ${window.to}.`
  if (!errors.from && !errors.to && daysBetween(from, to) > 30) {
    errors.to = 'Keep the scenario to 30 days or fewer so the estimate stays reviewable.'
  }

  return errors
}

function ProcurementContent() {
  const { window, latestDeliveryDate, defaultRange } = useAppData()
  const { policy, setPolicy, policies } = usePolicySelection()

  const [demand, setDemand] = useState('')
  const [from, setFrom] = useState(defaultRange?.from ?? latestDeliveryDate ?? '')
  const [to, setTo] = useState(defaultRange?.to ?? latestDeliveryDate ?? '')
  const [includeIntervals, setIncludeIntervals] = useState(true)
  const [errors, setErrors] = useState({})
  const [state, setState] = useState({ isSubmitting: false, result: null, meta: {}, error: null })

  const controllerRef = useRef(null)
  useEffect(() => () => controllerRef.current?.abort(), [])

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault()
      const validation = validate({ demand, from, to, window })
      setErrors(validation)
      if (Object.keys(validation).length > 0) return

      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller
      setState((current) => ({ ...current, isSubmitting: true, error: null }))

      try {
        const { data, meta } = await fetchProcurementScenario(
          {
            demandMw: Number(demand),
            dateFrom: from,
            dateTo: to,
            policy,
            includeIntervals,
          },
          controller.signal,
        )
        setState({ isSubmitting: false, result: data, meta, error: null })
      } catch (thrown) {
        if (isCancelledError(thrown)) return
        setState({ isSubmitting: false, result: null, meta: {}, error: toApiError(thrown) })
      }
    },
    [demand, from, to, policy, includeIntervals, window],
  )

  const result = state.result
  const totals = result?.totals
  const series = procurementSeries(result?.intervals ?? [])

  return (
    <>
      <PageHeader
        eyebrow="Illustrative estimate"
        title="Procurement insights"
        description="Compare a flat demand scenario with the day-ahead wind forecast available at your cutoff. This is an arithmetic estimate, not a purchasing recommendation."
        badges={
          <>
            <Badge tone="warning">Illustrative only</Badge>
            {policy && <Badge tone="brand">Policy · {policy}</Badge>}
          </>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,22rem)_1fr] lg:items-start">
        <Card title="Demand scenario" description="All inputs are sent to the backend, which performs the calculation.">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Field
              id="demand"
              label="Demand scenario (MW)"
              hint="Flat demand for every settlement period in the range."
              error={errors.demand}
            >
              {({ describedBy, invalid }) => (
                <TextInput
                  id="demand"
                  type="number"
                  inputMode="decimal"
                  min="1"
                  max={MAX_DEMAND_MW}
                  step="1"
                  placeholder="e.g. 15000"
                  value={demand}
                  invalid={invalid}
                  describedBy={describedBy}
                  onChange={(event) => setDemand(event.target.value)}
                />
              )}
            </Field>

            <Field id="scenario-from" label="From" error={errors.from}>
              {({ describedBy, invalid }) => (
                <DateInput
                  id="scenario-from"
                  value={from}
                  min={window?.from}
                  max={window?.to}
                  invalid={invalid}
                  describedBy={describedBy}
                  onChange={(event) => setFrom(event.target.value)}
                />
              )}
            </Field>

            <Field id="scenario-to" label="To" error={errors.to}>
              {({ describedBy, invalid }) => (
                <DateInput
                  id="scenario-to"
                  value={to}
                  min={window?.from}
                  max={window?.to}
                  invalid={invalid}
                  describedBy={describedBy}
                  onChange={(event) => setTo(event.target.value)}
                />
              )}
            </Field>

            <Field id="scenario-policy" label="Cutoff policy">
              {() => (
                <select
                  id="scenario-policy"
                  value={policy}
                  onChange={(event) => setPolicy(event.target.value)}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
                >
                  {policies.length === 0 && <option value="">Default policy</option>}
                  {policies.map((entry) => (
                    <option key={entry.code} value={entry.code}>
                      {entry.code}
                    </option>
                  ))}
                </select>
              )}
            </Field>

            <Checkbox
              id="include-intervals"
              label="Return interval detail"
              description="Needed for the chart and the per-period table."
              checked={includeIntervals}
              onChange={(event) => setIncludeIntervals(event.target.checked)}
            />

            <button
              type="submit"
              disabled={state.isSubmitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[var(--color-brand-700)] px-3 py-2 text-sm font-semibold text-white hover:bg-[var(--color-brand-600)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {state.isSubmitting ? (
                <>
                  <Calculator className="h-4 w-4 animate-pulse" aria-hidden="true" />
                  Calculating…
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" aria-hidden="true" />
                  Calculate scenario
                </>
              )}
            </button>
            <p className="text-[11px] leading-relaxed text-slate-500">
              Uses the stored as-of selection for the selected policy. Positive delta means the
              scenario exceeds the forecast (estimated shortfall).
            </p>
          </form>
        </Card>

        <div className="space-y-5">
          {state.error && (
            <ErrorState
              error={state.error}
              title="Scenario could not be calculated"
              onRetry={() => handleSubmit({ preventDefault: () => {} })}
            />
          )}

          {state.isSubmitting && !result && (
            <Card title="Result">
              <LoadingState label="Waiting for the backend calculation…" rows={4} />
            </Card>
          )}

          {!result && !state.error && !state.isSubmitting && (
            <Card title="Result">
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-5 py-10 text-center">
                <p className="text-sm font-semibold text-slate-800">No scenario calculated yet</p>
                <p className="mt-1 text-xs text-slate-600">
                  Enter a demand scenario and a date range, then calculate. Nothing is estimated
                  until the backend returns a result.
                </p>
              </div>
            </Card>
          )}

          {result && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Demand scenario"
                  value={formatMW(result.demand_mw)}
                  sample={`${formatMWh(totals?.total_demand_mwh)} over ${formatCount(totals?.intervals)} intervals`}
                  definition={`${formatLondonDate(result.date_from)} → ${formatLondonDate(result.date_to)}`}
                />
                <MetricCard
                  label="Selected wind forecast"
                  value={formatMWh(totals?.total_forecast_mwh)}
                  sample={`${formatCount(totals?.evaluated_intervals)} intervals evaluated`}
                  definition="Day-ahead as-of selection, summed at 0.5 h per settlement period."
                />
                <MetricCard
                  label="Net delta"
                  value={formatSignedMWh(totals?.total_delta_mwh)}
                  tone={totals?.total_delta_mwh > 0 ? 'warning' : 'default'}
                  sample={`${formatCount(totals?.shortfall_intervals)} shortfall · ${formatCount(totals?.surplus_intervals)} surplus`}
                  definition="Positive means the scenario exceeds forecast wind generation."
                />
                <MetricCard
                  label="Unavailable intervals"
                  value={formatCount(totals?.unavailable_intervals)}
                  sample={`${formatCount(totals?.balanced_intervals)} balanced`}
                  definition="Intervals with no eligible forecast are excluded from the energy totals."
                />
              </div>

              <ProcurementChart rows={series} />

              <Alert tone="warning" title="Illustrative estimate only">
                {result.disclaimer}
              </Alert>

              {state.meta?.excluded_inputs && (
                <Alert tone="neutral" title="Not modelled by this estimate">
                  Excluded inputs: {state.meta.excluded_inputs.join(', ')}. {state.meta.sign_convention}.
                </Alert>
              )}

              <Card
                title="Interval detail"
                description={`${formatLondonDate(result.date_from)} → ${formatLondonDate(result.date_to)} · policy ${result.policy_code}`}
                bodyClassName="px-0 py-0"
              >
                <DataTable
                  caption="Per-interval demand scenario, forecast and delta"
                  columns={[
                    { key: 'settlement_date', header: 'Day', render: (row) => formatLondonDate(row.settlement_date) },
                    { key: 'settlement_period', header: 'SP', numeric: true, align: 'right' },
                    { key: 'local_start', header: 'Interval start' },
                    { key: 'demand_mw', header: 'Demand', numeric: true, align: 'right', render: (row) => formatMW(row.demand_mw) },
                    { key: 'forecast_mw', header: 'Forecast', numeric: true, align: 'right', render: (row) => formatMW(row.forecast_mw) },
                    {
                      key: 'delta_mw',
                      header: 'Delta',
                      numeric: true,
                      align: 'right',
                      render: (row) => formatSignedMWh(row.delta_mw),
                    },
                    {
                      key: 'classification',
                      header: 'Classification',
                      render: (row) => (
                        <Badge tone={row.classification === 'shortfall' ? 'warning' : row.classification === 'surplus' ? 'success' : 'neutral'}>
                          {row.classification}
                        </Badge>
                      ),
                    },
                  ]}
                  rows={result.intervals ?? []}
                  getRowKey={(row) => `${row.settlement_date}-${row.settlement_period}`}
                  dense
                  maxHeight={420}
                  emptyMessage="Interval detail was not requested for this scenario."
                />
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  )
}

export default function ProcurementInsights() {
  useDocumentTitle('Procurement Insights')
  return (
    <AppDataGate>
      <ProcurementContent />
    </AppDataGate>
  )
}
