import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const routerPushMock = vi.hoisted(() => vi.fn())
const userApiMock = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPushMock }),
}))

vi.mock('../../src/api/user', () => userApiMock)

const LoginView = (await import('../../src/views/LoginView.vue')).default

function mountLogin() {
  return mount(LoginView, {
    global: {
      plugins: [createPinia()],
    },
  })
}

describe('LoginView wallet/session form', () => {
  it('blocks empty login submissions on the client side', async () => {
    const wrapper = mountLogin()

    await wrapper.find('form').trigger('submit.prevent')

    expect(ElMessage.warning).toHaveBeenCalledWith('请填写虚拟地址和密码')
    expect(userApiMock.login).not.toHaveBeenCalled()
  })

  it('rejects whitespace-only login identifiers before calling the API', async () => {
    const wrapper = mountLogin()
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('   ')
    await inputs[1].setValue('secret123')

    await wrapper.find('form').trigger('submit.prevent')

    expect(ElMessage.warning).toHaveBeenCalledWith('请填写虚拟地址和密码')
    expect(userApiMock.login).not.toHaveBeenCalled()
  })

  it('stores token and routes to dashboard after successful login', async () => {
    userApiMock.login.mockResolvedValue({
      code: 200,
      data: { token: 'token-1', user: { user_name: 'alice', virtual_address: '0xA' } },
    })
    const wrapper = mountLogin()
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('0xA')
    await inputs[1].setValue('secret123')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(localStorage.getItem('token')).toBe('token-1')
    expect(ElMessage.success).toHaveBeenCalledWith('登录成功')
    expect(routerPushMock).toHaveBeenCalledWith('/dashboard')
  })

  it('rejects weak register passwords beyond length-only checks', async () => {
    userApiMock.register.mockResolvedValue({ code: 200, data: {} })
    const wrapper = mountLogin()
    wrapper.vm.activeTab = 'register'
    await nextTick()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('alice')
    await inputs[1].setValue('0xA')
    await inputs[2].setValue('abcdef')
    await inputs[3].setValue('abcdef')

    await wrapper.find('form').trigger('submit.prevent')

    expect(ElMessage.warning).toHaveBeenCalledWith('密码需同时包含数字和字母')
    expect(userApiMock.register).not.toHaveBeenCalled()
  })

  it('rejects mismatched registration confirmation passwords', async () => {
    const wrapper = mountLogin()
    wrapper.vm.activeTab = 'register'
    await nextTick()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('alice')
    await inputs[1].setValue('0xA')
    await inputs[2].setValue('abc12345')
    await inputs[3].setValue('abc12346')

    await wrapper.find('form').trigger('submit.prevent')

    expect(ElMessage.warning).toHaveBeenCalledWith('两次输入的密码不一致')
    expect(userApiMock.register).not.toHaveBeenCalled()
  })
})
