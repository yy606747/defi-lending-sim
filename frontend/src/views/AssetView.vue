<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>虚拟资产管理</h2>
        <p class="page-desc">查看并管理所有虚拟资产，模拟市场价格波动</p>
      </div>
      <button class="btn-accent" :disabled="simulating" @click="handleSimulate">
        <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
        {{ simulating ? '模拟中...' : '模拟价格波动' }}
      </button>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>资产名称</th>
            <th>代码</th>
            <th>当前价格 (USD)</th>
            <th>波动率</th>
            <th>价格变化</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="asset in assets" :key="asset.asset_id">
            <td>
              <div class="asset-name">
                <span class="asset-dot" :style="{ background: assetColor(asset.asset_code) }" />
                {{ asset.asset_name }}
              </div>
            </td>
            <td><span class="code-badge">{{ asset.asset_code }}</span></td>
            <td class="mono">{{ formatPrice(asset.current_price) }}</td>
            <td class="mono muted">{{ (Number(asset.price_volatility) * 100).toFixed(1) }}%</td>
            <td>
              <span v-if="priceChanges[asset.asset_id] !== undefined" class="change-badge" :class="priceChanges[asset.asset_id] >= 0 ? 'up' : 'down'">
                {{ priceChanges[asset.asset_id] >= 0 ? '+' : '' }}{{ priceChanges[asset.asset_id].toFixed(2) }}%
              </span>
              <span v-else class="muted">--</span>
            </td>
          </tr>
          <tr v-if="!assets.length">
            <td colspan="5" class="empty">暂无资产数据</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssetList, simulatePrice } from '../api/asset'

const assets = ref([])
const priceChanges = ref({})
const simulating = ref(false)

const assetColors = { BTC: '#f7931a', ETH: '#627eea', USDT: '#26a17b' }
function assetColor(code) { return assetColors[code] || '#6366f1' }

function formatPrice(p) {
  return Number(p).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAssets() {
  const res = await getAssetList()
  if (res.code === 200) assets.value = res.data
}

async function handleSimulate() {
  simulating.value = true
  const oldPrices = {}
  assets.value.forEach(a => { oldPrices[a.asset_id] = Number(a.current_price) })
  try {
    const res = await simulatePrice()
    if (res.code === 200) {
      assets.value = res.data
      const changes = {}
      res.data.forEach(a => {
        const old = oldPrices[a.asset_id]
        if (old) changes[a.asset_id] = ((Number(a.current_price) - old) / old) * 100
      })
      priceChanges.value = changes
      ElMessage.success('价格模拟完成')
    }
  } finally {
    simulating.value = false
  }
}

onMounted(loadAssets)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-header h2 { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--text-muted); }

.btn-accent {
  display: flex; align-items: center; gap: 6px; padding: 10px 18px;
  border: none; border-radius: 10px; cursor: pointer; font-family: var(--font-sans);
  background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff;
  font-size: 13px; font-weight: 600; transition: transform 0.15s, box-shadow 0.2s;
}
.btn-accent svg { width: 16px; height: 16px; }
.btn-accent:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.3); }
.btn-accent:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.card {
  background: var(--bg-card); backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden;
}

.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  text-align: left; padding: 14px 20px; font-size: 12px; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-subtle); background: rgba(15,23,42,0.4);
}
.data-table td {
  padding: 16px 20px; font-size: 14px; color: var(--text-primary);
  border-bottom: 1px solid rgba(99,102,241,0.06);
}
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(99,102,241,0.04); }

.mono { font-family: var(--font-mono); }
.muted { color: var(--text-muted); }

.asset-name { display: flex; align-items: center; gap: 8px; font-weight: 500; }
.asset-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.code-badge {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  padding: 3px 8px; border-radius: 6px; background: rgba(99,102,241,0.1); color: var(--accent-light);
}

.change-badge {
  font-family: var(--font-mono); font-size: 13px; font-weight: 600;
  padding: 3px 10px; border-radius: 6px;
}
.change-badge.up { background: var(--green-glow); color: var(--green); }
.change-badge.down { background: var(--rose-glow); color: var(--rose); }

.empty { text-align: center; color: var(--text-muted); padding: 40px 20px !important; }
</style>
