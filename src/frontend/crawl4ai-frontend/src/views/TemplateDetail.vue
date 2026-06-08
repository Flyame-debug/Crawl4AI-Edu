<template>
  <div class="template-detail">
    <!-- 面包屑导航 -->
    <el-breadcrumb separator=">">
      <el-breadcrumb-item to="/home">首页</el-breadcrumb-item>
      <el-breadcrumb-item to="/templates">模板页面</el-breadcrumb-item>
      <el-breadcrumb-item>模板详情</el-breadcrumb-item>
    </el-breadcrumb>

    <h2>{{ template.name }}</h2>
    <p>{{ template.description }}</p>

    <el-button type="primary">开始采集</el-button>
    <el-button type="success">预览数据</el-button>
  </div>
</template>

<script>
export default {
  name: 'TemplateDetail',
  data() {
    return {
      template: { name: '', description: '' }
    }
  },
  created() {
    const id = this.$route.params.id
    // 模拟根据 id 获取模板详情
    const templates = [
      { id: 1, name: '课程信息采集', description: '采集高校课程相关网页内容' },
      { id: 2, name: '教师主页采集', description: '采集教师个人主页信息' },
      { id: 3, name: '科研成果采集', description: '采集科研论文与项目数据' }
    ]
    this.template = templates.find(t => t.id == id) || {}
  }
}
</script>

<style scoped>
.template-detail {
  padding: 20px;
}
</style>
