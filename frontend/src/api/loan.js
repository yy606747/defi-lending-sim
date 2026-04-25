import request from './request'

export function createLoan(data) {
  return request.post('/api/loan/create', data)
}

export function getLoanList() {
  return request.get('/api/loan/list')
}

export function getLoanRate(assetId) {
  return request.get('/api/loan/rate', { params: { asset_id: assetId } })
}
