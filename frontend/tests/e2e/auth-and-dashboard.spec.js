import { expect, test } from '@playwright/test'
import { loginByStorage, mockApi } from './helpers/mock-api.js'

test.describe('browser auth and dashboard flows', () => {
  test('redirects unauthenticated dashboard access to login', async ({ page }) => {
    await mockApi(page)

    await page.goto('/dashboard/home')

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible()
  })

  test('login success writes token and opens dashboard', async ({ page }) => {
    await mockApi(page)

    await page.goto('/login')
    await page.getByPlaceholder('0x...').fill('0xALICE')
    await page.getByPlaceholder('请输入密码').fill('abc12345')
    await page.getByRole('button', { name: '连接钱包' }).click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByText('DeFi Lending').first()).toBeVisible()
    await expect.poll(() => page.evaluate(() => localStorage.getItem('token'))).toBe('browser-token')
  })

  test('rejects whitespace-only login address before calling backend', async ({ page }) => {
    await mockApi(page)

    await page.goto('/login')
    await page.getByPlaceholder('0x...').fill('   ')
    await page.getByPlaceholder('请输入密码').fill('abc12345')
    await page.getByRole('button', { name: '连接钱包' }).click()

    await expect(page.getByText('请填写虚拟地址和密码')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('rejects weak register password with missing number', async ({ page }) => {
    await mockApi(page)

    await page.goto('/login')
    await page.getByRole('button', { name: '注册' }).click()
    await page.getByPlaceholder('请输入用户名').fill('alice')
    await page.getByPlaceholder('0x...').fill('0xALICE')
    await page.getByPlaceholder('至少6位').fill('abcdef')
    await page.getByPlaceholder('再次输入密码').fill('abcdef')
    await page.getByRole('button', { name: '创建账户' }).click()

    await expect(page.getByText('密码需同时包含数字和字母')).toBeVisible()
  })

  test('redirects authenticated users away from login page', async ({ page }) => {
    await mockApi(page)
    await loginByStorage(page)

    await page.goto('/login')

    await expect(page).toHaveURL(/\/dashboard\/home$/)
  })

  test('home dashboard should not show hardcoded zero positions when backend has active data', async ({ page }) => {
    await mockApi(page)
    await loginByStorage(page)

    await page.goto('/dashboard/home')

    await expect(page.getByText('质押数量').locator('..').getByText('0')).toHaveCount(0)
    await expect(page.getByText('活跃借贷').locator('..').getByText('0')).toHaveCount(0)
  })
})

