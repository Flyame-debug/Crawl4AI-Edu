<template>
  <div class="task-list-page">
    <!-- 搜索卡片 -->
    <el-card class="search-card" shadow="hover">
      <div class="filters">
        <div class="filter-row">
          <el-input
            v-model="searchKeyword"
            placeholder="请输入任务名称搜索"
            clearable
            class="search-input"
            @keyup.enter="fetchTasks"
          />
          <el-button type="primary" @click="fetchTasks">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </div>
        
        <!-- ✅ 批量操作栏（与 TaskMonitor 风格一致） -->
        <div class="batch-actions" v-if="hasRunningTasks">
          <el-divider direction="vertical" />
          <span class="batch-tip">批量操作：</span>
          <el-button
            type="danger"
            size="small"
            :disabled="selectedTasks.length === 0"
            :loading="batchStopping"
            @click="handleBatchStop"
          >
            ⏹️ 批量停止 ({{ selectedTasks.length }})
          </el-button>
          <el-button
            type="warning"
            size="small"
            :loading="allStopping"
            @click="handleStopAll"
          >
            ⏹️ 全部停止
          </el-button>
          <span class="hint-text">共 {{ runningTasksCount }} 个运行/等待中任务</span>
        </div>
      </div>
    </el-card>

    <!-- 任务列表表格 -->
    <el-table
      :data="filteredTasks"
      border
      stripe
      size="default"
      class="task-table"
      style="table-layout:auto;"
      v-loading="loading"
      @selection-change="handleSelectionChange"
      ref="tableRef"
    >
      <!-- ✅ 多选列（与 TaskMonitor 一致） -->
      <el-table-column type="selection" width="45" :selectable="checkSelectable" />

      <el-table-column prop="task_name" label="任务名称" min-width="150">
        <template #default="scope">
          <span>
            <el-tag v-if="scope.row.task_type === 'preview'" size="small" type="warning" style="margin-right: 6px;">预览</el-tag>
            {{ scope.row.task_name || scope.row.task_id || '未命名任务' }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="创建时间" width="180">
        <template #default="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column prop="duration" label="采集时长" width="100" />

      <el-table-column label="数据条数" width="120">
        <template #default="scope">
          <span>{{ scope.row.success_pages || 0 }} / {{ scope.row.total_pages || 0 }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="320" fixed="right">
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
              style="margin-left: 4px;"
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
      stoppingIds: [],
      // ✅ 批量操作相关
      selectedTasks: [],
      batchStopping: false,
      allStopping: false,
    }
  },
  computed: {
    filteredTasks() {
      if (!this.searchKeyword) return this.tasks
      const keyword = this.searchKeyword.toLowerCase()
      return this.tasks.filter(task =>
        task.task_name && task.task_name.toLowerCase().includes(keyword)
      )
    },
    // ✅ 可停止的任务列表
    runningTasks() {
      return this.tasks.filter(task => this.canStop(task.status))
    },
    // ✅ 是否有运行中的任务
    hasRunningTasks() {
      return this.runningTasks.length > 0
    },
    // ✅ 运行中的任务数量
    runningTasksCount() {
      return this.runningTasks.length
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
    // ✅ 判断是否可以停止
    canStop(status) {
      return ['pending', 'running', 'paused'].includes(status)
    },
    
    // ✅ 判断任务是否可选（只有可停止的任务才能被勾选）
    checkSelectable(row) {
      return this.canStop(row.status)
    },
    
    // ✅ 表格选中变化
    handleSelectionChange(selection) {
      this.selectedTasks = selection
    },
    
    // ✅ 执行停止（抽取公共逻辑）
    async doStopTask(row, options = { silent: false }) {
      try {
        const res = await stopTask(row.task_id)
        if (res.data.code === 200) {
          if (!options.silent) {
            this.$message.success(`任务「${row.task_name || row.task_id}」已停止`)
          }
          return true
        } else {
          if (!options.silent) {
            this.$message.error(res.data.msg || '停止失败')
          }
          return false
        }
      } catch (error) {
        if (!options.silent) {
          console.error('停止任务失败：', error)
          this.$message.error(`停止「${row.task_name || row.task_id}」失败：${error.message}`)
        }
        throw error
      }
    },
    
    // ✅ 单个停止
    async handleStop(row) {
      try {
        await this.$confirm(
          `确认停止任务【${row.task_name || row.task_id}】？\n已采集的数据会保留。`,
          '停止确认',
          { type: 'warning' }
        )
        
        this.stoppingIds.push(row.task_id)
        await this.doStopTask(row)
        await this.fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('停止任务失败：', error)
          this.$message.error('停止失败：' + (error.message || '未知错误'))
        }
      } finally {
        this.stoppingIds = this.stoppingIds.filter(id => id !== row.task_id)
      }
    },
    
    // ✅ 批量停止
    async handleBatchStop() {
      if (this.selectedTasks.length === 0) {
        this.$message.warning('请先选择要停止的任务')
        return
      }
      
      try {
        await this.$confirm(
          `确认停止选中的 ${this.selectedTasks.length} 个任务？\n已采集的数据会保留。`,
          '批量停止确认',
          { type: 'warning' }
        )
        
        this.batchStopping = true
        const tasks = [...this.selectedTasks]
        const concurrency = 5
        let successCount = 0
        let failCount = 0
        
        for (let i = 0; i < tasks.length; i += concurrency) {
          const batch = tasks.slice(i, i + concurrency)
          const results = await Promise.allSettled(
            batch.map(task => this.doStopTask(task, { silent: true }))
          )
          results.forEach(result => {
            if (result.status === 'fulfilled' && result.value) {
              successCount++
            } else {
              failCount++
            }
          })
        }
        
        this.selectedTasks = []
        if (this.$refs.tableRef) {
          this.$refs.tableRef.clearSelection()
        }
        
        await this.fetchTasks()
        
        if (failCount === 0) {
          this.$message.success(`✅ 批量停止完成：${successCount} 个任务已停止`)
        } else {
          this.$message.warning(`⚠️ 批量停止完成：${successCount} 个成功，${failCount} 个失败`)
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量停止失败：', error)
          this.$message.error('批量停止失败')
        }
      } finally {
        this.batchStopping = false
      }
    },
    
    // ✅ 全部停止
    async handleStopAll() {
      const runningTasks = this.runningTasks
      if (runningTasks.length === 0) {
        this.$message.warning('没有正在运行或等待中的任务')
        return
      }
      
      try {
        await this.$confirm(
          `确认停止全部 ${runningTasks.length} 个运行/等待中的任务？\n已采集的数据会保留。`,
          '全部停止确认',
          { type: 'warning', confirmButtonText: '全部停止' }
        )
        
        this.allStopping = true
        const tasks = [...runningTasks]
        const concurrency = 5
        let successCount = 0
        let failCount = 0
        
        for (let i = 0; i < tasks.length; i += concurrency) {
          const batch = tasks.slice(i, i + concurrency)
          const results = await Promise.allSettled(
            batch.map(task => this.doStopTask(task, { silent: true }))
          )
          results.forEach(result => {
            if (result.status === 'fulfilled' && result.value) {
              successCount++
            } else {
              failCount++
            }
          })
        }
        
        this.selectedTasks = []
        if (this.$refs.tableRef) {
          this.$refs.tableRef.clearSelection()
        }
        
        await this.fetchTasks()
        
        if (failCount === 0) {
          this.$message.success(`✅ 全部停止完成：${successCount} 个任务已停止`)
        } else {
          this.$message.warning(`⚠️ 全部停止完成：${successCount} 个成功，${failCount} 个失败`)
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('全部停止失败：', error)
          this.$message.error('全部停止失败')
        }
      } finally {
        this.allStopping = false
      }
    },
    
    // ✅ 导出任务结果
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
    
    // ✅ 获取任务列表
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
        console.log(`📥 模板 ${this.template.id} 的任务列表:`, res)
        
        if (res.data.code === 200) {
          this.tasks = res.data.data.results || []
          console.log(`✅ 加载了 ${this.tasks.length} 个任务`)
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
      // ✅ 清空选中
      this.selectedTasks = []
      if (this.$refs.tableRef) {
        this.$refs.tableRef.clearSelection()
      }
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
        // ✅ 清空选中
        this.selectedTasks = []
        if (this.$refs.tableRef) {
          this.$refs.tableRef.clearSelection()
        }
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
/* ✅ 统一风格，与 TaskMonitor 一致 */
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

.search-input {
  width: 280px;
}

/* ✅ 批量操作栏样式 */
.batch-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 0 4px 0;
}

.batch-tip {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
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

/* ✅ 操作按钮容器 */
.op-buttons {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.op-buttons .el-button {
  margin: 0;
}
</style>