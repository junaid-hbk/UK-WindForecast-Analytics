import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartFrame from '../charts/ChartFrame.jsx'
import ChartTooltip from '../charts/ChartTooltip.jsx'
import { formatLondonDateTime } from '../../utils/datetime.js'

const SERIES_COLORS = ['#0e7490', '#b45309', '#4338ca']

/**
 * Native hourly points, exactly as each vintage was published.
 * No hourly→half-hourly mapping is applied here; that mapping is the backend's
 * documented job and is already reflected in the as-of selection.
 */
export default function VintageComparisonChart({ rows = [], series = [], height = 300 }) {
  const isEmpty = rows.length === 0 || series.length === 0

  return (
    <ChartFrame
      title="Forecast vintages compared (hourly, as published)"
      description="Overlay of the selected publication vintages on their own timestamps. Gaps stay empty where a vintage published no point."
      height={height}
      isEmpty={isEmpty}
      emptyMessage="Select one or more vintages above to compare their published series."
      footnote="Hourly WINDFOR resolution. The 30-minute as-of selection is shown separately in the chart above."
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#475569' }}
            tickMargin={8}
            minTickGap={16}
            interval="preserveStartEnd"
            label={{
              value: 'Hour starting (Europe/London)',
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
              value: 'Forecast generation (MW)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <Tooltip content={<ChartTooltip unit="MW" />} />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} />
          {series.map((entry, index) => (
            <Line
              key={entry.key}
              type="monotone"
              dataKey={entry.key}
              name={`#${entry.id} · ${formatLondonDateTime(entry.publishTime)}`}
              stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
