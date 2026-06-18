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
      />
      <el-select v-model="tool" placeholder="选择工具">
        <el-option label="高校课程信息采集工具" value="course" />
        <el-option label="学术论文元数据采集工具" value="paper" />
      </el-select>
      <el-select v-model="mode" placeholder="采集方式">
        <el-option label="按课程ID采集" value="courseId" />
        <el-option label="按论文DOI采集" value="doi" />
      </el-select>
      <el-button type="primary" @click="fetchStats">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <!-- 子板块切换 -->
    <el-tabs v-model="activeSubTab">
      <!-- 总数据 -->
      <el-tab-pane label="总数据" name="total">
        <div class="cards">
          <el-card>总请求数: {{ stats.totalRequests }}</el-card>
          <el-card>成功次数: {{ stats.success }}</el-card>
          <el-card>失败次数: {{ stats.fail }}</el-card>
          <el-card>平均成功率: {{ stats.successRate }}%</el-card>
        </div>
        <div class="chart-toggle">
          <el-radio-group v-model="chartType">
            <el-radio-button label="bar">柱状</el-radio-button>
            <el-radio-button label="line">折线</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="chartTotal" class="chart"></div>
        <el-table :data="tableData.total">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="success" label="成功次数" />
          <el-table-column prop="fail" label="失败次数" />
          <el-table-column prop="total" label="总使用次数" />
          <el-table-column prop="successRate" label="成功率" />
          <el-table-column prop="avgResponse" label="平均响应时间" />
        </el-table>
      </el-tab-pane>

      <!-- 成功率 -->
      <el-tab-pane label="成功率" name="rate">
        <div class="cards">
          <el-card>总请求数: {{ stats.totalRequests }}</el-card>
          <el-card>平均成功率: {{ stats.successRate }}%</el-card>
          <el-card>平均失败率: {{ stats.failRate }}%</el-card>
        </div>
        <div class="chart-toggle">
          <el-radio-group v-model="chartType">
            <el-radio-button label="bar">柱状</el-radio-button>
            <el-radio-button label="line">折线</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="chartRate" class="chart"></div>
        <el-table :data="tableData.rate">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="requests" label="请求次数" />
          <el-table-column prop="successRate" label="平均成功率" />
          <el-table-column prop="failRate" label="平均失败率" />
        </el-table>
      </el-tab-pane>

      <!-- 响应时间 -->
      <el-tab-pane label="响应时间" name="time">
        <div class="cards">
          <el-card>平均响应时间: {{ stats.avgResponse }}</el-card>
          <el-card>中位数(P50): {{ stats.p50 }}</el-card>
          <el-card>P90: {{ stats.p90 }}</el-card>
        </div>
        <div class="chart-toggle">
          <el-radio-group v-model="chartType">
            <el-radio-button label="bar">柱状</el-radio-button>
            <el-radio-button label="line">折线</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="chartTime" class="chart"></div>
        <el-table :data="tableData.time">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="avgResponse" label="平均响应时间" />
          <el-table-column prop="p50" label="中位数(P50)" />
          <el-table-column prop="p90" label="P90" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getStats } from '@/api/stats'

