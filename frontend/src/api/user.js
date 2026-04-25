import request from './request'

export function register(data) {
  return request.post('/api/user/register', data)
}

export function login(data) {
  return request.post('/api/user/login', data)
}

export function getInfo() {
  return request.get('/api/user/info')
}

export function updateInfo(data) {
  return request.put('/api/user/info', data)
}
