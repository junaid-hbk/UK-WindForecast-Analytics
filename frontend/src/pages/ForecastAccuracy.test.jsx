import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/index.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    fetchMetaConfig: vi.fn(),
    fetchIngestionRuns: vi.fn(),
    fetchDataStatus: vi.fn(),
    fetchAccuracySummary: vi.fn(),
    fetchDailyAccuracy: vi.fn(),
    fetchLeadTimeAccuracy: vi.fn(),
  }
})

import {
  fetchAccuracySummary,
  fetchDailyAccuracy,
  fetchDataStatus,
  fetchIngestionRuns,
  fetchLeadTimeAccuracy,
  fetchMetaConfig,
} from '../api/index.js'
import ForecastAccuracy from './ForecastAccuracy.jsx'
import { renderWithApp } from '../test/render.jsx'
import {
  accuracySummary,
  dailyAccuracy,
  dataStatus,
  ingestionRuns,
  leadTimeAccuracy,
  metaConfig,
} from '../test/fixtures.js'

function prime() {
  fetchMetaConfig.mockResolvedValue({ data: metaConfig, meta: {} })
  fetchIngestionRuns.mockResolvedValue({ data: ingestionRuns, meta: {} })
  fetchDataStatus.mockResolvedValue({ data: dataStatus, meta: {} })
  fetchAccuracySummary.mockResolvedValue({
    data: accuracySummary,
    meta: { missing_data_policy: 'excluded and counted; never imputed' },
  })
  fetchDailyAccuracy.mockResolvedValue({
    data: dailyAccuracy,
    meta: { note: 'Days with no evaluated intervals are omitted.' },
  })
  fetchLeadTimeAccuracy.mockResolvedValue({
    data: leadTimeAccuracy,
    meta: { lead_time_definition: 'delivery interval start minus vintage publishTime' },
  })
}

describe('ForecastAccuracy', () => {
  beforeEach(() => {
    prime()
  })

  it('shows authoritative metrics with observation counts', async () => {
    renderWithApp(<ForecastAccuracy />, { route: '/accuracy' })

    expect(await screen.findByText('2,145 MW')).toBeInTheDocument()
    expect(screen.getAllByText('2,616 MW').length).toBeGreaterThan(0)
    expect(screen.getAllByText('18.5 %').length).toBeGreaterThan(0)
    expect(screen.getByText('+1,852 MW')).toBeInTheDocument()
    expect(screen.getAllByText(/n = 1,488 evaluated of 1,488 expected/).length).toBeGreaterThan(0)
    expect(await screen.findByText('Intervals evaluated')).toBeInTheDocument()
    expect(screen.getAllByText('1,488').length).toBeGreaterThan(0)
  })

  it('shows metric definitions from the API', async () => {
    renderWithApp(<ForecastAccuracy />, { route: '/accuracy' })

    expect(await screen.findByText('How these metrics are defined')).toBeInTheDocument()
    expect(screen.getAllByText('WAPE').length).toBeGreaterThan(0)
    expect(screen.getByText('100 * sum(|e|) / sum(|actual|).')).toBeInTheDocument()
    expect(
      screen.getByText('Number of intervals with both a forecast and an actual.'),
    ).toBeInTheDocument()
  })

  it('shows daily and lead-time charts plus empty buckets', async () => {
    renderWithApp(<ForecastAccuracy />, { route: '/accuracy' })

    expect(await screen.findByText('Daily accuracy (100 − WAPE)')).toBeInTheDocument()
    expect(await screen.findByText('Daily error and bias')).toBeInTheDocument()
    expect(await screen.findByText('Accuracy by forecast lead time')).toBeInTheDocument()

    // Wait for the lead-time data itself, not just the chart frame.
    expect((await screen.findAllByText('12-18h')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('0-6h').length).toBeGreaterThan(0)
    expect(
      await screen.findByText(/Buckets with no observations are left blank/),
    ).toBeInTheDocument()
  })

  it('validates a range outside the loaded window', async () => {
    renderWithApp(<ForecastAccuracy />, { route: '/accuracy' })
    await screen.findByText('2,145 MW')

    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-06-01' } })

    expect(await screen.findByText('Adjust the date range')).toBeInTheDocument()
    expect(screen.getByText('The loaded data window ends on 2026-02-28.')).toBeInTheDocument()
  })
})
