import { expect, test } from '@playwright/test'
import { loginByStorage, mockApi } from './helpers/mock-api.js'

test.describe('browser data center charts', () => {
  test.beforeEach(async ({ page }) => {
    await loginByStorage(page)
  })

  test('renders protocol statistics and normal price chart', async ({ page }) => {
    await mockApi(page)

    await page.goto('/dashboard/data')

    await expect(page.getByText('6.67%')).toBeVisible()
    await expect(page.getByText('2.27%')).toBeVisible()
    await expect(page.locator('canvas')).toHaveCount(1)
  })

  test('does not render chart when dates and prices lengths differ', async ({ page }) => {
    await mockApi(page, {
      priceHistory: {
        dates: ['2026-06-01', '2026-06-02'],
        prices: [100, 101, 102],
      },
    })

    await page.goto('/dashboard/data')

    await expect(page.getByText('加载中...')).toBeVisible()
    await expect(page.locator('canvas')).toHaveCount(0)
  })
})

