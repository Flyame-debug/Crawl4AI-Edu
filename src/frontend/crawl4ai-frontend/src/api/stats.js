// src/api/stats.js
import api from '@/utils/api'

// 获取全局统计数据（仪表盘）
export function getStats() {
  return api.get('/stats/')
}