import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 5000
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = Bearer 
    }
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response,
  error => Promise.reject(error)
)

export default api
