/** 服务视频API */
import request from './request'

export const uploadServiceVideo = (formData) => request.post('/api/video/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
