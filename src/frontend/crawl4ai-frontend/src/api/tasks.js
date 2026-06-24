// src/api/tasks.js
import request from './request'

// ===== 停止任务 =====
export function stopTask(taskId) {
  return request({
    url: `/tasks/${taskId}/stop/`,  // ✅ 去掉 /api/
    method: 'POST',
  })
}

// 其他函数如果有类似问题，也一起修复
export function getTasks(params) {
  return request({
    url: '/tasks/',  // ✅ 去掉 /api/
    method: 'GET',
    params
  })
}

export function getTaskDetail(taskId) {
  return request({
    url: `/tasks/${taskId}/detail/`,  // ✅ 去掉 /api/
    method: 'GET'
  })
}

export function getTaskProgress(taskId) {
  return request({
    url: `/tasks/${taskId}/progress/`,  // ✅ 去掉 /api/
    method: 'GET'
  })
}

export function getTaskPreview(taskId, limit = 10) {
  return request({
    url: `/tasks/${taskId}/preview/`,  // ✅ 去掉 /api/
    method: 'GET',
    params: { limit }
  })
}

export function startTask(data) {
  return request({
    url: '/tasks/start/',  // ✅ 去掉 /api/
    method: 'POST',
    data
  })
}

export function deleteTask(taskId) {
  return request({
    url: `/tasks/${taskId}/delete/`,  // ✅ 去掉 /api/
    method: 'DELETE'
  })
}