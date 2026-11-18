import { screen } from '@testing-library/react'
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
  }
})

import {
  ApiError,
  fetchAccuracySummary,
  fetchActuals,
  fetchActualsDaily,
  fetchDailyAccuracy,
  fetchDataStatus,
  fetchIngestionRuns,
  fetchMetaConfig,
  fetchSelectedForecast,
} from '../api/index.js'
import Dashboard from './Dashboard.jsx'
import { renderWithApp } from '../test/render.jsx'
import {
  accuracyMetrics,
  accuracySummary,
  actualIntervals,
  dailyAccuracy,
  dailyActuals,
  dataStatus,
  ingestionRuns,
  metaConfig,
  selectedDay,
} from '../test/fixtures.js'

function primeHappyPath() {
  fetchMetaConfig.mockResolvedValue({ data: metaConfig, meta: {} })
  fetchIngestionRuns.mockResolvedValue({ data: ingestionRuns, meta: {} })
  fetchDataStatus.mockResolvedValue({ data: dataStatus, meta: {} })
  fetchSelectedForecast.mockResolvedValue({ data: selectedDay, meta: {} })
  fetchActuals.mockResolvedValue({ data: actualIntervals, meta: {} })
  fetchActualsDaily.mockResolvedValue({ data: dailyActuals, meta: {} })
  fetchAccuracySummary.mockResolvedValue({ data: accuracySummary, meta: {} })
  fetchDailyAccuracy.mockResolvedValue({ data: dailyAccuracy, meta: {} })
}

describe('Dashboard', () => {
  beforeEach(() => {
    primeHappyPath()
  })

  it('shows a configuration loading state before metadata arrives', () => {
    fetchMetaConfig.mockReturnValue(new Promise(() => {}))
    renderWithApp(<Dashboard />)
    expect(screen.getByRole('status')).toHaveTextContent(/Loading platform configuration/i)
  })

  it('renders backend metrics, sample counts and the comparison chart', async () => {
    renderWithApp(<Dashboard />)

    expect(await screen.findByText('2,145 MW')).toBeInTheDocument()
    expect(screen.getAllByText('18.5 %').length).toBeGreaterThan(0)
    expect(screen.getByText('+1,852 MW')).toBeInTheDocument()
    expect(screen.getAllByText(/n = 1,488 evaluated of 1,488 expected/).length).toBeGreaterThan(0)
    expect(
      screen.getAllByText('Mean absolute error in MW over evaluated intervals.').length,
    ).toBeGreaterThan(0)

    expect(screen.getByText('Latest available wind forecast')).toBeInTheDocument()
    expect(await screen.findByText('10,000 MW')).toBeInTheDocument()
    expect(await screen.findByText('15,001 MW·h')).toBeInTheDocument()

    expect(
      screen.getByRole('img', { name: /Forecast versus actual generation/ }),
    ).toBeInTheDocument()
    expect(await screen.findByText('Actual wind generation')).toBeInTheDocument()
    expect(screen.getByText('Data availability')).toBeInTheDocument()
  })

  it('renders an honest empty state when the backend evaluated no intervals', async () => {
    fetchAccuracySummary.mockResolvedValue({
      data: {
        ...accuracySummary,
        metrics: { ...accuracyMetrics, n_evaluated: 0, n_expected: 0, insufficient_data: true, coverage_pct: null },
      },
      meta: {},
    })

    renderWithApp(<Dashboard />)

    expect(await screen.findByText('No evaluated intervals in this range')).toBeInTheDocument()
    expect(screen.queryByText('2,145 MW')).not.toBeInTheDocument()
  })

  it('shows an empty state when no forecast selection is stored', async () => {
    fetchSelectedForecast.mockRejectedValue(
      new ApiError({
        code: 'DATA_UNAVAILABLE',
        message: 'No forecast selection stored for 2026-02-28 under policy EPEX_GB_DA_1H_0920.',
      }),
    )

    renderWithApp(<Dashboard />)

    expect(await screen.findByText('No forecast selection stored')).toBeInTheDocument()
  })

  it('surfaces an API error with a retry action', async () => {
    fetchSelectedForecast.mockRejectedValue(
      new ApiError({ code: 'NETWORK_ERROR', message: 'Cannot reach the WindPulse API at http://x/api/v1.' }),
    )

    renderWithApp(<Dashboard />)

    expect(await screen.findByText('Forecast unavailable')).toBeInTheDocument()
    expect(screen.getByText(/Cannot reach the WindPulse API/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Try again/i })).toBeInTheDocument()
  })

  it('defaults to the January 2026 decision window from the loaded coverage', async () => {
    const january = Array.from({ length: 31 }, (_, index) => ({
      settlement_date: `2026-01-${String(index + 1).padStart(2, '0')}`,
      intervals: 48,
      selected_intervals: 48,
      missing_intervals: 0,
    }))
    // 1 Feb delivery is the D+1 outcome of the 31 Jan decision.
    january.push({
      settlement_date: '2026-02-01',
      intervals: 48,
      selected_intervals: 48,
      missing_intervals: 0,
    })
    fetchDataStatus.mockResolvedValue({
      data: { ...dataStatus, coverage: january },
      meta: {},
    })

    renderWithApp(<Dashboard />)

    expect(await screen.findByText('2,145 MW')).toBeInTheDocument()
    // January decisions under a D-1 policy deliver from 2 Jan to 1 Feb.
    expect(fetchAccuracySummary).toHaveBeenCalledWith(
      expect.objectContaining({ from: '2026-01-02', to: '2026-02-01' }),
      expect.anything(),
    )
    expect(screen.getByText(/Delivery window 02 Jan 2026 to 01 Feb 2026/)).toBeInTheDocument()
  })
})
