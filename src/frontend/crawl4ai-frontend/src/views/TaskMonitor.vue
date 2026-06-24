<template>
  <div class="task-list-page">
    <!-- 搜索卡片 -->
    <el-card class="search-card" shadow="hover">
      <div class="filters">
        <div class="filter-row">
          <el-checkbox v-model="filters.includePreview" @change="fetchTasks">
            显示预览任务
          </el-checkbox>
          <el-select v-model="filters.type" placeholder="任务类型" style="width: 130px; margin-right: 8px;">
            <el-option label="正式采集" value="formal" />
            <el-option label="预览采集" value="preview" />
          </el-select>
          <el-select v-model="filters.status" placeholder="状态" style="width: 130px; margin-right: 8px;">
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
          <el-button type="primary" @click="fetchTasks" style="margin-left: 8px;">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
    </el-card>

    <!-- 任务列表表格（外层加滚动容器） -->
    <div class="table-scroll-wrapper">
      <el-table :data="displayTasks" class="task-table" empty-text="暂无任务" v-loading="loading">
        <!-- 关键修改：min-width 全部改为 width -->
        <el-table-column prop="task_name" label="任务名称" width="120" show-overflow-tooltip>
          <template #default="scope">
            <span>
              <el-tag v-if="scope.row.task_type === 'preview'" size="small" type="warning" style="margin-right: 6px;">预览</el-tag>
              {{ scope.row.task_name || scope.row.task_id || '未命名任务' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="执行时间" width="140" show-overflow-tooltip>
          <template #default="scope">
            <span>{{ formatTime(scope.row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" show-overflow-tooltip>
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_pages" label="数据条数" width="80" show-overflow-tooltip>
          <template #default="scope">
            <span>{{ scope.row.success_pages || 0 }} / {{ scope.row.total_pages || 0 }}</span>
          </template>
        </el-table-column>
        <!-- 操作列 width 代替 min-width -->
        <el-table-column label="操作" width="280">
          <template #default="scope">
            <div class="op-buttons">
              <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
              <el-button size="small" @click="viewLog(scope.row)">日志</el-button>
              <el-button
                size="small"
                type="warning"
                @click="rerunTask(scope.row)"
                :disabled="!scope.row.template_id"
                :title="!scope.row.template_id ? '缺少关联模板，无法重新执行' : ''"
              >
                🔄 重新执行
              </el-button>
              <el-button
                v-if="scope.row.status === 'running' || scope.row.status === 'pending'"
                size="small"
                type="danger"
                @click="stopRunningTask(scope.row)"
                :loading="stoppingIds.includes(scope.row.task_id)"
              >
                停止
              </el-button>
              <el-dropdown @command="(format) => exportTask(scope.row, format)">
                <el-button size="small" type="primary">
                  导出 <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="json">📊 JSON</el-dropdown-item>
                    <el-dropdown-item command="csv">📊 CSV</el-dropdown-item>
                    <el-dropdown-item command="xlsx">📊 Excel</el-dropdown-item>
                    <el-dropdown-item divided command="html">📄 HTML</el-dropdown-item>
                    <el-dropdown-item command="markdown">📄 Markdown</el-dropdown-item>
                    <el-dropdown-item command="txt">📄 TXT</el-dropdown-item>
                    <el-dropdown-item divided command="xml">📦 XML</el-dropdown-item>
                    <el-dropdown-item command="sql">📦 SQL</el-dropdown-item>
                    <el-dropdown-item command="rss">📡 RSS</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 预览结果弹窗（不变） -->
    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="700px"
      :close-on-click-modal="false"
    >
      <div v-if="detailLoading" v-loading="detailLoading" style="min-height: 100px;"></div>
      <div v-else class="markdown-body" v-html="detailHtml"></div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTasks, getTaskDetail, startTask, stopTask, getTaskPreview } from '@/api/tasks'
import { getTaskLogs } from '@/api/logs'
import { marked } from 'marked'
import * as XLSX from 'xlsx'

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
        includePreview: false,
        
      },
      stoppingIds:[],
      detailDialogVisible: false,
      detailLoading: false,
      detailHtml: ''
    }
  },
  computed: {
    displayTasks() {
      if (this.filters.includePreview) return this.tasks
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
        params.page = 1
        params.page_size = 50
        const res = await getTasks(params)
        if (res.data.code === 200) {
          this.tasks = res.data.data.results || res.data.data || []
        } else {
          ElMessage.error(res.data.msg || '获取任务列表失败')
        }
      } catch (error) {
        console.error('获取任务列表失败：', error)
        ElMessage.error('获取任务列表失败，请稍后重试')
        this.tasks = []
      } finally {
        this.loading = false
      }
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
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit'
        })
      } catch { return timeStr }
    },
    
    resetFilters() {
      this.filters = { type: '', status: '', dateRange: [], includePreview: false }
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
    
    // ✅ 停止任务
    async stopRunningTask(task) {
  // ✅ 获取正确的 task_id
  const taskId = task.task_id || task.id
  if (!taskId) {
    ElMessage.error('任务ID不存在')
    return
  }
  
  let message = `确认停止任务【${task.task_name || taskId}】？`
  if (task.task_type === 'preview') {
    message += '\n⚠️ 预览任务停止后，已采集的数据会保留。'
  }
  
  try {
    await this.$confirm(message, '停止确认', { type: 'warning' })
    
    this.stoppingIds.push(taskId)
    const res = await stopTask(taskId)
    
    if (res.data.code === 200) {
      this.$message.success('任务已停止')
      this.fetchTasks()
    } else {
      this.$message.error(res.data.msg || '停止失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止任务失败：', error)
      this.$message.error('停止失败：' + (error.message || '未知错误'))
    }
  } finally {
    this.stoppingIds = this.stoppingIds.filter(id => id !== taskId)
  }
},

    // ✅ 重新执行任务（修复版）
    // TaskMonitor.vue - rerunTask 方法
async rerunTask(task) {
  if (!task.template_id) {
    ElMessage.warning('该任务没有关联模板，无法重新执行')
    return
  }
  
  try {
    await ElMessageBox.confirm('确认重新执行？', '提示', { type: 'info' })
    
    const res = await startTask({
      template_id: task.template_id,  // ✅ 直接传递模板ID
      task_type: task.task_type || 'formal',
      config: {
        max_depth: 2,
        max_concurrent: 5
      }
    })
    
    if (res.data.code === 200) {
      ElMessage.success('任务已重新启动')
      this.fetchTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新执行失败:', error)
      ElMessage.error('重新执行失败')
    }
  }
},

    async viewDetail(task) {
  // ✅ 获取正确的 task_id
  const taskId = task.task_id || task.id
  if (!taskId) {
    ElMessage.error('任务ID不存在')
    return
  }
  
  this.detailLoading = true
  this.detailDialogVisible = true
  try {
    const res = await getTaskDetail(taskId)
    if (res.data.code === 200) {
      const data = res.data.data || {}
      const markdownContent = data.extracted_data || ''
      if (markdownContent && typeof markdownContent === 'string') {
        this.detailHtml = marked(markdownContent)
      } else {
        this.detailHtml = `<pre>${JSON.stringify(data, null, 2)}</pre>`
      }
    } else {
      this.detailHtml = `<pre>${JSON.stringify(task, null, 2)}</pre>`
    }
  } catch (error) {
    console.error('获取任务详情失败:', error)
    this.detailHtml = `<pre>${JSON.stringify(task, null, 2)}</pre>`
  } finally {
    this.detailLoading = false
  }
},
    
    async viewLog(task) {
  try {
    // ✅ 获取正确的 task_id
    const taskId = task.task_id || task.id
    if (!taskId) {
      ElMessage.error('任务ID不存在')
      return
    }
    
    const res = await getTaskLogs(taskId, 200)
    if (res.data && res.data.code === 200) {
      const logs = res.data.data.logs || []
      if (logs.length > 0) {
        const logContent = logs.join('\n')
        ElMessageBox.alert(
          `<pre style="max-height:500px;overflow:auto;font-size:12px;white-space:pre-wrap;word-break:break-all;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;line-height:1.6;">${logContent}</pre>`,
          `📋 任务日志 - ${task.task_name || taskId}`,
          { dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
        )
        return
      }
    }
    ElMessageBox.alert(
      `<div style="padding:20px;text-align:center;color:#909399;">暂无日志</div>`,
      `📋 任务日志 - ${task.task_name || taskId}`,
      { dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
    )
  } catch (error) {
    console.error('查看日志失败:', error)
    ElMessage.error('查看日志失败')
  }
},
  
    // ===== 导出功能 =====
    async exportTask(task, format) {
      try {
        const taskId = task.task_id || task.id
        if (!taskId) {
          ElMessage.error('任务ID缺失')
          return
        }
    
        if (task.task_type === 'preview') {
          ElMessage.warning('预览任务不支持导出')
          return
        }
        
        const res = await getTaskPreview(taskId, 1000)
        if (!res || !res.data || res.data.code !== 200) {
          ElMessage.error('获取任务数据失败')
          return
        }
        let dataList = res.data.data?.preview || res.data.data || []
        if (!Array.isArray(dataList)) dataList = []
        if (dataList.length === 0) {
          ElMessage.warning('该任务没有可导出的数据')
          return
        }

        const taskInfo = {
          name: task.task_name || '未命名',
          template: task.template_name || '',
          time: this.formatTime(task.created_at),
          status: this.getStatusText(task.status)
        }

        let content, mime, ext
        switch (format) {
          case 'json':
            content = JSON.stringify(dataList, null, 2)
            mime = 'application/json'
            ext = 'json'
            break
          case 'csv':
            content = this.generateCSV(dataList)
            mime = 'text/csv'
            ext = 'csv'
            break
          case 'xlsx':
            this.generateExcel(dataList, taskId)
            return
          case 'html':
            content = this.generateHTML(taskInfo, dataList)
            mime = 'text/html'
            ext = 'html'
            break
          case 'markdown':
            content = this.generateMarkdown(taskInfo, dataList)
            mime = 'text/markdown'
            ext = 'md'
            break
          case 'txt':
            content = this.generateTXT(dataList)
            mime = 'text/plain'
            ext = 'txt'
            break
          case 'xml':
            content = this.generateXML(dataList)
            mime = 'application/xml'
            ext = 'xml'
            break
          case 'sql':
            content = this.generateSQL(dataList)
            mime = 'application/sql'
            ext = 'sql'
            break
          case 'rss':
            content = this.generateRSS(dataList)
            mime = 'application/rss+xml'
            ext = 'xml'
            break
          default:
            ElMessage.error('不支持的格式')
            return
        }
        this.downloadBlob(content, mime, `task_${taskId}_${new Date().toISOString().slice(0,10)}.${ext}`)
        ElMessage.success('导出成功')
      } catch (error) {
        console.error('导出失败：', error)
        ElMessage.error('导出失败')
      }
    },

    // ===== 生成函数 =====
    generateCSV(data) {
      const columns = Object.keys(data[0])
      let csv = '\ufeff' + columns.join(',') + '\n'
      data.forEach(row => {
        csv += columns.map(col => {
          let val = row[col] ?? ''
          if (typeof val === 'object') val = JSON.stringify(val)
          val = String(val).replace(/"/g, '""')
          return `"${val}"`
        }).join(',') + '\n'
      })
      return csv
    },

    generateExcel(data, taskId) {
      const ws = XLSX.utils.json_to_sheet(data)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
      XLSX.writeFile(wb, `task_${taskId}_${new Date().toISOString().slice(0,10)}.xlsx`)
    },

    generateTXT(data) {
      return data.map(row => {
        return Object.entries(row).map(([k, v]) => `${k}: ${v}`).join('\n')
      }).join('\n\n---\n\n')
    },

    generateXML(data) {
      let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<records>\n'
      data.forEach(row => {
        xml += '  <record>\n'
        Object.entries(row).forEach(([k, v]) => {
          // ✅ 确保XML特殊字符被转义
          const value = String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          xml += `    <${k}>${value}</${k}>\n`
        })
        xml += '  </record>\n'
      })
      xml += '</records>'
      return xml
    },

    generateSQL(data) {
      const table = 'exported_data'
      const cols = Object.keys(data[0])
      const values = data.map(row => {
        const vals = cols.map(c => {
          const v = row[c] ?? ''
          if (typeof v === 'string') return `'${v.replace(/'/g, "''")}'`
          if (typeof v === 'object') return `'${JSON.stringify(v).replace(/'/g, "''")}'`
          return v
        }).join(', ')
        return `INSERT INTO ${table} (${cols.join(', ')}) VALUES (${vals});`
      }).join('\n')
      return `-- Task export\n${values}\n`
    },

    generateRSS(data) {
      let rss = `<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>\n<title>Task Export</title>\n<description>采集数据</description>\n`
      data.forEach(row => {
        const title = row.title || row.name || row.url || 'Item'
        const description = JSON.stringify(row).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        rss += '  <item>\n'
        rss += `    <title>${title}</title>\n`
        rss += `    <description>${description}</description>\n`
        rss += '  </item>\n'
      })
      rss += '</channel>\n</rss>'
      return rss
    },

    downloadBlob(content, mime, filename) {
      const blob = new Blob(['\ufeff' + content], { type: mime + ';charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    },

    generateHTML(info, data) {
      const columns = data.length > 0 ? Object.keys(data[0]) : []
      let tableHTML = ''
      if (columns.length > 0) {
        const headerHTML = '<tr>' + columns.map(col => `<th>${col}</th>`).join('') + '</tr>'
        const bodyHTML = data.map(row => {
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
        tableHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`
      }
      return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>任务导出 - ${info.name}</title>
  <style>
    body { font-family: sans-serif; margin: 30px; background: #f5f7fa; }
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
    <h1>📊 任务：${info.name}</h1>
    <div class="meta">
      <div class="meta-item"><strong>模板来源：</strong>${info.template || '无模板'}</div>
      <div class="meta-item"><strong>执行时间：</strong>${info.time || '-'}</div>
      <div class="meta-item"><strong>状态：</strong>${info.status}</div>
      <div class="meta-item"><strong>数据条数：</strong><span class="data-count">${data.length}</span></div>
    </div>
    <hr>
    ${tableHTML}
    <div class="footer">导出时间：${new Date().toLocaleString('zh-CN')}</div>
  </div>
</body>
</html>`
    },

    generateMarkdown(info, data) {
      const columns = data.length > 0 ? Object.keys(data[0]) : []
      let md = `# 📊 任务：${info.name}\n\n`
      md += `- **模板来源**：${info.template || '无模板'}\n`
      md += `- **执行时间**：${info.time || '-'}\n`
      md += `- **状态**：${info.status}\n`
      md += `- **数据条数**：${data.length}\n\n`
      if (columns.length > 0) {
        md += '| ' + columns.join(' | ') + ' |\n'
        md += '| ' + columns.map(() => '---').join(' | ') + ' |\n'
        data.forEach(row => {
          md += '| ' + columns.map(col => {
            const value = row[col] ?? ''
            return typeof value === 'object' ? JSON.stringify(value) : value
          }).join(' | ') + ' |\n'
        })
      } else {
        md += '```json\n' + JSON.stringify(data, null, 2) + '\n```\n'
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
  box-sizing: border-box;
  overflow-x: hidden;   /* 关键：阻止页面级横向溢出 */
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
  gap: 8px;
}

/* 表格滚动容器 */
.table-scroll-wrapper {
  width: 100%;
  overflow-x: auto;
  border-radius: 14px;
}

/* 表格宽度策略 */
.task-table {
  border: 1px solid #eee;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  background-color: #fff;
  width: max-content;
  min-width: 100%;
  table-layout: fixed;
  box-sizing: border-box;
  border-radius: 14px;
}
.task-table th {
  background-color: #fafafa;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-table td {
  background-color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-table .el-table__row:hover {
  background-color: #f5f7fa;
}
.op-buttons {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}
.op-buttons .el-button {
  margin: 0;
}
.short-date-picker {
  width: 110px !important;
}
.markdown-body {
  padding: 10px;
  line-height: 1.7;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 1em;
  margin-bottom: 0.5em;
}
.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
.markdown-body :deep(th) {
  background-color: #f2f2f2;
}
</style>