import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

const assetApi = vi.hoisted(() => ({
  getAssetList: vi.fn(),
  simulatePrice: vi.fn(),
}))
const pledgeApi = vi.hoisted(() => ({
  createPledge: vi.fn(),
  getPledgeList: vi.fn(),
  unlockPledge: vi.fn(),
}))
const loanApi = vi.hoisted(() => ({
  createLoan: vi.fn(),
  getLoanList: vi.fn(),
  getLoanRate: vi.fn(),
}))
const repaymentApi = vi.hoisted(() => ({
  createRepayment: vi.fn(),
  getRepaymentList: vi.fn(),
}))
const liquidationApi = vi.hoisted(() => ({
  getLiquidationRisk: vi.fn(),
  executeLiquidation: vi.fn(),
  getLiquidationList: vi.fn(),
}))
const simulationApi = vi.hoisted(() => ({
  getStatistics: vi.fn(),
  getPriceHistory: vi.fn(),
  advanceTime: vi.fn(),
}))

vi.mock('../../src/api/asset', () => assetApi)
vi.mock('../../src/api/pledge', () => pledgeApi)
vi.mock('../../src/api/loan', () => loanApi)
vi.mock('../../src/api/repayment', () => repaymentApi)
vi.mock('../../src/api/liquidation', () => liquidationApi)
vi.mock('../../src/api/simulation', () => simulationApi)
vi.mock('vue-echarts', () => ({
  default: { name: 'VChart', props: ['option'], template: '<div data-test="v-chart" />' },
}))
vi.mock('echarts/core', () => ({ use: vi.fn() }))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))
vi.mock('echarts/charts', () => ({ LineChart: {} }))
vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
}))

const assets = [
  { asset_id: 1, asset_name: 'Ethereum', asset_code: 'ETH', current_price: '3000.0000', price_volatility: '0.050000' },
  { asset_id: 2, asset_name: 'Bitcoin', asset_code: 'BTC', current_price: '60000.0000', price_volatility: '0.030000' },
  { asset_id: 3, asset_name: 'Tether', asset_code: 'USDT', current_price: '1.0000', price_volatility: '0.001000' },
]

beforeEach(() => {
  assetApi.getAssetList.mockResolvedValue({ code: 200, data: assets })
  assetApi.simulatePrice.mockResolvedValue({ code: 200, data: assets })
  pledgeApi.getPledgeList.mockResolvedValue({ code: 200, data: [] })
  pledgeApi.createPledge.mockResolvedValue({ code: 200, data: {} })
  pledgeApi.unlockPledge.mockResolvedValue({ code: 200, data: {} })
  loanApi.getLoanList.mockResolvedValue({ code: 200, data: [] })
  loanApi.getLoanRate.mockResolvedValue({
    code: 200,
    data: {
      asset_name: 'Ethereum',
      asset_code: 'ETH',
      base_rate: '0.05',
      rates: [
        { term: 30, label: '30 天', rate: '0.0450' },
        { term: 60, label: '60 天', rate: '0.0500' },
        { term: 90, label: '90 天', rate: '0.0500' },
        { term: 180, label: '180 天', rate: '0.0600' },
      ],
    },
  })
  loanApi.createLoan.mockResolvedValue({ code: 200, data: {} })
  repaymentApi.getRepaymentList.mockResolvedValue({ code: 200, data: [] })
  repaymentApi.createRepayment.mockResolvedValue({ code: 200, data: {} })
  liquidationApi.getLiquidationRisk.mockResolvedValue({ code: 200, data: [] })
  liquidationApi.getLiquidationList.mockResolvedValue({ code: 200, data: [] })
  liquidationApi.executeLiquidation.mockResolvedValue({ code: 200, data: {} })
  simulationApi.getStatistics.mockResolvedValue({
    code: 200,
    data: {
      total_users: 2,
      total_pledge_value: '6000.0000',
      total_loan_amount: '400.0000',
      total_liquidations: 1,
      utilization_rate: '0.0667',
      avg_dynamic_rate: '0.0227',
    },
  })
  simulationApi.getPriceHistory.mockResolvedValue({
    code: 200,
    data: { dates: ['2026-06-01', '2026-06-02'], prices: [100, 101] },
  })
  simulationApi.advanceTime.mockResolvedValue({
    code: 200,
    data: { days: '30', interest_accrued: '4.1096' },
  })
})

