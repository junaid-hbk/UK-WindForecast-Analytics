import { ExternalLink } from 'lucide-react'

import Alert from '../components/common/Alert.jsx'
import AppDataGate from '../components/common/AppDataGate.jsx'
import Badge, { statusTone } from '../components/common/Badge.jsx'
import Card from '../components/common/Card.jsx'
import DataTable from '../components/common/DataTable.jsx'
import EmptyState from '../components/common/EmptyState.jsx'
import ErrorState from '../components/common/ErrorState.jsx'
import LoadingState from '../components/common/LoadingState.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import { fetchDataIssues } from '../api/index.js'
import { useApiResource } from '../hooks/useApiResource.js'
import { useAppData } from '../hooks/useAppData.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'
import {
  formatDurationMinutes,
  formatLondonDate,
  formatLondonDateTime,
  formatUtcTimestamp,
} from '../utils/datetime.js'
import { formatCount } from '../utils/format.js'

const ELEXON = {
  FUELHH: {
    dataset: 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH',
    stream: 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream',
  },
  WINDFOR: {
    dataset: 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR',
    stream: 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream',
  },
}

const GENERAL_DOCS = 'https://bmrs.elexon.co.uk/api-documentation'
const ELEXON_DATA = 'https://www.elexon.co.uk/data/'

function SourceCard({ title, source }) {
  if (!source) return null
  const links = ELEXON[source.dataset] ?? {}

  return (
    <Card
      title={title}
      description={`${source.provider} · ${source.dataset}`}
      actions={<Badge tone="brand">{source.dataset}</Badge>}
      footer={
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {links.dataset && (
            <a
              href={links.dataset}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"
            >
              Dataset documentation
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
            </a>
          )}
          {links.stream && (
            <a
              href={links.stream}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"
            >
              {source.endpoint} endpoint
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
            </a>
          )}
        </div>
      }
    >
      <dl className="space-y-1.5 text-xs">
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Endpoint</dt>
          <dd className="text-right font-mono text-[11px] text-slate-800">{source.endpoint}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Fields used</dt>
          <dd className="text-right font-mono text-[11px] text-slate-800">
            {(source.fields ?? []).join(', ')}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Native resolution</dt>
          <dd className="text-right text-slate-800">{source.resolution_minutes} minutes</dd>
        </div>
        {source.filter && (
          <div className="flex justify-between gap-3">
            <dt className="text-slate-600">Filter</dt>
            <dd className="text-right font-mono text-[11px] text-slate-800">{source.filter}</dd>
          </div>
        )}
      </dl>
      {source.note && (
        <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] leading-relaxed text-slate-600">
          {source.note}
        </p>
      )}
    </Card>
  )
}

function lastSuccessful(runs, dataset) {
  return (runs ?? []).find((run) => run.dataset === dataset && run.status === 'succeeded') ?? null
}

function RunTable({ runs }) {
  const columns = [
    {
      key: 'run_id',
      header: 'Run',
      render: (row) => <span className="font-mono text-[11px]">#{row.run_id}</span>,
    },
    { key: 'dataset', header: 'Dataset' },
    { key: 'run_type', header: 'Type' },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
    },
    {
      key: 'window',
      header: 'Window',
      render: (row) => (
        <span className="text-[11px] text-slate-600">
          {formatLondonDate(row.window_from_utc)} → {formatLondonDate(row.window_to_utc)}
        </span>
      ),
    },
    {
      key: 'inserted',
      header: 'Rows inserted',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.rows_inserted),
    },
    {
      key: 'rejected',
      header: 'Rejected',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.rows_rejected),
    },
    {
      key: 'http',
      header: 'HTTP',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.http_requests),
    },
    {
      key: 'finished',
      header: 'Finished',
      render: (row) => (
        <span className="text-[11px] text-slate-600">
          {row.finished_at_utc ? formatLondonDateTime(row.finished_at_utc) : 'still running'}
        </span>
      ),
    },
    {
      key: 'error',
      header: 'Error',
      render: (row) =>
        row.error_code ? (
          <span className="text-[11px] text-rose-700" title={row.error_message ?? ''}>
            {row.error_code}
          </span>
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
  ]

  return (
    <Card
      title="Ingestion history"
      description="Most recent Elexon ingestion attempts, newest first, as recorded by the backend."
      bodyClassName="px-0 py-0"
    >
      <DataTable
        caption="Recent ingestion runs with dataset, status, window, row counts and errors"
        columns={columns}
        rows={(runs ?? []).slice(0, 25)}
        getRowKey={(row) => row.run_id}
        dense
        maxHeight={420}
        emptyMessage="No ingestion runs have been recorded."
      />
    </Card>
  )
}

