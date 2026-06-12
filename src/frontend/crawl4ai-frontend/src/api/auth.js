// src/api/auth.js
import api from '@/utils/api'   // 确保 utils/api.js 里有 export default api

// 登录接口 A1
export function login(data) {
  return api.post('/auth/login/', data)
}

// 注册接口 A2
export function register(data) {
  return api.post('/auth/register/', data)
}

// 发送邮箱验证码接口 A3
export function sendEmailCode(data) {
  return api.post('/auth/send-code/', data)
}
