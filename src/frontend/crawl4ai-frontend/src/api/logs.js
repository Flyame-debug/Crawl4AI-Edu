// src/api/logs.js
import api from '@/utils/api'

// 获取日志（通用）
export function getLogs(params) {
  return api.get('/api/logs/', { params })
}

// ✅ 获取任务专属日志（按任务ID查询）
export function getTaskLogs(taskId, lines = 200) {
  return api.get('/api/logs/', { 
    params: { 
      task_id: taskId,
      lines: lines
    }
  })
}

// 获取日志文件列表
export function getLogFiles() {
  return api.get('/api/logs/files/')
}