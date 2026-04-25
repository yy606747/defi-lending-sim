<template>
  <div class="login-page">
    <canvas ref="canvasRef" class="particle-canvas" />

    <div class="login-wrapper">
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 48 48" fill="none">
            <rect x="4" y="4" width="40" height="40" rx="12" stroke="url(#g1)" stroke-width="2.5" />
            <path d="M16 28l4-12h8l4 12" stroke="url(#g2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <circle cx="24" cy="20" r="3" fill="url(#g2)" />
            <line x1="14" y1="32" x2="34" y2="32" stroke="url(#g2)" stroke-width="2" stroke-linecap="round" />
            <defs>
              <linearGradient id="g1" x1="4" y1="4" x2="44" y2="44"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>
              <linearGradient id="g2" x1="14" y1="16" x2="34" y2="32"><stop stop-color="#818cf8"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>
            </defs>
          </svg>
        </div>
        <h1>DeFi Lending</h1>
        <p>去中心化借贷协议仿真平台</p>
      </div>

      <div class="login-card">
        <div class="tab-bar">
          <button :class="{ active: activeTab === 'login' }" @click="activeTab = 'login'">登录</button>
          <button :class="{ active: activeTab === 'register' }" @click="activeTab = 'register'">注册</button>
          <div class="tab-indicator" :style="{ left: activeTab === 'login' ? '4px' : '50%' }" />
        </div>

        <Transition name="fade" mode="out-in">
          <form v-if="activeTab === 'login'" key="login" class="form" @submit.prevent="handleLogin">
            <div class="field">
              <label>虚拟地址</label>
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2H7V7a3 3 0 015.905-.75 1 1 0 001.937-.5A5.002 5.002 0 0010 2z"/></svg>
                <input v-model="loginForm.virtual_address" placeholder="0x..." />
              </div>
            </div>
            <div class="field">
              <label>密码</label>
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>
                <input v-model="loginForm.password" :type="showPwd ? 'text' : 'password'" placeholder="请输入密码" />
                <button type="button" class="toggle-pwd" @click="showPwd = !showPwd">
                  <svg v-if="!showPwd" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/></svg>
                  <svg v-else viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clip-rule="evenodd"/><path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z"/></svg>
                </button>
              </div>
            </div>
            <button type="submit" class="btn-primary" :disabled="loginLoading">
              <span v-if="loginLoading" class="spinner" />
              {{ loginLoading ? '登录中...' : '连接钱包' }}
            </button>
          </form>

          <form v-else key="register" class="form" @submit.prevent="handleRegister">
            <div class="field">
              <label>用户名</label>
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/></svg>
                <input v-model="registerForm.user_name" placeholder="请输入用户名" />
              </div>
            </div>
            <div class="field">
              <label>虚拟地址</label>
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2H7V7a3 3 0 015.905-.75 1 1 0 001.937-.5A5.002 5.002 0 0010 2z"/></svg>
                <input v-model="registerForm.virtual_address" placeholder="0x..." />
              </div>
            </div>
            <div class="field">
              <label>密码</label>
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>
                <input v-model="registerForm.password" type="password" placeholder="至少6位" />
              </div>
            </div>
            <div class="field">
              <label>确认密码</label>
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>
                <input v-model="registerForm.confirm_password" type="password" placeholder="再次输入密码" />
              </div>
              <p v-if="registerForm.confirm_password && registerForm.confirm_password !== registerForm.password" class="field-error">两次输入的密码不一致</p>
            </div>
            <button type="submit" class="btn-primary" :disabled="registerLoading">
              <span v-if="registerLoading" class="spinner" />
              {{ registerLoading ? '注册中...' : '创建账户' }}
            </button>
          </form>
        </Transition>
      </div>

      <p class="footer-text">Simulation Only · 不涉及真实资金</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/user'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref('login')
const showPwd = ref(false)
const loginLoading = ref(false)
const registerLoading = ref(false)
const canvasRef = ref(null)

const loginForm = reactive({ virtual_address: '', password: '' })
const registerForm = reactive({ user_name: '', virtual_address: '', password: '', confirm_password: '' })

async function handleLogin() {
  if (!loginForm.virtual_address || !loginForm.password) {
    ElMessage.warning('请填写虚拟地址和密码')
    return
  }
  loginLoading.value = true
  try {
    const res = await login(loginForm)
    if (res.code === 200) {
      userStore.setToken(res.data.token)
      userStore.userInfo = res.data.user
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } else {
      ElMessage.error(res.message)
    }
  } catch {
    ElMessage.error('网络错误')
  } finally {
    loginLoading.value = false
  }
}

async function handleRegister() {
  if (!registerForm.user_name || !registerForm.virtual_address || !registerForm.password) {
    ElMessage.warning('请填写所有字段')
    return
  }
  if (registerForm.password.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  if (registerForm.password !== registerForm.confirm_password) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  registerLoading.value = true
  try {
    const res = await register(registerForm)
    if (res.code === 200) {
      ElMessage.success('注册成功，请登录')
      activeTab.value = 'login'
      loginForm.virtual_address = registerForm.virtual_address
    } else {
      ElMessage.error(res.message)
    }
  } catch {
    ElMessage.error('网络错误')
  } finally {
    registerLoading.value = false
  }
}

let animId = 0
onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let w, h
  const particles = []
  const count = 60

  function resize() {
    w = canvas.width = window.innerWidth
    h = canvas.height = window.innerHeight
  }
  resize()
  window.addEventListener('resize', resize)

  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h,
      r: Math.random() * 1.5 + 0.5,
      dx: (Math.random() - 0.5) * 0.4,
      dy: (Math.random() - 0.5) * 0.4,
    })
  }

  function draw() {
    ctx.clearRect(0, 0, w, h)
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i]
      p.x += p.dx
      p.y += p.dy
      if (p.x < 0) p.x = w
      if (p.x > w) p.x = 0
      if (p.y < 0) p.y = h
      if (p.y > h) p.y = 0

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(99,102,241,0.5)'
      ctx.fill()

      for (let j = i + 1; j < particles.length; j++) {
        const q = particles[j]
        const dist = Math.hypot(p.x - q.x, p.y - q.y)
        if (dist < 140) {
          ctx.beginPath()
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(q.x, q.y)
          ctx.strokeStyle = `rgba(99,102,241,${0.12 * (1 - dist / 140)})`
          ctx.lineWidth = 0.6
          ctx.stroke()
        }
      }
    }
    animId = requestAnimationFrame(draw)
  }
  draw()
})

