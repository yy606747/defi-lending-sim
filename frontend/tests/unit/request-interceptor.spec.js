import { describe, it, expect, vi } from 'vitest'
import request from '../../src/api/request'
import router from '../../src/router'

describe('axios request/response interceptor', () => {
  it('attaches JWT bearer token to outgoing requests', async () => {
    localStorage.setItem('token', 'front-token')

    const response = await request.get('/api/user/info', {
      adapter: async (config) => ({
        data: { headers: config.headers },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }),
    })

    expect(response.headers.Authorization).toBe('Bearer front-token')
  })

  it('clears token and redirects to login when backend returns 401', async () => {
    localStorage.setItem('token', 'expired-token')
    const pushSpy = vi.spyOn(router, 'push').mockResolvedValue()

    await expect(
      request.get('/api/user/info', {
        adapter: async () => Promise.reject({ response: { status: 401 } }),
      }),
    ).rejects.toBeTruthy()

    expect(localStorage.getItem('token')).toBeNull()
    expect(pushSpy).toHaveBeenCalledWith('/login')
  })

  it('does not attach an Authorization header when no token exists', async () => {
    const response = await request.get('/api/asset/list', {
      adapter: async (config) => ({
        data: { headers: config.headers },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }),
    })

    expect(response.headers.Authorization).toBeUndefined()
  })
})

