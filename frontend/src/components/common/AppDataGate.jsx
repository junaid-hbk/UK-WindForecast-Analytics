import EmptyState from './EmptyState.jsx'
import ErrorState from './ErrorState.jsx'
import LoadingState from './LoadingState.jsx'
import { useAppData } from '../../hooks/useAppData.jsx'

/**
 * Pages depend on `/meta/config` (policies, definitions, data window).
 * This gate keeps that dependency explicit and testable.
 */
export default function AppDataGate({ children }) {
  const { isLoading, error, meta, reload } = useAppData()

  if (isLoading) {
    return (
      <div className="mx-auto max-w-xl py-10">
        <LoadingState label="Loading platform configuration…" rows={5} />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState error={error} title="Platform configuration unavailable" onRetry={reload} />
    )
  }

  if (!meta) {
    return (
      <EmptyState
        title="Platform metadata is missing"
        description="The API responded without /meta/config data, so policies and metric definitions cannot be shown."
      />
    )
  }

  return children
}
