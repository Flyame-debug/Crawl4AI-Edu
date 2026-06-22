import axios from 'axios'

// 后端地址：根据环境配置
// 开发环境使用代理或直接指向后端
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_BASE_URL,  // 直接指向后端，不加 /api
  timeout: 120000,  // 超时时间调长一点
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：自动添加 Token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    console.log('请求URL:', config.url, 'Token:', token)  // 添加这行调试
    if (token) {
      config.headers.Authorization = `Bearer ${token}`  // ✅ 修正：加空格和 token
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  response => {
    // 直接返回 response，由调用方处理
    return response
  },
  error => {
    // 401 未登录：跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      window.location.href = '/auth'
    }
    return Promise.reject(error)
  }
)

export default api