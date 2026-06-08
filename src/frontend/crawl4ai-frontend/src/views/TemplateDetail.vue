<template>
  <div class="template-detail">
    <!-- 面包屑导航 -->
    <el-breadcrumb separator=">">
      <el-breadcrumb-item to="/home">首页</el-breadcrumb-item>
      <el-breadcrumb-item to="/templates">模板页面</el-breadcrumb-item>
      <el-breadcrumb-item>模板详情</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 模板信息 -->
    <h2>{{ template.name }}</h2>
    <p>{{ template.description }}</p>

    <!-- 控制按钮区 -->
    <div class="collect-buttons">
      <!-- 开始/继续采集按钮 -->
      <el-button
        type="primary"
        :disabled="collectState === 'collecting'"
        @click="handleCollect"
      >
        {{ collectState === 'idle' ? '开始采集' : '继续采集' }}
      </el-button>

      <!-- 暂停按钮（采集中可点，暂停时保留但禁用） -->
      <el-button
        v-if="collectState !== 'idle'"
        type="warning"
        circle
        :disabled="collectState === 'paused'"
        @click="pauseCollect"
      >
        <el-icon><VideoPause /></el-icon>
      </el-button>

      <!-- 停止按钮（采集中或暂停时都显示） -->
      <el-button
        v-if="collectState !== 'idle'"
        type="danger"
        circle
        @click="endCollect"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <!-- 使用方法 -->
    <section class="usage">
      <h3>使用方法</h3>
      <p>{{ template.usage }}</p>
    </section>

    <!-- 注意事项 -->
    <section class="notes">
      <h3>注意事项</h3>
      <p>{{ template.notes }}</p>
    </section>

    <!-- 数据预览 -->
    <section class="preview">
      <h3>采集数据预览</h3>
      <el-table v-if="previewData.length" :data="previewData" style="width: 100%">
        <el-table-column prop="field" label="字段" />
        <el-table-column prop="value" label="值" />
      </el-table>
      <p v-else>暂无数据</p>
    </section>
  </div>
</template>

<script>
import { VideoPause, Close } from '@element-plus/icons-vue'

export default {
  name: 'TemplateDetail',
  components: { VideoPause, Close },
  data() {
    return {
      collectState: 'idle', // idle, collecting, paused
      template: { name: '', description: '', usage: '', notes: '' },
      previewData: []
    }
  },
  created() {
    const id = this.$route.params.id
    const templates = [
      { id: 1, name: '课程信息采集', description: '采集高校课程相关网页内容', usage: '单击开始采集，采集高校课程网页内容。', notes: '采集过程中请确保网络稳定。' },
      { id: 2, name: '教师主页采集', description: '采集教师个人主页信息', usage: '单击开始采集，采集教师主页数据。', notes: '注意避免采集过快导致封禁。' },
      { id: 3, name: '科研成果采集', description: '采集科研论文与项目数据', usage: '单击开始采集，采集科研成果信息。', notes: '采集时请遵守版权和数据使用规范。' }
    ]
    this.template = templates.find(t => t.id == id) || {}
  },
  methods: {
    handleCollect() {
      this.collectState = 'collecting'
      setTimeout(() => {
        this.previewData = [
          { field: '课程名', value: '数据结构' },
          { field: '教师', value: '张三' },
          { field: '学分', value: '3' }
        ]
      }, 2000)
    },
    pauseCollect() {
      this.collectState = 'paused'
    },
    endCollect() {
      this.collectState = 'idle'
      this.previewData = []
    }
  }
}
</script>

<style scoped>
.template-detail {
  padding: 20px;
}
.collect-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
section {
  margin-top: 20px;
}
</style>
