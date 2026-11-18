import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/index.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    fetchMetaConfig: vi.fn(),
    fetchIngestionRuns: vi.fn(),
    fetchDataStatus: vi.fn(),
    fetchSelectedForecast: vi.fn(),
    fetchVintages: vi.fn(),
    fetchVintage: vi.fn(),
    fetchActuals: vi.fn(),
  }
})

import {
  fetchActuals,
  fetchDataStatus,
  fetchIngestionRuns,
  fetchMetaConfig,
  fetchSelectedForecast,
  fetchVintage,
  fetchVintages,
} from '../api/index.js'
import ForecastExplorer from './ForecastExplorer.jsx'
import { renderWithApp } from '../test/render.jsx'
import {
  actualIntervals,
  dataStatus,
  ingestionRuns,
  metaConfig,
  selectedDay,
  vintageDetail,
  vintages,
} from '../test/fixtures.js'

function prime() {
  fetchMetaConfig.mockResolvedValue({ data: metaConfig, meta: {} })
  fetchIngestionRuns.mockResolvedValue({ data: ingestionRuns, meta: {} })
  fetchDataStatus.mockResolvedValue({ data: dataStatus, meta: {} })
  fetchSelectedForecast.mockResolvedValue({ data: selectedDay, meta: {} })
  fetchVintages.mockResolvedValue({ data: vintages, meta: { vintages: 2, used: 1 } })
  fetchVintage.mockResolvedValue({ data: vintageDetail, meta: { points: 2 } })
  fetchActuals.mockResolvedValue({ data: actualIntervals, meta: {} })
}

describe('ForecastExplorer', () => {
  beforeEach(() => {
    prime()
  })

  it('shows the decision cutoff, the used vintage and settlement detail', async () => {
    renderWithApp(<ForecastExplorer />, { route: '/forecast' })

    expect(await screen.findByText('Decision cutoff')).toBeInTheDocument()
    expect(await screen.findByText(/2026-02-27T09:20:00Z/)).toBeInTheDocument()
    expect(await screen.findByText('Used for the decision')).toBeInTheDocument()
    expect(await screen.findByText('Published after cutoff')).toBeInTheDocument()
    expect(await screen.findByText('Hours in day')).toBeInTheDocument()
    expect(await screen.findByText('Settlement period detail')).toBeInTheDocument()
    expect(await screen.findByText('10,000 MW')).toBeInTheDocument()
    expect(screen.getByText('Forecast lineage')).toBeInTheDocument()
  })

  it('refetches when the delivery date changes', async () => {
    renderWithApp(<ForecastExplorer />, { route: '/forecast' })
    await screen.findByText('Decision cutoff')

    await waitFor(() =>
      expect(fetchSelectedForecast).toHaveBeenCalledWith(
        expect.objectContaining({ deliveryDate: '2026-02-28' }),
        expect.anything(),
      ),
    )

    fireEvent.change(screen.getByLabelText('Delivery date'), { target: { value: '2026-02-01' } })

    await waitFor(() =>
      expect(fetchSelectedForecast).toHaveBeenCalledWith(
        expect.objectContaining({ deliveryDate: '2026-02-01' }),
        expect.anything(),
      ),
    )
  })

  it('rejects a date outside the loaded window without calling the API', async () => {
    renderWithApp(<ForecastExplorer />, { route: '/forecast' })
    await screen.findByText('Decision cutoff')

    const callsBefore = fetchSelectedForecast.mock.calls.length
    fireEvent.change(screen.getByLabelText('Delivery date'), { target: { value: '2025-12-01' } })

    expect(
      await screen.findByText('The loaded data window starts on 2026-01-01.'),
    ).toBeInTheDocument()
    expect(fetchSelectedForecast).toHaveBeenCalledTimes(callsBefore)
    expect(screen.getByText('Adjust the delivery date')).toBeInTheDocument()
  })

  it('renders missing forecasts as gaps, not zeroes', async () => {
    renderWithApp(<ForecastExplorer />, { route: '/forecast' })

    const rows = await screen.findAllByRole('row')
    // Header row + 3 settlement periods.
    expect(rows.length).toBeGreaterThanOrEqual(4)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})
