<template>
  <div class="task-list-page">
    <!-- 搜索卡片 -->
    <el-card class="search-card" shadow="hover">
      <div class="filters">
        <div class="filter-row">
          <el-select v-model="filters.type" placeholder="任务类型" style="width: 160px; margin-right: 10px;">
            <el-option label="正式采集" value="formal" />
            <el-option label="预览采集" value="preview" />
          </el-select>
          <el-select v-model="filters.product" placeholder="产品" style="width: 160px; margin-right: 10px;">
            <el-option label="教师信息" value="teacher" />
            <el-option label="课程信息" value="course" />
            <el-option label="科研成果" value="research" />
          </el-select>
          <el-select v-model="filters.tool" placeholder="工具" style="width: 160px; margin-right: 10px;">
            <el-option label="爬虫引擎A" value="engineA" />
            <el-option label="爬虫引擎B" value="engineB" />
          </el-select>
        </div>
        <div class="filter-row">
          <el-select v-model="filters.status" placeholder="状态" style="width: 160px; margin-right: 10px;">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="采集中" value="running" />
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
      <el-table-column prop="task_name" label="任务名称" width="120" />
      <el-table-column prop="template_source" label="模板来源" width="120" />
      <el-table-column prop="executed_at" label="执行时间" width="150" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="data_count" label="数据条数" width="90" />
      <el-table-column label="操作" width="260">
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
                  <el-dropdown-item @click="exportTask(scope.row, 'json')">导出JSON</el-dropdown-item>
                  <el-dropdown-item @click="exportTask(scope.row, 'csv')">导出CSV</el-dropdown-item>
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
import { getTasks, getTaskDetail, startTask, downloadTaskResult } from '@/api/tasks'

export default {
  name: 'TaskMonitor',
  components: { ArrowDown },
  data() {
    return {
      tasks: [],
      loading: false,
      filters: {
        type: '',
        product: '',
        tool: '',
        status: '',
        dateRange: []
      }
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
        if (this.filters.product) params.category = this.filters.product
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.dateRange && this.filters.dateRange.length === 2) {
          params.start_date = this.formatDate(this.filters.dateRange[0])
          params.end_date = this.formatDate(this.filters.dateRange[1])
        }
        const res = await getTasks(params)
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
        { id: 1, task_name: '示例任务A', template_source: '教师信息', executed_at: '2026-06-17 10:00', status: 'success', data_count: 120 },
        { id: 2, task_name: '示例任务B', template_source: '课程信息', executed_at: '2026-06-17 11:30', status: 'running', data_count: 45 },
        { id: 3, task_name: '示例任务C', template_source: '科研成果', executed_at: '2026-06-17 12:15', status: 'failed', data_count: 0 }
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
    resetFilters() {
      this.filters = { type: '', product: '', tool: '', status: '', dateRange: [] }
      this.fetchTasks()
    },
    getStatusText(status) {
      const map = { running: '采集中', success: '成功', failed: '失败' }
      return map[status] || status
    },
    getStatusType(status) {
      const map = { running: 'primary', success: 'success', failed: 'danger' }
      return map[status] || 'info'
    },
    async viewDetail(task) {
      try {
        const res = await getTaskDetail(task.id)
        if (res.data.code === 200) {
          ElMessageBox.alert(JSON.stringify(res.data.data, null, 2), '任务详情')
        } else {
          ElMessageBox.alert(JSON.stringify(task, null, 2), '任务详情（本地数据）')
        }
      } catch {
        ElMessageBox.alert(JSON.stringify(task, null, 2), '任务详情')
      }
    },
    viewLog(task) {
      ElMessageBox.alert(task.log || '暂无日志信息', '任务日志')
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
    async exportTask(task, format) {
      try {
        const res = await downloadTaskResult(task.id, format)
        const blob = new Blob([res.data], { type: format === 'json' ? 'application/json' : 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `task_${task.id}.${format}`
        a.click()
        URL.revokeObjectURL(url)
        ElMessage.success('下载成功')
      } catch (error) {
        console.error('导出失败：', error)
        ElMessage.error('导出失败')
      }
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
  table-layout: fixed;
  margin-top: 0;
  margin-bottom: 20px;
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
</style>

<style>
.short-date-picker {
  width: 120px !important;
  margin-right: 10px;
}
.task-table .el-table__cell {
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}
</style>