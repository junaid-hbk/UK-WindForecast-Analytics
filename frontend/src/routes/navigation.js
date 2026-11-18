import {
  Activity,
  Database,
  LayoutDashboard,
  SlidersHorizontal,
  Target,
} from 'lucide-react'

/** Single source of truth for navigation, reused by the shell and tests. */
export const NAV_ITEMS = [
  {
    to: '/',
    label: 'Dashboard',
    description: 'Latest forecast and accuracy at a glance',
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: '/forecast',
    label: 'Forecast Explorer',
    description: 'Settlement periods, vintages and the cutoff',
    icon: Activity,
  },
  {
    to: '/accuracy',
    label: 'Forecast Accuracy',
    description: 'MAE, RMSE, WAPE, bias and lead time',
    icon: Target,
  },
  {
    to: '/procurement',
    label: 'Procurement Insights',
    description: 'Illustrative demand-scenario deltas',
    icon: SlidersHorizontal,
  },
  {
    to: '/data',
    label: 'Data Sources',
    description: 'Elexon ingestion, coverage and runs',
    icon: Database,
  },
]
