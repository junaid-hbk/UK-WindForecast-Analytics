import Card from '../common/Card.jsx'
import DataTable from '../common/DataTable.jsx'
import EmptyState from '../common/EmptyState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { formatLondonDate } from '../../utils/datetime.js'
import { formatCount, formatMW, formatPercent } from '../../utils/format.js'

export default function DailySummaryTable({ rows = [], isLoading, error, onRetry, limit = 7 }) {
  const newestFirst = [...rows].slice(-limit).reverse()

  const columns = [
    {
      key: 'settlement_date',
      header: 'Settlement day',
      render: (row) => formatLondonDate(row.settlement_date),
    },
    {
      key: 'accuracy_pct',
      header: 'Accuracy',
      align: 'right',
      numeric: true,
      render: (row) => formatPercent(row.accuracy_pct),
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
      key: 'bias',
      header: 'Bias',
      align: 'right',
      numeric: true,
      render: (row) => formatMW(row.metrics?.bias_mw),
    },
    {
      key: 'n',
      header: 'Intervals (n)',
      align: 'right',
      numeric: true,
      render: (row) => formatCount(row.metrics?.n_evaluated),
    },
  ]

  return (
    <Card
      title="Daily performance summary"
      description="Most recent evaluated settlement days in the analysis window. Days without observations are omitted by the API."
      bodyClassName="px-0 py-0"
    >
      {isLoading ? (
        <div className="px-5 py-4">
          <LoadingState label="Loading daily metrics…" rows={4} compact />
        </div>
      ) : error ? (
        <div className="px-5 py-4">
          <ErrorState error={error} onRetry={onRetry} title="Daily metrics unavailable" />
        </div>
      ) : newestFirst.length === 0 ? (
        <div className="px-5 py-4">
          <EmptyState
            title="No evaluated days"
            description="No settlement day in this window has both a selected forecast and an actual outturn."
          />
        </div>
      ) : (
        <DataTable
          caption="Daily forecast accuracy: accuracy percentage, MAE, WAPE, bias and number of evaluated intervals"
          columns={columns}
          rows={newestFirst}
          getRowKey={(row) => row.settlement_date}
          dense
        />
      )}
    </Card>
  )
}
