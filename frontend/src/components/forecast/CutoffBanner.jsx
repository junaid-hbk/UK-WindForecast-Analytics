import { Clock, Scissors } from 'lucide-react'

import Badge from '../common/Badge.jsx'
import { formatLondonDateTime, formatUtcTimestamp } from '../../utils/datetime.js'

/**
 * The cutoff is the whole point of an as-of forecast, so it is stated in both
 * local and UTC time and never hidden behind a tooltip.
 */
export default function CutoffBanner({ cutoffUtc, cutoffDefinition, policyCode, mapping, note }) {
  return (
    <div className="rounded-xl border border-brand-100 bg-brand-100/60 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <Scissors className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" aria-hidden="true" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              Decision cutoff
            </p>
            <p className="mt-0.5 text-sm font-semibold text-slate-900">
              {formatLondonDateTime(cutoffUtc)} local
              <span className="ml-2 font-mono text-[11px] font-normal text-slate-600">
                {formatUtcTimestamp(cutoffUtc)} UTC
              </span>
            </p>
            <p className="mt-0.5 text-[11px] text-slate-600">
              {cutoffDefinition ?? 'Cutoff definition unavailable.'}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {policyCode && <Badge tone="brand">{policyCode}</Badge>}
          {mapping && <Badge tone="neutral" icon={Clock}>{mapping}</Badge>}
        </div>
      </div>
      {note && <p className="mt-2 border-t border-brand-100 pt-2 text-[11px] text-slate-600">{note}</p>}
    </div>
  )
}
