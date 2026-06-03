<template>
  <div class="page">
    <h2 class="page-title">清算模拟</h2>

    <div class="card form-card">
      <h3>市场价格调整 (模拟波动)</h3>
      <p class="form-desc">拖动滑块模拟资产价格下跌，观察质押风险变化</p>
      <div class="slider-grid">
        <div v-for="a in assets" :key="a.asset_id" class="slider-item">
          <div class="slider-header">
            <span class="code-badge">{{ a.asset_code }}</span>
            <span class="mono">${{ formatNum(a.tempPrice) }}</span>
          </div>
          <input type="range" class="slider" :min="Number(a.current_price) * 0.3" :max="Number(a.current_price) * 1.5" :step="0.01" v-model.number="a.tempPrice" />
          <div class="slider-range">
            <span>-70%</span>
            <span class="slider-change" :class="a.tempPrice >= Number(a.current_price) ? 'up' : 'down'">
              {{ ((a.tempPrice / Number(a.current_price) - 1) * 100).toFixed(1) }}%
            </span>
            <span>+50%</span>
          </div>
        </div>
      </div>
      <button class="btn-accent" style="margin-top: 16px;" @click="applyPrices">应用价格并刷新风险</button>
    </div>

    <div class="card">
      <h3 class="card-title">质押风险列表</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>资产</th>
            <th>质押数量</th>
            <th>当前价值</th>
            <th>总负债</th>
            <th>质押率</th>
            <th>风险</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in risks" :key="r.pledge_id">
            <td><span class="code-badge">{{ r.asset_code }}</span> {{ r.asset_name }}</td>
            <td class="mono">{{ formatNum(r.pledge_amount) }}</td>
            <td class="mono">${{ formatNum(r.current_value) }}</td>
            <td class="mono">${{ formatNum(r.total_debt) }}</td>
            <td class="mono">{{ Number(r.collateral_ratio).toFixed(2) }}</td>
            <td><span class="risk-tag" :class="r.risk_level">{{ riskMap[r.risk_level] }}</span></td>
            <td>
              <button v-if="r.risk_level === 'high'" class="btn-danger" @click="handleLiquidate(r.pledge_id)">执行清算</button>
              <span v-else class="muted">--</span>
            </td>
          </tr>
          <tr v-if="!risks.length"><td colspan="7" class="empty">暂无活跃质押</td></tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h3 class="card-title">清算历史</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>清算ID</th>
            <th>资产</th>
            <th>清算价格</th>
            <th>清算金额</th>
            <th>时间</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in liquidations" :key="l.liquidation_id">
            <td class="mono">#{{ l.liquidation_id }}</td>
            <td>{{ l.asset_name || '--' }}</td>
            <td class="mono">${{ formatNum(l.liquidation_price) }}</td>
            <td class="mono">${{ formatNum(l.liquidation_amount) }}</td>
            <td class="muted">{{ formatTime(l.liquidation_time) }}</td>
            <td><span class="status-tag completed">{{ l.liquidation_status }}</span></td>
          </tr>
          <tr v-if="!liquidations.length"><td colspan="6" class="empty">暂无清算记录</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssetList, simulatePrice } from '../api/asset'
import { getLiquidationRisk, executeLiquidation, getLiquidationList } from '../api/liquidation'

const assets = ref([])
const risks = ref([])
const liquidations = ref([])
const riskMap = { low: '低风险', medium: '中风险', high: '高风险' }

function formatNum(v) { return Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '--' }

async function loadData() {
  const [a, r, l] = await Promise.all([getAssetList(), getLiquidationRisk(), getLiquidationList()])
  if (a.code === 200) assets.value = a.data.map(x => ({ ...x, tempPrice: Number(x.current_price) }))
  if (r.code === 200) risks.value = r.data
  if (l.code === 200) liquidations.value = l.data
}

async function applyPrices() {
  const selectedPrices = assets.value
    .filter(a => Number(a.tempPrice) !== Number(a.current_price))
    .map(a => ({
      asset_id: a.asset_id,
      current_price: Number(a.tempPrice),
    }))
  await simulatePrice(selectedPrices)
  const [r, l] = await Promise.all([getLiquidationRisk(), getLiquidationList()])
  if (r.code === 200) risks.value = r.data
  if (l.code === 200) liquidations.value = l.data
  const a = await getAssetList()
  if (a.code === 200) assets.value = a.data.map(x => ({ ...x, tempPrice: Number(x.current_price) }))
  ElMessage.success('价格已更新')
}

async function handleLiquidate(pledgeId) {
  const res = await executeLiquidation({ pledge_id: pledgeId })
  if (res.code === 200) { ElMessage.success('清算完成'); loadData() }
  else ElMessage.error(res.message)
}

onMounted(loadData)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }
.card { background: var(--bg-card); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden; }
.form-card { padding: 24px; }
.form-card h3 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.form-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 18px; }
.card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--border-subtle); }

.slider-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
.slider-item { padding: 16px; background: rgba(15,23,42,0.6); border: 1px solid var(--border-subtle); border-radius: 10px; }
.slider-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.slider { width: 100%; accent-color: var(--accent); height: 4px; cursor: pointer; }
.slider-range { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-top: 6px; }
.slider-change { font-weight: 600; }
.slider-change.up { color: var(--green); }
.slider-change.down { color: var(--rose); }

.btn-accent { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-family: var(--font-sans); background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; font-size: 13px; font-weight: 600; transition: transform 0.15s, box-shadow 0.2s; }
.btn-accent:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.3); }

.btn-danger { padding: 5px 12px; border: 1px solid var(--rose); border-radius: 6px; background: var(--rose-glow); color: var(--rose); font-size: 12px; font-weight: 600; cursor: pointer; font-family: var(--font-sans); transition: all 0.15s; }
.btn-danger:hover { background: rgba(244,63,94,0.25); }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th { text-align: left; padding: 14px 20px; font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-subtle); background: rgba(15,23,42,0.4); }
.data-table td { padding: 14px 20px; font-size: 13px; color: var(--text-primary); border-bottom: 1px solid rgba(99,102,241,0.06); }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(99,102,241,0.04); }
.mono { font-family: var(--font-mono); }
.muted { color: var(--text-muted); }
.code-badge { font-family: var(--font-mono); font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: rgba(99,102,241,0.1); color: var(--accent-light); margin-right: 6px; }

.risk-tag { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 6px; }
.risk-tag.low { background: var(--green-glow); color: var(--green); }
.risk-tag.medium { background: var(--amber-glow); color: var(--amber); }
.risk-tag.high { background: var(--rose-glow); color: var(--rose); }

.status-tag { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 6px; }
.status-tag.completed { background: var(--green-glow); color: var(--green); }

.empty { text-align: center; color: var(--text-muted); padding: 40px 20px !important; }
</style>
