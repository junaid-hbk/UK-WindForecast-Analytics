const TONES = {
  neutral: 'border-slate-200 bg-slate-100 text-slate-700',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
  brand: 'border-brand-100 bg-brand-100 text-brand-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  danger: 'border-rose-200 bg-rose-50 text-rose-800',
}

export default function Badge({ tone = 'neutral', children, icon: Icon, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${TONES[tone] ?? TONES.neutral} ${className}`}
    >
      {Icon && <Icon className="h-3 w-3" aria-hidden="true" />}
      {children}
    </span>
  )
}

export function statusTone(status) {
  switch (status) {
    case 'succeeded':
      return 'success'
    case 'running':
      return 'info'
    case 'failed':
      return 'danger'
    case 'partial':
      return 'warning'
    default:
      return 'neutral'
  }
}
