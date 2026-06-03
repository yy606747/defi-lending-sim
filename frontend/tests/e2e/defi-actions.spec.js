import { expect, test } from '@playwright/test'
import { loginByStorage, mockApi } from './helpers/mock-api.js'

test.describe('browser DeFi transaction guardrails', () => {
  test.beforeEach(async ({ page }) => {
    await loginByStorage(page)
  })

  test('pledge preview uses protocol LTV for ETH and USDT', async ({ page }) => {
    await mockApi(page)
    await page.goto('/dashboard/pledge')

    await page.locator('select').first().selectOption('1')
    await page.getByPlaceholder('输入数量').fill('1')
    await expect(page.locator('.computed-value')).toHaveText('$2,400.00')

    await page.locator('select').first().selectOption('3')
    await page.getByPlaceholder('输入数量').fill('1000')
    await expect(page.locator('.computed-value')).toHaveText('$900.00')
  })

  test('pledge blocks negative amount submission', async ({ page }) => {
    await mockApi(page)
    await page.goto('/dashboard/pledge')

    await page.locator('select').first().selectOption('1')
    await page.getByPlaceholder('输入数量').fill('-1')

    await expect(page.getByRole('button', { name: '确认质押' })).toBeDisabled()
  })

  test('loan blocks zero and over-limit borrow amounts', async ({ page }) => {
    await mockApi(page)
    await page.goto('/dashboard/loan')

    await page.locator('select').first().selectOption('1')
    await page.getByPlaceholder('输入金额').fill('0')
    await expect(page.getByRole('button', { name: '确认借贷' })).toBeDisabled()

    await page.getByPlaceholder('输入金额').fill('2400.0001')
    await expect(page.getByRole('button', { name: '确认借贷' })).toBeDisabled()
  })

  test('repayment only lists unpaid loans and blocks overpayment', async ({ page }) => {
    await mockApi(page)
    await page.goto('/dashboard/repayment')

    await expect(page.locator('select option')).toHaveCount(2)
    const optionTexts = await page.locator('select option').evaluateAll((options) =>
      options.map((option) => option.textContent.trim())
    )
    expect(optionTexts).toEqual(expect.arrayContaining([expect.stringContaining('#1 Ethereum')]))
    expect(optionTexts).not.toEqual(expect.arrayContaining([expect.stringContaining('#2 Bitcoin')]))

    await page.locator('select').selectOption('1')
    await page.getByPlaceholder('输入金额').fill('50.0001')
    await expect(page.getByRole('button', { name: '确认还款' })).toBeDisabled()
  })

  test('liquidation only exposes action for high-risk positions', async ({ page }) => {
    await mockApi(page)
    await page.goto('/dashboard/liquidation')

    await expect(page.getByRole('button', { name: '执行清算' })).toHaveCount(1)
  })

  test('liquidation applies user-selected slider prices instead of random simulation', async ({ page }) => {
    const state = await mockApi(page)
    await page.goto('/dashboard/liquidation')

    await page.locator('input[type="range"]').first().evaluate((input) => {
      input.value = '1500'
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))
    })
    await page.getByRole('button', { name: '应用价格并刷新风险' }).click()

    await expect.poll(() => state.simulateRequests[0]).toEqual([
      expect.objectContaining({ asset_id: 1, current_price: 1500 }),
    ])
  })
})
