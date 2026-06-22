import api from '@/utils/api'

export function login(data) {
  return api.post('/auth/login/', data)
}

export function register(data) {
  return api.post('/auth/register/', data)
}

export function sendEmailCode(data) {
  return api.post('/auth/send-code/', data)
}