onUnmounted(() => cancelAnimationFrame(animId))
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(ellipse at 30% 20%, rgba(99,102,241,0.12) 0%, transparent 60%),
              radial-gradient(ellipse at 70% 80%, rgba(6,182,212,0.08) 0%, transparent 60%),
              var(--bg-deep);
  overflow: hidden;
}

.particle-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.login-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

.brand {
  text-align: center;
}
.brand-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  animation: float 6s ease-in-out infinite;
}
.brand-icon svg {
  width: 100%;
  height: 100%;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.brand h1 {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #f1f5f9, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  letter-spacing: -0.5px;
}
.brand p {
  color: var(--text-muted);
  font-size: 14px;
  margin-top: 6px;
}

.login-card {
  width: 420px;
  background: var(--bg-card);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 32px;
  box-shadow: var(--shadow-card), 0 0 80px rgba(99,102,241,0.06);
}

.tab-bar {
  position: relative;
  display: flex;
  background: rgba(30, 41, 59, 0.7);
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 28px;
}
.tab-bar button {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: color 0.3s;
  font-family: var(--font-sans);
}
.tab-bar button.active {
  color: var(--text-primary);
}
.tab-indicator {
  position: absolute;
  top: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.field label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 12px;
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  pointer-events: none;
}
.input-wrapper input {
  width: 100%;
  padding: 11px 12px 11px 38px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: var(--font-sans);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-wrapper input::placeholder {
  color: var(--text-muted);
}
.input-wrapper input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}
.toggle-pwd {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
}
.toggle-pwd svg {
  width: 16px;
  height: 16px;
}
.toggle-pwd:hover {
  color: var(--text-secondary);
}

.field-error {
  color: var(--rose);
  font-size: 12px;
  margin-top: 4px;
}

.btn-primary {
  width: 100%;
  padding: 12px;
  margin-top: 4px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  position: relative;
  overflow: hidden;
}
.btn-primary::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
  transform: translateX(-100%);
  transition: transform 0.5s;
}
.btn-primary:hover::before {
  transform: translateX(100%);
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(99, 102, 241, 0.35);
}
.btn-primary:active {
  transform: translateY(0);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.footer-text {
  color: var(--text-muted);
  font-size: 12px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
