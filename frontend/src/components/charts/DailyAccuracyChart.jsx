import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartFrame from './ChartFrame.jsx'
import ChartTooltip from './ChartTooltip.jsx'

/** Daily accuracy convenience metric: 100 − WAPE, as returned by the API. */
export default function DailyAccuracyChart({ rows = [], height = 300, footnote }) {
  const data = rows.filter((row) => row.accuracy_pct !== null)
  const isEmpty = data.length === 0

  return (
    <ChartFrame
      title="Daily accuracy (100 − WAPE)"
      description="Computed by the backend per settlement day. Days without evaluated intervals are omitted, never plotted as zero."
      height={height}
      isEmpty={isEmpty}
      emptyMessage="No day in this range has both forecast and actual values."
      footnote={footnote}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#475569' }}
            tickMargin={8}
            interval="preserveStartEnd"
            label={{
              value: 'Settlement day',
              position: 'insideBottom',
              offset: -12,
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#475569' }}
            width={52}
            label={{
              value: 'Accuracy (%)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <Tooltip
            content={<ChartTooltip unit="%" />}
            cursor={{ fill: 'rgba(148, 163, 184, 0.12)' }}
          />
          <Bar
            dataKey="accuracy_pct"
            name="Accuracy (100 − WAPE)"
            fill="var(--color-forecast)"
            isAnimationActive={false}
            radius={[2, 2, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
