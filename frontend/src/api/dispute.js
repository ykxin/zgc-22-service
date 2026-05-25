/** 纠纷API */
import request from './request'

export const createDispute = (token, data) =>
  request.post('/api/dispute/create', data, { params: { token } })
export const getDisputes = (token) =>
  request.get('/api/dispute/list', { params: { token } })
export const getDisputeDetail = (id, token) =>
  request.get(`/api/dispute/${id}`, { params: { token } })

// 评价
export const createReview = (token, data) =>
  request.post('/api/review/create', data, { params: { token } })