function CoverageTable({ coverage }) {
  const columns = [
    {
      key: 'settlement_date',
      header: 'Settlement day',
      render: (row) => formatLondonDate(row.settlement_date),
    },
    {
      key: 'intervals',
      header: 'Intervals',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.intervals),
    },
    {
      key: 'selected',
      header: 'Selected',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.selected_intervals),
    },
    {
      key: 'missing',
      header: 'Missing',
      align: 'right',
      numeric: true,
      render: (row) =>
        row.missing_intervals > 0 ? (
          <Badge tone="warning">{formatCount(row.missing_intervals)}</Badge>
        ) : (
          <span className="text-slate-500">0</span>
        ),
    },
    {
      key: 'lead',
      header: 'Lead range',
      render: (row) =>
        row.min_lead_minutes === null
          ? '—'
          : `${formatDurationMinutes(row.min_lead_minutes)} – ${formatDurationMinutes(row.max_lead_minutes)}`,
    },
    {
      key: 'vintage',
      header: 'Latest vintage used (UTC)',
      render: (row) => (
        <span className="font-mono text-[11px] text-slate-600">
          {formatUtcTimestamp(row.latest_used_vintage)}
        </span>
      ),
    },
  ]

  return (
    <Card
      title="Coverage by settlement day"
      description="Selection completeness for the loaded window. A missing interval means no eligible vintage covered it."
      bodyClassName="px-0 py-0"
    >
      <DataTable
        caption="Per-day coverage: intervals, selected, missing, lead range and latest vintage used"
        columns={columns}
        rows={coverage ?? []}
        getRowKey={(row) => row.settlement_date}
        dense
        maxHeight={420}
        emptyMessage="No coverage rows exist for this window."
      />
    </Card>
  )
}

function IssuesPanel({ issues, isLoading, error, onRetry }) {
  return (
    <Card title="Data-quality issues" description="Recorded problems, newest first." bodyClassName="px-0 py-0">
      {isLoading ? (
        <div className="px-5 py-4">
          <LoadingState label="Loading issues…" rows={3} compact />
        </div>
      ) : error ? (
        <div className="px-5 py-4">
          <ErrorState error={error} onRetry={onRetry} title="Issues unavailable" />
        </div>
      ) : issues.length === 0 ? (
        <div className="px-5 py-4">
          <EmptyState
            title="No recorded issues"
            description="The backend has no data-quality issues stored. Absence of issues is not proof of completeness — check the coverage table above."
          />
        </div>
      ) : (
        <DataTable
          caption="Recorded data-quality issues"
          columns={[
            { key: 'severity', header: 'Severity', render: (row) => <Badge tone={row.severity === 'error' ? 'danger' : row.severity === 'warning' ? 'warning' : 'neutral'}>{row.severity}</Badge> },
            { key: 'dataset', header: 'Dataset' },
            { key: 'issue_type', header: 'Type' },
            { key: 'settlement_date', header: 'Settlement day', render: (row) => (row.settlement_date ? formatLondonDate(row.settlement_date) : '—') },
            { key: 'detail', header: 'Detail', render: (row) => <span className="text-xs">{row.detail ?? '—'}</span> },
            { key: 'created', header: 'Recorded', render: (row) => formatLondonDateTime(row.created_at_utc) },
          ]}
          rows={issues}
          getRowKey={(row) => row.issue_id}
          dense
        />
      )}
    </Card>
  )
}

