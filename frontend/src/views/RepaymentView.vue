<template>
  <div class="page">
    <h2 class="page-title">还款管理</h2>

    <div class="card form-card">
      <h3>发起还款</h3>
      <div class="form-row">
        <div class="form-group" style="flex: 2;">
          <label>选择未还清借贷</label>
          <select v-model="form.loan_id" class="input">
            <option value="" disabled>请选择借贷</option>
            <option v-for="l in unpaidLoans" :key="l.loan_id" :value="l.loan_id">
              #{{ l.loan_id }} {{ l.asset_name }} — 剩余 ${{ formatNum(l.remaining_principal) }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>还款金额 (USD)</label>
          <input v-model="form.repayment_amount" type="number" step="any" min="0" class="input" placeholder="输入金额" />
        </div>
        <div class="form-group" style="align-self: flex-end;">
          <button class="btn-accent" :disabled="!canSubmit" @click="handleRepay">确认还款</button>
        </div>
      </div>
      <div v-if="selectedLoan" class="loan-detail">
        <span>借贷金额: <strong>${{ formatNum(selectedLoan.loan_amount) }}</strong></span>
        <span>利率: <strong>{{ (Number(selectedLoan.loan_rate) * 100).toFixed(2) }}%</strong></span>
        <span>剩余本金: <strong class="accent">${{ formatNum(selectedLoan.remaining_principal) }}</strong></span>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">还款历史</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>借贷ID</th>
            <th>关联资产</th>
            <th>还款金额</th>
            <th>还款类型</th>
            <th>还款时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in repayments" :key="r.repayment_id">
            <td class="mono">#{{ r.loan_id }}</td>
            <td>{{ r.asset_name || '--' }}</td>
            <td class="mono">${{ formatNum(r.repayment_amount) }}</td>
            <td><span class="type-badge">{{ r.repayment_type === 'early' ? '提前还款' : '到期还款' }}</span></td>
            <td class="muted">{{ formatTime(r.repayment_time) }}</td>
          </tr>
          <tr v-if="!repayments.length"><td colspan="5" class="empty">暂无还款记录</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getLoanList } from '../api/loan'
import { createRepayment, getRepaymentList } from '../api/repayment'

const loans = ref([])
const repayments = ref([])
const form = ref({ loan_id: '', repayment_amount: '' })

const unpaidLoans = computed(() => loans.value.filter(l => l.repay_status !== 'paid'))
const selectedLoan = computed(() => loans.value.find(l => Number(l.loan_id) === Number(form.value.loan_id)))
const canSubmit = computed(() => {
  const amount = Number(form.value.repayment_amount)
  const remaining = Number(selectedLoan.value?.remaining_principal)
  return Boolean(selectedLoan.value) && Number.isFinite(amount) && amount > 0 && amount <= remaining
})

function formatNum(v) { return Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '--' }

async function loadData() {
  const [l, r] = await Promise.all([getLoanList(), getRepaymentList()])
  if (l.code === 200) loans.value = l.data
  if (r.code === 200) repayments.value = r.data
}

async function handleRepay() {
  if (!canSubmit.value) {
    ElMessage.warning('还款金额必须大于0且不能超过剩余本金')
    return
  }
  const res = await createRepayment({ loan_id: form.value.loan_id, repayment_amount: form.value.repayment_amount })
  if (res.code === 200) {
    ElMessage.success('还款成功')
    form.value = { loan_id: '', repayment_amount: '' }
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
.card { background: var(--bg-card); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden; }
.form-card { padding: 24px; }
.form-card h3 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 18px; }
.card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--border-subtle); }

.form-row { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.form-group { display: flex; flex-direction: column; gap: 6px; min-width: 180px; flex: 1; }
.form-group label { font-size: 12px; font-weight: 500; color: var(--text-muted); }
.input { padding: 10px 12px; background: rgba(15,23,42,0.8); border: 1px solid var(--border-subtle); border-radius: 8px; color: var(--text-primary); font-size: 14px; font-family: var(--font-sans); outline: none; }
.input:focus { border-color: var(--accent); }

.loan-detail { display: flex; gap: 24px; margin-top: 16px; padding: 14px 16px; border-radius: 8px; background: rgba(15,23,42,0.6); border: 1px solid var(--border-subtle); font-size: 13px; color: var(--text-secondary); }
.loan-detail strong { color: var(--text-primary); }
.loan-detail .accent { color: var(--accent-light); }

.btn-accent { display: flex; align-items: center; gap: 6px; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-family: var(--font-sans); background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; font-size: 13px; font-weight: 600; transition: transform 0.15s, box-shadow 0.2s; white-space: nowrap; }
.btn-accent:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.3); }
.btn-accent:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th { text-align: left; padding: 14px 20px; font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-subtle); background: rgba(15,23,42,0.4); }
.data-table td { padding: 14px 20px; font-size: 13px; color: var(--text-primary); border-bottom: 1px solid rgba(99,102,241,0.06); }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(99,102,241,0.04); }
.mono { font-family: var(--font-mono); }
.muted { color: var(--text-muted); }
.type-badge { font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 6px; background: rgba(99,102,241,0.1); color: var(--accent-light); }
.empty { text-align: center; color: var(--text-muted); padding: 40px 20px !important; }
</style>
