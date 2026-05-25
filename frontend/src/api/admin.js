/** 管理后台API */
import request from './request'

export const getDashboard = (token) => request.get('/api/admin/dashboard', { params: { token } })
export const getUsers = (token, params) => request.get('/api/admin/users', { params: { token, ...params } })
export const toggleUser = (id, token) => request.put(`/api/admin/users/${id}/status`, null, { params: { token } })
export const getCertifications = (token, params) =>
  request.get('/api/admin/certifications', { params: { token, ...params } })
export const reviewCert = (id, token, data) =>
  request.put(`/api/admin/certifications/${id}/review`, data, { params: { token } })
export const getAllOrders = (token, params) =>
  request.get('/api/admin/orders', { params: { token, ...params } })
export const getAllDisputes = (token, params) =>
  request.get('/api/admin/disputes', { params: { token, ...params } })
export const getAdminSops = (token, category) =>
  request.get('/api/admin/sops', { params: { token, category } })
export const createSop = (token, data) =>
  request.post('/api/service/sop', data, { params: { token } })
export const updateSop = (id, token, data) =>
  request.put(`/api/service/sop/${id}`, data, { params: { token } })
export const toggleSop = (id, token) =>
  request.put(`/api/service/sop/${id}/toggle`, null, { params: { token } })
