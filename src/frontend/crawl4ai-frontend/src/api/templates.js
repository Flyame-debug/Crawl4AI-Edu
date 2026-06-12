// src/api/templates.js
import api from '@/utils/api'

// 获取模板列表 T1
export function getTemplates(params) {
  return api.get('/templates/', { params })
}

// 获取模板详情 T2
export function getTemplateDetail(id) {
  return api.get(`/templates/${id}/`)
}

// 新建模板 T3
export function createTemplate(data) {
  return api.post('/templates/', data)
}

// 更新模板 T4
export function updateTemplate(id, data) {
  return api.put(`/templates/${id}/`, data)
}



