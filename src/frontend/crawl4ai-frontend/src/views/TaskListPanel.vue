<template>
  <div class="tasklist-panel" v-loading="loading">
    <!-- 搜索区 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="请输入任务名称搜索"
        clearable
        class="search-input"
      />
      <el-button type="primary" @click="fetchTasks">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <!-- 横向滚动容器 -->
    <div class="table-wrapper">
      <el-table
        :data="filteredTasks"
        border
        stripe
        size="default"
        class="wide-table"
      >
        <el-table-column prop="task_name" label="任务名称" min-width="100" show-overflow-tooltip>
          <template #default="scope">
            <span>
              <el-tag v-if="scope.row.task_type === 'preview'" size="small" type="warning" style="margin-right: 4px;">预览</el-tag>
              {{ scope.row.task_name || scope.row.task_id || '未命名任务' }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="80">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="160">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="duration" label="采集时长" width="95" />
        
        <el-table-column label="数据条数" width="90">
          <template #default="scope">
            <span>{{ scope.row.success_pages || 0 }} / {{ scope.row.total_pages || 0 }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <div class="op-buttons">
              <el-button 
                v-if="canStop(scope.row.status)" 
                size="small" 
                type="danger" 
                @click="handleStop(scope.row)"
                :loading="stoppingIds.includes(scope.row.task_id)"
              >
                ⏹️ 停止
              </el-button>
              
              <el-button size="small" type="primary" @click="viewTask(scope.row)">查看</el-button>
              
              <el-dropdown 
                v-if="scope.row.status === 'completed' || scope.row.status === 'success'"
                @command="(format) => handleExport(scope.row, format)"
              >
                <el-button size="small" type="success">
                  导出 <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="json">📊 JSON</el-dropdown-item>
                    <el-dropdown-item command="csv">📊 CSV</el-dropdown-item>
                    <el-dropdown-item command="xlsx">📊 Excel</el-dropdown-item>
                    <el-dropdown-item divided command="md">📄 Markdown</el-dropdown-item>
                    <el-dropdown-item command="txt">📄 TXT</el-dropdown-item>
                    <el-dropdown-item command="html">📄 HTML</el-dropdown-item>
                    <el-dropdown-item divided command="xml">📦 XML</el-dropdown-item>
                    <el-dropdown-item command="sql">📦 SQL</el-dropdown-item>
                    <el-dropdown-item command="rss">📡 RSS订阅</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              
              <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { getTasks, deleteTask, stopTask } from '@/api/tasks'
import { ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'TaskListPanel',
  components: { ArrowDown },
  props: {
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      searchKeyword: '',
      tasks: [],
      loading: false,
      stoppingIds: []
    }
  },
  computed: {
    filteredTasks() {
      if (!this.searchKeyword) return this.tasks
      const keyword = this.searchKeyword.toLowerCase()
      return this.tasks.filter(task =>
        task.task_name && task.task_name.toLowerCase().includes(keyword)
      )
    }
  },
  watch: {
    template: {
      handler() {
        this.fetchTasks()
      },
      deep: true,
      immediate: true
    }
  },
  mounted() {
    this.fetchTasks()
  },
  methods: {
    canStop(status) {
      return ['pending', 'running', 'paused'].includes(status)
    },
    
    async handleStop(row) {
      try {
        await this.$confirm(
          `确认停止任务【${row.task_name || row.task_id}】？\n已采集的数据会保留。`,
          '停止确认', { type: 'warning' }
        )
        this.stoppingIds.push(row.task_id)
        const res = await stopTask(row.task_id)
        if (res.data.code === 200) {
          this.$message.success('任务已停止')
          await this.fetchTasks()
        } else {
          this.$message.error(res.data.msg || '停止失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('停止任务失败：', error)
          this.$message.error('停止失败：' + (error.message || '未知错误'))
        }
      } finally {
        this.stoppingIds = this.stoppingIds.filter(id => id !== row.task_id)
      }
    },
    
    async handleExport(row, format) {
      try {
        const loading = this.$loading({
          text: `正在导出 ${format.toUpperCase()} 格式...`,
          spinner: 'el-icon-loading'
        })
        const response = await fetch(
          `/api/tasks/${row.task_id}/export/?format=${format}`,
          {
            headers: {
              'Authorization': 'Bearer ' + (localStorage.getItem('token') || '')
            }
          }
        )
        loading.close()
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || errorData.msg || '导出失败')
        }
        const contentDisposition = response.headers.get('Content-Disposition')
        let filename = `task_${row.task_id}.${format}`
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?([^"]+)"?/)
          if (match) filename = match[1]
        }
        const blob = await response.blob()
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(link.href)
        this.$message.success(`导出成功：${filename}`)
      } catch (error) {
        console.error('导出失败：', error)
        this.$message.error('导出失败：' + error.message)
      }
    },
    
    async fetchTasks() {
      if (!this.template || !this.template.id) {
        console.warn('⚠️ 没有模板ID，无法获取任务列表')
        this.tasks = []
        return
      }
      this.loading = true
      try {
        const params = {
          template_id: this.template.id,
          include_preview: 'true',
          page: 1,
          page_size: 50
        }
        const res = await getTasks(params)
        if (res.data.code === 200) {
          this.tasks = res.data.data.results || []
        } else {
          this.$message.error(res.data.msg || '获取任务列表失败')
        }
      } catch (error) {
        console.error('获取任务列表失败：', error)
        this.$message.error('获取任务列表失败')
        this.tasks = []
      } finally {
        this.loading = false
      }
    },
    
    resetSearch() {
      this.searchKeyword = ''
    },
    
    viewTask(row) {
      const taskId = row.task_id || row.id
      if (taskId) {
        this.$router.push(`/task/${taskId}`)
      } else {
        this.$message.error('任务ID不存在')
      }
    },
    
    async handleDelete(row) {
      try {
        await this.$confirm(`确认删除任务【${row.task_name || row.task_id}】？`, '删除确认', { type: 'warning' })
        await deleteTask(row.task_id)
        this.$message.success('删除成功')
        this.fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除任务失败：', error)
          this.$message.error('删除失败')
        }
      }
    },
    
    getStatusText(status) {
      const map = {
        pending: '⏳ 等待中',
        running: '🔄 采集中',
        paused: '⏸️ 已暂停',
        stopped: '⏹️ 已停止',
        completed: '✅ 已完成',
        success: '✅ 成功',
        failed: '❌ 失败'
      }
      return map[status] || status
    },
    
    getStatusType(status) {
      const map = {
        pending: 'warning',
        running: 'primary',
        paused: 'info',
        stopped: 'info',
        completed: 'success',
        success: 'success',
        failed: 'danger'
      }
      return map[status] || 'info'
    },
    
    formatTime(dateStr) {
      if (!dateStr) return '-'
      try {
        const date = new Date(dateStr)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      } catch {
        return dateStr
      }
    }
  }
}
</script>

<style scoped>
.tasklist-panel {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  margin: 0 auto;
  padding: 20px 0;
  box-sizing: border-box;
  overflow: hidden;
}

.search-bar {
  display: flex;
  justify-content: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}
.search-input { width: 260px; }

/* 表格容器，内容过宽时出现横向滚动条 */
.table-wrapper {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
}

/* 强制表格宽度等于容器，不再用 max-content */
.wide-table {
  width: 100% !important;
  max-width: 100% !important;
  table-layout: fixed !important;
  font-size: 14px;
  border-radius: 8px;
  overflow: hidden;
}

/* 表头样式 */
.wide-table ::v-deep(.el-table__header-wrapper) { background-color: #f9f9f9; }
.wide-table ::v-deep(th) {
  background-color: #f9f9f9;
  color: #606266;
  font-weight: 600;
  font-size: 13px;
  padding: 10px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 表格行 */
.wide-table ::v-deep(td) {
  font-size: 13px;
  padding: 8px 6px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wide-table ::v-deep(.el-table__body tr:hover > td) {
  background-color: #f0f9ff !important;
}

/* 操作按钮不换行 */
.op-buttons {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
  align-items: center;
}
</style>