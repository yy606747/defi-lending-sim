import request from './request'

export function createPledge(data) {
  return request.post('/api/pledge/create', data)
}

export function getPledgeList() {
  return request.get('/api/pledge/list')
}

export function unlockPledge(pledgeId) {
  return request.post(`/api/pledge/unlock/${pledgeId}`)
}
