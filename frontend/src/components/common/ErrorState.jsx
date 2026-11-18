import { AlertTriangle, RefreshCw } from 'lucide-react'

/**
 * Renders a normalised `ApiError`. The backend's own message is shown verbatim;
 * technical details stay behind a disclosure so they are available, not dominant.
 */
export default function ErrorState({ error, title = 'Could not load this data', onRetry }) {
  if (!error) return null

  const details = error.details ? JSON.stringify(error.details, null, 2) : null

  return (
    <div
      role="alert"
      className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-900"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{title}</p>
          <p className="mt-1 leading-relaxed">{error.message}</p>
          <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-rose-700">
            {error.code}
            {error.status ? ` · HTTP ${error.status}` : ''}
          </p>

          {details && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs font-medium text-rose-800">
                Technical details
              </summary>
              <pre className="mt-1 max-h-48 overflow-auto rounded bg-white/70 p-2 text-[11px] leading-relaxed text-rose-900">
                {details}
              </pre>
            </details>
          )}

          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-rose-300 bg-white px-3 py-1.5 text-xs font-semibold text-rose-900 hover:bg-rose-100"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
