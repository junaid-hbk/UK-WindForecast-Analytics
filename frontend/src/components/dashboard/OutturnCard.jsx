import Card from '../common/Card.jsx'
import EmptyState from '../common/EmptyState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { formatLondonDate } from '../../utils/datetime.js'
import { formatCount, formatMW, formatMWh } from '../../utils/format.js'

function Row({ label, value }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className="text-right text-xs font-medium tabular-nums text-slate-900">{value}</dd>
    </div>
  )
}

export default function OutturnCard({ daily, deliveryDate, isLoading, error, onRetry }) {
  const day = Array.isArray(daily) ? daily[0] : null
  const periods = day?.periods_with_data ?? 0
  const complete = periods >= 48

  return (
    <Card
      title="Actual wind generation"
      description={
        deliveryDate
          ? `FUELHH outturn for ${formatLondonDate(deliveryDate)} (latest revision per settlement period).`
          : 'Actual outturn requires a delivery date.'
      }
      footer="Half-hourly metered wind outturn. Missing periods are counted, never filled with zero."
    >
      {isLoading ? (
        <LoadingState label="Loading actual outturn…" rows={4} compact />
      ) : error ? (
        <ErrorState error={error} onRetry={onRetry} title="Outturn unavailable" />
      ) : !day || periods === 0 ? (
        <EmptyState
          title="No actual outturn stored"
          description="FUELHH has not been ingested for this settlement date yet."
        />
      ) : (
        <>
          <dl className="divide-y divide-slate-100">
            <Row label="Mean generation" value={formatMW(day.mean_mw)} />
            <Row label="Energy" value={formatMWh(day.total_mwh)} />
            <Row label="Settlement periods" value={`${formatCount(periods)} / 48`} />
            <Row label="Day completeness" value={complete ? 'Complete' : 'Partial'} />
          </dl>
          {!complete && (
            <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] leading-relaxed text-amber-800">
              Only {formatCount(periods)} of 48 settlement periods have an outturn, so daily energy is
              not comparable with a complete day.
            </p>
          )}
        </>
      )}
    </Card>
  )
}
