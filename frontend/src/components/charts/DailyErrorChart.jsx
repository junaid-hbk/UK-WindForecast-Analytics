import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartFrame from './ChartFrame.jsx'
import ChartTooltip from './ChartTooltip.jsx'

/** Daily MAE and signed bias, both straight from the accuracy API. */
export default function DailyErrorChart({ rows = [], height = 300, footnote }) {
  const data = rows.filter((row) => row.mae_mw !== null || row.bias_mw !== null)
  const isEmpty = data.length === 0

  return (
    <ChartFrame
      title="Daily error and bias"
      description="Mean absolute error and mean signed bias in MW, as calculated by the backend for each settlement day."
      height={height}
      isEmpty={isEmpty}
      emptyMessage="No evaluated day exists in this range."
      footnote={footnote}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
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
            tick={{ fontSize: 10, fill: '#475569' }}
            tickFormatter={(value) => value.toLocaleString('en-GB')}
            width={62}
            label={{
              value: 'Error (MW)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
          <Tooltip content={<ChartTooltip unit="MW" />} />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="mae_mw"
            name="MAE"
            stroke="var(--color-forecast)"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="bias_mw"
            name="Bias (signed)"
            stroke="var(--color-shortfall)"
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
