/** AI资质核验API */
import request from './request'

export const uploadCert = (formData) => request.post('/api/cert/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
export const getCertList = (token) => request.get('/api/cert/list', { params: { token } })
export const checkExpiring = (token) => request.get('/api/cert/expiring', { params: { token } })
