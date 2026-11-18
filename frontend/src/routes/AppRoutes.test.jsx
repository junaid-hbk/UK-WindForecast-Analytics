import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/index.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    fetchMetaConfig: vi.fn(),
    fetchIngestionRuns: vi.fn(),
    fetchDataStatus: vi.fn(),
    fetchSelectedForecast: vi.fn(),
    fetchActuals: vi.fn(),
    fetchActualsDaily: vi.fn(),
    fetchAccuracySummary: vi.fn(),
    fetchDailyAccuracy: vi.fn(),
    fetchLeadTimeAccuracy: vi.fn(),
    fetchVintages: vi.fn(),
    fetchVintage: vi.fn(),
    fetchDataIssues: vi.fn(),
  }
})

import {
  fetchAccuracySummary,
  fetchActuals,
  fetchActualsDaily,
  fetchDailyAccuracy,
  fetchDataIssues,
  fetchDataStatus,
  fetchIngestionRuns,
  fetchLeadTimeAccuracy,
  fetchMetaConfig,
  fetchSelectedForecast,
  fetchVintage,
  fetchVintages,
} from '../api/index.js'
import App from '../App.jsx'
import { renderWithApp } from '../test/render.jsx'
import {
  accuracySummary,
  actualIntervals,
  dailyAccuracy,
  dailyActuals,
  dataStatus,
  ingestionRuns,
  leadTimeAccuracy,
  metaConfig,
  selectedDay,
  vintageDetail,
  vintages,
} from '../test/fixtures.js'

beforeEach(() => {
  fetchMetaConfig.mockResolvedValue({ data: metaConfig, meta: {} })
  fetchIngestionRuns.mockResolvedValue({ data: ingestionRuns, meta: {} })
  fetchDataStatus.mockResolvedValue({ data: dataStatus, meta: {} })
  fetchSelectedForecast.mockResolvedValue({ data: selectedDay, meta: {} })
  fetchActuals.mockResolvedValue({ data: actualIntervals, meta: {} })
  fetchActualsDaily.mockResolvedValue({ data: dailyActuals, meta: {} })
  fetchAccuracySummary.mockResolvedValue({ data: accuracySummary, meta: {} })
  fetchDailyAccuracy.mockResolvedValue({ data: dailyAccuracy, meta: {} })
  fetchLeadTimeAccuracy.mockResolvedValue({ data: leadTimeAccuracy, meta: {} })
  fetchVintages.mockResolvedValue({ data: vintages, meta: { vintages: 2, used: 1 } })
  fetchVintage.mockResolvedValue({ data: vintageDetail, meta: {} })
  fetchDataIssues.mockResolvedValue({ data: [], meta: {} })
})

describe('AppRoutes', () => {
  it('renders the dashboard at / with an active navigation item', async () => {
    renderWithApp(<App />)

    expect(
      await screen.findByRole('heading', { name: 'Wind forecast dashboard' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Dashboard/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument()
  })

  it('navigates to accuracy and procurement', async () => {
    const user = userEvent.setup()
    renderWithApp(<App />)

    await screen.findByRole('heading', { name: 'Wind forecast dashboard' })

    await user.click(screen.getByRole('link', { name: /Forecast Accuracy/ }))
    expect(await screen.findByRole('heading', { name: 'Forecast accuracy' })).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /Procurement Insights/ }))
    expect(await screen.findByRole('heading', { name: 'Procurement insights' })).toBeInTheDocument()
  })

  it('shows a not-found page for an unknown route', async () => {
    renderWithApp(<App />, { route: '/does-not-exist' })

    expect(await screen.findByText('Page not found')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toBeInTheDocument()
  })
})
