import Card from '../common/Card.jsx'
import EmptyState from '../common/EmptyState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import {
  formatDurationMinutes,
  formatLondonDate,
  formatLondonDateTime,
} from '../../utils/datetime.js'
import { formatCount, formatMW, formatMWh } from '../../utils/format.js'

function Row({ label, value, title }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className="text-right text-xs font-medium tabular-nums text-slate-900" title={title}>
        {value}
      </dd>
    </div>
  )
}

export default function LatestForecastCard({
  forecast,
  deliveryDate,
  isLoading,
  error,
  onRetry,
  footnote,
}) {
  const summary = forecast?.summary

  return (
    <Card
      title="Latest available wind forecast"
      description={
        deliveryDate
          ? `As-of selection for ${formatLondonDate(deliveryDate)}, built from vintages available at the decision cutoff.`
          : 'Waiting for the latest delivery date.'
      }
      footer={footnote}
    >
      {isLoading ? (
        <LoadingState label="Loading selected forecast…" rows={5} compact />
      ) : error?.isMissingData ? (
        <EmptyState
          title="No forecast selection stored"
          description={error.message}
        />
      ) : error ? (
        <ErrorState error={error} onRetry={onRetry} title="Forecast unavailable" />
      ) : !forecast ? (
        <EmptyState
          title="No forecast available"
          description="The API returned no selection for the latest delivery date."
        />
      ) : (
        <>
          <dl className="divide-y divide-slate-100">
            <Row label="Mean forecast" value={formatMW(summary?.mean_forecast_mw)} />
            <Row label="Forecast energy" value={formatMWh(summary?.total_forecast_mwh)} />
            <Row
              label="Intervals selected"
              value={`${formatCount(summary?.selected)} / ${formatCount(summary?.intervals)}`}
            />
            <Row
              label="Lead time range"
              value={
                summary?.min_lead_minutes === null || summary?.min_lead_minutes === undefined
                  ? '—'
                  : `${formatDurationMinutes(summary.min_lead_minutes)} – ${formatDurationMinutes(
                      summary.max_lead_minutes,
                    )}`
              }
            />
            <Row
              label="Decision cutoff"
              value={formatLondonDateTime(forecast.cutoff_utc)}
              title={forecast.cutoff_definition}
            />
          </dl>
          <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] leading-relaxed text-slate-500">
            {forecast.cutoff_definition}. Policy <span className="font-mono">{forecast.policy_code}</span>.
          </p>
        </>
      )}
    </Card>
  )
}
