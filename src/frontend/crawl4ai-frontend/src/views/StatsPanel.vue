<template>
  <div class="stats-panel" v-loading="loading">
    <!-- 搜索区 -->
    <div class="search-bar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        size="small"
      />
      <el-select v-model="taskType" placeholder="任务类型" size="small" style="width: 130px;">
        <el-option label="全部" value="" />
        <el-option label="正式采集" value="formal" />
        <el-option label="预览采集" value="preview" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" size="small" style="width: 130px;">
        <el-option label="全部" value="" />
        <el-option label="已完成" value="completed" />
        <el-option label="采集中" value="running" />
        <el-option label="失败" value="failed" />
        <el-option label="等待中" value="pending" />
      </el-select>
      <el-button type="primary" size="small" @click="fetchStats">查询</el-button>
      <el-button size="small" @click="resetSearch">重置</el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="cards">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-number">{{ stats.totalTasks || 0 }}</div>
        <div class="stat-label">总任务数</div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-number" style="color: #67C23A;">{{ stats.successRate || 0 }}%</div>
        <div class="stat-label">成功率</div>
        <div class="stat-sub">{{ stats.completedTasks || 0 }} / {{ stats.totalTasks || 0 }}</div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-number" style="color: #409EFF;">{{ stats.totalPages || 0 }}</div>
        <div class="stat-label">总数据量</div>
        <div class="stat-sub">成功 {{ stats.successPages || 0 }} 条</div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-number" style="color: #E6A23C;">{{ stats.runningTasks || 0 }}</div>
        <div class="stat-label">运行中</div>
      </el-card>
    </div>

    <!-- 子板块切换 -->
    <el-tabs v-model="activeSubTab" @tab-change="onTabChange">
      <!-- 总数据 -->
      <el-tab-pane label="总数据" name="total">
        <div class="chart-toggle">
          <el-radio-group v-model="chartType" size="small">
            <el-radio-button label="bar">柱状</el-radio-button>
            <el-radio-button label="line">折线</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="chartTotal" class="chart"></div>
        <el-table :data="tableData.total" size="small" stripe>
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column prop="success" label="成功次数" />
          <el-table-column prop="fail" label="失败次数" />
          <el-table-column prop="total" label="总任务数" />
          <el-table-column prop="successRate" label="成功率" />
        </el-table>
      </el-tab-pane>

      <!-- 任务状态分布 -->
      <el-tab-pane label="任务状态" name="status">
        <div class="chart-toggle">
          <el-radio-group v-model="statusChartType" size="small">
            <el-radio-button label="pie">饼图</el-radio-button>
            <el-radio-button label="bar">柱状</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="chartStatus" class="chart"></div>
        <el-table :data="statusTableData" size="small" stripe>
          <el-table-column prop="status" label="状态" />
          <el-table-column prop="count" label="数量" />
          <el-table-column prop="percentage" label="占比" />
        </el-table>
      </el-tab-pane>

      <!-- 最近任务 -->
      <el-tab-pane label="最近任务" name="recent">
        <el-table :data="stats.recentTasks || []" size="small" stripe>
          <el-table-column prop="task_name" label="任务名称" min-width="150" />
          <el-table-column label="类型" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.task_type === 'preview' ? 'warning' : 'success'" size="small">
                {{ scope.row.task_type === 'preview' ? '预览' : '正式' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数据量" width="100">
            <template #default="scope">
              {{ scope.row.success_pages || 0 }} / {{ scope.row.total_pages || 0 }}
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getTasks } from '@/api/tasks'

export default {
  name: 'StatsPanel',
  props: {
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      dateRange: [],
      taskType: '',
      statusFilter: '',
      activeSubTab: 'total',
      chartType: 'bar',
      statusChartType: 'pie',
      loading: false,
      stats: {
        totalTasks: 0,
        completedTasks: 0,
        runningTasks: 0,
        failedTasks: 0,
        pendingTasks: 0,
        successRate: 0,
        totalPages: 0,
        successPages: 0,
        recentTasks: []
      },
      tableData: {
        total: []
      },
      statusTableData: [],
      chartInstances: {}
    }
  },
  watch: {
    template: {
      handler() {
        if (this.template && this.template.id) {
          this.fetchStats()
        }
      },
      deep: true,
      immediate: true
    },
    chartType() {
      this.renderTotalChart()
    },
    statusChartType() {
      this.renderStatusChart()
    },
    activeSubTab() {
      this.$nextTick(() => {
        this.initCharts()
        this.renderCharts()
      })
    }
  },
  mounted() {
    if (this.template && this.template.id) {
      this.fetchStats()
    }
    window.addEventListener('resize', this.resizeCharts)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCharts)
    Object.values(this.chartInstances).forEach(instance => instance?.dispose())
  },
  methods: {
    async fetchStats() {
      if (!this.template || !this.template.id) {
        console.warn('⚠️ 没有模板ID，无法获取统计')
        return
      }

      this.loading = true
      try {
        const params = {
          template_id: this.template.id,
          include_preview: 'true',
          page: 1,
          page_size: 100
        }
        if (this.taskType) params.task_type = this.taskType
        if (this.statusFilter) params.status = this.statusFilter
        if (this.dateRange && this.dateRange.length === 2) {
          params.start_date = this.formatDate(this.dateRange[0])
          params.end_date = this.formatDate(this.dateRange[1])
        }

        const res = await getTasks(params)
        console.log('📊 模板统计:', res)

        if (res.data.code === 200) {
          const tasks = res.data.data.results || []
          this.processStats(tasks)
        } else {
          this.$message.error(res.data.msg || '获取统计数据失败')
        }
      } catch (error) {
        console.error('获取统计数据失败：', error)
        this.$message.error('获取统计数据失败')
        this.loadMockData()
      } finally {
        this.loading = false
        this.$nextTick(() => {
          this.initCharts()
          this.renderCharts()
        })
      }
    },

    processStats(tasks) {
      // 基础统计
      const total = tasks.length
      const completed = tasks.filter(t => t.status === 'completed').length
      const running = tasks.filter(t => t.status === 'running').length
      const failed = tasks.filter(t => t.status === 'failed').length
      const pending = tasks.filter(t => t.status === 'pending').length

      this.stats = {
        totalTasks: total,
        completedTasks: completed,
        runningTasks: running,
        failedTasks: failed,
        pendingTasks: pending,
        successRate: total > 0 ? Math.round(completed / total * 100) : 0,
        totalPages: tasks.reduce((sum, t) => sum + (t.total_pages || 0), 0),
        successPages: tasks.reduce((sum, t) => sum + (t.success_pages || 0), 0),
        recentTasks: tasks.slice(0, 10)
      }

      // 状态表格数据
      const statusMap = {
        completed: '已完成',
        running: '采集中',
        failed: '失败',
        pending: '等待中',
        paused: '已暂停',
        stopped: '已停止'
      }
      this.statusTableData = Object.entries(statusMap).map(([key, label]) => {
        const count = tasks.filter(t => t.status === key).length
        return {
          status: label,
          count: count,
          percentage: total > 0 ? Math.round(count / total * 100) : 0
        }
      }).filter(item => item.count > 0)

      // 每日统计
      const dailyMap = {}
      tasks.forEach(t => {
        const date = t.created_at ? t.created_at.slice(0, 10) : '未知'
        if (!dailyMap[date]) {
          dailyMap[date] = { success: 0, fail: 0, total: 0 }
        }
        dailyMap[date].total += 1
        if (t.status === 'completed') {
          dailyMap[date].success += 1
        } else if (t.status === 'failed') {
          dailyMap[date].fail += 1
        }
      })

      this.tableData.total = Object.entries(dailyMap).map(([date, data]) => ({
        date: date,
        success: data.success,
        fail: data.fail,
        total: data.total,
        successRate: data.total > 0 ? Math.round(data.success / data.total * 100) : 0
      })).sort((a, b) => a.date.localeCompare(b.date))
    },

    loadMockData() {
      this.stats = {
        totalTasks: 45,
        completedTasks: 30,
        runningTasks: 5,
        failedTasks: 8,
        pendingTasks: 2,
        successRate: 67,
        totalPages: 1250,
        successPages: 980,
        recentTasks: []
      }
      this.tableData.total = [
        { date: '2026-06-15', success: 6, fail: 2, total: 8, successRate: 75 },
        { date: '2026-06-16', success: 8, fail: 1, total: 9, successRate: 89 }
      ]
      this.statusTableData = [
        { status: '已完成', count: 30, percentage: 67 },
        { status: '采集中', count: 5, percentage: 11 },
        { status: '失败', count: 8, percentage: 18 },
        { status: '等待中', count: 2, percentage: 4 }
      ]
    },

    resetSearch() {
      this.dateRange = []
      this.taskType = ''
      this.statusFilter = ''
      this.fetchStats()
    },

    formatDate(date) {
      if (!date) return ''
      const d = new Date(date)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
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
          minute: '2-digit'
        })
      } catch {
        return dateStr
      }
    },

    getStatusText(status) {
      const map = {
        pending: '等待中',
        running: '采集中',
        paused: '已暂停',
        stopped: '已停止',
        completed: '已完成',
        failed: '失败'
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
        failed: 'danger'
      }
      return map[status] || 'info'
    },

    initCharts() {
      Object.values(this.chartInstances).forEach(instance => instance?.dispose())
      this.chartInstances = {}

      const refMap = {
        total: 'chartTotal',
        status: 'chartStatus'
      }
      const refName = refMap[this.activeSubTab === 'recent' ? 'total' : this.activeSubTab]
      if (refName && this.$refs[refName]) {
        this.chartInstances[this.activeSubTab] = echarts.init(this.$refs[refName])
      }
    },

    renderCharts() {
      if (this.activeSubTab === 'total') {
        this.renderTotalChart()
      } else if (this.activeSubTab === 'status') {
        this.renderStatusChart()
      }
    },

    renderTotalChart() {
      const instance = this.chartInstances.total
      if (!instance) return

      const data = this.tableData.total
      instance.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['成功', '失败'] },
        grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
        xAxis: { type: 'category', data: data.map(d => d.date) },
        yAxis: { type: 'value' },
        series: [
          { name: '成功', type: this.chartType, barWidth: '35%', data: data.map(d => d.success) },
          { name: '失败', type: this.chartType, barWidth: '35%', data: data.map(d => d.fail) }
        ]
      })
      setTimeout(() => instance.resize(), 50)
    },

    renderStatusChart() {
      const instance = this.chartInstances.status
      if (!instance) return

      const data = this.statusTableData
      if (this.statusChartType === 'pie') {
        instance.setOption({
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
          legend: { orient: 'vertical', left: 'left' },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            label: { formatter: '{b}\n{d}%' },
            data: data.map(item => ({ name: item.status, value: item.count }))
          }]
        })
      } else {
        instance.setOption({
          tooltip: { trigger: 'axis' },
          grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
          xAxis: { type: 'category', data: data.map(d => d.status) },
          yAxis: { type: 'value' },
          series: [{
            type: 'bar',
            barWidth: '40%',
            data: data.map(d => d.count),
            label: { show: true, position: 'top' }
          }]
        })
      }
      setTimeout(() => instance.resize(), 50)
    },

    resizeCharts() {
      Object.values(this.chartInstances).forEach(instance => instance?.resize())
    },

    onTabChange() {
      this.$nextTick(() => {
        this.initCharts()
        this.renderCharts()
      })
    }
  }
}
</script>

<style scoped>
.stats-panel {
  padding: 20px;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 16px;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.stat-sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 2px;
}

.chart-toggle {
  margin-bottom: 10px;
}

.chart {
  height: 280px;
  width: 100%;
  margin-bottom: 20px;
}
</style>