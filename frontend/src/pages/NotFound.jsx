import { Link } from 'react-router-dom'

import EmptyState from '../components/common/EmptyState.jsx'
import { useDocumentTitle } from '../hooks/useDocumentTitle.js'

export default function NotFound() {
  useDocumentTitle('Page not found')

  return (
    <div className="py-10">
      <EmptyState
        title="Page not found"
        description="That route does not exist in WindPulse UK. Use the navigation to reach the dashboard, forecast explorer, accuracy, procurement or data sources."
        action={
          <Link
            to="/"
            className="inline-flex rounded-md bg-[var(--color-brand-700)] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[var(--color-brand-600)]"
          >
            Back to dashboard
          </Link>
        }
      />
    </div>
  )
}
