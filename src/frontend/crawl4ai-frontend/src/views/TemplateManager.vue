<template>
  <div class="template-manager">
    <h2>采集模板</h2>

    <!-- 搜索栏 -->
    <el-input
      v-model="searchQuery"
      placeholder="搜索模板..."
      clearable
      class="search-bar"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <!-- 模板列表 -->
    <el-row :gutter="20" class="template-list">
      <el-col :span="8" v-for="template in filteredTemplates" :key="template.id">
        <el-card shadow="hover" @dblclick="openDetail(template)">
          <h3>{{ template.name }}</h3>
          <p>{{ template.description }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { Search } from '@element-plus/icons-vue'

export default {
  name: 'TemplateManager',
  components: { Search },
  data() {
    return {
      searchQuery: '',
      templates: [
        { id: 1, name: '课程信息采集', description: '采集高校课程相关网页内容' },
        { id: 2, name: '教师主页采集', description: '采集教师个人主页信息' },
        { id: 3, name: '科研成果采集', description: '采集科研论文与项目数据' }
      ]
    }
  },
  computed: {
    filteredTemplates() {
      if (!this.searchQuery) return this.templates
      return this.templates.filter(t =>
        t.name.includes(this.searchQuery) || t.description.includes(this.searchQuery)
      )
    }
  },
  methods: {
    openDetail(template) {
      this.$router.push(`/templates/${template.id}`)
    }
  }
}
</script>

<style scoped>
.template-manager {
  padding: 20px;
}
.search-bar {
  margin-bottom: 20px;
  width: 400px;
}
.template-list {
  margin-top: 20px;
}
</style>
