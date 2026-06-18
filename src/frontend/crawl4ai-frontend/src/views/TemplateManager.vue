<template>
  <div class="template-manager" v-loading="loading">
    <!-- 搜索区卡片 -->
    <el-card shadow="hover" class="search-card">
      <div class="wave"></div>
      <div class="wave"></div>
      <div class="wave"></div>

      <h2 class="search-title">探索海量 网页采集 API</h2>
      <p class="search-desc">
        通过简单的 API 调用，即可获取搜索引擎、社交媒体、电商和视频平台的结构化数据，助力业务快速增长。
      </p>
      <el-input
        v-model="searchQuery"
        placeholder="请输入模板名称或关键词"
        clearable
        class="search-bar"
        @keyup.enter="doSearch"
      >
        <template #prefix>
          <el-icon><SearchIcon /></el-icon>
        </template>
        <template #append>
          <el-button type="primary" @click="doSearch">搜索</el-button>
        </template>
      </el-input>
      <p class="new-template-hint">
        没有想要找的模板？
        <span class="link" @click="goCreate">点击新建</span>
      </p>
    </el-card>

    <!-- 分类按钮区 -->
    <div class="category-bar">
      <el-button
        v-for="cat in categories"
        :key="cat"
        type="default"
        :class="{ active: activeCategory === cat }"
        @click="filterCategory(cat)"
      >
        {{ cat }}
      </el-button>
    </div>

    <!-- 模板列表区 -->
    <div class="template-list" v-if="!loading">
      <el-row :gutter="30" style="flex-wrap: wrap;">
        <el-col :span="8" v-for="template in templates" :key="template.id">
          <el-card shadow="hover" class="template-card" @dblclick="openDetail(template)">
            <h3>{{ template.name }}</h3>
            <p>{{ template.description }}</p>
            <!-- 悬停提示文字 -->
            <div class="hover-tip">双击查看模板详情</div>
          </el-card>
        </el-col>
      </el-row>
      <!-- 无数据提示 -->
      <el-empty v-if="!templates.length" description="暂无模板" />
    </div>
  </div>
</template>

<script>
import { Search as SearchIcon } from '@element-plus/icons-vue'
import { getTemplates } from '@/api/templates'

export default {
  name: 'TemplateManager',
  components: { SearchIcon },
  data() {
    return {
      searchQuery: '',
      activeCategory: '全部',
      categories: ['全部', '教师信息', '课程信息', '新闻公告', '科研成果', '其他'],
      templates: [],
      loading: false
    }
  },
  methods: {
    // 获取模板列表（真实接口）
    async fetchTemplates() {
      this.loading = true
      try {
        const params = {}
        // 分类筛选：如果选择具体分类则传入 category 参数
        if (this.activeCategory !== '全部') {
          params.category = this.categoryMap(this.activeCategory)
        }
        // 搜索关键词（接口如果不支持 search，就前端过滤）
        if (this.searchQuery) {
          params.search = this.searchQuery  // 尝试传参，后端可忽略
        }
        const res = await getTemplates(params)
        if (res.data.code === 200) {
          this.templates = res.data.data.results || res.data.data || []
          // 如果后端不支持 search 参数，前端再做关键词过滤
          if (this.searchQuery) {
            this.templates = this.templates.filter(t =>
              t.name.includes(this.searchQuery) ||
              (t.description && t.description.includes(this.searchQuery))
            )
          }
        }
      } catch (error) {
        console.error('获取模板列表失败：', error)
        this.$message.error('获取模板列表失败，请稍后重试')
        this.templates = []
      } finally {
        this.loading = false
      }
    },
    // 搜索
    doSearch() {
      this.fetchTemplates()
    },
    // 分类筛选
    filterCategory(cat) {
      this.activeCategory = cat
      this.fetchTemplates()
    },
    // 分类中文到英文映射
    categoryMap(cn) {
      const map = {
        '教师信息': 'teacher',
        '课程信息': 'course',
        '新闻公告': 'news',
        '科研成果': 'research',
        '其他': 'other'
      }
      return map[cn] || ''
    },
    // 跳转模板详情
    openDetail(template) {
      this.$router.push(`/templates/${template.id}`)
    },
    // 跳转新建模板
    goCreate() {
      this.$router.push('/templates/create')
    }
  },
  mounted() {
    this.fetchTemplates()
  }
}
</script>

