<template>
  <div class="dashboard">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-dot" />
        <span>DeFi Lending</span>
      </div>

      <nav class="sidebar-nav">
        <router-link v-for="item in menuItems" :key="item.path" :to="item.path" class="nav-item" :class="{ active: route.path === item.path }">
          <component :is="item.icon" class="nav-icon" />
          <span>{{ item.label }}</span>
          <div v-if="route.path === item.path" class="active-bar" />
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="network-badge">
          <span class="network-dot" />
          Testnet
        </div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <h2 class="page-title">{{ currentPageTitle }}</h2>
        </div>
        <div class="topbar-right">
          <div class="user-chip" @click="showUserMenu = !showUserMenu">
            <div class="avatar">{{ userStore.userInfo?.user_name?.[0]?.toUpperCase() || '?' }}</div>
            <span class="user-name">{{ userStore.userInfo?.user_name }}</span>
            <svg class="chevron" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
          </div>
          <Transition name="dropdown">
            <div v-if="showUserMenu" class="user-dropdown">
              <div class="dropdown-header">
                <span class="dropdown-addr">{{ userStore.userInfo?.virtual_address }}</span>
              </div>
              <button class="dropdown-item danger" @click="handleLogout">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clip-rule="evenodd"/></svg>
                断开连接
              </button>
            </div>
          </Transition>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showUserMenu = ref(false)

const IconHome = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/>' }) }
const IconCoin = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.736 6.979C9.208 6.193 9.696 6 10 6c.304 0 .792.193 1.264.979a1 1 0 001.715-1.029C12.279 4.784 11.232 4 10 4s-2.279.784-2.979 1.95c-.285.475-.507 1-.67 1.55H6a1 1 0 000 2h.013a9.358 9.358 0 000 1H6a1 1 0 100 2h.351c.163.55.385 1.075.67 1.55C7.721 15.216 8.768 16 10 16s2.279-.784 2.979-1.95a1 1 0 10-1.715-1.029C10.792 13.807 10.304 14 10 14c-.304 0-.792-.193-1.264-.979a5.5 5.5 0 01-.354-.721h.618a1 1 0 100-2H8.048a7.461 7.461 0 010-1h.952a1 1 0 100-2h-.618c.13-.27.23-.502.354-.721z"/>' }) }
const IconLock = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/>' }) }
const IconMoney = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/>' }) }
const IconRefresh = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>' }) }
const IconWarning = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>' }) }
const IconChart = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'currentColor', innerHTML: '<path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>' }) }
const IconRadar = { render: () => h('svg', { viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', innerHTML: '<path d="M10 2.5v15"/><path d="M2.5 10h15"/><circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="2.5"/><path d="M10 10l4.2-4.2"/>' }) }

const menuItems = [
  { path: '/dashboard/home', label: '系统首页', icon: IconHome },
  { path: '/dashboard/assets', label: '虚拟资产', icon: IconCoin },
  { path: '/dashboard/pledge', label: '质押管理', icon: IconLock },
  { path: '/dashboard/loan', label: '借贷管理', icon: IconMoney },
  { path: '/dashboard/repayment', label: '还款管理', icon: IconRefresh },
  { path: '/dashboard/liquidation', label: '清算模拟', icon: IconWarning },
  { path: '/dashboard/data', label: '数据中心', icon: IconChart },
  { path: '/dashboard/oracle', label: '预言机控制台', icon: IconRadar },
]

const pageTitles = {
  '/dashboard/home': '系统首页',
  '/dashboard/assets': '虚拟资产管理',
  '/dashboard/pledge': '质押管理',
  '/dashboard/loan': '借贷管理',
  '/dashboard/repayment': '还款管理',
  '/dashboard/liquidation': '清算模拟',
  '/dashboard/data': '数据中心',
  '/dashboard/oracle': '预言机与全局风控监控中心',
}
const currentPageTitle = computed(() => pageTitles[route.path] || 'Dashboard')

onMounted(() => {
  if (!userStore.userInfo) userStore.fetchUserInfo()
  document.addEventListener('click', closeMenu)
})
onUnmounted(() => document.removeEventListener('click', closeMenu))

function closeMenu(e) {
  if (!e.target.closest('.topbar-right')) showUserMenu.value = false
}

function handleLogout() {
  userStore.clearToken()
  router.push('/login')
}
</script>

<style scoped>
.dashboard {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

	/* ---- 侧边栏 ---- */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px 32px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}
.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #06b6d4);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.5);
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 10px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  position: relative;
}
.nav-item:hover {
  color: var(--text-secondary);
  background: rgba(99, 102, 241, 0.06);
}
.nav-item.active {
  color: var(--accent-light);
  background: rgba(99, 102, 241, 0.1);
}
.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.active-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}
.network-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
.network-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px var(--green-glow);
}

	/* ---- 主内容区 ---- */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-deep);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 28px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(10, 14, 23, 0.8);
  backdrop-filter: blur(12px);
  flex-shrink: 0;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.topbar-right {
  position: relative;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
}
.user-chip:hover {
  background: rgba(99, 102, 241, 0.08);
}
.avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}
.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}
.chevron {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 220px;
  background: var(--bg-card-solid);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  z-index: 100;
}
.dropdown-header {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
}
.dropdown-addr {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  word-break: break-all;
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background 0.15s;
}
.dropdown-item:hover {
  background: rgba(99, 102, 241, 0.08);
}
.dropdown-item svg {
  width: 16px;
  height: 16px;
}
.dropdown-item.danger {
  color: var(--rose);
}
.dropdown-item.danger:hover {
  background: var(--rose-glow);
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
}

/* 页面切换动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
