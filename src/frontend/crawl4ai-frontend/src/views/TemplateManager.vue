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
      <!-- 左侧图标 -->
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
      <!-- 右侧搜索按钮 -->
      <template #append>
        <el-button type="primary" @click="doSearch">搜索</el-button>
      </template>
    </el-input>

    <!-- 模板列表 -->
    <el-row :gutter="20" class="template-list">
      <el-col :span="8" v-for="template in filteredTemplates" :key="template.id">
        <el-card shadow="hover" @dblclick="openDetail(template)">
          <h3>{{ template.name }}</h3>
          <p>{{ template.description }}</p>
          <p class="hint">💡 双击进入详情</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部提示 -->
    <div class="new-template-hint">
      没有想要找的模板？
      <span class="link" @click="goCreate">点击新建</span>
    </div>
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
    },
    goCreate() {
      this.$router.push('/templates/create')
    },
    doSearch() {
      if (!this.searchQuery.trim()) {
        this.$message.warning('请输入搜索关键词')
        return
      }
      this.$message.info(`正在搜索：${this.searchQuery}`)
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
.el-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.el-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
}
.hint {
  font-size: 12px;
  color: #888;
  margin-top: 10px;
}
.new-template-hint {
  text-align: right;
  margin-top: 20px;
  font-size: 13px;
  color: #666;
}
.link {
  color: #409EFF;
  cursor: pointer;
  margin-left: 5px;
}
.link:hover {
  text-decoration: underline;
}
</style>
