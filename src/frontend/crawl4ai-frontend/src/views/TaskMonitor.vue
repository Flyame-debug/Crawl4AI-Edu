<template>
  <div class="task-monitor-page">
    <h2>任务监控</h2>

    <el-table :data="tasks" border style="width: 100%" empty-text="暂无任务">
      <!-- 任务名 -->
      <el-table-column prop="name" label="任务名" width="200" />

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
                <el-dropdown-item @click="downloadTask(scope.row)">下载</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>

      <!-- 采集用时 -->
      <el-table-column prop="duration" label="采集用时" width="150" />

      <!-- 任务操作（改成 min-width，避免过宽） -->
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
  </div>
</template>

<script>
import { MoreFilled } from '@element-plus/icons-vue'

export default {
  name: 'TaskMonitor',
  components: { MoreFilled },
  data() {
    return {
      tasks: [
        { id: 1, name: '课程采集任务', status: '已完成', duration: '30s' },
        { id: 2, name: '教师主页采集', status: '进行中', duration: '15s' },
        { id: 3, name: '科研成果采集', status: '已暂停', duration: '45s' },
        { id: 4, name: '招生信息采集', status: '错误退出', duration: '10s' }
      ]
    }
  },
  methods: {
    pauseTask(task) {
      this.$message.warning(`任务【${task.name}】已暂停`)
      task.status = '已暂停'
    },
    continueTask(task) {
      this.$message.success(`任务【${task.name}】继续采集`)
      task.status = '进行中'
    },
    deleteTask(task) {
      this.tasks = this.tasks.filter(t => t.id !== task.id)
      this.$message.error(`任务【${task.name}】已删除`)
    },
    previewTask(task) {
      this.$message.success(`预览任务【${task.name}】结果`)
    },
    downloadTask(task) {
      this.$message.success(`下载任务【${task.name}】结果`)
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
</style>
