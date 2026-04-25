import request from './request'

export function getAssetList() {
  return request.get('/api/asset/list')
}

export function getAsset(id) {
  return request.get(`/api/asset/${id}`)
}

export function simulatePrice() {
  return request.post('/api/asset/simulate')
}
