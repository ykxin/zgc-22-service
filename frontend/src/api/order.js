/** 订单API */
import request from './request'

export const getOrders = (token, params = {}) => request.get('/api/order/list', { params: { token, ...params } })
export const getOrderDetail = (id, token) => request.get(`/api/order/${id}`, { params: { token } })
export const updateOrderStatus = (id, status, token) =>
  request.put(`/api/order/${id}/status`, null, { params: { token, status } })

// 服务标准打卡
export const doCheckin = (formData) => request.post('/api/service/checkin', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
export const doAcceptance = (orderId, token) =>
  request.post(`/api/service/acceptance/${orderId}`, null, { params: { token } })
export const getSops = (category) => request.get('/api/service/sops', { params: { category } })
export const createCustomStandard = (token, data) =>
  request.post('/api/service/custom-standard', data, { params: { token } })
export const getCustomStandards = (token, category) =>
  request.get('/api/service/custom-standards', { params: { token, category } })
