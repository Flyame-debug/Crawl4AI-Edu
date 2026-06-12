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
      <template #append>
        <el-button type="primary" @click="doSearch">搜索</el-button>
      </template>
    </el-input>

    <!-- 模板列表（页面整体滚动） -->
    <div class="template-list">
      <el-row :gutter="20" style="flex-wrap: wrap;">
        <el-col :span="8" v-for="template in templates" :key="template.id">
          <el-card shadow="hover" @dblclick="openDetail(template)">
            <h3>{{ template.name }}</h3>
            <p>{{ template.description }}</p>
            <p class="hint">💡 双击进入详情</p>
          </el-card>
        </el-col>
      </el-row>
      <p v-if="loading" class="loading">加载中...</p>
      <p v-if="noMore" class="no-more">没有更多模板了</p>
    </div>

    <!-- 底部提示 -->
    <div class="new-template-hint">
      没有想要找的模板？
      <span class="link" @click="goCreate">点击新建</span>
    </div>
  </div>
</template>

<script>
import { Search } from '@element-plus/icons-vue'
import { getTemplates } from '@/api/templates'

export default {
  name: 'TemplateManager',
  components: { Search },
  data() {
    return {
      searchQuery: '',
      templates: [],      // ✅ 空数组
      page: 1,
      pageSize: 6,
      loading: false,
      noMore: false
    }
  },
  mounted() {
    this.fetchTemplates()
    window.addEventListener('scroll', this.handleScroll)
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.handleScroll)
  },
  methods: {
    async fetchTemplates() {
      if (this.loading || this.noMore) return
      this.loading = true
      try {
        const res = await getTemplates({ page: this.page, pageSize: this.pageSize, search: this.searchQuery })
        if (res.data && res.data.results && res.data.results.length) {
          if (this.page === 1) {
            this.templates = res.data.results
          } else {
            this.templates = [...this.templates, ...res.data.results]
          }
          if (res.data.results.length < this.pageSize) {
            this.noMore = true
          }
          this.page++
        } else if (this.page === 1) {
          // ✅ 没有数据时只是提示，不显示默认模板
          console.log('暂无模板数据，请先创建模板')
        }
      } catch (e) {
        console.error('获取模板列表失败:', e)
        this.$message.error('获取模板列表失败')
      } finally {
        this.loading = false
      }
    },
    handleScroll() {
      const { scrollTop, clientHeight, scrollHeight } = document.documentElement
      if (scrollTop + clientHeight >= scrollHeight - 10) {
        this.fetchTemplates()
      }
    },
    openDetail(template) {
      this.$router.push(`/templates/${template.id}`)
    },
    goCreate() {
      this.$router.push('/templates/create')
    },
    doSearch() {
      this.page = 1
      this.noMore = false
      this.templates = []      // ✅ 清空数组
      this.fetchTemplates()    // ✅ 从后端重新加载
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
.template-list .el-col {
  margin-bottom: 20px;
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
.loading,
.no-more {
  text-align: center;
  margin: 10px 0;
  color: #666;
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
</style><template>
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
      <template #append>
        <el-button type="primary" @click="doSearch">搜索</el-button>
      </template>
    </el-input>

    <!-- 模板列表（页面整体滚动） -->
    <div class="template-list">
      <el-row :gutter="20" style="flex-wrap: wrap;">
        <el-col :span="8" v-for="template in templates" :key="template.id">
          <el-card shadow="hover" @dblclick="openDetail(template)">
            <h3>{{ template.name }}</h3>
            <p>{{ template.description }}</p>
            <p class="hint">💡 双击进入详情</p>
          </el-card>
        </el-col>
      </el-row>
      <p v-if="loading" class="loading">加载中...</p>
      <p v-if="noMore" class="no-more">没有更多模板了</p>
    </div>

    <!-- 底部提示 -->
    <div class="new-template-hint">
      没有想要找的模板？
      <span class="link" @click="goCreate">点击新建</span>
    </div>
  </div>
</template>

<script>
import { Search } from '@element-plus/icons-vue'
import { getTemplates } from '@/api/templates'

export default {
  name: 'TemplateManager',
  components: { Search },
  data() {
    return {
      searchQuery: '',
      templates: [
        { id: 1, name: '课程信息采集', description: '采集高校课程相关网页内容' },
        { id: 2, name: '教师主页采集', description: '采集教师个人主页信息' },
        { id: 3, name: '科研成果采集', description: '采集科研论文与项目数据' },
        { id: 4, name: '招生信息采集', description: '采集高校招生简章与政策' },
        { id: 5, name: '学术会议采集', description: '采集学术会议通知与日程' },
        { id: 6, name: '实验室信息采集', description: '采集实验室成员与研究方向' }
      ],
      page: 1,
      pageSize: 6,
      loading: false,
      noMore: false
    }
  },
  mounted() {
    this.fetchTemplates()
    window.addEventListener('scroll', this.handleScroll)
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.handleScroll)
  },
  methods: {
    async fetchTemplates() {
      if (this.loading || this.noMore) return
      this.loading = true
      try {
        const res = await getTemplates({ page: this.page, pageSize: this.pageSize, search: this.searchQuery })
        if (res.data && res.data.results && res.data.results.length) {
          if (this.page === 1) {
            this.templates = res.data.results
          } else {
            this.templates = [...this.templates, ...res.data.results]
          }
          if (res.data.results.length < this.pageSize) {
            this.noMore = true
          }
          this.page++
        } else if (this.page === 1) {
          this.$message.info('后端暂无数据，显示默认模板')
        }
      } catch (e) {
        this.$message.error('获取模板列表失败（当前显示默认卡片）')
      } finally {
        this.loading = false
      }
    },
    handleScroll() {
      const { scrollTop, clientHeight, scrollHeight } = document.documentElement
      if (scrollTop + clientHeight >= scrollHeight - 10) {
        this.fetchTemplates()
      }
    },
    openDetail(template) {
      this.$router.push(`/templates/${template.id}`)
    },
    goCreate() {
      this.$router.push('/templates/create')
    },
    doSearch() {
      this.page = 1
      this.noMore = false
      this.templates = [
        { id: 1, name: '课程信息采集', description: '采集高校课程相关网页内容' },
        { id: 2, name: '教师主页采集', description: '采集教师个人主页信息' },
        { id: 3, name: '科研成果采集', description: '采集科研论文与项目数据' },
        { id: 4, name: '招生信息采集', description: '采集高校招生简章与政策' },
        { id: 5, name: '学术会议采集', description: '采集学术会议通知与日程' },
        { id: 6, name: '实验室信息采集', description: '采集实验室成员与研究方向' }
      ]
      this.fetchTemplates()
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
  /* 不再限制高度和滚动，由页面整体滚动 */
}
.template-list .el-col {
  margin-bottom: 20px;
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
.loading,
.no-more {
  text-align: center;
  margin: 10px 0;
  color: #666;
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
