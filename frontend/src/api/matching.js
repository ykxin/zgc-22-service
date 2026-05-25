/** AI匹配API */
import request from './request'

export const getRecommend = (token, serviceCategory) =>
  request.get('/api/match/recommend', { params: { token, service_category: serviceCategory } })
export const createBooking = (token, data) =>
  request.post('/api/match/booking', data, { params: { token } })
export const acceptBooking = (orderId, token) =>
  request.put(`/api/match/booking/${orderId}/accept`, null, { params: { token } })
export const rejectBooking = (orderId, token) =>
  request.put(`/api/match/booking/${orderId}/reject`, null, { params: { token } })
