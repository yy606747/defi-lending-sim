import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getInfo } from '../api/user'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

  function setToken(t) {
    token.value = t
    localStorage.setItem('token', t)
  }

  function clearToken() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  async function fetchUserInfo() {
    const res = await getInfo()
    if (res.code === 200) {
      userInfo.value = res.data
    }
  }

  return { token, userInfo, setToken, clearToken, fetchUserInfo }
})
