<template>
  <div class="task-monitor-page">
    <h2>任务监控</h2>

    <el-table :data="tasks" border style="width: 100%" empty-text="暂无任务">
      <!-- 任务名 -->
      <el-table-column prop="task_name" label="任务名" width="200" />

      <!-- 采集状态 -->
      <el-table-column prop="status" label="采集状态" width="200">
        <template #default="scope">
          <span>{{ scope.row.status }}</span>
          <el-dropdown v-if="scope.row.status === '已完成'" trigger="click">
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
          <el-progress :percentage="scope.row.progress_percent || 0" status="active"></el-progress>
          <small>{{ scope.row.progress || '' }}</small>
        </template>
      </el-table-column>

      <!-- 任务操作 -->
      <el-table-column label="任务操作" min-width="160">
        <template #default="scope">
          <el-button
            v-if="scope.row.status === '进行中'"
            type="warning"
            size="small"
            @click="pauseTask(scope.row)"
          >
            暂停
          </el-button>
          <el-button
            v-else-if="scope.row.status === '已暂停'"
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

    <!-- 新增：数据预览弹窗 -->
    <el-dialog v-model="snapshotVisible" title="采集数据预览" width="80%">
      <div class="filters">
        <el-select v-model="filters.category" placeholder="选择分类" style="width: 150px; margin-right: 10px;">
          <el-option label="师资" value="师资" />
          <el-option label="课程" value="课程" />
          <el-option label="科研" value="科研" />
          <el-option label="其他" value="其他" />
        </el-select>
        <el-input v-model="filters.search" placeholder="搜索关键词" style="width: 200px; margin-right: 10px;" />
        <el-button type="primary" @click="filterPages">查询</el-button>
      </div>

      <el-table :data="filteredPages" border style="width: 100%" empty-text="暂无数据">
        <el-table-column prop="task_name" label="任务名" width="200" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="url" label="页面URL" width="300" />
        <el-table-column label="内容" min-width="300">
          <template #default="scope">
            <div v-html="scope.row.markdown"></div>
          </template>
        </el-table-column>
        <el-table-column label="图片" width="200">
          <template #default="scope">
            <img v-for="img in scope.row.images" :key="img" :src="img" style="width: 80px; margin-right: 5px;" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="采集时间" width="180" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script>
import { MoreFilled } from '@element-plus/icons-vue'
import { downloadTaskResult } from '@/api/tasks'

export default {
  name: 'TaskMonitor',
  components: { MoreFilled },
  data() {
    return {
      tasks: [],
      snapshotVisible: false,
      filters: { category: '', search: '' },
      // 新增：测试数据（后端覆盖）
      pages: []
    }
  },
  computed: {
    filteredPages() {
      return this.pages.filter(p => {
        const matchCategory = this.filters.category ? p.category === this.filters.category : true
        const matchSearch = this.filters.search ? p.markdown.includes(this.filters.search) || p.url.includes(this.filters.search) : true
        return matchCategory && matchSearch
      })
    }
  },
  methods: {
    pauseTask(task) {
      task.status = '已暂停'
      this.$message.success(`任务【${task.task_name}】已暂停`)
    },
    continueTask(task) {
      task.status = '进行中'
      this.$message.success(`任务【${task.task_name}】继续采集`)
    },
    deleteTask(task) {
      this.tasks = this.tasks.filter(t => t.task_id !== task.task_id)
      this.$message.success(`任务【${task.task_name}】已删除`)
    },
    viewDetail(task) {
      this.$alert(
        `任务名称: ${task.task_name}\n状态: ${task.status}\n进度: ${task.progress || '暂无'}\n用时: ${task.duration}`,
        '任务详情',
        { confirmButtonText: '确定' }
      )
    },
    previewTask(task) {
      // 保留原有逻辑，但现在打开弹窗展示数据
      this.snapshotVisible = true
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
        console.error(e) // 打印错误方便调试
        this.$message.error(`下载任务【${task.task_name}】失败，请稍后重试`)
      }
    },
    filterPages() {
      this.$message.success('筛选已应用')
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
