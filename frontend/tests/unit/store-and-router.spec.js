import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const getInfoMock = vi.hoisted(() => vi.fn())

vi.mock('../../src/api/user', () => ({
  getInfo: getInfoMock,
}))

describe('user store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('persists token and clears all user session state', async () => {
    const { useUserStore } = await import('../../src/stores/user')
    const store = useUserStore()

    store.setToken('token-1')
    store.userInfo = { user_name: 'alice' }
    expect(localStorage.getItem('token')).toBe('token-1')

    store.clearToken()
    expect(store.token).toBe('')
    expect(store.userInfo).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('loads current user info only when backend envelope is successful', async () => {
    const { useUserStore } = await import('../../src/stores/user')
    const store = useUserStore()
    getInfoMock.mockResolvedValue({ code: 200, data: { user_name: 'alice', virtual_address: '0xA' } })

    await store.fetchUserInfo()

    expect(store.userInfo).toEqual({ user_name: 'alice', virtual_address: '0xA' })
  })

  it('leaves stale userInfo untouched when backend returns non-200 envelope', async () => {
    const { useUserStore } = await import('../../src/stores/user')
    const store = useUserStore()
    store.userInfo = { user_name: 'old' }
    getInfoMock.mockResolvedValue({ code: 400, data: { user_name: 'new' } })

    await store.fetchUserInfo()

    expect(store.userInfo).toEqual({ user_name: 'old' })
  })
})

describe('router auth guard', () => {
  it('redirects unauthenticated users away from dashboard routes', async () => {
    const router = (await import('../../src/router')).default

    await router.push('/dashboard/home')
    await router.isReady()

    expect(router.currentRoute.value.fullPath).toBe('/login')
  })

  it('allows authenticated users to enter dashboard child routes', async () => {
    const router = (await import('../../src/router')).default
    localStorage.setItem('token', 'token-1')

    await router.push('/dashboard/loan')
    await router.isReady()

    expect(router.currentRoute.value.fullPath).toBe('/dashboard/loan')
  })

  it('redirects authenticated users away from login page to the dashboard', async () => {
    const router = (await import('../../src/router')).default
    localStorage.setItem('token', 'token-1')

    await router.push('/login')
    await router.isReady()

    expect(router.currentRoute.value.fullPath).toBe('/dashboard/home')
  })
})

