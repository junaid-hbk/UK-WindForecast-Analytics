import Badge from '../common/Badge.jsx'
import Card from '../common/Card.jsx'
import DataTable from '../common/DataTable.jsx'
import EmptyState from '../common/EmptyState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { formatDurationMinutes, formatLondonDateTime } from '../../utils/datetime.js'
import { formatMW, formatSignedMW } from '../../utils/format.js'

export default function IntervalTable({ rows = [], isLoading, error, onRetry }) {
  const columns = [
    {
      key: 'settlement_period',
      header: 'SP',
      numeric: true,
      render: (row) => <span className="tabular-nums">{row.settlement_period}</span>,
    },
    {
      key: 'local_start',
      header: 'Interval start',
      render: (row) => row.local_start ?? formatLondonDateTime(row.interval_start_utc),
    },
    {
      key: 'forecast_mw',
      header: 'Forecast',
      align: 'right',
      numeric: true,
      render: (row) => formatMW(row.forecast_mw),
    },
    {
      key: 'actual_mw',
      header: 'Actual',
      align: 'right',
      numeric: true,
      render: (row) => formatMW(row.actual_mw),
    },
    {
      key: 'difference_mw',
      header: 'Forecast − actual',
      align: 'right',
      numeric: true,
      render: (row) => formatSignedMW(row.difference_mw),
    },
    {
      key: 'vintage',
      header: 'Selected vintage',
      render: (row) =>
        row.vintage_id ? (
          <span className="font-mono text-[11px]">#{row.vintage_id}</span>
        ) : (
          <span className="text-slate-400">none eligible</span>
        ),
    },
    {
      key: 'vintage_publish',
      header: 'Published',
      render: (row) =>
        row.vintage_publish_time_utc ? (
          <span className="text-[11px] text-slate-600">
            {formatLondonDateTime(row.vintage_publish_time_utc)}
          </span>
        ) : (
          '—'
        ),
    },
    {
      key: 'lead',
      header: 'Lead time',
      align: 'right',
      render: (row) => formatDurationMinutes(row.lead_time_minutes),
    },
    {
      key: 'status',
      header: 'Selection',
      render: (row) =>
        row.selection_status === 'selected' ? (
          <Badge tone="success">Selected</Badge>
        ) : (
          <Badge tone="warning">{row.selection_status ?? 'missing'}</Badge>
        ),
    },
  ]

  return (
    <Card
      title="Settlement period detail"
      description="All 48 half hours of the delivery day, using the vintage that was available at the cutoff for each interval."
      bodyClassName="px-0 py-0"
      footer="Fallback depth of zero means the interval used the most recent eligible vintage; a higher value indicates older fallbacks."
    >
      {isLoading ? (
        <div className="px-5 py-4">
          <LoadingState label="Loading settlement periods…" rows={6} compact />
        </div>
      ) : error?.isMissingData ? (
        <div className="px-5 py-4">
          <EmptyState title="No selection stored for this day" description={error.message} />
        </div>
      ) : error ? (
        <div className="px-5 py-4">
          <ErrorState error={error} onRetry={onRetry} title="Settlement periods unavailable" />
        </div>
      ) : rows.length === 0 ? (
        <div className="px-5 py-4">
          <EmptyState
            title="No intervals returned"
            description="The API returned an empty selection for this delivery date."
          />
        </div>
      ) : (
        <DataTable
          caption="Half-hourly selected forecast, actual outturn, error, vintage and lead time"
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.key}
          dense
          maxHeight={520}
        />
      )}
    </Card>
  )
}
