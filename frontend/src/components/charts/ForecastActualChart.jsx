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

import { formatDurationMinutes } from '../../utils/datetime.js'
import ChartFrame from './ChartFrame.jsx'
import ChartTooltip from './ChartTooltip.jsx'

export default function ForecastActualChart({
  rows = [],
  title = 'As-of forecast vs actual generation',
  description = 'Each point is one settlement period. Missing values leave a gap rather than a zero.',
  height = 340,
  footnote,
}) {
  const isEmpty = !rows.some((row) => row.forecast_mw !== null || row.actual_mw !== null)

  return (
    <ChartFrame
      title={title}
      description={description}
      height={height}
      isEmpty={isEmpty}
      emptyMessage="Neither a selected forecast nor an actual outturn exists for this day."
      footnote={footnote}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#475569' }}
            interval="preserveStartEnd"
            tickMargin={8}
            minTickGap={16}
            label={{
              value: 'Settlement period start (Europe/London)',
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
              value: 'Generation (MW)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <Tooltip
            content={<ChartTooltip unit="MW" />}
            labelFormatter={(label, payload) => {
              const row = payload?.[0]?.payload
              if (!row) return label
              const lead = formatDurationMinutes(row.lead_time_minutes)
              return `${row.local_start ?? label} · lead ${lead}`
            }}
          />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="forecast_mw"
            name="As-of forecast (selected at cutoff)"
            stroke="var(--color-forecast)"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="actual_mw"
            name="Actual wind outturn (FUELHH)"
            stroke="var(--color-actual)"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