export default {
  name: 'StatsPanel',
  data() {
    return {
      dateRange: [],
      tool: 'course',
      mode: 'courseId',
      activeSubTab: 'total',
      chartType: 'bar',
      loading: false,
      stats: {
        totalRequests: 0,
        success: 0,
        fail: 0,
        successRate: 0,
        failRate: 0,
        avgResponse: 0,
        p50: 0,
        p90: 0
      },
      tableData: {
        total: [],
        rate: [],
        time: []
      },
      chartInstances: {}
    }
  },
  mounted() {
    this.$nextTick(() => {
      // 仅初始化当前可见的图表
      this.initCharts()
      this.fetchStats()
    })
    window.addEventListener('resize', this.resizeCharts)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCharts)
    // 销毁所有图表实例
    Object.values(this.chartInstances).forEach(instance => instance?.dispose())
  },
  watch: {
    chartType() {
      this.renderCharts()
    },
    activeSubTab() {
      this.$nextTick(() => {
        this.initCharts()
        this.renderCharts()
        this.resizeCharts()
      })
    }
  },
  methods: {
    // 初始化或重新初始化图表
    initCharts() {
      // 销毁旧实例
      Object.values(this.chartInstances).forEach(instance => instance?.dispose())
      this.chartInstances = {}
      // 根据当前激活的tab初始化对应图表
      if (this.activeSubTab === 'total' && this.$refs.chartTotal) {
        this.chartInstances.total = echarts.init(this.$refs.chartTotal)
      } else if (this.activeSubTab === 'rate' && this.$refs.chartRate) {
        this.chartInstances.rate = echarts.init(this.$refs.chartRate)
      } else if (this.activeSubTab === 'time' && this.$refs.chartTime) {
        this.chartInstances.time = echarts.init(this.$refs.chartTime)
      }
    },
    resetSearch() {
      this.dateRange = []
      this.tool = 'course'
      this.mode = 'courseId'
      this.fetchStats()
    },
    resizeCharts() {
      Object.values(this.chartInstances).forEach(instance => instance?.resize())
    },
    async fetchStats() {
      this.loading = true
      try {
        const res = await getStats()
        if (res.data.code === 200) {
          const data = res.data.data || {}
          this.stats = {
            totalRequests: data.total_tasks ?? data.totalRequests ?? 0,
            success: data.success_tasks ?? data.success ?? 0,
            fail: data.failed_tasks ?? data.fail ?? 0,
            successRate: data.success_rate ?? data.successRate ?? 0,
            failRate: data.fail_rate ?? data.failRate ?? 0,
            avgResponse: data.avg_response ?? data.avgResponse ?? 0,
            p50: data.p50 ?? 0,
            p90: data.p90 ?? 0
          }
        } else {
          this.$message.error(res.data.msg || '获取统计数据失败')
        }
        this.loadMockTableData()
      } catch (error) {
        console.error('获取统计数据失败：', error)
        this.$message.error('获取统计数据失败，展示示例数据')
        this.loadMockTableData()
      } finally {
        this.loading = false
        this.$nextTick(() => {
          this.renderCharts()
        })
      }
    },
    loadMockTableData() {
      this.tableData = {
        total: [
          { date: '2026-06-15', success: 60, fail: 10, total: 70, successRate: 85.7, avgResponse: 1.3 },
          { date: '2026-06-14', success: 35, fail: 15, total: 50, successRate: 70.0, avgResponse: 1.5 }
        ],
        rate: [
          { date: '2026-06-15', requests: 70, successRate: 85.7, failRate: 14.3 },
          { date: '2026-06-14', requests: 50, successRate: 70.0, failRate: 30.0 }
        ],
        time: [
          { date: '2026-06-15', avgResponse: 1.3, p50: 1.2, p90: 2.5 },
          { date: '2026-06-14', avgResponse: 1.5, p50: 1.4, p90: 3.0 }
        ]
      }
    },
    renderCharts() {
      const instance = this.chartInstances[this.activeSubTab]
      if (!instance) return

      const gridCfg = { left: '5%', right: '5%', bottom: '10%', containLabel: true }

      if (this.activeSubTab === 'total') {
        instance.setOption({
          tooltip: {},
          legend: { data: ['成功次数', '失败次数'] },
          grid: gridCfg,
          xAxis: { type: 'category', data: this.tableData.total.map(d => d.date) },
          yAxis: { type: 'value' },
          series: [
            { name: '成功次数', type: this.chartType, barWidth: '40%', data: this.tableData.total.map(d => d.success) },
            { name: '失败次数', type: this.chartType, barWidth: '40%', data: this.tableData.total.map(d => d.fail) }
          ]
        })
      } else if (this.activeSubTab === 'rate') {
        instance.setOption({
          tooltip: {},
          legend: { data: ['成功率', '失败率'] },
          grid: gridCfg,
          xAxis: { type: 'category', data: this.tableData.rate.map(d => d.date) },
          yAxis: { type: 'value', min: 0, max: 100 },
          series: [
            { name: '成功率', type: this.chartType, barWidth: '40%', data: this.tableData.rate.map(d => d.successRate) },
            { name: '失败率', type: this.chartType, barWidth: '40%', data: this.tableData.rate.map(d => d.failRate) }
          ]
        })
      } else if (this.activeSubTab === 'time') {
        instance.setOption({
          tooltip: {},
          legend: { data: ['平均响应时间', 'P50', 'P90'] },
          grid: gridCfg,
          xAxis: { type: 'category', data: this.tableData.time.map(d => d.date) },
          yAxis: { type: 'value' },
          series: [
            { name: '平均响应时间', type: this.chartType, barWidth: '40%', data: this.tableData.time.map(d => d.avgResponse) },
            { name: 'P50', type: this.chartType, barWidth: '40%', data: this.tableData.time.map(d => d.p50) },
            { name: 'P90', type: this.chartType, barWidth: '40%', data: this.tableData.time.map(d => d.p90) }
          ]
        })
      }
      // 延迟 resize 确保容器尺寸已更新
      setTimeout(() => instance.resize(), 50)
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
}
.cards {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.chart-toggle {
  margin-bottom: 10px;
}
.chart {
  height: 300px;
  width: 100%;
  background: #f5f5f5;
  margin-bottom: 20px;
}
</style>