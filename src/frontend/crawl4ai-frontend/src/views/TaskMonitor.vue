<template>
  <div class="task-monitor-page">
    <h2>任务监控</h2>

    <el-table :data="tasks" border style="width: 100%" empty-text="暂无任务" v-loading="loading">
      <!-- 任务名 -->
      <el-table-column prop="task_name" label="任务名" width="200" />

      <!-- 采集状态 -->
      <el-table-column prop="status" label="采集状态" width="200">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
          <el-dropdown v-if="scope.row.status === 'completed'" trigger="click">
            <span class="el-dropdown-link">
              <el-icon style="vertical-align: middle; margin-left: 6px;">
                <MoreFilled />
              </el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="previewTask(scope.row)">预览</el-dropdown-item>
                <el-dropdown-item @click="downloadTask(scope.row, 'csv')">下载CSV</el-dropdown-item>
                <el-dropdown-item @click="downloadTask(scope.row, 'json')">下载JSON</el-dropdown-item>
                <el-dropdown-item @click="viewDetail(scope.row)">详情</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>

      <!-- 采集用时 -->
      <el-table-column prop="duration" label="采集用时" width="150" />

      <!-- 进度 -->
      <el-table-column label="进度" width="200">
        <template #default="scope">
          <el-progress :percentage="scope.row.progress_percent || 0"></el-progress>
          <small>{{ scope.row.progress || '' }}</small>
        </template>
      </el-table-column>

      <!-- 任务操作 -->
      <el-table-column label="任务操作" min-width="160">
        <template #default="scope">
          <el-button
            v-if="scope.row.status === 'running'"
            type="warning"
            size="small"
            @click="pauseTask(scope.row)"
          >
            暂停
          </el-button>
          <el-button
            v-else-if="scope.row.status === 'paused'"
            type="primary"
            size="small"
            @click="continueTask(scope.row)"
          >
            继续
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click="deleteTask(scope.row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 数据预览弹窗 -->
    <el-dialog v-model="snapshotVisible" title="采集数据预览" width="80%">
      <div class="filters">
        <el-select v-model="filters.category" placeholder="选择分类" style="width: 150px; margin-right: 10px;">
          <el-option label="师资" value="师资" />
          <el-option label="课程" value="课程" />
          <el-option label="科研" value="科研" />
          <el-option label="其他" value="其他" />
        </el-select>
        <el-input v-model="filters.search" placeholder="搜索关键词" style="width: 200px; margin-right: 10px;" />
        <el-button type="primary" @click="fetchPreviewData">查询</el-button>
      </div>

      <el-table :data="previewPages" border style="width: 100%" empty-text="暂无数据">
        <el-table-column prop="url" label="页面URL" width="300" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="created_at" label="采集时间" width="180" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script>
import { MoreFilled } from '@element-plus/icons-vue'
import { getTasks, getTaskPreview, pauseTask, stopTask, deleteTask, downloadTaskResult } from '@/api/tasks'

export default {
  name: 'TaskMonitor',
  components: { MoreFilled },
  data() {
    return {
      tasks: [],
      loading: false,
      pollingTimer: null,
      snapshotVisible: false,
      currentTaskId: null,
      previewPages: [],
      filters: { category: '', search: '' }
    }
  },
  mounted() {
    this.fetchTasks()
    this.startPolling()
  },
  beforeUnmount() {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer)
    }
  },
  methods: {
    getStatusText(status) {
      const map = {
        'pending': '等待中',
        'running': '进行中',
        'paused': '已暂停',
        'stopped': '已停止',
        'completed': '已完成',
        'failed': '失败'
      }
      return map[status] || status
    },
    getStatusType(status) {
      const map = {
        'pending': 'info',
        'running': 'primary',
        'paused': 'warning',
        'stopped': 'info',
        'completed': 'success',
        'failed': 'danger'
      }
      return map[status] || 'info'
    },
    
    async fetchTasks() {
      this.loading = true
      try {
        const res = await getTasks({ page: 1, page_size: 50 })
        console.log('获取任务列表:', res.data)
        if (res.data && res.data.results) {
          this.tasks = res.data.results
        }
      } catch (error) {
        console.error('获取任务列表失败:', error)
        this.$message.error('获取任务列表失败')
      } finally {
        this.loading = false
      }
    },
    
    startPolling() {
      this.pollingTimer = setInterval(() => {
        this.fetchTasks()
      }, 5000)
    },
    
    async pauseTask(task) {
      try {
        const res = await pauseTask(task.task_id)
        this.$message.success(`任务【${task.task_name}】已暂停`)
        this.fetchTasks()
      } catch (error) {
        this.$message.error('暂停失败')
      }
    },
    
    async continueTask(task) {
      this.$message.info('继续功能需要重新启动任务')
    },
    
    async deleteTask(task) {
      try {
        const res = await deleteTask(task.task_id)
        this.$message.success(`任务【${task.task_name}】已删除`)
        this.fetchTasks()
      } catch (error) {
        this.$message.error('删除失败')
      }
    },
    
    viewDetail(task) {
      this.$alert(
        `任务名称: ${task.task_name}\n状态: ${task.status}\n进度: ${task.progress || '暂无'}\n用时: ${task.duration}\n错误: ${task.error_message || '无'}`,
        '任务详情',
        { confirmButtonText: '确定' }
      )
    },
    
    async previewTask(task) {
      this.currentTaskId = task.task_id
      this.snapshotVisible = true
      await this.fetchPreviewData()
    },
    
    async fetchPreviewData() {
      if (!this.currentTaskId) return
      try {
        const res = await getTaskPreview(this.currentTaskId, 20)
        if (res.data && res.data.preview) {
          this.previewPages = res.data.preview
        }
      } catch (error) {
        console.error('获取预览数据失败:', error)
        this.$message.error('获取预览数据失败')
      }
    },
    
    async downloadTask(task, format = 'csv') {
      try {
        const res = await downloadTaskResult(task.task_id, format)
        const blob = new Blob([res.data], { type: res.headers['content-type'] })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `task_${task.task_id}_result.${format}`
        link.click()
        window.URL.revokeObjectURL(url)
        this.$message.success(`任务【${task.task_name}】结果已下载`)
      } catch (e) {
        console.error(e)
        this.$message.error(`下载任务【${task.task_name}】失败，请稍后重试`)
      }
    }
  }
}
</script>

<style scoped>
.task-monitor-page {
  padding: 20px;
}
.el-dropdown-link {
  cursor: pointer;
}
.el-table {
  margin-top: 20px;
}
.filters {
  margin-bottom: 20px;
}
</style>