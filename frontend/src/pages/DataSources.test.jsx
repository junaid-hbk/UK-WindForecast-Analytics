import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/index.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    fetchMetaConfig: vi.fn(),
    fetchIngestionRuns: vi.fn(),
    fetchDataStatus: vi.fn(),
    fetchDataIssues: vi.fn(),
  }
})

import {
  fetchDataIssues,
  fetchDataStatus,
  fetchIngestionRuns,
  fetchMetaConfig,
} from '../api/index.js'
import DataSources from './DataSources.jsx'
import { renderWithApp } from '../test/render.jsx'
import { dataStatus, ingestionRuns, metaConfig } from '../test/fixtures.js'

function prime() {
  fetchMetaConfig.mockResolvedValue({ data: metaConfig, meta: {} })
  fetchIngestionRuns.mockResolvedValue({ data: ingestionRuns, meta: {} })
  fetchDataStatus.mockResolvedValue({ data: dataStatus, meta: {} })
  fetchDataIssues.mockResolvedValue({ data: [], meta: { returned: 0 } })
}

describe('DataSources', () => {
  beforeEach(() => {
    prime()
  })

  it('shows both Elexon sources with official documentation links', async () => {
    renderWithApp(<DataSources />, { route: '/data' })

    expect(await screen.findByText('Actual generation source')).toBeInTheDocument()
    expect(screen.getByText('Forecast generation source')).toBeInTheDocument()
    expect(screen.getAllByText('FUELHH').length).toBeGreaterThan(0)
    expect(screen.getAllByText('WINDFOR').length).toBeGreaterThan(0)

    const fuelhhLink = screen.getAllByRole('link', { name: /FUELHH dataset/i })[0]
    expect(fuelhhLink).toHaveAttribute(
      'href',
      'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH',
    )
    expect(fuelhhLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows ingestion status, latest timestamps and coverage', async () => {
    renderWithApp(<DataSources />, { route: '/data' })

    expect(await screen.findByText('Latest available data')).toBeInTheDocument()
    expect(screen.getByText('Last successful ingestion')).toBeInTheDocument()
    expect(screen.getAllByText('succeeded').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('28 Feb 2026')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Coverage by settlement day')).toBeInTheDocument()
    expect(await screen.findByText('01 Jan 2026')).toBeInTheDocument()
    // One day has two missing intervals, rendered as a warning badge.
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
  })

  it('shows an honest empty state when no issues are recorded', async () => {
    renderWithApp(<DataSources />, { route: '/data' })

    expect(await screen.findByText('No recorded issues')).toBeInTheDocument()
    expect(
      screen.getByText(/Absence of issues is not proof of completeness/),
    ).toBeInTheDocument()
  })

  it('flags stale data with a warning', async () => {
    fetchDataStatus.mockResolvedValue({
      data: { ...dataStatus, stale: true },
      meta: {},
    })

    renderWithApp(<DataSources />, { route: '/data' })

    expect(await screen.findByText('Stored data is older than the stale threshold')).toBeInTheDocument()
    expect(screen.getByText('Stale data')).toBeInTheDocument()
  })
})
