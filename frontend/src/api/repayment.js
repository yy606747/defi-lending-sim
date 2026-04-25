import request from './request'

export function createRepayment(data) {
  return request.post('/api/repayment/create', data)
}

export function getRepaymentList() {
  return request.get('/api/repayment/list')
}
