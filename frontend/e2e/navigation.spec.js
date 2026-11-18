import { expect, test } from '@playwright/test'

test('every page renders against the live backend', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Wind forecast dashboard' })).toBeVisible()
  await expect(page.getByText('Cannot reach the WindPulse API')).toHaveCount(0)

  const pages = [
    { link: /Forecast Explorer/, heading: 'Forecast explorer' },
    { link: /Forecast Accuracy/, heading: 'Forecast accuracy' },
    { link: /Procurement Insights/, heading: 'Procurement insights' },
    { link: /Data Sources/, heading: 'Data sources' },
  ]

  for (const entry of pages) {
    await page.getByRole('link', { name: entry.link }).click()
    await expect(page.getByRole('heading', { name: entry.heading, exact: true })).toBeVisible()
  }

  await page.getByRole('link', { name: /Dashboard/ }).click()
  await expect(page.getByRole('heading', { name: 'Wind forecast dashboard' })).toBeVisible()
})
