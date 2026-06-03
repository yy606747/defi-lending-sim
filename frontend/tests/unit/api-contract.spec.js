import { describe, it, expect, vi, beforeEach } from 'vitest'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))

vi.mock('../../src/api/request', () => ({
  default: requestMock,
}))

describe('frontend API contract wrappers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('maps user API calls to the documented backend endpoints', async () => {
    const userApi = await import('../../src/api/user')
    const payload = { virtual_address: '0xabc', password: 'secret123' }

    userApi.register(payload)
    userApi.login(payload)
    userApi.getInfo()
    userApi.updateInfo({ user_name: 'alice' })

    expect(requestMock.post).toHaveBeenCalledWith('/api/user/register', payload)
    expect(requestMock.post).toHaveBeenCalledWith('/api/user/login', payload)
    expect(requestMock.get).toHaveBeenCalledWith('/api/user/info')
    expect(requestMock.put).toHaveBeenCalledWith('/api/user/info', { user_name: 'alice' })
  })

  it('maps asset and simulation endpoints without dropping identifiers', async () => {
    const assetApi = await import('../../src/api/asset')
    const simulationApi = await import('../../src/api/simulation')

    assetApi.getAssetList()
    assetApi.getAsset(7)
    assetApi.simulatePrice()
    simulationApi.getPriceHistory(7)
    simulationApi.getStatistics()

    expect(requestMock.get).toHaveBeenCalledWith('/api/asset/list')
    expect(requestMock.get).toHaveBeenCalledWith('/api/asset/7')
    expect(requestMock.post).toHaveBeenCalledWith('/api/asset/simulate')
    expect(requestMock.get).toHaveBeenCalledWith('/api/simulation/price-history/7')
    expect(requestMock.get).toHaveBeenCalledWith('/api/simulation/statistics')
  })

  it('maps financial mutation endpoints to authenticated backend routes', async () => {
    const pledgeApi = await import('../../src/api/pledge')
    const loanApi = await import('../../src/api/loan')
    const repaymentApi = await import('../../src/api/repayment')
    const liquidationApi = await import('../../src/api/liquidation')

    pledgeApi.createPledge({ asset_id: 1, pledge_amount: '1' })
    pledgeApi.getPledgeList()
    pledgeApi.unlockPledge(9)
    loanApi.createLoan({ asset_id: 1, loan_amount: '100', loan_term: 30 })
    loanApi.getLoanList()
    loanApi.getLoanRate(1)
    repaymentApi.createRepayment({ loan_id: 3, repayment_amount: '10' })
    repaymentApi.getRepaymentList()
    liquidationApi.getLiquidationRisk()
    liquidationApi.executeLiquidation({ pledge_id: 5 })
    liquidationApi.getLiquidationList()

    expect(requestMock.post).toHaveBeenCalledWith('/api/pledge/create', { asset_id: 1, pledge_amount: '1' })
    expect(requestMock.get).toHaveBeenCalledWith('/api/pledge/list')
    expect(requestMock.post).toHaveBeenCalledWith('/api/pledge/unlock/9')
    expect(requestMock.post).toHaveBeenCalledWith('/api/loan/create', { asset_id: 1, loan_amount: '100', loan_term: 30 })
    expect(requestMock.get).toHaveBeenCalledWith('/api/loan/list')
    expect(requestMock.get).toHaveBeenCalledWith('/api/loan/rate', { params: { asset_id: 1 } })
    expect(requestMock.post).toHaveBeenCalledWith('/api/repayment/create', { loan_id: 3, repayment_amount: '10' })
    expect(requestMock.get).toHaveBeenCalledWith('/api/repayment/list')
    expect(requestMock.get).toHaveBeenCalledWith('/api/liquidation/risk')
    expect(requestMock.post).toHaveBeenCalledWith('/api/liquidation/execute', { pledge_id: 5 })
    expect(requestMock.get).toHaveBeenCalledWith('/api/liquidation/list')
  })
})

