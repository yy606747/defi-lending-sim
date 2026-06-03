import request from './request'

export function getAssetList() {
  return request.get('/api/asset/list')
}

export function getAsset(id) {
  return request.get(`/api/asset/${id}`)
}

export function simulatePrice(prices) {
  if (prices === undefined) return request.post('/api/asset/simulate')
  return request.post('/api/asset/simulate', prices)
}