describe('PledgeView DeFi amount and LTV checks', () => {
  it('uses asset-specific LTV for frontend borrow-power preview', async () => {
    const PledgeView = (await import('../../src/views/PledgeView.vue')).default
    const wrapper = mount(PledgeView)
    await flushPromises()

    wrapper.vm.form.asset_id = 1
    wrapper.vm.form.pledge_amount = '1'
    wrapper.vm.calcAvailable()
    await nextTick()

    expect(wrapper.text()).toContain('$2,400.00')
  })

  it('uses USDT stablecoin LTV instead of the default 75% preview', async () => {
    const PledgeView = (await import('../../src/views/PledgeView.vue')).default
    const wrapper = mount(PledgeView)
    await flushPromises()

    wrapper.vm.form.asset_id = 3
    wrapper.vm.form.pledge_amount = '1000'
    wrapper.vm.calcAvailable()
    await nextTick()

    expect(wrapper.text()).toContain('$900.00')
  })

  it('disables pledge submission for zero or negative amounts', async () => {
    const PledgeView = (await import('../../src/views/PledgeView.vue')).default
    const wrapper = mount(PledgeView)
    await flushPromises()

    wrapper.vm.form.asset_id = 1
    wrapper.vm.form.pledge_amount = '-1'
    await nextTick()
    const button = wrapper.find('.btn-accent')

    expect(button.attributes('disabled')).toBeDefined()
  })
})

describe('LoanView DeFi borrow checks', () => {
  it('sums active pledge availability for the visible borrow limit', async () => {
    pledgeApi.getPledgeList.mockResolvedValue({
      code: 200,
      data: [
        { pledge_status: 'active', available_loan_amount: '100.0000' },
        { pledge_status: 'active', available_loan_amount: '200.0000' },
        { pledge_status: 'unlocked', available_loan_amount: '999.0000' },
      ],
    })
    const LoanView = (await import('../../src/views/LoanView.vue')).default
    const wrapper = mount(LoanView)
    await flushPromises()

    expect(wrapper.text()).toContain('$300.00')
  })

  it('disables borrow submission when amount is zero or negative', async () => {
    pledgeApi.getPledgeList.mockResolvedValue({ code: 200, data: [{ pledge_status: 'active', available_loan_amount: '100.0000' }] })
    const LoanView = (await import('../../src/views/LoanView.vue')).default
    const wrapper = mount(LoanView)
    await flushPromises()

    wrapper.vm.form.asset_id = 1
    wrapper.vm.form.loan_amount = '0'
    await nextTick()

    expect(wrapper.find('.btn-accent').attributes('disabled')).toBeDefined()
  })

  it('disables borrow submission above the visible available credit', async () => {
    pledgeApi.getPledgeList.mockResolvedValue({ code: 200, data: [{ pledge_status: 'active', available_loan_amount: '100.0000' }] })
    const LoanView = (await import('../../src/views/LoanView.vue')).default
    const wrapper = mount(LoanView)
    await flushPromises()

    wrapper.vm.form.asset_id = 1
    wrapper.vm.form.loan_amount = '100.0001'
    await nextTick()

    expect(wrapper.find('.btn-accent').attributes('disabled')).toBeDefined()
  })

  it('calculates estimated repayment using selected annualized rate and term', async () => {
    const LoanView = (await import('../../src/views/LoanView.vue')).default
    const wrapper = mount(LoanView)
    await flushPromises()

    wrapper.vm.form.loan_amount = '1000'
    wrapper.vm.form.loan_term = 180
    wrapper.vm.selectedRate = '0.0600'
    await nextTick()

    expect(wrapper.text()).toContain('$1,029.59')
  })

  it('advances loan time and reloads accrued interest', async () => {
    loanApi.getLoanList
      .mockResolvedValueOnce({
        code: 200,
        data: [{ loan_id: 1, repay_status: 'unpaid', remaining_principal: '1000.0000', total_repay: '1000.0000' }],
      })
      .mockResolvedValueOnce({
        code: 200,
        data: [{ loan_id: 1, repay_status: 'unpaid', remaining_principal: '1000.0000', total_repay: '1004.1096' }],
      })
    const LoanView = (await import('../../src/views/LoanView.vue')).default
    const wrapper = mount(LoanView)
    await flushPromises()

    await wrapper.get('[data-test="advance-time"]').trigger('click')
    await flushPromises()

    expect(simulationApi.advanceTime).toHaveBeenCalledWith(30)
    expect(loanApi.getLoanList).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('$1,004.11')
  })

  it('disables time advance above the 3650-day limit', async () => {
    loanApi.getLoanList.mockResolvedValue({
      code: 200,
      data: [{ loan_id: 1, repay_status: 'unpaid', remaining_principal: '1000.0000', total_repay: '1000.0000' }],
    })
    const LoanView = (await import('../../src/views/LoanView.vue')).default
    const wrapper = mount(LoanView)
    await flushPromises()

    wrapper.vm.advanceDays = 3651
    await nextTick()

    const input = wrapper.get('[aria-label="时间快进天数"]')
    const button = wrapper.get('[data-test="advance-time"]')
    expect(input.attributes('max')).toBe('3650')
    expect(button.attributes('disabled')).toBeDefined()
  })
})

