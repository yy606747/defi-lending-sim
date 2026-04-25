<template>
  <div class="page">
    <h2 class="page-title">借贷管理</h2>

    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-label">可借总额度</span>
        <span class="stat-value accent">${{ formatNum(totalAvailable) }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">当前基准利率</span>
        <span class="stat-value cyan">{{ rateInfo ? (Number(rateInfo.base_rate) * 100).toFixed(2) + '%' : '--' }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">已借总额</span>
        <span class="stat-value amber">${{ formatNum(totalBorrowed) }}</span>
      </div>
    </div>

    <div class="card form-card">
      <h3>申请借贷</h3>
      <div class="form-row">
        <div class="form-group">
          <label>借贷资产</label>
          <select v-model="form.asset_id" class="input" @change="onAssetChange">
            <option value="" disabled>请选择资产</option>
            <option v-for="a in assets" :key="a.asset_id" :value="a.asset_id">{{ a.asset_name }} ({{ a.asset_code }})</option>
          </select>
        </div>
        <div class="form-group">
          <label>借贷金额 (USD)</label>
          <input v-model="form.loan_amount" type="number" step="any" min="0" class="input" placeholder="输入金额" />
        </div>
        <div class="form-group">
          <label>借贷期限</label>
          <select v-model="form.loan_term" class="input" @change="onTermChange">
            <option v-for="r in (rateInfo ? rateInfo.rates : defaultTerms)" :key="r.term" :value="r.term">{{ r.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>预计还款本息</label>
          <div class="computed-value">${{ formatNum(estimatedRepay) }}</div>
        </div>
        <div class="form-group" style="align-self: flex-end;">
          <button class="btn-accent" :disabled="!form.asset_id || !form.loan_amount" @click="handleCreate">确认借贷</button>
        </div>
      </div>

      <div v-if="rateInfo" class="rate-table-wrapper">
        <h4>{{ rateInfo.asset_name }} 各期限利率</h4>
        <div class="rate-cards">
          <div v-for="r in rateInfo.rates" :key="r.term" class="rate-card" :class="{ selected: form.loan_term === r.term }" @click="selectTerm(r.term)">
            <span class="rate-term">{{ r.label }}</span>
            <span class="rate-value">{{ (Number(r.rate) * 100).toFixed(2) }}%</span>
            <span class="rate-tag">年化</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">借贷记录</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>资产</th>
            <th>金额</th>
            <th>利率</th>
            <th>期限</th>
            <th>应还本息</th>
            <th>剩余本金</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in loans" :key="l.loan_id">
            <td><span class="code-badge">{{ l.asset_code }}</span> {{ l.asset_name }}</td>
            <td class="mono">${{ formatNum(l.loan_amount) }}</td>
            <td class="mono">{{ (Number(l.loan_rate) * 100).toFixed(2) }}%</td>
            <td>{{ l.loan_term }} 天</td>
            <td class="mono">${{ formatNum(l.total_repay) }}</td>
            <td class="mono">${{ formatNum(l.remaining_principal) }}</td>
            <td><span class="status-tag" :class="l.repay_status">{{ repayStatusMap[l.repay_status] }}</span></td>
          </tr>
          <tr v-if="!loans.length"><td colspan="7" class="empty">暂无借贷记录</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssetList } from '../api/asset'
import { getPledgeList } from '../api/pledge'
import { createLoan, getLoanList, getLoanRate } from '../api/loan'

const assets = ref([])
const loans = ref([])
const rateInfo = ref(null)
const selectedRate = ref(null)
const totalAvailable = ref(0)
const form = ref({ asset_id: '', loan_amount: '', loan_term: 30 })
const repayStatusMap = { unpaid: '未还款', partial: '部分还款', paid: '已还清' }
const defaultTerms = [
  { term: 30, label: '30 天' },
  { term: 60, label: '60 天' },
  { term: 90, label: '90 天' },
  { term: 180, label: '180 天' },
]

function formatNum(v) { return Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }

const totalBorrowed = computed(() => loans.value.filter(l => l.repay_status !== 'paid').reduce((s, l) => s + Number(l.remaining_principal), 0))

const estimatedRepay = computed(() => {
  const amount = Number(form.value.loan_amount) || 0
  const rate = selectedRate.value ? Number(selectedRate.value) : 0
  const term = Number(form.value.loan_term)
  return amount * (1 + rate * term / 365)
})

function findRate(term) {
  if (!rateInfo.value) return null
  const r = rateInfo.value.rates.find(x => x.term === term)
  return r ? r.rate : null
}

async function onAssetChange() {
  rateInfo.value = null
  selectedRate.value = null
  if (!form.value.asset_id) return
  const res = await getLoanRate(form.value.asset_id)
  if (res.code === 200) {
    rateInfo.value = res.data
    selectedRate.value = findRate(form.value.loan_term)
  }
}

function onTermChange() {
  selectedRate.value = findRate(form.value.loan_term)
}

function selectTerm(term) {
  form.value.loan_term = term
  selectedRate.value = findRate(term)
}

async function loadData() {
  const [a, p, l] = await Promise.all([getAssetList(), getPledgeList(), getLoanList()])
  if (a.code === 200) assets.value = a.data
  if (p.code === 200) totalAvailable.value = p.data.filter(x => x.pledge_status === 'active').reduce((s, x) => s + Number(x.available_loan_amount), 0)
  if (l.code === 200) loans.value = l.data
}

async function handleCreate() {
  const res = await createLoan({ asset_id: form.value.asset_id, loan_amount: form.value.loan_amount, loan_term: form.value.loan_term })
  if (res.code === 200) {
    ElMessage.success('借贷成功')
    form.value = { asset_id: '', loan_amount: '', loan_term: 30 }
    rateInfo.value = null
    selectedRate.value = null
    loadData()
  } else {
    ElMessage.error(res.message)
  }
}

onMounted(loadData)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-card {
  display: flex; flex-direction: column; gap: 6px; padding: 20px;
  background: var(--bg-card); backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle); border-radius: var(--radius);
}
.stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.stat-value { font-size: 22px; font-weight: 700; font-family: var(--font-mono); letter-spacing: -0.5px; }
.stat-value.accent { color: var(--accent-light); }
.stat-value.cyan { color: var(--cyan); }
.stat-value.amber { color: var(--amber); }

.card { background: var(--bg-card); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden; }
.form-card { padding: 24px; }
.form-card h3 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 18px; }
.card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--border-subtle); }

