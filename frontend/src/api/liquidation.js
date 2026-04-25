import request from './request'

export function getLiquidationRisk() {
  return request.get('/api/liquidation/risk')
}

export function executeLiquidation(data) {
  return request.post('/api/liquidation/execute', data)
}

export function getLiquidationList() {
  return request.get('/api/liquidation/list')
}
