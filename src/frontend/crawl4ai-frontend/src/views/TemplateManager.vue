<template>
  <div class="template-manager">
    <!-- 搜索区卡片 -->
    <el-card shadow="hover" class="search-card">
      <h2 class="search-title">探索海量 网页采集 API</h2>
      <p class="search-desc">
        通过简单的 API 调用，即可获取搜索引擎、社交媒体、电商和视频平台的结构化数据，助力业务快速增长。
      </p>
      <el-input
        v-model="searchQuery"
        placeholder="请输入模板名称或关键词"
        clearable
        class="search-bar"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
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
    <div class="template-list">
      <el-row :gutter="30" style="flex-wrap: wrap;">
        <el-col :span="8" v-for="template in filteredTemplates" :key="template.id">
          <el-card shadow="hover" class="template-card" @dblclick="openDetail(template)">
            <h3>{{ template.name }}</h3>
            <p>{{ template.description }}</p>
            <p class="hint">💡 双击进入详情</p>
          </el-card>
        </el-col>
      </el-row>
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
      activeCategory: '全部',
      categories: ['全部', '教育', '科研', '医疗'],
      templates: [
        { id: 1, name: '教育数据采集', description: '采集高校官网的课程与公告信息', category: '教育' },
        { id: 2, name: '科研论文采集', description: '采集学术网站的论文摘要与引用', category: '科研' },
        { id: 3, name: '医疗资讯采集', description: '采集医疗网站的最新资讯与政策', category: '医疗' },
        { id: 4, name: '教育新闻采集', description: '采集教育类新闻门户的最新动态', category: '教育' },
        { id: 5, name: '科研项目采集', description: '采集科研机构的项目与成果信息', category: '科研' },
        { id: 6, name: '医疗政策采集', description: '采集医疗政策文件与公告', category: '医疗' }
      ]
    }
  },
  computed: {
    filteredTemplates() {
      let list = this.templates
      if (this.activeCategory !== '全部') {
        list = list.filter(t => t.category === this.activeCategory)
      }
      if (this.searchQuery) {
        list = list.filter(t =>
          t.name.includes(this.searchQuery) || t.description.includes(this.searchQuery)
        )
      }
      return list
    }
  },
  methods: {
    doSearch() {
      // 前端过滤，后续接后端时替换为 API 请求
    },
    filterCategory(cat) {
      this.activeCategory = cat
    },
    openDetail(template) {
      this.$router.push(`/templates/${template.id}`)
    },
    goCreate() {
      this.$router.push('/templates/create')
    }
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
  box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* 阴影 */
}

.search-title {
  font-size: 26px;
  font-weight: bold;
  margin-bottom: 15px;
}

.search-desc {
  font-size: 15px;
  color: #666;
  margin-bottom: 25px;
}

/* 搜索框：圆角 + 半透明 + 更长 */
.search-bar {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 15px;
}
.search-bar .el-input__inner {
  border-radius: 25px;
  background-color: rgba(255, 255, 255, 0.85);
  padding: 12px 20px;
}

.new-template-hint {
  font-size: 13px;
  color: #666;
  margin-top: 10px;
}

.link {
  color: #409EFF;
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
  margin: 0;
  border-radius: 0;
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
  row-gap: 35px; /* 上下间距 */
}
.template-list .el-col {
  margin-bottom: 35px;
}

.template-card {
  cursor: pointer;
  transition: transform 0.25s, box-shadow 0.25s;
  text-align: center;
  border-radius: 14px; /* 卡片圆角 */
  min-height: 200px;   /* 高度适中 */
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 25px;       /* 内部留白 */
  box-shadow: 0 4px 10px rgba(0,0,0,0.08); /* 默认阴影 */
}
.template-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.15); /* 悬停加深 */
}

.template-card h3 {
  font-size: 17px;
  font-weight: bold;
  margin-bottom: 12px;
}
.template-card p {
  font-size: 14px;
  color: #555;
  line-height: 1.5;
}
.hint {
  font-size: 12px;
  color: #888;
  margin-top: 8px;
}
</style>
