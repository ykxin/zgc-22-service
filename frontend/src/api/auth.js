/** 用户认证API */
import request from './request'

export const sendSms = (phone) => request.post('/api/auth/send-sms', { phone })
export const register = (data) => request.post('/api/auth/register', data)
export const login = (data) => request.post('/api/auth/login', data)
export const getProfile = (token) => request.get('/api/auth/profile-by-token', { params: { token } })
export const updateProfile = (token, data) => request.put('/api/auth/profile', data, { params: { token } })
export const resetPassword = (data) => request.post('/api/auth/reset-password', data)
