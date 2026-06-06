<template>
  <div class="page">
    <div class="top-grid">
      <div class="card control-card">
        <div class="card-head">
          <h3>预言机喂价</h3>
          <el-button type="primary" :loading="loading" @click="applyFeed">执行全局喂价</el-button>
        </div>

        <div class="asset-controls">
          <div v-for="asset in assets" :key="asset.asset_id" class="asset-control">
            <div class="asset-row">
              <div>
                <span class="code-badge">{{ asset.asset_code }}</span>
                <span class="asset-name">{{ asset.asset_name }}</span>
              </div>
              <span class="mono" :class="priceChangeClass(asset)">{{ priceChange(asset) }}</span>
            </div>
            <div class="price-row">
              <span class="muted mono">${{ formatNum(asset.current_price) }}</span>
              <el-input-number
                v-model="asset.targetPrice"
                :min="minPrice(asset)"
                :max="maxPrice(asset)"
                :step="stepPrice(asset)"
                :precision="4"
                controls-position="right"
                size="small"
              />
            </div>
            <el-slider
              v-model="asset.targetPrice"
              :min="minPrice(asset)"
              :max="maxPrice(asset)"
              :step="stepPrice(asset)"
              :show-tooltip="false"
            />
          </div>
        </div>

        <div v-if="stageText" class="stage-line">
          <span class="pulse-dot" />
          <span>{{ stageText }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div v-for="item in statCards" :key="item.label" class="stat-card">
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value" :style="{ color: item.color }">{{ item.value }}</strong>
        </div>
      </div>
    </div>

    <div class="risk-grid">
      <div class="card">
        <div class="card-head table-head">
          <h3>冲击瞬间高危头寸</h3>
          <span class="count-pill">{{ atRiskBefore.length }}</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>资产</th>
                <th>抵押价值</th>
                <th>总负债</th>
                <th>HF</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in atRiskBefore" :key="riskKey(row, index, 'before')" :class="{ danger: row.will_liquidate }">
                <td>{{ row.user_name }}</td>
                <td><span class="code-badge">{{ row.asset_code }}</span></td>
                <td class="mono">${{ formatNum(row.current_value) }}</td>
                <td class="mono">${{ formatNum(row.total_debt) }}</td>
                <td><span class="hf-pill" :class="hfClass(row.health_factor)">{{ formatHf(row.health_factor) }}</span></td>
                <td>
                  <span class="risk-tag" :class="row.will_liquidate ? 'high' : 'medium'">
                    {{ row.will_liquidate ? '将被清算' : '预警' }}
                  </span>
                </td>
              </tr>
              <tr v-if="!atRiskBefore.length"><td colspan="6" class="empty">暂无冲击快照</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-head table-head">
          <h3>清算后残留风险</h3>
          <span class="count-pill">{{ atRisk.length }}</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>资产</th>
                <th>抵押价值</th>
                <th>总负债</th>
                <th>HF</th>
                <th>风险</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in atRisk" :key="riskKey(row, index, 'after')">
                <td>{{ row.user_name }}</td>
                <td><span class="code-badge">{{ row.asset_code }}</span></td>
                <td class="mono">${{ formatNum(row.current_value) }}</td>
                <td class="mono">${{ formatNum(row.total_debt) }}</td>
                <td><span class="hf-pill" :class="hfClass(row.health_factor)">{{ formatHf(row.health_factor) }}</span></td>
                <td><span class="risk-tag" :class="row.risk_level">{{ riskLabel(row.risk_level) }}</span></td>
              </tr>
              <tr v-if="!atRisk.length"><td colspan="6" class="empty">暂无残留高危头寸</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-head table-head">
        <h3>清算播报</h3>
        <span class="count-pill">{{ currentLiquidations.length || recent.length }}</span>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户</th>
              <th>资产</th>
              <th>价格</th>
              <th>偿还债务</th>
              <th>扣押抵押</th>
              <th>HF 前后</th>
              <th>坏账</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in liquidationRows" :key="row.liquidation_id">
              <td class="mono">#{{ row.liquidation_id }}</td>
              <td>{{ row.user_name || `用户 ${row.user_id}` }}</td>
              <td><span class="code-badge">{{ row.asset_code || '--' }}</span></td>
              <td class="mono">${{ formatNum(row.liquidation_price) }}</td>
              <td class="mono">${{ formatNum(row.debt_repaid) }}</td>
              <td class="mono">{{ formatNum(row.collateral_seized) }}</td>
              <td class="mono">{{ formatHf(row.health_factor_before) }} → {{ formatHf(row.health_factor_after) }}</td>
              <td class="mono" :class="{ rose: Number(row.bad_debt || 0) > 0 }">${{ formatNum(row.bad_debt) }}</td>
            </tr>
            <tr v-if="!liquidationRows.length"><td colspan="8" class="empty">暂无清算记录</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssetList } from '../api/asset'
