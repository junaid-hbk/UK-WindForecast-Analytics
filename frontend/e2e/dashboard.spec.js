import { expect, test } from '@playwright/test'

test('dashboard shows real forecast, outturn and accuracy data', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Wind forecast dashboard' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Accuracy over the analysis window' })).toBeVisible()
  await expect(page.getByText('Latest available wind forecast')).toBeVisible()
  await expect(page.getByText('Actual wind generation')).toBeVisible()

  // The KPI strip must either show authoritative MW metrics or an honest empty state.
  const metrics = page.getByText(/MW$/).first()
  const emptyState = page.getByText('No evaluated intervals in this range')
  await expect(metrics.or(emptyState).first()).toBeVisible()

  await expect(
    page.getByRole('img', { name: /Forecast versus actual generation/ }),
  ).toBeVisible()

  await expect(page.getByText('Data availability')).toBeVisible()
  await expect(page.getByText('Decision cutoff', { exact: true }).first()).toBeVisible()
})
