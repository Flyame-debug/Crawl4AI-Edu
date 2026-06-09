// src/api/auth.js

// ======================
// 当前测试阶段：假接口版本
// ======================

// 登录接口（假数据）
export function login(data) {
  return Promise.resolve({ data: { token: 'fake-token-123' } })
}

// 注册接口（假数据）
export function register(data) {
  // 模拟后端返回一个用户 ID
  return Promise.resolve({ data: { userId: 'fake-user-001', ...data } })
}

// ======================
// 等后端接上时：真实接口版本
// ======================
// import api from '@/utils/api'

// export function login(data) {
//   return api.post('/auth/login', data)
// }

// export function register(data) {
//   return api.post('/auth/register', data)
// }
