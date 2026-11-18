import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'

import Badge from '../common/Badge.jsx'
import Card from '../common/Card.jsx'
import EmptyState from '../common/EmptyState.jsx'
import { formatLondonDate, formatLondonDateTime } from '../../utils/datetime.js'
import { formatCount } from '../../utils/format.js'

function Row({ label, value }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className="text-right text-xs font-medium text-slate-900">{value}</dd>
    </div>
  )
}

export default function AvailabilityCard({ status }) {
  if (!status) {
    return (
      <Card title="Data availability">
        <EmptyState
          title="Status unavailable"
          description="The data status endpoint did not return a response for the loaded window."
        />
      </Card>
    )
  }

  const issues = Object.values(status.issue_counts ?? {}).reduce(
    (total, count) => total + Number(count || 0),
    0,
  )

  return (
    <Card
      title="Data availability"
      description="Freshness and completeness of what this dashboard is allowed to show."
      actions={
        <Badge tone={status.stale ? 'warning' : 'success'}>
          {status.stale ? 'Stale' : 'Current'}
        </Badge>
      }
      footer={
        <Link
          to="/data"
          className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"
        >
          Open Data Sources
          <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
        </Link>
      }
    >
      <dl className="divide-y divide-slate-100">
        <Row
          label="Latest actual settlement date"
          value={
            status.latest_actual_settlement_date
              ? formatLondonDate(status.latest_actual_settlement_date)
              : '—'
          }
        />
        <Row
          label="Latest vintage published"
          value={formatLondonDateTime(status.latest_vintage_publish_time_utc)}
        />
        <Row label="Selection intervals" value={formatCount(status.selection_intervals)} />
        <Row label="Days with coverage gaps" value={formatCount(status.coverage_days_with_gaps)} />
        <Row label="Open data-quality issues" value={formatCount(issues)} />
      </dl>
      {status.stale && (
        <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] leading-relaxed text-amber-800">
          The most recent actual settlement date is older than the stale threshold, so this view
          describes historical data rather than today&apos;s market.
        </p>
      )}
    </Card>
  )
}
