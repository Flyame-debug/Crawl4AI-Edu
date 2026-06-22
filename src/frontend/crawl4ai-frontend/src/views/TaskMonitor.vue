<template>
  <div class="task-list-page">
    <!-- 搜索卡片 -->
    <el-card class="search-card" shadow="hover">
      <div class="filters">
        <div class="filter-row">
        <!-- ✅ 新增：显示预览任务的开关 -->
          <el-checkbox v-model="filters.includePreview" @change="fetchTasks">
            显示预览任务
          </el-checkbox>
          <el-select v-model="filters.type" placeholder="任务类型" style="width: 160px; margin-right: 10px;">
            <el-option label="正式采集" value="formal" />
            <el-option label="预览采集" value="preview" />
          </el-select>
          <el-select v-model="filters.status" placeholder="状态" style="width: 160px; margin-right: 10px;">
            <el-option label="等待中" value="pending" />
            <el-option label="采集中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已停止" value="stopped" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            class="short-date-picker"
          />
          <el-button type="primary" @click="fetchTasks" style="margin-left: 10px;">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
    </el-card>

    <!-- 任务列表表格 -->
    <el-table :data="tasks" class="task-table" empty-text="暂无任务" v-loading="loading">
      <!-- ✅ 任务名称列增加预览标识 -->
      <el-table-column prop="task_name" label="任务名称" min-width="150">
        <template #default="scope">
          <span>
            <el-tag v-if="scope.row.task_type === 'preview'" size="small" type="warning" style="margin-right: 6px;">预览</el-tag>
            {{ scope.row.task_name || scope.row.task_id || '未命名任务' }}
          </span>
        </template>
      </el-table-column>
      
      <el-table-column prop="template_name" label="模板来源" min-width="120">
        <template #default="scope">
          <span>{{ scope.row.template_name || '无模板' }}</span>
        </template>
      </el-table-column>
      
      <el-table-column prop="created_at" label="执行时间" min-width="160">
        <template #default="scope">
          <span>{{ formatTime(scope.row.created_at) }}</span>
        </template>
      </el-table-column>
      
      <el-table-column prop="status" label="状态" min-width="100">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="total_pages" label="数据条数" min-width="100">
        <template #default="scope">
          <span>{{ scope.row.success_pages || 0 }} / {{ scope.row.total_pages || 0 }}</span>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" min-width="280" fixed="right">
        <template #default="scope">
          <div class="op-buttons">
            <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
            <el-button size="small" @click="viewLog(scope.row)">日志</el-button>
            <el-button size="small" @click="rerunTask(scope.row)">重新执行</el-button>
            <el-dropdown>
              <el-button size="small" type="primary">
                导出 <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="exportTask(scope.row, 'html')">导出 HTML</el-dropdown-item>
                  <el-dropdown-item @click="exportTask(scope.row, 'markdown')">导出 Markdown</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTasks, getTaskDetail, startTask, getTaskPreview } from '@/api/tasks'

// ✅ 导入 getLogs API
import { getTaskLogs } from '@/api/logs'  // ✅ 新增导入

