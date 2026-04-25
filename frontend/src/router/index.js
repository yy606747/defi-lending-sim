import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: LoginView },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    redirect: '/dashboard/home',
    children: [
      { path: 'home', name: 'Home', component: () => import('../views/HomeView.vue') },
      { path: 'assets', name: 'Assets', component: () => import('../views/AssetView.vue') },
      { path: 'pledge', name: 'Pledge', component: () => import('../views/PledgeView.vue') },
      { path: 'loan', name: 'Loan', component: () => import('../views/LoanView.vue') },
      { path: 'repayment', name: 'Repayment', component: () => import('../views/RepaymentView.vue') },
      { path: 'liquidation', name: 'Liquidation', component: () => import('../views/LiquidationView.vue') },
      { path: 'data', name: 'Data', component: () => import('../views/DataView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path.startsWith('/dashboard') && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
