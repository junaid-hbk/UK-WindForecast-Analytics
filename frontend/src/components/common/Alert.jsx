import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from 'lucide-react'

const TONES = {
  info: {
    wrapper: 'border-sky-200 bg-sky-50 text-sky-900',
    icon: 'text-sky-700',
    Icon: Info,
  },
  warning: {
    wrapper: 'border-amber-200 bg-amber-50 text-amber-900',
    icon: 'text-amber-700',
    Icon: AlertTriangle,
  },
  danger: {
    wrapper: 'border-rose-200 bg-rose-50 text-rose-900',
    icon: 'text-rose-700',
    Icon: ShieldAlert,
  },
  success: {
    wrapper: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    icon: 'text-emerald-700',
    Icon: CheckCircle2,
  },
  neutral: {
    wrapper: 'border-slate-200 bg-slate-50 text-slate-800',
    icon: 'text-slate-500',
    Icon: Info,
  },
}

export default function Alert({ tone = 'info', title, children, icon: OverrideIcon }) {
  const config = TONES[tone] ?? TONES.info
  const Icon = OverrideIcon ?? config.Icon

  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${config.wrapper}`}>
      <div className="flex items-start gap-2.5">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${config.icon}`} aria-hidden="true" />
        <div className="min-w-0">
          {title && <p className="font-semibold">{title}</p>}
          <div className={`text-xs leading-relaxed ${title ? 'mt-1' : ''}`}>{children}</div>
        </div>
      </div>
    </div>
  )
}
