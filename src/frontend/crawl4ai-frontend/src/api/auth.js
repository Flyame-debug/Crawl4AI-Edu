import api from '@/utils/api'

export function login(data) {
  return api.post('/api/auth/login/', data)  // 加上 /api/
}

export function register(data) {
  return api.post('/api/auth/register/', data)  // 加上 /api/
}

export function sendEmailCode(data) {
  return api.post('/api/auth/send-code/', data)  // 加上 /api/
}