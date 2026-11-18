import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartFrame from './ChartFrame.jsx'
import ChartTooltip from './ChartTooltip.jsx'

/**
 * MAE by lead-time bucket. Empty buckets have no bar (not a zero bar) and are
 * called out in the footnote so the shape of the chart is never misread.
 */
export default function LeadTimeChart({ rows = [], height = 300, footnote }) {
  const isEmpty = !rows.some((row) => row.mae_mw !== null)
  const emptyLabels = rows.filter((row) => row.mae_mw === null).map((row) => row.label)

  return (
    <ChartFrame
      title="Accuracy by forecast lead time"
      description="Mean absolute error per half-open lead-time bucket, calculated by the backend over the selected range."
      height={height}
      isEmpty={isEmpty}
      emptyMessage="No lead-time bucket contains an interval with both a forecast and an actual."
      footnote={
        footnote ??
        (emptyLabels.length > 0
          ? `Buckets with no observations are left blank: ${emptyLabels.join(', ')}.`
          : undefined)
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#475569' }}
            tickMargin={8}
            label={{
              value: 'Lead time bucket',
              position: 'insideBottom',
              offset: -12,
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#475569' }}
            tickFormatter={(value) => value.toLocaleString('en-GB')}
            width={62}
            label={{
              value: 'MAE (MW)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <Tooltip content={<ChartTooltip unit="MW" />} cursor={{ fill: 'rgba(148, 163, 184, 0.12)' }} />
          <Bar dataKey="mae_mw" name="MAE" isAnimationActive={false} radius={[2, 2, 0, 0]}>
            {rows.map((row) => (
              <Cell
                key={row.key}
                fill={row.mae_mw === null ? 'transparent' : 'var(--color-forecast)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
