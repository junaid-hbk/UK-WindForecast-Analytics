/**
 * One authoritative metric taken straight from the API.
 *
 * `sample` always states the observation count so a number is never shown
 * without the dataset that produced it.
 */
export default function MetricCard({
  label,
  value,
  kpi,
  hint,
  sample,
  definition,
  icon: Icon,
  tone = 'default',
}) {
  const valueTone =
    tone === 'warning' ? 'text-amber-800' : tone === 'brand' ? 'text-brand-700' : 'text-slate-900'

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          {label}
        </p>
        {Icon && <Icon className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />}
      </div>

      <p className={`mt-2 text-2xl font-semibold tabular-nums ${valueTone}`}>{value}</p>
      {kpi && <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">{kpi}</p>}
      {hint && <p className="mt-1 text-xs text-slate-600">{hint}</p>}

      <div className="mt-auto pt-3">
        {sample && <p className="text-[11px] font-medium text-slate-500">{sample}</p>}
        {definition && (
          <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{definition}</p>
        )}
      </div>
    </div>
  )
}
