// src/utils/request.js
import axios from 'axios'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',  // 后端 API 基础路径
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 如果响应中有 code 字段，检查是否成功
    if (response.data && response.data.code !== undefined) {
      if (response.data.code === 401) {
        // Token 过期，跳转到登录页
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
        return Promise.reject(new Error('请重新登录'))
      }
    }
    return response
  },
  (error) => {
    console.error('响应错误:', error)
    if (error.response) {
      // 服务器返回了错误状态码
      const { status, data } = error.response
      if (status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    } else if (error.request) {
      // 请求发出但没有收到响应
      console.error('网络连接失败')
      return Promise.reject(new Error('网络连接失败，请检查网络'))
    } else {
      // 请求配置出错
      console.error('请求配置错误:', error.message)
      return Promise.reject(error)
    }
  }
)

export default request