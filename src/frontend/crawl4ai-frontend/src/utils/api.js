// src/utils/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',   // 后端接口统一前缀
  timeout: 5000
})

// 请求拦截器（可选）
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器（可选）
api.interceptors.response.use(
  response => response,
  error => Promise.reject(error)
)

export default api   // 关键：必须有这一行
