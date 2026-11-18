import { Inbox } from 'lucide-react'

export default function EmptyState({
  title = 'No data available',
  description,
  action,
  icon: Icon = Inbox,
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-10 text-center">
      <Icon className="h-7 w-7 text-slate-400" aria-hidden="true" />
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      {description && (
        <p className="max-w-md text-xs leading-relaxed text-slate-600">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
