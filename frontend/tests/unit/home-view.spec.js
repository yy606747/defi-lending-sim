import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

const pledgeApi = vi.hoisted(() => ({ getPledgeList: vi.fn() }))
const loanApi = vi.hoisted(() => ({ getLoanList: vi.fn() }))
const userApi = vi.hoisted(() => ({
  getInfo: vi.fn(),
  updateInfo: vi.fn(),
}))

vi.mock('../../src/api/pledge', () => pledgeApi)
vi.mock('../../src/api/loan', () => loanApi)
vi.mock('../../src/api/user', () => userApi)

const HomeView = (await import('../../src/views/HomeView.vue')).default
const { useUserStore } = await import('../../src/stores/user')

function mountHome() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    user_name: 'alice',
    virtual_address: '0xA',
    register_time: '2026-06-01T00:00:00',
    total_asset: '10000.0000',
  }
  const wrapper = mount(HomeView, { global: { plugins: [pinia] } })
  return { wrapper, store }
}

describe('HomeView user-name editing', () => {
  beforeEach(() => {
    pledgeApi.getPledgeList.mockResolvedValue({ code: 200, data: [] })
    loanApi.getLoanList.mockResolvedValue({ code: 200, data: [] })
    userApi.updateInfo.mockResolvedValue({
      code: 200,
      data: {
        user_name: 'bob',
        virtual_address: '0xA',
        register_time: '2026-06-01T00:00:00',
        total_asset: '10000.0000',
      },
    })
  })

  it('updates the user name and synchronizes the user store', async () => {
    const { wrapper, store } = mountHome()
    await flushPromises()

    await wrapper.get('[data-test="edit-user-name"]').trigger('click')
    await wrapper.get('[data-test="user-name-input"]').setValue('  bob  ')
    await wrapper.get('[data-test="save-user-name"]').trigger('click')
    await flushPromises()

    expect(userApi.updateInfo).toHaveBeenCalledWith({ user_name: 'bob' })
    expect(store.userInfo.user_name).toBe('bob')
    expect(wrapper.text()).toContain('bob')
    expect(ElMessage.success).toHaveBeenCalledWith('用户名更新成功')
  })

  it('rejects a blank user name before calling the API', async () => {
    const { wrapper } = mountHome()
    await flushPromises()

    await wrapper.get('[data-test="edit-user-name"]').trigger('click')
    await wrapper.get('[data-test="user-name-input"]').setValue('   ')
    await wrapper.get('[data-test="save-user-name"]').trigger('click')

    expect(userApi.updateInfo).not.toHaveBeenCalled()
    expect(ElMessage.warning).toHaveBeenCalledWith('用户名不能为空')
  })

  it('keeps edit mode open when the backend rejects the update', async () => {
    userApi.updateInfo.mockResolvedValue({ code: 400, message: '用户名不能为空', data: null })
    const { wrapper, store } = mountHome()
    await flushPromises()

    await wrapper.get('[data-test="edit-user-name"]').trigger('click')
    await wrapper.get('[data-test="user-name-input"]').setValue('bob')
    await wrapper.get('[data-test="save-user-name"]').trigger('click')
    await flushPromises()

    expect(store.userInfo.user_name).toBe('alice')
    expect(wrapper.find('[data-test="user-name-input"]').exists()).toBe(true)
    expect(ElMessage.error).toHaveBeenCalledWith('用户名不能为空')
  })
})
