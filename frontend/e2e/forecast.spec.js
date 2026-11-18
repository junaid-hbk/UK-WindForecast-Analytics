import { expect, test } from '@playwright/test'

test('forecast explorer shows the cutoff and the selected vintage', async ({ page }) => {
  await page.goto('/forecast')

  await expect(page.getByRole('heading', { name: 'Forecast explorer' })).toBeVisible()
  await expect(page.getByText('Decision cutoff', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(/UTC$/).first()).toBeVisible()

  // The stored as-of selection must identify at least one vintage used at cutoff.
  await expect(page.getByText('Used for the decision').first()).toBeVisible()

  await expect(page.getByText('Settlement period detail')).toBeVisible()
  await expect(page.getByRole('table', { name: /Half-hourly selected forecast/ })).toBeVisible()
})
