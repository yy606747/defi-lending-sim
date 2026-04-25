<template>
  <div class="page">
    <h2 class="page-title">数据中心</h2>

    <div class="stats-grid">
      <div v-for="s in statCards" :key="s.label" class="stat-card">
        <div class="stat-icon" :style="{ background: s.iconBg }" v-html="s.svg" />
        <div class="stat-body">
          <span class="stat-label">{{ s.label }}</span>
          <span class="stat-value" :style="{ color: s.color }">{{ s.value }}</span>
        </div>
      </div>
    </div>

    <div class="card chart-card">
      <div class="chart-header">
        <h3>资产价格趋势</h3>
        <div class="asset-tabs">
          <button v-for="a in assets" :key="a.asset_id" class="asset-tab" :class="{ active: selectedAsset === a.asset_id }" @click="switchAsset(a.asset_id)">
            {{ a.asset_code }}
          </button>
        </div>
      </div>
      <div class="chart-container">
        <v-chart v-if="chartOption" :option="chartOption" autoresize style="height: 380px;" />
        <div v-else class="chart-empty">加载中...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, shallowRef } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { getAssetList } from '../api/asset'
import { getStatistics, getPriceHistory } from '../api/simulation'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const stats = ref({})
const assets = ref([])
const selectedAsset = ref(null)
const chartOption = shallowRef(null)

function formatNum(v) { return Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }

const statCards = computed(() => [
  { label: '总用户数', value: stats.value.total_users ?? '--', color: '#6366f1', iconBg: 'var(--accent-glow)', svg: '<svg viewBox="0 0 20 20" fill="currentColor" style="width:20px;height:20px;color:#6366f1"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/></svg>' },
  { label: '总质押价值', value: `$${formatNum(stats.value.total_pledge_value)}`, color: '#10b981', iconBg: 'var(--green-glow)', svg: '<svg viewBox="0 0 20 20" fill="currentColor" style="width:20px;height:20px;color:#10b981"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>' },
  { label: '总借贷金额', value: `$${formatNum(stats.value.total_loan_amount)}`, color: '#06b6d4', iconBg: 'var(--cyan-glow)', svg: '<svg viewBox="0 0 20 20" fill="currentColor" style="width:20px;height:20px;color:#06b6d4"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/></svg>' },
  { label: '总清算次数', value: stats.value.total_liquidations ?? '--', color: '#f43f5e', iconBg: 'var(--rose-glow)', svg: '<svg viewBox="0 0 20 20" fill="currentColor" style="width:20px;height:20px;color:#f43f5e"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>' },
])

async function loadData() {
  const [a, s] = await Promise.all([getAssetList(), getStatistics()])
  if (a.code === 200) {
    assets.value = a.data
    if (a.data.length) { selectedAsset.value = a.data[0].asset_id; loadChart(a.data[0].asset_id) }
  }
  if (s.code === 200) stats.value = s.data
}

async function switchAsset(id) {
  selectedAsset.value = id
  await loadChart(id)
}

async function loadChart(assetId) {
  const res = await getPriceHistory(assetId)
  if (res.code !== 200) return
  const d = res.data
  chartOption.value = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15,23,42,0.9)',
      borderColor: 'rgba(99,102,241,0.3)',
      textStyle: { color: '#f1f5f9', fontSize: 13, fontFamily: 'Inter' },
      formatter: (p) => `${p[0].axisValue}<br/><strong>$${Number(p[0].value).toLocaleString()}</strong>`,
    },
    grid: { left: 60, right: 30, top: 20, bottom: 40 },
    xAxis: {
      type: 'category', data: d.dates,
      axisLine: { lineStyle: { color: 'rgba(99,102,241,0.15)' } },
      axisLabel: { color: '#64748b', fontSize: 11, formatter: v => v.slice(5) },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11, formatter: v => `$${v.toLocaleString()}` },
      splitLine: { lineStyle: { color: 'rgba(99,102,241,0.08)' } },
    },
    series: [{
      type: 'line', data: d.prices, smooth: true, symbol: 'none',
      lineStyle: { color: '#6366f1', width: 2.5 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(99,102,241,0.25)' }, { offset: 1, color: 'rgba(99,102,241,0)' }],
        },
      },
    }],
  }
}

onMounted(loadData)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card {
  display: flex; align-items: center; gap: 14px; padding: 20px;
  background: var(--bg-card); backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle); border-radius: var(--radius);
  transition: border-color 0.2s;
}
.stat-card:hover { border-color: var(--border-glow); }
.stat-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat-body { display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.stat-value { font-size: 20px; font-weight: 700; font-family: var(--font-mono); letter-spacing: -0.5px; }

.card { background: var(--bg-card); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); border-radius: var(--radius); overflow: hidden; }
.chart-card { padding: 0; }
.chart-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-subtle); }
.chart-header h3 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; }
.asset-tabs { display: flex; gap: 4px; }
.asset-tab {
  padding: 6px 14px; border: 1px solid var(--border-subtle); border-radius: 8px;
  background: transparent; color: var(--text-muted); font-size: 12px; font-weight: 600;
  font-family: var(--font-mono); cursor: pointer; transition: all 0.15s;
}
.asset-tab:hover { border-color: var(--border-glow); color: var(--text-secondary); }
.asset-tab.active { background: rgba(99,102,241,0.15); border-color: var(--accent); color: var(--accent-light); }
.chart-container { padding: 16px 8px; }
.chart-empty { display: flex; align-items: center; justify-content: center; height: 380px; color: var(--text-muted); }
</style>
