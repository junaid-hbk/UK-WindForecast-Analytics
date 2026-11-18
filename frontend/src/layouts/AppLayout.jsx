import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Menu, RefreshCw, Wind, X } from 'lucide-react'

import Badge from '../components/common/Badge.jsx'
import ErrorState from '../components/common/ErrorState.jsx'
import LoadingState from '../components/common/LoadingState.jsx'
import { useAppData } from '../hooks/useAppData.jsx'
import { NAV_ITEMS } from '../routes/navigation.js'
import { formatLondonDate } from '../utils/datetime.js'

function SidebarContent({ onNavigate }) {
  const { meta, latestDeliveryDate, status } = useAppData()

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--color-brand-600)] text-white">
          <Wind className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white">WindPulse UK</p>
          <p className="text-[11px] text-slate-400">Energy forecast intelligence</p>
        </div>
      </div>

      <nav aria-label="Primary" className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                `group flex items-start gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`mt-0.5 h-4 w-4 shrink-0 ${isActive ? 'text-[var(--color-forecast-soft)]' : 'text-slate-400'}`}
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span className="block font-medium">{item.label}</span>
                    <span className="block text-[11px] leading-snug text-slate-400">
                      {item.description}
                    </span>
                  </span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div className="space-y-2 border-t border-white/10 px-5 py-4 text-[11px] text-slate-400">
        <p>
          Data through{' '}
          <span className="font-semibold text-slate-200">
            {latestDeliveryDate ? formatLondonDate(latestDeliveryDate) : '—'}
          </span>
        </p>
        <p>
          Policy <span className="font-mono text-[10px] text-slate-300">{meta?.default_cutoff_policy ?? '—'}</span>
        </p>
        {status?.stale && <p className="text-amber-300">Data is stale — see Data Sources.</p>}
        <p className="text-[10px] text-slate-500">v{meta?.app_version ?? '—'} · {meta?.environment ?? '—'}</p>
      </div>
    </div>
  )
}

export default function AppLayout() {
  const { isLoading, error, reload, meta } = useAppData()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-slate-100 lg:flex">
      <a
        href="#main-content"
        className="sr-only-focusable absolute left-3 top-3 z-50 rounded bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow"
      >
        Skip to content
      </a>

      <aside className="hidden w-64 shrink-0 bg-[var(--color-ink-900)] lg:block">
        <div className="sticky top-0 h-screen">
          <SidebarContent />
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-slate-900/60"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative h-full w-72 bg-[var(--color-ink-900)] shadow-xl">
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-4 rounded p-1 text-slate-300 hover:text-white"
              aria-label="Close navigation"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex w-full max-w-[1440px] items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="rounded-md border border-slate-200 p-1.5 text-slate-700 lg:hidden"
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </button>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-900">
                Day-ahead wind forecast intelligence
              </p>
              <p className="truncate text-[11px] text-slate-500">
                Elexon FUELHH outturn vs WINDFOR vintages · times shown in Europe/London
              </p>
            </div>

            <div className="hidden items-center gap-2 sm:flex">
              {meta?.default_cutoff_policy && (
                <Badge tone="brand">Cutoff policy · {meta.default_cutoff_policy}</Badge>
              )}
              {meta?.environment && <Badge tone="neutral">{meta.environment}</Badge>}
            </div>

            <button
              type="button"
              onClick={reload}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </header>

        <main id="main-content" className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {isLoading ? (
            <div className="mx-auto max-w-xl py-16">
              <LoadingState label="Connecting to the WindPulse API…" rows={6} />
            </div>
          ) : error ? (
            <ErrorState
              error={error}
              title="The WindPulse API is unavailable"
              onRetry={reload}
            />
          ) : (
            <Outlet />
          )}
        </main>

        <footer className="border-t border-slate-200 bg-white px-4 py-4 text-[11px] text-slate-500 sm:px-6 lg:px-8">
          Source: Elexon BMRS Insights API. Forecasts are day-ahead as-of selections; procurement
          figures are illustrative estimates, not trading advice.
        </footer>
      </div>
    </div>
  )
}
