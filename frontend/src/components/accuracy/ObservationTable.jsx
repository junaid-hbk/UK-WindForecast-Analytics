import Card from '../common/Card.jsx'
import DataTable from '../common/DataTable.jsx'
import { formatCount, formatPercent } from '../../utils/format.js'

const ROWS = [
  { key: 'n_evaluated', label: 'Intervals evaluated', hint: 'Both a selected forecast and an actual exist.' },
  { key: 'n_expected', label: 'Intervals expected', hint: 'Settlement periods in the requested range.' },
  { key: 'n_missing_forecast', label: 'Missing forecast', hint: 'No eligible vintage covered the interval.' },
  { key: 'n_missing_actual', label: 'Missing actual', hint: 'No FUELHH outturn was stored.' },
  { key: 'n_no_vintage_before_cutoff', label: 'No vintage before cutoff', hint: 'Selection could not be made.' },
  { key: 'n_duplicate_intervals', label: 'Duplicate intervals', hint: 'Excluded from the evaluated set.' },
  { key: 'n_invalid_timestamps', label: 'Invalid timestamps', hint: 'Excluded from the evaluated set.' },
]

export default function ObservationTable({ metrics }) {
  const rows = ROWS.map((row) => ({
    ...row,
    value: metrics?.[row.key],
  }))

  return (
    <Card
      title="Observation counts"
      description="The evaluated sample behind every metric above. Missing data is excluded and counted, never imputed."
      bodyClassName="px-0 py-0"
      footer={
        metrics
          ? `Coverage ${formatPercent(metrics.coverage_pct)} of expected intervals.`
          : 'No metrics returned for this selection.'
      }
    >
      <DataTable
        caption="Observation composition: evaluated intervals, expected intervals and exclusion reasons"
        columns={[
          { key: 'label', header: 'Measure' },
          {
            key: 'hint',
            header: 'Meaning',
            render: (row) => <span className="text-xs text-slate-600">{row.hint}</span>,
          },
          {
            key: 'value',
            header: 'Count',
            align: 'right',
            numeric: true,
            render: (row) => formatCount(row.value),
          },
        ]}
        rows={rows}
        getRowKey={(row) => row.key}
        dense
        emptyMessage="No observation counts available."
      />
    </Card>
  )
}
