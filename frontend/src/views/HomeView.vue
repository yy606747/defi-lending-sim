<template>
  <div class="home">
    <div class="welcome-banner">
      <div class="welcome-text">
        <p class="greeting">Welcome back</p>
        <h1>{{ userStore.userInfo?.user_name || '...' }}</h1>
        <p class="sub">管理你的虚拟 DeFi 资产组合</p>
      </div>
      <div class="welcome-decoration">
        <svg viewBox="0 0 200 120" fill="none">
          <path d="M20 80 Q60 20 100 60 T180 40" stroke="url(#wg)" stroke-width="2" fill="none" opacity="0.6"/>
          <path d="M20 90 Q70 50 110 70 T180 50" stroke="url(#wg2)" stroke-width="1.5" fill="none" opacity="0.4"/>
          <circle cx="100" cy="60" r="3" fill="#6366f1"/>
          <circle cx="180" cy="40" r="2.5" fill="#06b6d4"/>
          <circle cx="20" cy="80" r="2" fill="#818cf8"/>
          <defs>
            <linearGradient id="wg" x1="0" y1="0" x2="200" y2="0"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>
            <linearGradient id="wg2" x1="0" y1="0" x2="200" y2="0"><stop stop-color="#6366f1" stop-opacity="0.5"/><stop offset="1" stop-color="#10b981" stop-opacity="0.5"/></linearGradient>
          </defs>
        </svg>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-icon" :style="{ background: stat.iconBg }">
          <div class="stat-icon-inner" :style="{ color: stat.color }" v-html="stat.svg" />
        </div>
        <div class="stat-body">
          <span class="stat-label">{{ stat.label }}</span>
          <span class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</span>
        </div>
      </div>
    </div>

    <div class="info-grid">
      <div class="info-card">
        <div class="info-header">
          <h3>账户信息</h3>
        </div>
        <div class="info-rows">
          <div class="info-row">
            <span class="info-key">用户名</span>
            <span class="info-val">{{ userStore.userInfo?.user_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">虚拟地址</span>
            <span class="info-val mono">{{ userStore.userInfo?.virtual_address }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">注册时间</span>
            <span class="info-val">{{ formatTime(userStore.userInfo?.register_time) }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">网络状态</span>
            <span class="info-val">
              <span class="status-dot green" />
              Testnet 已连接
            </span>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="info-header">
          <h3>快速操作</h3>
        </div>
        <div class="quick-actions">
          <router-link to="/dashboard/pledge" class="action-btn">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>
            质押资产
          </router-link>
          <router-link to="/dashboard/loan" class="action-btn">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/></svg>
            申请借贷
          </router-link>
          <router-link to="/dashboard/repayment" class="action-btn">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
            还款
          </router-link>
          <router-link to="/dashboard/data" class="action-btn">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>
            数据中心
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

function formatTime(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

const stats = computed(() => [
  {
    label: '资产总额',
    value: `$ ${Number(userStore.userInfo?.total_asset || 0).toLocaleString()}`,
    color: '#6366f1',
    iconBg: 'var(--accent-glow)',
    svg: '<svg viewBox="0 0 20 20" fill="currentColor"><path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.736 6.979C9.208 6.193 9.696 6 10 6c.304 0 .792.193 1.264.979a1 1 0 001.715-1.029C12.279 4.784 11.232 4 10 4s-2.279.784-2.979 1.95c-.285.475-.507 1-.67 1.55H6a1 1 0 000 2h.013a9.358 9.358 0 000 1H6a1 1 0 100 2h.351c.163.55.385 1.075.67 1.55C7.721 15.216 8.768 16 10 16s2.279-.784 2.979-1.95a1 1 0 10-1.715-1.029C10.792 13.807 10.304 14 10 14c-.304 0-.792-.193-1.264-.979a5.5 5.5 0 01-.354-.721h.618a1 1 0 100-2H8.048a7.461 7.461 0 010-1h.952a1 1 0 100-2h-.618c.13-.27.23-.502.354-.721z"/></svg>',
  },
  {
    label: '质押数量',
    value: '0',
    color: '#10b981',
    iconBg: 'var(--green-glow)',
    svg: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>',
  },
  {
    label: '活跃借贷',
    value: '0',
    color: '#06b6d4',
    iconBg: 'var(--cyan-glow)',
    svg: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/></svg>',
  },
  {
    label: '健康系数',
    value: '∞',
    color: '#f59e0b',
    iconBg: 'var(--amber-glow)',
    svg: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd"/></svg>',
  },
])
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ---- Welcome ---- */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 36px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(6,182,212,0.08) 100%);
  border: 1px solid var(--border-subtle);
  position: relative;
  overflow: hidden;
}
.welcome-banner::before {
  content: '';
  position: absolute;
  top: -80px;
  right: -80px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%);
  pointer-events: none;
}
.greeting {
  font-size: 13px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 500;
}
.welcome-text h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 6px 0 4px;
}
.welcome-text .sub {
  color: var(--text-secondary);
  font-size: 14px;
}
.welcome-decoration {
  width: 200px;
  opacity: 0.8;
}
.welcome-decoration svg {
  width: 100%;
  height: auto;
}

/* ---- Stats ---- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px 20px;
  border-radius: var(--radius);
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  border-color: var(--border-glow);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.08);
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon-inner {
  width: 22px;
  height: 22px;
}
.stat-icon-inner :deep(svg) {
  width: 100%;
  height: 100%;
}
.stat-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-mono);
  letter-spacing: -0.5px;
}

/* ---- Info ---- */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.info-card {
  border-radius: var(--radius);
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}
.info-header {
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-subtle);
}
.info-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.info-rows {
  padding: 6px 0;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 22px;
  transition: background 0.15s;
}
.info-row:hover {
  background: rgba(99, 102, 241, 0.04);
}
.info-key {
  font-size: 13px;
  color: var(--text-muted);
}
.info-val {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.info-val.mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-dot.green {
  background: var(--green);
  box-shadow: 0 0 6px var(--green-glow);
}

/* ---- Quick Actions ---- */
.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 16px 18px;
}
.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}
.action-btn svg {
  width: 16px;
  height: 16px;
  color: var(--accent-light);
  flex-shrink: 0;
}
.action-btn:hover {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--border-glow);
  color: var(--text-primary);
}
</style>
