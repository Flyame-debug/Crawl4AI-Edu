<template>
  <div class="task-detail-page">
    <!-- 返回按钮 -->
    <div class="page-header">
      <el-button @click="goBack" type="text">
        <el-icon><ArrowLeft /></el-icon> 返回任务列表
      </el-button>
      <h2>📋 任务详情</h2>
    </div>

    <!-- 任务基本信息 -->
    <el-card class="info-card" shadow="hover">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="info-item">
            <span class="label">任务名称</span>
            <span class="value">{{ taskInfo.task_name || '未命名' }}</span>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="info-item">
            <span class="label">状态</span>
            <el-tag :type="statusType">{{ statusText }}</el-tag>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="info-item">
            <span class="label">类型</span>
            <el-tag v-if="taskInfo.task_type === 'preview'" size="small" type="warning">预览</el-tag>
            <el-tag v-else size="small" type="success">正式</el-tag>
          </div>
        </el-col>
        <el-col :span="5">
          <div class="info-item">
            <span class="label">创建时间</span>
            <span class="value">{{ formatTime(taskInfo.created_at) }}</span>
          </div>
        </el-col>
        <el-col :span="5">
          <div class="info-item">
            <span class="label">数据条数</span>
            <span class="value">{{ taskInfo.success_pages || 0 }} / {{ taskInfo.total_pages || 0 }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据对比组件 -->
    <DataCompare
      v-if="taskId"
      :task-id="taskId"
      :task-name="taskInfo.task_name"
      :task-time="formatTime(taskInfo.created_at)"
      :task-status="taskInfo.status"
    />

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container" v-loading="loading">
      <span>加载中...</span>
    </div>
  </div>
</template>

<script>
import { ArrowLeft } from '@element-plus/icons-vue'
import { getTaskDetail } from '@/api/tasks'
import DataCompare from '@/components/DataCompare.vue'

export default {
  name: 'TaskDetail',
  components: { ArrowLeft, DataCompare },
  data() {
    return {
      taskId: null,
      taskInfo: {},
      loading: false
    }
  },
  computed: {
    statusText() {
      const map = {
        'pending': '⏳ 等待中',
        'running': '🔄 采集中',
        'paused': '⏸️ 已暂停',
        'stopped': '⏹️ 已停止',
        'completed': '✅ 已完成',
        'success': '✅ 成功',
        'failed': '❌ 失败'
      }
      return map[this.taskInfo.status] || this.taskInfo.status
    },
    statusType() {
      const map = {
        'pending': 'warning',
        'running': 'primary',
        'paused': 'info',
        'stopped': 'info',
        'completed': 'success',
        'success': 'success',
        'failed': 'danger'
      }
      return map[this.taskInfo.status] || 'info'
    }
  },
  mounted() {
    this.taskId = this.$route.params.id
    if (this.taskId) {
      this.fetchTaskDetail()
    }
  },
  methods: {
    async fetchTaskDetail() {
      this.loading = true
      try {
        const res = await getTaskDetail(this.taskId)
        if (res.data.code === 200) {
          this.taskInfo = res.data.data || {}
        }
      } catch (error) {
        console.error('获取任务详情失败:', error)
        this.$message.error('获取任务详情失败')
      } finally {
        this.loading = false
      }
    },
    goBack() {
      this.$router.push('/tasks')
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
    }
  }
}
</script>

<style scoped>
.task-detail-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.info-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 13px;
  color: #909399;
}

.info-item .value {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
</style>