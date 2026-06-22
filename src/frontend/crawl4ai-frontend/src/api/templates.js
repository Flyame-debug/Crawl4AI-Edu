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
  return api.post('/api/templates/create/', data)
}

// ✅ 更新模板 - 使用 /update/ 后缀
export function updateTemplate(id, data) {
  return api.put(`/api/templates/${id}/update/`, data)  // ← 改成 /update/
}

// 删除模板（补充）
export function deleteTemplate(id) {
  return api.delete(`/api/templates/${id}/`)
}

// 保存规则到模板
export function saveTemplateRule(id, rule) {
  return api.post(`/api/templates/${id}/save_rule/`, { crawler_rule: rule })
}


// 获取历史模板（P1 新增）
export function getTemplateHistory(params) {
  return api.get('/api/templates/history/', { params })
}