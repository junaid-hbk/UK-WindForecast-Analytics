import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartFrame from './ChartFrame.jsx'
import ChartTooltip from './ChartTooltip.jsx'

const OVER = 'var(--color-shortfall)'
const UNDER = 'var(--color-surplus)'

/**
 * Per-settlement-period forecast error (forecast − actual).
 * Bars are coloured by sign so direction is not conveyed by position alone.
 */
export default function IntervalErrorChart({ rows = [], height = 300, footnote }) {
  const data = rows.filter((row) => row.difference_mw !== null)
  const isEmpty = data.length === 0

  return (
    <ChartFrame
      title="Forecast error over settlement periods"
      description="Signed difference for each half hour: positive means the forecast was too high. Aggregate metrics come from the accuracy API, not from this chart."
      height={height}
      isEmpty={isEmpty}
      emptyMessage="No interval has both a selected forecast and an actual outturn, so no error can be shown."
      footnote={footnote}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#475569' }}
            interval="preserveStartEnd"
            minTickGap={16}
            tickMargin={8}
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
              value: 'Error (MW)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Tooltip content={<ChartTooltip unit="MW" />} />
          <Bar dataKey="difference_mw" name="Forecast − actual" isAnimationActive={false}>
            {data.map((row) => (
              <Cell key={row.key} fill={row.difference_mw >= 0 ? OVER : UNDER} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
