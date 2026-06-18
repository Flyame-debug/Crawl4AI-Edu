<template>
  <div class="task-list-page">
    <!-- 搜索卡片 -->
    <el-card class="search-card" shadow="hover">
      <div class="filters">
        <div class="filter-row">
          <el-select v-model="filters.type" placeholder="任务类型" style="width: 160px; margin-right: 10px;">
            <el-option label="正式采集" value="full" />
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
                  <el-dropdown-item @click="exportTask(scope.row, 'markdown')">导出Markdown</el-dropdown-item>
                  <el-dropdown-item @click="exportTask(scope.row, 'html')">导出HTML</el-dropdown-item>
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

export default {
  name: 'TaskList',
  components: { ArrowDown },
  data() {
    return {
      tasks: [
        { task_id: 1, task_name: '示例任务A', template_source: '教师信息', executed_at: '2026-06-17 10:00', status: 'success', data_count: 120 },
        { task_id: 2, task_name: '示例任务B', template_source: '课程信息', executed_at: '2026-06-17 11:30', status: 'running', data_count: 45 },
        { task_id: 3, task_name: '示例任务C', template_source: '科研成果', executed_at: '2026-06-17 12:15', status: 'failed', data_count: 0 }
      ],
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
  methods: {
    getStatusText(status) {
      const map = { running: '采集中', success: '成功', failed: '失败' }
      return map[status] || status
    },
    getStatusType(status) {
      const map = { running: 'primary', success: 'success', failed: 'danger' }
      return map[status] || 'info'
    },
    fetchTasks() {
      ElMessage.success('任务列表已刷新')
    },
    resetFilters() {
      this.filters = { type: '', product: '', tool: '', status: '', dateRange: [] }
      ElMessage.info('筛选条件已重置')
    },
    viewDetail(task) {
      ElMessageBox.alert(`任务详情：${JSON.stringify(task, null, 2)}`, '详情')
    },
    viewLog(task) {
      ElMessageBox.alert(`日志内容：${task.log || '暂无日志'}`, '日志')
    },
    rerunTask(task) {
      ElMessage.success(`任务【${task.task_name}】已重新执行`)
    },
    exportTask(task, format) {
      ElMessage.success(`任务【${task.task_name}】已导出${format}`)
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
  margin-bottom: 20px;          /* 从40px缩小到20px */
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

/* 表格美化 */
.task-table {
  border: 1px solid #eee;
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  background-color: #fff;
  width: 100%;
  table-layout: fixed;
  margin-top: 0;
  margin-bottom: 20px;          /* 从40px缩小到20px */
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

/* 操作按钮组 */
.op-buttons {
  display: flex;
  gap: 6px;
  align-items: center;
}
.op-buttons .el-button {
  margin: 0;
}
</style>

<!-- 全局样式：穿透 Element Plus 组件 -->
<style>
.short-date-picker {
  width: 120px !important;
  margin-right: 10px;
}

.task-table .el-table__cell {
  padding-top: 12px !important;   /* 从18px减小到12px */
  padding-bottom: 12px !important;
}
</style>