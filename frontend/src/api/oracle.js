import request from './request'

export function getOracleOverview() {
  return request.get('/api/oracle/overview')
}

export function feedPrices(updates) {
  return request.post('/api/oracle/feed', updates)
}