.form-row { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.form-group { display: flex; flex-direction: column; gap: 6px; min-width: 160px; flex: 1; }
.form-group label { font-size: 12px; font-weight: 500; color: var(--text-muted); }
.input { padding: 10px 12px; background: rgba(15,23,42,0.8); border: 1px solid var(--border-subtle); border-radius: 8px; color: var(--text-primary); font-size: 14px; font-family: var(--font-sans); outline: none; }
.input:focus { border-color: var(--accent); }
.computed-value { padding: 10px 12px; font-family: var(--font-mono); font-size: 16px; font-weight: 600; color: var(--accent-light); background: rgba(99,102,241,0.08); border-radius: 8px; border: 1px solid rgba(99,102,241,0.15); }

.rate-table-wrapper { margin-top: 20px; }
.rate-table-wrapper h4 { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 0 0 12px; }
.rate-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.rate-card {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 16px 12px; border-radius: 10px; cursor: pointer;
  background: rgba(15,23,42,0.6); border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}
.rate-card:hover { border-color: var(--border-glow); }
.rate-card.selected { background: rgba(99,102,241,0.12); border-color: var(--accent); }
.rate-term { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.rate-value { font-size: 20px; font-weight: 700; font-family: var(--font-mono); color: var(--cyan); letter-spacing: -0.5px; }
.rate-tag { font-size: 11px; color: var(--text-muted); }

.btn-accent { display: flex; align-items: center; gap: 6px; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-family: var(--font-sans); background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; font-size: 13px; font-weight: 600; transition: transform 0.15s, box-shadow 0.2s; white-space: nowrap; }
.btn-accent:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.3); }
.btn-accent:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th { text-align: left; padding: 14px 20px; font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-subtle); background: rgba(15,23,42,0.4); }
.data-table td { padding: 14px 20px; font-size: 13px; color: var(--text-primary); border-bottom: 1px solid rgba(99,102,241,0.06); }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(99,102,241,0.04); }
.mono { font-family: var(--font-mono); }
.code-badge { font-family: var(--font-mono); font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: rgba(99,102,241,0.1); color: var(--accent-light); margin-right: 6px; }
.status-tag { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 6px; }
.status-tag.unpaid { background: var(--amber-glow); color: var(--amber); }
.status-tag.partial { background: var(--cyan-glow); color: var(--cyan); }
.status-tag.paid { background: var(--green-glow); color: var(--green); }
.empty { text-align: center; color: var(--text-muted); padding: 40px 20px !important; }
</style>
