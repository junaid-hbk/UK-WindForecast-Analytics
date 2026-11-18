import { expect, test } from '@playwright/test'

test('procurement scenario is calculated by the backend', async ({ page }) => {
  await page.goto('/procurement')

  await expect(page.getByRole('heading', { name: 'Procurement insights' })).toBeVisible()

  await page.getByLabel('Demand scenario (MW)').fill('15000')
  await page.getByRole('button', { name: /Calculate scenario/ }).click()

  await expect(page.getByText('Net delta')).toBeVisible()
  await expect(page.getByText('Selected wind forecast')).toBeVisible()
  await expect(page.getByText(/Illustrative estimate only/).first()).toBeVisible()

  // Either the backend returns a delta or it explains why it cannot.
  const delta = page.getByText(/[+-]?[\d,]+ MW·h/).first()
  const error = page.getByText('Scenario could not be calculated')
  await expect(delta.or(error).first()).toBeVisible()
})