describe('RepaymentView repayment guardrails', () => {
  it('only offers unpaid or partial loans in repayment selection', async () => {
    loanApi.getLoanList.mockResolvedValue({
      code: 200,
      data: [
        { loan_id: 1, asset_name: 'ETH', repay_status: 'unpaid', remaining_principal: '50.0000', loan_amount: '100.0000', loan_rate: '0.05' },
        { loan_id: 2, asset_name: 'BTC', repay_status: 'paid', remaining_principal: '0.0000', loan_amount: '10.0000', loan_rate: '0.04' },
      ],
    })
    const RepaymentView = (await import('../../src/views/RepaymentView.vue')).default
    const wrapper = mount(RepaymentView)
    await flushPromises()

    expect(wrapper.text()).toContain('#1 ETH')
    expect(wrapper.text()).not.toContain('#2 BTC')
  })

  it('disables repayment above the selected remaining principal', async () => {
    loanApi.getLoanList.mockResolvedValue({
      code: 200,
      data: [{ loan_id: 1, asset_name: 'ETH', repay_status: 'partial', remaining_principal: '50.0000', loan_amount: '100.0000', loan_rate: '0.05' }],
    })
    const RepaymentView = (await import('../../src/views/RepaymentView.vue')).default
    const wrapper = mount(RepaymentView)
    await flushPromises()

    wrapper.vm.form.loan_id = 1
    wrapper.vm.form.repayment_amount = '50.0001'
    await nextTick()

    expect(wrapper.find('.btn-accent').attributes('disabled')).toBeDefined()
  })

  it('disables repayment when amount is zero or negative', async () => {
    loanApi.getLoanList.mockResolvedValue({
      code: 200,
      data: [{ loan_id: 1, asset_name: 'ETH', repay_status: 'unpaid', remaining_principal: '50.0000', loan_amount: '100.0000', loan_rate: '0.05' }],
    })
    const RepaymentView = (await import('../../src/views/RepaymentView.vue')).default
    const wrapper = mount(RepaymentView)
    await flushPromises()

    wrapper.vm.form.loan_id = 1
    wrapper.vm.form.repayment_amount = '0'
    await nextTick()

    expect(wrapper.find('.btn-accent').attributes('disabled')).toBeDefined()
  })
})

describe('LiquidationView risk simulation', () => {
  it('shows liquidation action only for high risk positions', async () => {
    liquidationApi.getLiquidationRisk.mockResolvedValue({
      code: 200,
      data: [
        { pledge_id: 1, asset_code: 'ETH', asset_name: 'Ethereum', pledge_amount: '1', current_value: '1000', total_debt: '1000', collateral_ratio: '1.0', risk_level: 'high' },
        { pledge_id: 2, asset_code: 'BTC', asset_name: 'Bitcoin', pledge_amount: '1', current_value: '60000', total_debt: '1000', collateral_ratio: '60', risk_level: 'low' },
      ],
    })
    const LiquidationView = (await import('../../src/views/LiquidationView.vue')).default
    const wrapper = mount(LiquidationView)
    await flushPromises()

    expect(wrapper.findAll('.btn-danger')).toHaveLength(1)
  })

  it('applies the user-selected slider prices instead of random simulation', async () => {
    const LiquidationView = (await import('../../src/views/LiquidationView.vue')).default
    const wrapper = mount(LiquidationView)
    await flushPromises()

    wrapper.vm.assets[0].tempPrice = 1500
    await wrapper.find('.btn-accent').trigger('click')
    await flushPromises()

    expect(assetApi.simulatePrice).toHaveBeenCalledWith([
      expect.objectContaining({ asset_id: 1, current_price: 1500 }),
    ])
  })
})

describe('DataView chart and statistics safety', () => {
  it('formats protocol statistics and renders a chart for well-shaped history data', async () => {
    const DataView = (await import('../../src/views/DataView.vue')).default
    const wrapper = mount(DataView)
    await flushPromises()

    expect(wrapper.text()).toContain('6.67%')
    expect(wrapper.text()).toContain('2.27%')
    expect(wrapper.find('[data-test="v-chart"]').exists()).toBe(true)
  })

  it('rejects mismatched dates/prices history before rendering risk charts', async () => {
    simulationApi.getPriceHistory.mockResolvedValue({
      code: 200,
      data: { dates: ['2026-06-01', '2026-06-02'], prices: [100, 101, 102] },
    })
    const DataView = (await import('../../src/views/DataView.vue')).default
    const wrapper = mount(DataView)
    await flushPromises()

    expect(wrapper.vm.chartOption).toBeNull()
  })
})