function DataSourcesContent() {
  const { meta, runs, status, latestDeliveryDate } = useAppData()
  const issues = useApiResource((signal) => fetchDataIssues({ limit: 50 }, signal), [])

  const sources = meta?.data_sources ?? {}
  const fuelhh = lastSuccessful(runs, 'FUELHH')
  const windfor = lastSuccessful(runs, 'WINDFOR')

  return (
    <>
      <PageHeader
        eyebrow="Provenance"
        title="Data sources"
        description="Exactly which Elexon datasets feed WindPulse UK, when they were last ingested, and where their coverage ends."
        badges={
          <>
            <Badge tone={status?.stale ? 'warning' : 'success'}>
              {status?.stale ? 'Stale data' : 'Fresh data'}
            </Badge>
            <Badge tone="neutral">Environment · {meta?.environment ?? '—'}</Badge>
          </>
        }
      />

      {status?.stale && (
        <div className="mb-4">
          <Alert tone="warning" title="Stored data is older than the stale threshold">
            Latest actual settlement date is{' '}
            {status.latest_actual_settlement_date
              ? formatLondonDate(status.latest_actual_settlement_date)
              : 'unknown'}.

            Ingestion has not caught up with the present, so every view is historical.
          </Alert>
        </div>
      )}

      <div className="mb-5 grid gap-4 lg:grid-cols-2">
        <SourceCard title="Actual generation source" source={sources.actual_generation} />
        <SourceCard title="Forecast generation source" source={sources.forecast_generation} />
      </div>

      <div className="mb-5 grid gap-4 lg:grid-cols-3">
        <Card title="Latest available data">
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Latest actual settlement date</dt>
              <dd className="font-medium text-slate-900">
                {status?.latest_actual_settlement_date
                  ? formatLondonDate(status.latest_actual_settlement_date)
                  : latestDeliveryDate
                    ? formatLondonDate(latestDeliveryDate)
                    : '—'}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Latest vintage published</dt>
              <dd className="text-right font-medium text-slate-900">
                {formatLondonDateTime(status?.latest_vintage_publish_time_utc)}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Actual periods stored</dt>
              <dd className="font-medium text-slate-900">{formatCount(status?.actual_settlement_periods)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Forecast points stored</dt>
              <dd className="font-medium text-slate-900">{formatCount(status?.forecast_points)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Vintages stored</dt>
              <dd className="font-medium text-slate-900">{formatCount(status?.forecast_vintages)}</dd>
            </div>
          </dl>
        </Card>

        <Card title="Last successful ingestion" description="Newest succeeded run per dataset.">
          <dl className="space-y-2 text-xs">
            {[
              { label: 'FUELHH', run: fuelhh },
              { label: 'WINDFOR', run: windfor },
            ].map(({ label, run }) => (
              <div key={label} className="rounded-md bg-slate-50 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <dt className="font-semibold text-slate-800">{label}</dt>
                  <dd>
                    {run ? <Badge tone={statusTone(run.status)}>{run.status}</Badge> : <Badge tone="danger">none</Badge>}
                  </dd>
                </div>
                <dd className="mt-1 text-[11px] text-slate-600">
                  {run
                    ? `${formatCount(run.rows_inserted)} rows · ${formatCount(run.http_requests)} HTTP requests · finished ${formatLondonDateTime(run.finished_at_utc)}`
                    : 'No successful run recorded.'}
                </dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card title="Official documentation" description="Elexon is the source of truth for these datasets.">
          <ul className="space-y-2 text-xs">
            {[
              { label: 'BMRS Insights API documentation', href: GENERAL_DOCS },
              { label: 'Elexon data portal', href: ELEXON_DATA },
              { label: 'FUELHH dataset', href: ELEXON.FUELHH.dataset },
              { label: 'WINDFOR dataset', href: ELEXON.WINDFOR.dataset },
            ].map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-medium text-brand-700 hover:underline"
                >
                  {link.label}
                  <ExternalLink className="h-3 w-3" aria-hidden="true" />
                </a>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="space-y-5">
        <CoverageTable coverage={status?.coverage} />
        <RunTable runs={runs} />
        <IssuesPanel
          issues={issues.data ?? []}
          isLoading={issues.isLoading}
          error={issues.error}
          onRetry={issues.reload}
        />
        {status?.notes?.length > 0 && (
          <Alert tone="neutral" title="Backend notes">
            <ul className="list-disc space-y-1 pl-4">
              {status.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </Alert>
        )}
      </div>
    </>
  )
}

export default function DataSources() {
  useDocumentTitle('Data Sources')
  return (
    <AppDataGate>
      <DataSourcesContent />
    </AppDataGate>
  )
}
