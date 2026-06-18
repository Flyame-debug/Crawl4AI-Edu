<template>
  <div class="tasklist-panel" v-loading="loading">
    <!-- 搜索区 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="请输入任务ID或关键字"
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
        style="table-layout:auto;"
      >
        <el-table-column prop="id" label="任务ID" width="120" />
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
        <el-table-column prop="duration" label="采集时长" width="120" />
        <el-table-column prop="successRate" label="成功率" width="100" />
        <el-table-column prop="fileSize" label="文件大小" width="120" />
        <el-table-column prop="logs" label="执行记录" width="180" />
        <el-table-column label="操作" width="160">
          <template #default="scope">
            <el-button size="small" type="primary" @click="viewTask(scope.row)">查看</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { getTasks, deleteTask } from '@/api/tasks'

export default {
  name: 'TaskListPanel',
  props: {
    // 从父组件（TemplateDetail）传入的模板数据
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      searchKeyword: '',
      tasks: [],
      loading: false
    }
  },
  computed: {
    filteredTasks() {
      if (!this.searchKeyword) return this.tasks
      const keyword = this.searchKeyword.toLowerCase()
      return this.tasks.filter(task =>
        String(task.id).includes(keyword) ||
        (task.task_name && task.task_name.toLowerCase().includes(keyword))
      )
    }
  },
  watch: {
    // 当父组件传入的模板变化时重新加载
    template: {
      handler() {
        this.fetchTasks()
      },
      deep: true
    }
  },
  mounted() {
    this.fetchTasks()
  },
  methods: {
    // 获取任务列表（按模板ID筛选）
    async fetchTasks() {
      this.loading = true
      try {
        const params = {}
        if (this.template && this.template.id) {
          params.template_id = this.template.id
        }
        if (this.searchKeyword) {
          params.search = this.searchKeyword
        }
        const res = await getTasks(params)
        if (res.data.code === 200) {
          this.tasks = res.data.data.results || res.data.data || []
        }
      } catch (error) {
        console.error('获取任务列表失败：', error)
        this.$message.error('获取任务列表失败')
        this.tasks = this.getMockTasks()
      } finally {
        this.loading = false
      }
    },
    // 兜底假数据
    getMockTasks() {
      return [
        { id: 1, task_name: '示例任务A', status: 'success', created_at: '2026-06-15T10:00:00', duration: '12s', successRate: '100%', fileSize: '2MB', logs: '执行成功' },
        { id: 2, task_name: '示例任务B', status: 'failed', created_at: '2026-06-14T09:30:00', duration: '8s', successRate: '0%', fileSize: '0MB', logs: '网络错误' },
        { id: 3, task_name: '示例任务C', status: 'running', created_at: '2026-06-13T14:20:00', duration: '15s', successRate: '95%', fileSize: '3MB', logs: '部分页面超时' }
      ]
    },
    // 重置搜索
    resetSearch() {
      this.searchKeyword = ''
      this.fetchTasks()
    },
    // 查看任务详情
    viewTask(row) {
      this.$router.push(`/task/${row.id}`)
    },
    // 删除任务（真实接口）
    async handleDelete(row) {
      try {
        await this.$confirm(`确认删除任务【${row.id}】？`, '删除确认', { type: 'warning' })
        await deleteTask(row.id)
        this.$message.success('删除成功')
        this.fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除任务失败：', error)
          this.$message.error('删除失败')
        }
      }
    },
    // 状态文本映射
    getStatusText(status) {
      const map = {
        pending: '待处理',
        running: '采集中',
        success: '成功',
        failed: '失败',
        paused: '已暂停',
        stopped: '已停止'
      }
      return map[status] || status
    },
    // 状态颜色映射
    getStatusType(status) {
      const map = {
        pending: 'info',
        running: 'primary',
        success: 'success',
        failed: 'danger',
        paused: 'warning',
        stopped: 'info'
      }
      return map[status] || 'info'
    },
    // 时间格式化
    formatTime(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${day} ${hours}:${minutes}`
    }
  }
}
</script>

<style scoped>
.tasklist-panel {
  width: 600px;
  margin: 0 auto;
  padding: 20px 0;
}

.search-bar {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 20px;
  width: 100%;
}
.search-input {
  flex: none;
  width: 580px;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
  position: relative;
}

.wide-table {
  width: 1080px;
  max-width: 1200px;
}
.table-wrapper ::v-deep(.el-table),
.table-wrapper ::v-deep(.el-table__inner),
.table-wrapper ::v-deep(.el-table__header),
.table-wrapper ::v-deep(.el-table__body) {
  padding-left: 0 !important;
  padding-right: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.table-wrapper::after {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  width: 30px;
  height: 100%;
  pointer-events: none;
  background: linear-gradient(to left, #fff, transparent);
}
</style>