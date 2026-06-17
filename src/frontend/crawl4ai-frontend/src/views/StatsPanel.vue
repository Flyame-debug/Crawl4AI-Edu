<template>
  <div class="stats-panel">
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
      <el-button type="primary" @click="renderCharts">搜索</el-button>
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

export default {
  name: 'StatsPanel',
  data() {
    return {
      dateRange: [],
      tool: 'course',
      mode: 'courseId',
      activeSubTab: 'total',
      chartType: 'bar',
      stats: {
        totalRequests: 120,
        success: 95,
        fail: 25,
        successRate: 79.2,
        failRate: 20.8,
        avgResponse: 1.4,
        p50: 1.2,
        p90: 2.8
      },
      tableData: {
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
      },
      chartInstances: {}
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.chartInstances.total = echarts.init(this.$refs.chartTotal)
      this.chartInstances.rate = echarts.init(this.$refs.chartRate)
      this.chartInstances.time = echarts.init(this.$refs.chartTime)
      this.renderCharts()
      window.addEventListener('resize', this.resizeCharts)
    })
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCharts)
  },
  watch: {
    chartType() {
      this.renderCharts()
    },
    activeSubTab() {
      // 每次切换 tab 时重新渲染并 resize
      this.$nextTick(() => {
        this.renderCharts()
        this.resizeCharts()
      })
    }
  },
  methods: {
    resetSearch() {
      this.dateRange = []
      this.tool = 'course'
      this.mode = 'courseId'
    },
    resizeCharts() {
      this.chartInstances.total?.resize()
      this.chartInstances.rate?.resize()
      this.chartInstances.time?.resize()
    },
    renderCharts() {
      if (!this.chartInstances.total || !this.chartInstances.rate || !this.chartInstances.time) return

      const gridCfg = { left: '5%', right: '5%', bottom: '10%', containLabel: true }

      this.chartInstances.total.setOption({
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

      this.chartInstances.rate.setOption({
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

      this.chartInstances.time.setOption({
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
  height: 300px;   /* 提高高度，避免压缩 */
  width: 100%;     /* 保证宽度占满父容器 */
  background: #f5f5f5;
  margin-bottom: 20px;
}
</style>

