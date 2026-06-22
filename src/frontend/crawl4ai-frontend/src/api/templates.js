// src/api/templates.js
import api from '@/utils/api'

// 获取模板列表（支持分类筛选）
export function getTemplates(params) {
  return api.get('/api/templates/', { params })
}

// 获取模板详情
export function getTemplateDetail(id) {
  return api.get(`/api/templates/${id}/`)
}

// 新建模板
export function createTemplate(data) {
  return api.post('/api/templates/', data)
}

// 更新模板
export function updateTemplate(id, data) {
  return api.put(`/api/templates/${id}/`, data)
}

// 删除模板（补充）
export function deleteTemplate(id) {
  return api.delete(`/api/templates/${id}/`)
}

// 获取历史模板（P1 新增）
export function getTemplateHistory(params) {
  return api.get('/api/templates/history/', { params })
}