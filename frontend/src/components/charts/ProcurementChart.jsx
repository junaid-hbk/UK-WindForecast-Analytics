import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartFrame from './ChartFrame.jsx'
import ChartTooltip from './ChartTooltip.jsx'

const COLORS = {
  shortfall: 'var(--color-shortfall)',
  surplus: 'var(--color-surplus)',
  balanced: '#94a3b8',
  unavailable: '#cbd5e1',
}

/**
 * Per-interval procurement delta (demand scenario − selected forecast).
 * Positive is a shortfall, negative a potential surplus.
 */
export default function ProcurementChart({ rows = [], height = 320, footnote }) {
  const isEmpty = rows.length === 0

  return (
    <ChartFrame
      title="Scenario delta by settlement period"
      description="Demand scenario minus the day-ahead wind forecast. Positive bars are estimated shortfall, negative bars are potential surplus."
      height={height}
      isEmpty={isEmpty}
      emptyMessage="The scenario returned no intervals to plot."
      footnote={footnote}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
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
              value: 'Delta (MW)',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 11, fill: '#475569' },
            }}
          />
          <ReferenceLine y={0} stroke="#64748b" />
          <Tooltip content={<ChartTooltip unit="MW" />} cursor={{ fill: 'rgba(148, 163, 184, 0.12)' }} />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="delta_mw" name="Demand − forecast" isAnimationActive={false}>
            {rows.map((row) => (
              <Cell key={row.key} fill={COLORS[row.classification] ?? COLORS.balanced} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
