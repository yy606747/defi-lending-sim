export const assets = [
  {
    asset_id: 1,
    asset_name: 'Ethereum',
    asset_code: 'ETH',
    current_price: '3000.0000',
    price_volatility: '0.050000',
  },
  {
    asset_id: 2,
    asset_name: 'Bitcoin',
    asset_code: 'BTC',
    current_price: '60000.0000',
    price_volatility: '0.030000',
  },
  {
    asset_id: 3,
    asset_name: 'Tether',
    asset_code: 'USDT',
    current_price: '1.0000',
    price_volatility: '0.001000',
  },
]

export const pledges = [
  {
    pledge_id: 1,
    asset_id: 1,
    asset_name: 'Ethereum',
    asset_code: 'ETH',
    pledge_amount: '1.0000',
    current_value: '3000.0000',
    available_loan_amount: '2400.0000',
    pledge_rate: '0.8000',
    pledge_status: 'active',
  },
]

export const loans = [
  {
    loan_id: 1,
    asset_id: 1,
    asset_name: 'Ethereum',
    asset_code: 'ETH',
    loan_amount: '100.0000',
    loan_rate: '0.050000',
    loan_term: 30,
    total_repay: '100.4110',
    remaining_principal: '50.0000',
    repay_status: 'partial',
  },
  {
    loan_id: 2,
    asset_id: 2,
    asset_name: 'Bitcoin',
    asset_code: 'BTC',
    loan_amount: '10.0000',
    loan_rate: '0.040000',
    loan_term: 30,
    total_repay: '10.0329',
    remaining_principal: '0.0000',
    repay_status: 'paid',
  },
]

export const risks = [
  {
    pledge_id: 1,
    asset_code: 'ETH',
    asset_name: 'Ethereum',
    pledge_amount: '1.0000',
    current_value: '1000.0000',
    total_debt: '1000.0000',
    collateral_ratio: '1.0000',
    risk_level: 'high',
  },
  {
    pledge_id: 2,
    asset_code: 'BTC',
    asset_name: 'Bitcoin',
    pledge_amount: '1.0000',
    current_value: '60000.0000',
    total_debt: '1000.0000',
    collateral_ratio: '60.0000',
    risk_level: 'low',
  },
]

function json(route, body, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

function ok(data, message = 'success') {
  return { code: 200, message, data }
}

export async function mockApi(page, overrides = {}) {
  const state = {
    simulateRequests: [],
    ...overrides,
  }

  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/user/login') {
      return json(route, ok({
        token: 'browser-token',
        user: {
          user_id: 1,
          user_name: 'alice',
          virtual_address: '0xALICE',
          register_time: '2026-06-01T00:00:00',
          total_asset: '10000.0000',
        },
      }, '登录成功'))
    }

    if (path === '/api/user/register') return json(route, ok({}, '注册成功'))
    if (path === '/api/user/info') {
      return json(route, ok({
        user_id: 1,
        user_name: 'alice',
        virtual_address: '0xALICE',
        register_time: '2026-06-01T00:00:00',
        total_asset: '10000.0000',
      }))
    }

    if (path === '/api/asset/list') return json(route, ok(state.assets ?? assets))
    if (path === '/api/asset/simulate') {
      state.simulateRequests.push(request.postDataJSON() ?? null)
      return json(route, ok(state.assets ?? assets, '价格模拟完成'))
    }

    if (path === '/api/pledge/list') return json(route, ok(state.pledges ?? pledges))
    if (path === '/api/pledge/create') return json(route, ok({}, '质押成功'))

    if (path === '/api/loan/list') return json(route, ok(state.loans ?? loans))
    if (path === '/api/loan/rate') {
      return json(route, ok({
        asset_name: 'Ethereum',
        asset_code: 'ETH',
        base_rate: '0.05',
        rates: [
          { term: 30, label: '30 天', rate: '0.0450' },
          { term: 60, label: '60 天', rate: '0.0500' },
          { term: 90, label: '90 天', rate: '0.0500' },
          { term: 180, label: '180 天', rate: '0.0600' },
        ],
      }))
    }
    if (path === '/api/loan/create') return json(route, ok({}, '借贷成功'))

    if (path === '/api/repayment/list') return json(route, ok([]))
    if (path === '/api/repayment/create') return json(route, ok({}, '还款成功'))

    if (path === '/api/liquidation/risk') return json(route, ok(state.risks ?? risks))
    if (path === '/api/liquidation/list') return json(route, ok([]))
    if (path === '/api/liquidation/execute') return json(route, ok({}, '清算执行完成'))

    if (path === '/api/simulation/statistics') {
      return json(route, ok({
        total_users: 2,
        total_pledge_value: '6000.0000',
        total_loan_amount: '400.0000',
        total_liquidations: 1,
        utilization_rate: '0.0667',
        avg_dynamic_rate: '0.0227',
      }))
    }
    if (path.startsWith('/api/simulation/price-history/')) {
      return json(route, ok(state.priceHistory ?? {
        dates: ['2026-06-01', '2026-06-02'],
        prices: [100, 101],
      }))
    }

    return json(route, { code: 404, message: `Unhandled mock route: ${path}`, data: null }, 404)
  })

  return state
}

export async function loginByStorage(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'browser-token')
  })
}