export default {
  name: 'TaskMonitor',
  components: { ArrowDown },
  data() {
    return {
      tasks: [],
      loading: false,
      filters: {
        type: '',
        status: '',
        dateRange: [],
        includePreview: false  // ✅ 默认不显示预览任务
      }
    }
  },
  computed: {
    // ✅ 计算属性：根据开关过滤任务
    displayTasks() {
      if (this.filters.includePreview) {
        return this.tasks
      }
      // 默认过滤掉预览任务
      return this.tasks.filter(task => task.task_type !== 'preview')
    }
  },
  mounted() {
    this.fetchTasks()
  },
  methods: {
    async fetchTasks() {
      this.loading = true
      try {
        const params = {}
        if (this.filters.type) params.task_type = this.filters.type
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.dateRange && this.filters.dateRange.length === 2) {
          params.start_date = this.formatDate(this.filters.dateRange[0])
          params.end_date = this.formatDate(this.filters.dateRange[1])
        }
        // ✅ 添加分页参数，获取更多数据
        params.page = 1
        params.page_size = 50  // 一次获取50条
        const res = await getTasks(params)
        console.log('📥 任务列表响应:', res)
        
        if (res.data.code === 200) {
          this.tasks = res.data.data.results || res.data.data || []
        } else {
          ElMessage.error(res.data.msg || '获取任务列表失败')
        }
      } catch (error) {
        console.error('获取任务列表失败：', error)
        ElMessage.error('获取任务列表失败，请稍后重试')
        this.tasks = this.getMockTasks()
      } finally {
        this.loading = false
      }
    },
    
    getMockTasks() {
      return [
        { 
          id: 1, 
          task_name: '示例任务A', 
          template_name: '教师信息模板', 
          created_at: '2026-06-17T10:00:00', 
          status: 'completed', 
          total_pages: 120, 
          success_pages: 120 
        },
        { 
          id: 2, 
          task_name: '示例任务B', 
          template_name: '课程信息模板', 
          created_at: '2026-06-17T11:30:00', 
          status: 'running', 
          total_pages: 50, 
          success_pages: 45 
        },
        { 
          id: 3, 
          task_name: '示例任务C', 
          template_name: '科研成果模板', 
          created_at: '2026-06-17T12:15:00', 
          status: 'failed', 
          total_pages: 10, 
          success_pages: 0 
        }
      ]
    },
    
    formatDate(date) {
      if (!date) return ''
      const d = new Date(date)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    },
    
    formatTime(timeStr) {
      if (!timeStr) return '-'
      try {
        const date = new Date(timeStr)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      } catch {
        return timeStr
      }
    },
    
    resetFilters() {
      this.filters = { type: '', status: '', dateRange: [] }
      this.fetchTasks()
    },
    
    getStatusText(status) {
      const map = {
        'pending': '⏳ 等待中',
        'running': '🔄 采集中',
        'paused': '⏸️ 已暂停',
        'stopped': '⏹️ 已停止',
        'completed': '✅ 已完成',
        'success': '✅ 成功',
        'failed': '❌ 失败'
      }
      return map[status] || status
    },
    
    getStatusType(status) {
      const map = {
        'pending': 'warning',
        'running': 'primary',
        'paused': 'info',
        'stopped': 'info',
        'completed': 'success',
        'success': 'success',
        'failed': 'danger'
      }
      return map[status] || 'info'
    },
    
    async viewDetail(task) {
      try {
        const res = await getTaskDetail(task.id)
        if (res.data.code === 200) {
          ElMessageBox.alert(
            `<pre style="max-height:400px;overflow:auto;">${JSON.stringify(res.data.data, null, 2)}</pre>`,
            '任务详情',
            { dangerouslyUseHTMLString: true }
          )
        } else {
          ElMessageBox.alert(JSON.stringify(task, null, 2), '任务详情')
        }
      } catch {
        ElMessageBox.alert(JSON.stringify(task, null, 2), '任务详情')
      }
    },
    
    // ✅ 查看日志 - 从后端获取
    async viewLog(task) {
  try {
    const taskId = task.task_id || task.id
    console.log(`📤 获取任务 ${taskId} 的日志...`)
    
    // ✅ 1. 先尝试获取任务专属日志
    const res = await getTaskLogs(taskId, 200)
    console.log('📥 任务日志响应:', res)
    
    if (res.data && res.data.code === 200) {
      const logs = res.data.data.logs || []
      const message = res.data.data.message || ''
      
      if (logs.length > 0) {
        // ✅ 显示任务专属日志
        const logContent = logs.join('\n')
        
        ElMessageBox.alert(
          `<pre style="max-height:500px;overflow:auto;font-size:12px;white-space:pre-wrap;word-break:break-all;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;line-height:1.6;">${logContent}</pre>`,
          `📋 任务日志 - ${task.task_name || taskId}`,
          { 
            dangerouslyUseHTMLString: true, 
            confirmButtonText: '关闭',
            customClass: 'task-log-dialog'
          }
        )
        return
      } else if (message) {
        // 日志文件不存在，显示提示
        ElMessage.info(message)
      }
    }
    
    // ✅ 2. 如果没有专属日志，从任务字段读取
    if (task.error_message || task.traceback || task.report) {
      let logContent = ''
      if (task.error_message) {
        logContent += `❌ 错误信息：\n${task.error_message}\n\n`
      }
      if (task.traceback) {
        logContent += `📋 错误堆栈：\n${task.traceback}\n\n`
      }
      if (task.report) {
        logContent += `📊 爬虫报告：\n${task.report}`
      }
      
      ElMessageBox.alert(
        `<pre style="max-height:400px;overflow:auto;white-space:pre-wrap;word-break:break-all;">${logContent}</pre>`,
        `任务日志 - ${task.task_name || task.id}`,
        { dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
      )
      return
    }
    
    // ✅ 3. 没有任何日志
    ElMessageBox.alert(
      `<div style="padding:20px;text-align:center;color:#909399;">
        <div style="font-size:48px;margin-bottom:16px;">📭</div>
        <div style="font-size:16px;font-weight:500;">暂无日志</div>
        <div style="font-size:13px;margin-top:8px;">该任务还没有产生日志</div>
      </div>`,
      `📋 任务日志 - ${task.task_name || taskId}`,
      { dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
    )
    
  } catch (error) {
    console.error('❌ 查看日志失败:', error)
    ElMessage.error('查看日志失败：' + (error.message || '请稍后重试'))
  }
},
    
    async rerunTask(task) {
      try {
        await ElMessageBox.confirm(`确认重新执行任务【${task.task_name}】？`, '提示', { type: 'info' })
        if (!task.template_id) {
          ElMessage.warning('任务缺少关联模板，无法重新执行')
          return
        }
        await startTask({
          template_id: task.template_id,
          task_type: task.task_type || 'formal',
          user_prompt: task.user_prompt || '',
          ai_model: task.ai_model || '',
          ai_api_url: task.ai_api_url || '',
          ai_api_key: task.ai_api_key || ''
        })
        ElMessage.success('任务已重新启动')
        this.fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('重新执行失败：', error)
          ElMessage.error('操作失败')
        }
      }
    },
  
    // ✅ 导出任务数据为 HTML 或 Markdown
    async exportTask(task, format) {
  try {
    // 预览任务不允许导出
    if (task.task_type === 'preview') {
      ElMessage.warning('预览任务不支持导出')
      return
    }
    
    // 获取任务ID
    const taskId = task.task_id || task.id
    if (!taskId) {
      ElMessage.error('任务ID缺失')
      return
    }
    
    console.log('📤 导出任务ID:', taskId)
    
    // 获取任务预览数据
    const res = await getTaskPreview(taskId, 1000)
    console.log('📥 预览数据响应:', res)
    
    // 检查响应
    if (!res || !res.data) {
      ElMessage.error('获取任务数据失败：响应为空')
      return
    }
    
    if (res.data.code !== 200) {
      ElMessage.error(res.data.msg || '获取任务数据失败')
      return
    }
    
    // 提取数据列表
    let dataList = []
    if (res.data.data && res.data.data.preview) {
      dataList = res.data.data.preview
    } else if (Array.isArray(res.data.data)) {
      dataList = res.data.data
    } else {
      dataList = []
    }
    
    console.log('📊 数据条数:', dataList.length)
    
    if (!dataList || dataList.length === 0) {
      ElMessage.warning('该任务没有可导出的数据')
      return
    }
    
    // 生成文件内容
    let content = ''
    let mimeType = ''
    let fileExtension = ''
    
    if (format === 'html') {
      content = this.generateHTML(task, dataList)
      mimeType = 'text/html'
      fileExtension = 'html'
    } else if (format === 'markdown') {
      content = this.generateMarkdown(task, dataList)
      mimeType = 'text/markdown'
      fileExtension = 'md'
    } else {
      ElMessage.error('不支持的格式')
      return
    }
    
    // 下载文件
    const blob = new Blob(['\ufeff' + content], { type: mimeType + ';charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `task_${taskId}_${new Date().toISOString().slice(0,10)}.${fileExtension}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success('导出成功')
    
  } catch (error) {
    console.error('❌ 导出失败:', error)
    ElMessage.error('导出失败：' + (error.response?.data?.msg || error.message || '请稍后重试'))
  }
},
    // ✅ 生成 HTML 文件
    generateHTML(taskInfo, dataList) {
      const columns = dataList.length > 0 ? Object.keys(dataList[0]) : []
      
      let tableHTML = ''
      if (columns.length > 0) {
        const headerHTML = '<tr>' + columns.map(col => `<th>${col}</th>`).join('') + '</tr>'
        const bodyHTML = dataList.map(row => {
          return '<tr>' + columns.map(col => {
            const value = row[col] ?? ''
            const displayValue = typeof value === 'object' ? JSON.stringify(value) : value
            return `<td>${displayValue}</td>`
          }).join('') + '</tr>'
        }).join('')
        tableHTML = `<table border="1" cellspacing="0" cellpadding="5" style="border-collapse:collapse;width:100%;">
          <thead style="background-color:#f2f2f2;">${headerHTML}</thead>
          <tbody>${bodyHTML}</tbody>
        </table>`
      } else {
        tableHTML = `<pre>${JSON.stringify(dataList, null, 2)}</pre>`
      }

      return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>任务导出 - ${taskInfo.task_name || '未命名任务'}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 30px; background: #f5f7fa; }
    .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
    h1 { color: #1a1a2e; border-bottom: 3px solid #409EFF; padding-bottom: 12px; }
    .meta { background: #f0f4f8; padding: 16px 20px; border-radius: 8px; margin: 16px 0 24px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
    .meta-item { font-size: 14px; }
    .meta-item strong { color: #333; margin-right: 8px; }
    table { margin-top: 16px; }
    th, td { padding: 10px 14px; text-align: left; }
    th { font-weight: 600; color: #333; }
    tr:nth-child(even) { background-color: #fafafa; }
    tr:hover { background-color: #e8f0fe; }
    .data-count { color: #409EFF; font-weight: 600; }
    .footer { margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; color: #999; font-size: 13px; text-align: center; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📊 任务：${taskInfo.task_name || '未命名任务'}</h1>
    <div class="meta">
      <div class="meta-item"><strong>模板来源：</strong>${taskInfo.template_name || '无模板'}</div>
      <div class="meta-item"><strong>执行时间：</strong>${this.formatTime(taskInfo.created_at) || '-'}</div>
      <div class="meta-item"><strong>状态：</strong>${this.getStatusText(taskInfo.status)}</div>
      <div class="meta-item"><strong>数据条数：</strong><span class="data-count">${dataList.length}</span></div>
    </div>
    <hr>
    ${tableHTML}
    <div class="footer">导出时间：${new Date().toLocaleString('zh-CN')}</div>
  </div>
</body>
</html>`
    },

    // ✅ 生成 Markdown 文件
    generateMarkdown(taskInfo, dataList) {
      const columns = dataList.length > 0 ? Object.keys(dataList[0]) : []
      
      let md = `# 📊 任务：${taskInfo.task_name || '未命名任务'}\n\n`
      md += `- **模板来源**：${taskInfo.template_name || '无模板'}\n`
      md += `- **执行时间**：${this.formatTime(taskInfo.created_at) || '-'}\n`
      md += `- **状态**：${this.getStatusText(taskInfo.status)}\n`
      md += `- **数据条数**：${dataList.length}\n\n`

      if (columns.length > 0) {
        md += '| ' + columns.join(' | ') + ' |\n'
        md += '| ' + columns.map(() => '---').join(' | ') + ' |\n'
        dataList.forEach(row => {
          md += '| ' + columns.map(col => {
            const value = row[col] ?? ''
            return typeof value === 'object' ? JSON.stringify(value) : value
          }).join(' | ') + ' |\n'
        })
      } else {
        md += '```json\n' + JSON.stringify(dataList, null, 2) + '\n```\n'
      }
      
      md += `\n---\n*导出时间：${new Date().toLocaleString('zh-CN')}*\n`
      return md
    }
  }
}
</script>

<style scoped>
.task-list-page {
  padding: 20px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;
}
.search-card {
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
  padding: 20px;
  background-color: #fff;
  width: 100%;
  box-sizing: border-box;
}
.filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.task-table {
  border: 1px solid #eee;
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  background-color: #fff;
  width: 100%;
  box-sizing: border-box;
}
.task-table th {
  background-color: #fafafa;
  font-weight: 600;
  color: #333;
}
.task-table td {
  background-color: #fff;
  word-break: break-word;
}
.task-table .el-table__row:hover {
  background-color: #f5f7fa;
}
.op-buttons {
  display: flex;
  gap: 6px;
  align-items: center;
}
.op-buttons .el-button {
  margin: 0;
}
.short-date-picker {
  width: 120px !important;
  margin-right: 10px;
}
</style>