<style scoped>
.template-manager {
  padding: 40px 80px;
}

/* 搜索区卡片 */
.search-card {
  margin-bottom: 40px;
  text-align: center;
  padding: 40px;
  border-radius: 16px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 6px 24px rgba(0,0,0,0.15);
  background: #bbdefb;
}

/* 波浪背景 */
.search-card .wave {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 220%;
  height: 180%;
  border-radius: 50%;
  transform: translate(-50%, -50%);
}
.search-card .wave:nth-child(1) {
  background: conic-gradient(from 0deg, #2196f3, #1976d2, #2196f3);
  animation: rotate1 25s linear infinite;
  opacity: 0.7;
}
.search-card .wave:nth-child(2) {
  background: conic-gradient(from 120deg, #1565c0, #0d47a1, #1565c0);
  animation: rotate2 40s linear infinite;
  opacity: 0.5;
}
.search-card .wave:nth-child(3) {
  background: conic-gradient(from 240deg, #0d47a1, #0b3c8c, #0d47a1);
  animation: rotate3 60s linear infinite;
  opacity: 0.4;
}

@keyframes rotate1 {
  0% { transform: translate(-50%, -50%) rotate(0deg); }
  100% { transform: translate(-50%, -50%) rotate(360deg); }
}
@keyframes rotate2 {
  0% { transform: translate(-50%, -50%) rotate(120deg); }
  100% { transform: translate(-50%, -50%) rotate(480deg); }
}
@keyframes rotate3 {
  0% { transform: translate(-50%, -50%) rotate(240deg); }
  100% { transform: translate(-50%, -50%) rotate(600deg); }
}

.search-title,
.search-desc,
.search-bar,
.new-template-hint {
  position: relative;
  z-index: 1;
}

.search-title {
  font-size: 26px;
  font-weight: bold;
  margin-bottom: 15px;
  color: #fff;
}
.search-desc {
  font-size: 15px;
  color: #e3f2fd;
  margin-bottom: 25px;
}

/* 搜索框 */
.search-bar {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 15px;
}
.search-bar .el-input__inner {
  border-radius: 80px;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.4);
  padding: 18px 30px;
  color: #003366;
  font-weight: 500;
  box-shadow: 0 0 14px rgba(100,180,255,0.35);
  transition: box-shadow 0.3s ease;
}
.search-bar .el-input__inner:focus {
  box-shadow: 0 0 20px rgba(100,180,255,0.6);
}

.new-template-hint {
  font-size: 13px;
  color: #fff;
  margin-top: 10px;
  position: relative;
  z-index: 1;
}
.link {
  color: #bbdefb;
  cursor: pointer;
  margin-left: 5px;
}
.link:hover {
  text-decoration: underline;
}

/* 分类按钮区 */
.category-bar {
  display: flex;
  justify-content: center;
  margin-bottom: 30px;
}
.category-bar .el-button {
  margin: 0 6px;
  border-radius: 25px;
  padding: 8px 18px;
}
.category-bar .el-button.active {
  background-color: #409EFF;
  color: #fff;
}

/* 模板列表区 */
.template-list {
  margin-top: 20px;
}
.template-list .el-row {
  row-gap: 35px;
}
.template-list .el-col {
  margin-bottom: 35px;
}

/* 模板卡片 */
.template-card {
  cursor: pointer;
  transition: transform 0.25s, box-shadow 0.25s;
  text-align: center;
  border-radius: 14px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.08);
  position: relative;
}
.template-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.15);
}
.template-card h3 {
  font-size: 17px;
  font-weight: bold;
  margin-bottom: 10px;
}
.template-card p {
  font-size: 14px;
  color: #555;
  line-height: 1.5;
}

/* 悬停提示文字 */
.template-card .hover-tip {
  margin-top: 12px;
  font-size: 13px;
  color: #409EFF;
  font-weight: 500;
  text-align: center;
  display: none;
}

.template-card:hover .hover-tip {
  display: block;
}
</style>