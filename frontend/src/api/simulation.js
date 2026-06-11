import request from './request'

export function getPriceHistory(assetId) {
  return request.get(`/api/simulation/price-history/${assetId}`)
}

export function getStatistics() {
  return request.get('/api/simulation/statistics')
}

export function advanceTime(days) {
  return request.post('/api/simulation/advance-time', { days })
}
