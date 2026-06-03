import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function source(path) {
  return readFileSync(resolve(process.cwd(), path), 'utf8')
}

describe('static DeFi frontend standards', () => {
  it('does not hardcode live dashboard financial metrics in HomeView', () => {
    const code = source('src/views/HomeView.vue')

    expect(code).not.toContain("label: '质押数量',\n    value: '0'")
    expect(code).not.toContain("label: '活跃借贷',\n    value: '0'")
  })

  it('does not describe deterministic price adjustment while only calling random simulation', () => {
    const code = source('src/views/LiquidationView.vue')

    expect(code).not.toContain('await simulatePrice()')
    expect(code).toMatch(/tempPrice/)
  })

  it('keeps password policy text aligned with the stronger registration rule', () => {
    const code = source('src/views/LoginView.vue')

    expect(code).toContain('至少6位且包含数字和字母')
  })
})

