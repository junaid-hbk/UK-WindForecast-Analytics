import { formatCount, formatNumber } from '../../utils/format.js'

/** Shared Recharts tooltip: label, swatch, series name and unit. */
export default function ChartTooltip({ active, payload, label, unit = 'MW', extra = [] }) {
  if (!active || !payload || payload.length === 0) return null

  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-semibold text-slate-800">{label}</p>
      <ul className="mt-1 space-y-0.5">
        {payload.map((item) => (
          <li key={item.dataKey ?? item.name} className="flex items-center gap-2 text-slate-700">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: item.color ?? item.stroke ?? '#64748b' }}
              aria-hidden="true"
            />
            <span>{item.name}</span>
            <span className="ml-auto pl-3 font-medium tabular-nums text-slate-900">
              {item.value === null || item.value === undefined
                ? 'no data'
                : `${formatNumber(item.value, 1)} ${unit}`}
            </span>
          </li>
        ))}
      </ul>
      {extra.length > 0 && (
        <dl className="mt-1 border-t border-slate-100 pt-1 text-[11px] text-slate-600">
          {extra
            .filter((row) => row.value !== null && row.value !== undefined)
            .map((row) => (
              <div key={row.label} className="flex justify-between gap-4">
                <dt>{row.label}</dt>
                <dd className="font-medium tabular-nums text-slate-800">
                  {row.count ? formatCount(row.value) : formatNumber(row.value, 1)}
                  {row.unit ? ` ${row.unit}` : ''}
                </dd>
              </div>
            ))}
        </dl>
      )}
    </div>
  )
}
