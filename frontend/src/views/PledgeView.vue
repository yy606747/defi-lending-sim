<template>
  <div class="page">
    <h2 class="page-title">质押管理</h2>

    <div class="card form-card">
      <h3>创建质押</h3>
      <div class="form-row">
        <div class="form-group">
          <label>选择资产</label>
          <select v-model="form.asset_id" class="input" @change="calcAvailable">
            <option value="" disabled>请选择资产</option>
            <option v-for="a in assets" :key="a.asset_id" :value="a.asset_id">
              {{ a.asset_name }} ({{ a.asset_code }}) — ${{ formatNum(a.current_price) }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>质押数量</label>
          <input v-model="form.pledge_amount" type="number" step="any" min="0" class="input" placeholder="输入数量" @input="calcAvailable" />
        </div>
        <div class="form-group">
          <label>预计可借额度</label>
          <div class="computed-value">${{ formatNum(availableLoan) }}</div>
        </div>
        <div class="form-group" style="align-self: flex-end;">
          <button class="btn-accent" :disabled="!canSubmit" @click="handleCreate">确认质押</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">质押记录</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>资产</th>
            <th>数量</th>
            <th>当前价值</th>
            <th>可借额度</th>
            <th>质押率</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pledges" :key="p.pledge_id">
            <td><span class="code-badge">{{ p.asset_code }}</span> {{ p.asset_name }}</td>
            <td class="mono">{{ formatNum(p.pledge_amount) }}</td>
            <td class="mono">${{ formatNum(p.current_value) }}</td>
            <td class="mono">${{ formatNum(p.available_loan_amount) }}</td>
            <td class="mono">{{ (Number(p.pledge_rate) * 100).toFixed(0) }}%</td>
            <td><span class="status-tag" :class="p.pledge_status">{{ statusMap[p.pledge_status] }}</span></td>
            <td>
              <button v-if="p.pledge_status === 'active'" class="btn-small" @click="handleUnlock(p.pledge_id)">解锁</button>
              <span v-else class="muted">--</span>
            </td>
          </tr>
          <tr v-if="!pledges.length"><td colspan="7" class="empty">暂无质押记录</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssetList } from '../api/asset'
import { createPledge, getPledgeList, unlockPledge } from '../api/pledge'

const assets = ref([])
const pledges = ref([])
const form = ref({ asset_id: '', pledge_amount: '' })
const availableLoan = ref(0)
const statusMap = { active: '活跃', liquidated: '已清算', unlocked: '已解锁' }
const assetLtv = { ETH: 0.8, BTC: 0.75, USDT: 0.9 }

function formatNum(v) { return Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function selectedAsset() { return assets.value.find(a => Number(a.asset_id) === Number(form.value.asset_id)) }
function getLtv(asset) { return assetLtv[asset?.asset_code] ?? 0.75 }

const canSubmit = computed(() => {
  const amount = Number(form.value.pledge_amount)
  return Boolean(form.value.asset_id) && Number.isFinite(amount) && amount > 0
})

function calcAvailable() {
  const asset = selectedAsset()
  const amount = Number(form.value.pledge_amount) || 0
  availableLoan.value = asset && amount > 0 ? amount * Number(asset.current_price) * getLtv(asset) : 0
}

async function loadData() {
  const [a, p] = await Promise.all([getAssetList(), getPledgeList()])
  if (a.code === 200) assets.value = a.data
  if (p.code === 200) pledges.value = p.data
}

async function handleCreate() {
  if (!canSubmit.value) {
    ElMessage.warning('质押数量必须大于0')
    return
  }
  const res = await createPledge({ asset_id: form.value.asset_id, pledge_amount: form.value.pledge_amount })
  if (res.code === 200) {
    ElMessage.success('质押成功')
    form.value = { asset_id: '', pledge_amount: '' }
    availableLoan.value = 0
    loadData()
  } else {
    ElMessage.error(res.message)
  }
}

async function handleUnlock(id) {
  const res = await unlockPledge(id)
  if (res.code === 200) { ElMessage.success('解锁成功'); loadData() }
  else ElMessage.error(res.message)
}

onMounted(loadData)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.card {
  background: var(--bg-card); backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden;
}
.form-card { padding: 24px; }
.form-card h3 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 18px; }
.card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--border-subtle); }

.form-row { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.form-group { display: flex; flex-direction: column; gap: 6px; min-width: 180px; flex: 1; }
.form-group label { font-size: 12px; font-weight: 500; color: var(--text-muted); }
.input {
  padding: 10px 12px; background: rgba(15,23,42,0.8); border: 1px solid var(--border-subtle);
  border-radius: 8px; color: var(--text-primary); font-size: 14px; font-family: var(--font-sans); outline: none;
  transition: border-color 0.2s;
}
.input:focus { border-color: var(--accent); }
select.input { cursor: pointer; }

.computed-value {
  padding: 10px 12px; font-family: var(--font-mono); font-size: 16px; font-weight: 600;
  color: var(--accent-light); background: rgba(99,102,241,0.08); border-radius: 8px;
  border: 1px solid rgba(99,102,241,0.15);
}

.btn-accent {
  display: flex; align-items: center; gap: 6px; padding: 10px 20px;
  border: none; border-radius: 8px; cursor: pointer; font-family: var(--font-sans);
  background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff;
  font-size: 13px; font-weight: 600; transition: transform 0.15s, box-shadow 0.2s; white-space: nowrap;
}
.btn-accent:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.3); }
.btn-accent:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.btn-small {
  padding: 5px 12px; border: 1px solid var(--border-subtle); border-radius: 6px;
  background: transparent; color: var(--accent-light); font-size: 12px; font-weight: 500;
  cursor: pointer; font-family: var(--font-sans); transition: all 0.15s;
}
.btn-small:hover { background: rgba(99,102,241,0.1); border-color: var(--accent); }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  text-align: left; padding: 14px 20px; font-size: 12px; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-subtle); background: rgba(15,23,42,0.4);
}
.data-table td { padding: 14px 20px; font-size: 13px; color: var(--text-primary); border-bottom: 1px solid rgba(99,102,241,0.06); }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(99,102,241,0.04); }

.mono { font-family: var(--font-mono); }
.muted { color: var(--text-muted); }
.code-badge {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  padding: 2px 6px; border-radius: 4px; background: rgba(99,102,241,0.1); color: var(--accent-light);
  margin-right: 6px;
}
.status-tag {
  font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 6px;
}
.status-tag.active { background: var(--green-glow); color: var(--green); }
.status-tag.liquidated { background: var(--rose-glow); color: var(--rose); }
.status-tag.unlocked { background: rgba(100,116,139,0.15); color: var(--text-muted); }
.empty { text-align: center; color: var(--text-muted); padding: 40px 20px !important; }
</style>
