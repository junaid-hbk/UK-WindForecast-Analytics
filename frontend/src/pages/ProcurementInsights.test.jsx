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
    fetchProcurementScenario: vi.fn(),
  }
})

import {
  ApiError,
  fetchDataStatus,
  fetchIngestionRuns,
  fetchMetaConfig,
  fetchProcurementScenario,
} from '../api/index.js'
import ProcurementInsights from './ProcurementInsights.jsx'
import { renderWithApp } from '../test/render.jsx'
import {
  dataStatus,
  ingestionRuns,
  metaConfig,
  procurementScenario,
} from '../test/fixtures.js'

function prime() {
  fetchMetaConfig.mockResolvedValue({ data: metaConfig, meta: {} })
  fetchIngestionRuns.mockResolvedValue({ data: ingestionRuns, meta: {} })
  fetchDataStatus.mockResolvedValue({ data: dataStatus, meta: {} })
}

describe('ProcurementInsights', () => {
  beforeEach(() => {
    prime()
  })

  it('does not call the API when demand is missing', async () => {
    const user = userEvent.setup()
    renderWithApp(<ProcurementInsights />, { route: '/procurement' })

    await screen.findByText('Demand scenario')
    await user.click(screen.getByRole('button', { name: /Calculate scenario/i }))

    expect(await screen.findByText('Enter a demand scenario in MW.')).toBeInTheDocument()
    expect(fetchProcurementScenario).not.toHaveBeenCalled()
    expect(screen.getByText('No scenario calculated yet')).toBeInTheDocument()
  })

  it('rejects negative demand', async () => {
    const user = userEvent.setup()
    renderWithApp(<ProcurementInsights />, { route: '/procurement' })

    await screen.findByLabelText('Demand scenario (MW)')
    await user.type(screen.getByLabelText('Demand scenario (MW)'), '-5')
    await user.click(screen.getByRole('button', { name: /Calculate scenario/i }))

    expect(await screen.findByText('Demand must be greater than zero.')).toBeInTheDocument()
    expect(fetchProcurementScenario).not.toHaveBeenCalled()
  })

  it('renders the backend calculation and the illustrative disclaimer', async () => {
    const user = userEvent.setup()
    fetchProcurementScenario.mockResolvedValue({
      data: procurementScenario,
      meta: {
        sign_convention: 'positive delta = estimated shortfall, negative = potential surplus',
        excluded_inputs: ['actual demand', 'prices'],
      },
    })

    renderWithApp(<ProcurementInsights />, { route: '/procurement' })

    const demand = await screen.findByLabelText('Demand scenario (MW)')
    await user.type(demand, '15000')
    await user.click(screen.getByRole('button', { name: /Calculate scenario/i }))

    expect(await screen.findByText(/360,000 MW·h/)).toBeInTheDocument()
    expect(screen.getByText(/278,630 MW·h/)).toBeInTheDocument()
    expect(screen.getByText(/\+81,370 MW·h/)).toBeInTheDocument()
    expect(screen.getAllByText(/Illustrative estimate only/).length).toBeGreaterThan(0)
    expect(screen.getByText(/actual demand, prices/)).toBeInTheDocument()

    expect(fetchProcurementScenario).toHaveBeenCalledWith(
      expect.objectContaining({
        demandMw: 15000,
        dateFrom: '2026-01-02',
        dateTo: '2026-02-01',
        policy: 'EPEX_GB_DA_1H_0920',
        includeIntervals: true,
      }),
      expect.anything(),
    )

    expect(
      screen.getByRole('img', { name: /Scenario delta by settlement period/ }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('shortfall').length).toBeGreaterThan(0)
  })

  it('surfaces a backend error', async () => {
    const user = userEvent.setup()
    fetchProcurementScenario.mockRejectedValue(
      new ApiError({ code: 'DATA_UNAVAILABLE', message: 'No selection stored for this range.' }),
    )

    renderWithApp(<ProcurementInsights />, { route: '/procurement' })

    await user.type(await screen.findByLabelText('Demand scenario (MW)'), '15000')
    await user.click(screen.getByRole('button', { name: /Calculate scenario/i }))

    expect(await screen.findByText('Scenario could not be calculated')).toBeInTheDocument()
    expect(screen.getByText('No selection stored for this range.')).toBeInTheDocument()
  })
})
