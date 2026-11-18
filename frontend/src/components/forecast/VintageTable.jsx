import { CheckCircle2, Clock, XCircle } from 'lucide-react'

import Badge from '../common/Badge.jsx'
import Card from '../common/Card.jsx'
import DataTable from '../common/DataTable.jsx'
import EmptyState from '../common/EmptyState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { formatDurationMinutes, formatLondonDateTime, formatUtcTimestamp } from '../../utils/datetime.js'
import { formatCount } from '../../utils/format.js'

const MAX_COMPARE = 3

export default function VintageTable({
  vintages,
  cutoffUtc,
  selectedIds,
  onToggle,
  isLoading,
  error,
  onRetry,
  note,
}) {
  const rows = vintages ?? []

  const columns = [
    {
      key: 'compare',
      header: 'Compare',
      render: (row) => {
        const checked = selectedIds.includes(row.vintage_id)
        const atLimit = !checked && selectedIds.length >= MAX_COMPARE
        return (
          <input
            type="checkbox"
            checked={checked}
            disabled={atLimit}
            onChange={() => onToggle(row.vintage_id)}
            aria-label={`Compare vintage ${row.vintage_id} in the hourly chart`}
            className="h-4 w-4 rounded border-slate-300 accent-[var(--color-brand-600)] disabled:opacity-40"
          />
        )
      },
    },
    {
      key: 'vintage_id',
      header: 'Vintage',
      numeric: true,
      render: (row) => <span className="font-mono text-xs">#{row.vintage_id}</span>,
    },
    {
      key: 'publish_local',
      header: 'Published (local)',
      render: (row) => row.local_publish_time ?? formatLondonDateTime(row.publish_time_utc),
    },
    {
      key: 'publish_utc',
      header: 'Published (UTC)',
      render: (row) => (
        <span className="font-mono text-[11px] text-slate-600">
          {formatUtcTimestamp(row.publish_time_utc)}
        </span>
      ),
    },
    {
      key: 'points',
      header: 'Points',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.point_count),
    },
    {
      key: 'hours',
      header: 'Hours in day',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.hours_in_delivery_day),
    },
    {
      key: 'lead',
      header: 'Lead to day start',
      align: 'right',
      render: (row) => {
        if (!row.publish_time_utc || !cutoffUtc) return '—'
        const publish = Date.parse(row.publish_time_utc)
        const cutoff = Date.parse(cutoffUtc)
        if (Number.isNaN(publish) || Number.isNaN(cutoff)) return '—'
        return formatDurationMinutes(Math.round((cutoff - publish) / 60000))
      },
    },
    {
      key: 'flags',
      header: 'Status at cutoff',
      render: (row) =>
        row.is_used_at_cutoff ? (
          <Badge tone="success" icon={CheckCircle2}>
            Used for the decision
          </Badge>
        ) : row.is_after_cutoff ? (
          <Badge tone="warning" icon={XCircle}>
            Published after cutoff
          </Badge>
        ) : (
          <Badge tone="neutral" icon={Clock}>
            Available, superseded
          </Badge>
        ),
    },
  ]

  return (
    <Card
      title="Forecast publication vintages"
      description="Every WINDFOR vintage that could apply to this delivery day, with how it relates to the decision cutoff. Compare up to three in the hourly chart."
      bodyClassName="px-0 py-0"
      footer={note}
    >
      {isLoading ? (
        <div className="px-5 py-4">
          <LoadingState label="Loading vintages…" rows={4} compact />
        </div>
      ) : error ? (
        <div className="px-5 py-4">
          <ErrorState error={error} onRetry={onRetry} title="Vintage lineage unavailable" />
        </div>
      ) : rows.length === 0 ? (
        <div className="px-5 py-4">
          <EmptyState
            title="No vintages stored"
            description="WINDFOR has no vintage published in the window around this delivery date."
          />
        </div>
      ) : (
        <DataTable
          caption="Forecast vintages, publication times, coverage and whether each was used at the decision cutoff"
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.vintage_id}
          dense
          maxHeight={420}
        />
      )}
    </Card>
  )
}
