// src/api/tasks.js
import api from '@/utils/api'

// ----------------------
// 任务控制接口 J1–J4
// ----------------------

// 启动采集任务 J1
export function startTask(data) {
  return api.post('/tasks/start/', data)
}

// 暂停任务 J2
export function pauseTask(taskId) {
  return api.post(`/tasks/${taskId}/pause/`)
}

// 停止/取消任务 J3
export function stopTask(taskId) {
  return api.post(`/tasks/${taskId}/stop/`)
}

// 删除任务 J4
export function deleteTask(taskId) {
  return api.delete(`/tasks/${taskId}/`)
}

// ----------------------
// 任务查询接口 Q1–Q4
// ----------------------

// Q1 获取任务列表
export function getTasks(params) {
  return api.get('/tasks/', { params })
}

// Q2 获取任务详情
export function getTaskDetail(taskId) {
  return api.get(`/tasks/${taskId}/`)
}

// Q3 获取任务进度
export function getTaskProgress(taskId) {
  return api.get(`/tasks/${taskId}/progress/`)
}

// Q4 获取采集数据预览
export function getTaskPreview(taskId, limit = 5) {
  return api.get(`/tasks/${taskId}/preview/`, { params: { limit } })
}

// ----------------------
// 数据导出接口 E1
// ----------------------

// 下载任务结果（返回文件流）
export function downloadTaskResult(taskId, format = 'json') {
  return api.get(`/tasks/${taskId}/download/`, {
    params: { format },
    responseType: 'blob' // 关键：返回文件流
  })
}

// ----------------------
// 数据展示接口 D1
// ----------------------

// 获取页面列表
export function getPageSnapshots(params) {
  return api.get('/pagesnapshot/', { params })
}
