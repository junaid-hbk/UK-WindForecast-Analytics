import { Gauge, Ruler, Scale, Target } from 'lucide-react'

import EmptyState from '../common/EmptyState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import MetricCard from '../common/MetricCard.jsx'
import StatGrid from '../common/StatGrid.jsx'
import {
  formatCount,
  formatMW,
  formatPercent,
  formatSignedMW,
  formatSignedPercent,
} from '../../utils/format.js'
import { formatLondonDate } from '../../utils/datetime.js'

export default function KpiStrip({ metrics, definitions = {}, range, isLoading, error, onRetry }) {
  if (isLoading) {
    return (
      <StatGrid>
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="h-36 animate-pulse rounded-xl bg-slate-100" />
        ))}
      </StatGrid>
    )
  }

  if (error) {
    return <ErrorState error={error} title="Accuracy metrics unavailable" onRetry={onRetry} />
  }

  if (!metrics) {
    return (
      <EmptyState
        title="No metrics loaded"
        description="No accuracy response is available for this selection yet. Check the date range and cutoff policy."
      />
    )
  }

  if (metrics.insufficient_data) {
    return (
      <EmptyState
        title="No evaluated intervals in this range"
        description="The backend found no settlement period with both a selected forecast and an actual outturn. Nothing is estimated or imputed in the dashboard."
      />
    )
  }

  const sample = `n = ${formatCount(metrics.n_evaluated)} evaluated of ${formatCount(
    metrics.n_expected,
  )} expected · coverage ${formatPercent(metrics.coverage_pct)}`

  const cards = [
    {
      label: 'MAE',
      kpi: 'mean absolute error',
      value: formatMW(metrics.mae_mw),
      icon: Target,
      definition: definitions.mae,
    },
    {
      label: 'RMSE',
      kpi: 'root mean squared error',
      value: formatMW(metrics.rmse_mw),
      icon: Ruler,
      definition: definitions.rmse,
    },
    {
      label: 'WAPE',
      kpi: 'weighted absolute % error',
      value: formatPercent(metrics.wape_pct),
      icon: Gauge,
      definition: definitions.wape,
      hint: metrics.wape_note ?? undefined,
    },
    {
      label: 'Bias',
      kpi: 'mean signed error',
      value: formatSignedMW(metrics.bias_mw),
      icon: Scale,
      hint: `${formatSignedPercent(metrics.bias_pct)} of actual generation`,
      definition: definitions.bias,
    },
  ]

  return (
    <div>
      <StatGrid>
        {cards.map((card) => (
          <MetricCard key={card.label} {...card} sample={sample} />
        ))}
      </StatGrid>
      {range && (
        <p className="mt-2 text-[11px] text-slate-500">
          Delivery window {formatLondonDate(range.from)} to {formatLondonDate(range.to)} · decisions
          taken at the policy cutoff on the preceding day; metrics calculated by the backend over
          the selected forecast vintage only.
        </p>
      )}
    </div>
  )
}