import { feedPrices, getOracleOverview } from '../api/oracle'

const assets = ref([])
const stats = ref({})
const atRiskBefore = ref([])
const atRisk = ref([])
const recent = ref([])
const currentLiquidations = ref([])
const loading = ref(false)
const stageText = ref('')

function formatNum(value, digits = 2) {
  return Number(value || 0).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatPct(value) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`
}

function formatHf(value) {
  return Number(value || 0).toFixed(4)
}

function minPrice(asset) {
  return Number(asset.current_price) * 0.5
}

function maxPrice(asset) {
  return Number(asset.current_price) * 1.5
}

function stepPrice(asset) {
  return Math.max(Number(asset.current_price) * 0.01, 0.0001)
}

function priceChange(asset) {
  const base = Number(asset.current_price)
  if (!base) return '0.0%'
  const pct = ((Number(asset.targetPrice) - base) / base) * 100
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
}

function priceChangeClass(asset) {
  return Number(asset.targetPrice) >= Number(asset.current_price) ? 'green' : 'rose'
}

function hfClass(value) {
  const hf = Number(value || 0)
  if (hf < 1) return 'high'
  if (hf < 1.15) return 'medium'
  return 'low'
}

function riskLabel(level) {
  return ({ low: '低风险', medium: '中风险', high: '高风险' })[level] || level || '--'
}

function riskKey(row, index, prefix) {
  return `${prefix}-${row.user_id}-${row.pledge_id ?? 'bad'}-${index}`
}

const statCards = computed(() => [
  { label: 'TVL', value: `$${formatNum(stats.value.total_pledge_value, 0)}`, color: '#10b981' },
  { label: '总负债', value: `$${formatNum(stats.value.total_loan_amount, 0)}`, color: '#06b6d4' },
  { label: '资金利用率', value: formatPct(stats.value.utilization_rate), color: '#f59e0b' },
  { label: '平均利率', value: formatPct(stats.value.avg_dynamic_rate), color: '#818cf8' },
  { label: '累计清算', value: stats.value.total_liquidations ?? 0, color: '#f43f5e' },
])

const liquidationRows = computed(() => (
  currentLiquidations.value.length ? currentLiquidations.value : recent.value
))

async function loadAll() {
  const [assetRes, overviewRes] = await Promise.all([getAssetList(), getOracleOverview()])
  if (assetRes.code === 200) {
    assets.value = assetRes.data.map((asset) => ({
      ...asset,
      targetPrice: Number(asset.current_price),
    }))
  }
  if (overviewRes.code === 200) {
    stats.value = overviewRes.data.stats
    atRisk.value = overviewRes.data.at_risk
    recent.value = overviewRes.data.recent_liquidations
  }
}

function buildUpdates() {
  return assets.value
    .filter((asset) => Math.abs(Number(asset.targetPrice) - Number(asset.current_price)) > 0.0001)
    .map((asset) => ({
      asset_id: asset.asset_id,
      current_price: Number(asset.targetPrice),
    }))
}

async function delay(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

async function applyFeed() {
  const updates = buildUpdates()
  if (!updates.length) {
    ElMessage.warning('请先调整至少一个资产价格')
    return
  }

  loading.value = true
  currentLiquidations.value = []
  try {
    stageText.value = '正在广播预言机价格'
    const res = await feedPrices(updates)
    stageText.value = '正在扫描全局风险'
    await delay(300)
    stageText.value = '正在同步清算结果'
    await delay(300)

    if (res.code !== 200) {
      ElMessage.error(res.message || '喂价失败')
      return
    }

    assets.value = res.data.assets.map((asset) => ({
      ...asset,
      targetPrice: Number(asset.current_price),
    }))
    atRiskBefore.value = res.data.at_risk_before
    atRisk.value = res.data.at_risk
    currentLiquidations.value = res.data.liquidations
    recent.value = res.data.recent_liquidations
    stats.value = res.data.stats

    const count = res.data.liquidations.length
    ElMessage.success(count ? `本轮触发 ${count} 笔清算` : '喂价完成，无账户触及清算线')
  } catch (error) {
    ElMessage.error('喂价请求异常')
  } finally {
    loading.value = false
    stageText.value = ''
  }
}

onMounted(loadAll)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.top-grid { display: grid; grid-template-columns: minmax(360px, 1.45fr) minmax(280px, 1fr); gap: 20px; align-items: stretch; }
.risk-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.card { background: var(--bg-card); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden; }
.control-card { padding: 20px; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 18px; }
.card-head h3 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0; }
.table-head { padding: 18px 20px; margin: 0; border-bottom: 1px solid var(--border-subtle); }
.asset-controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.asset-control { padding: 14px; background: rgba(15,23,42,0.56); border: 1px solid rgba(99,102,241,0.12); border-radius: 10px; }
.asset-row, .price-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.asset-row { margin-bottom: 12px; }
.price-row { margin-bottom: 8px; }
.asset-name { color: var(--text-secondary); font-size: 13px; }
.code-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 44px; font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 3px 7px; border-radius: 6px; background: rgba(99,102,241,0.12); color: var(--accent-light); margin-right: 6px; }
.mono { font-family: var(--font-mono); }
.muted { color: var(--text-muted); }
.green { color: var(--green); }
.rose { color: var(--rose); }
.stage-line { display: flex; align-items: center; gap: 8px; height: 28px; margin-top: 14px; color: var(--text-secondary); font-size: 13px; }
.pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent-light); box-shadow: 0 0 12px var(--accent); animation: pulse 1s infinite; }
.stats-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.stat-card { min-height: 92px; display: flex; flex-direction: column; justify-content: center; gap: 8px; padding: 18px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius); }
.stat-label { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.stat-value { font-size: 24px; font-weight: 800; font-family: var(--font-mono); }
.count-pill { min-width: 32px; text-align: center; padding: 3px 9px; border-radius: 999px; background: rgba(99,102,241,0.14); color: var(--accent-light); font-family: var(--font-mono); font-size: 12px; font-weight: 700; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; min-width: 720px; }
.data-table th { text-align: left; padding: 13px 18px; font-size: 12px; font-weight: 700; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle); background: rgba(15,23,42,0.42); }
.data-table td { padding: 14px 18px; font-size: 13px; color: var(--text-primary); border-bottom: 1px solid rgba(99,102,241,0.06); white-space: nowrap; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(99,102,241,0.04); }
.data-table tr.danger td { background: rgba(244,63,94,0.05); }
.hf-pill, .risk-tag { display: inline-flex; align-items: center; justify-content: center; min-width: 64px; padding: 3px 9px; border-radius: 7px; font-size: 12px; font-weight: 700; font-family: var(--font-mono); }
.hf-pill.low, .risk-tag.low { background: var(--green-glow); color: var(--green); }
.hf-pill.medium, .risk-tag.medium { background: var(--amber-glow); color: var(--amber); }
.hf-pill.high, .risk-tag.high { background: var(--rose-glow); color: var(--rose); }
.empty { text-align: center; color: var(--text-muted); padding: 34px 20px !important; }

@keyframes pulse {
  0% { opacity: 0.45; transform: scale(0.92); }
  50% { opacity: 1; transform: scale(1.08); }
  100% { opacity: 0.45; transform: scale(0.92); }
}

@media (max-width: 1120px) {
  .top-grid, .risk-grid { grid-template-columns: 1fr; }
}
</style>
