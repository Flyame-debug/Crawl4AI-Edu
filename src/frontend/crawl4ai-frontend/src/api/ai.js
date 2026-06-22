import api from '@/utils/api'

// AI 生成采集规则
export function generateRules(data) {
  return api.post('/api/ai/generate-rules/', data)
}