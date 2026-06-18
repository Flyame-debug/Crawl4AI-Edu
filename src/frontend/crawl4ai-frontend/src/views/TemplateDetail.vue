<template>
  <div class="template-detail">
    <!-- 顶部简介卡片 -->
    <el-card class="intro-card" shadow="hover">
      <h2>{{ template.name }}</h2>
      <p>{{ template.description }}</p>
      <el-tag>{{ template.category || '未分类' }}</el-tag>
    </el-card>

    <div class="content-area">
      <!-- 左侧主体卡片 -->
      <div class="main-card" :class="{ shrink: codeExpanded }">
        <el-card shadow="hover">
          <el-tabs v-model="activeTab" type="card">
            <el-tab-pane label="配置" name="config">
              <ConfigPanel :template="template" />
            </el-tab-pane>
            <el-tab-pane label="概述信息" name="overview">
              <OverviewPanel :template="template" />
            </el-tab-pane>
            <el-tab-pane label="任务列表" name="tasks">
              <TaskListPanel :template="template" />
            </el-tab-pane>
            <el-tab-pane label="统计" name="stats">
              <StatsPanel :template="template" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>

      <!-- 右侧代码示例 -->
      <div class="code-sidebar" :class="{ expanded: codeExpanded }">
        <div v-if="!codeExpanded" class="vertical-toggle" @click="toggleCode">
          <div class="arrow-left">
            <el-icon class="arrow-icon"><ArrowLeft /></el-icon>
            <span class="vertical-text">&lt;/&gt; 代码示例</span>
          </div>
        </div>
        <div v-else class="code-expanded">
          <div class="toolbar">
            <el-icon class="arrow-icon collapse-toggle" @click="toggleCode"><ArrowRight /></el-icon>
            <div class="selector">
              <div class="fake-select" @click="showMenu = !showMenu">
                {{ codeTab }}
                <el-icon class="caret"><ArrowDown /></el-icon>
              </div>
              <div v-if="showMenu" class="dropdown">
                <div class="item" @click="selectTab('XPath')">XPath</div>
                <div class="item" @click="selectTab('CSS')">CSS</div>
              </div>
            </div>
            <el-button type="text" class="copy-btn" @click="copyCode">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </div>
          <div class="code-box">
            <pre v-if="codeTab === 'XPath'">{{ xpathExample }}</pre>
            <pre v-else>{{ cssExample }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ConfigPanel from './ConfigPanel.vue'
import OverviewPanel from './OverviewPanel.vue'
import TaskListPanel from './TaskListPanel.vue'
import StatsPanel from './StatsPanel.vue'
import { CopyDocument, ArrowLeft, ArrowRight, ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'TemplateDetail',
  components: { ConfigPanel, OverviewPanel, TaskListPanel, StatsPanel, CopyDocument, ArrowLeft, ArrowRight, ArrowDown },
  data() {
    return {
      activeTab: 'config',
      codeExpanded: false,
      codeTab: 'XPath',
      showMenu: false,
      template: {
        name: '教育数据采集',
        description: '采集高校官网的课程与公告信息',
        category: '教育'
      },
      xpathExample: `//div[@class="course-list"]/div/h3`,
      cssExample: `.course-list > div > h3`
    }
  },
  methods: {
    toggleCode() {
      this.codeExpanded = !this.codeExpanded
      this.showMenu = false
    },
    copyCode() {
      const text = this.codeTab === 'XPath' ? this.xpathExample : this.cssExample
      navigator.clipboard.writeText(text).then(() => {
        this.$message.success('代码已复制')
      })
    },
    selectTab(tab) {
      this.codeTab = tab
      this.showMenu = false
    }
  }
}
</script>

<style scoped>
.template-detail {
  padding: 20px;
}

/* 顶部简介卡片统一宽度 + 大圆角 */
.intro-card {
  border-radius: 20px; /* 圆角更大 */
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  
  margin-left: auto;
  margin-right: auto;
  width: 100%;
}

.content-area {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

/* 主体卡片本身圆角更大 + 内部卡片限制宽度 */
.main-card {
  flex: 1;
  display: flex;
  justify-content: center;
  transition: flex 0.3s ease;
  border-radius: 20px; /* 主体卡片圆角更大 */
}
.main-card.shrink {
  flex: 0.7;
}
.main-card > .el-card {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  border-radius: 20px; /* 内部卡片也保持一致圆角 */
}

/* Tab 栏选中高亮蓝线 */
::v-deep(.el-tabs__item.is-active) {
  color: #409EFF !important; /* 蓝色高亮 */
  font-weight: 600;          /* 加粗 */
  border-bottom: 3px solid #409EFF !important; /* 粗蓝线 */
}
::v-deep(.el-tabs__item) {
  transition: all 0.3s ease;
}
::v-deep(.el-tabs__nav-wrap::after) {
  display: none; /* 去掉默认灰色下划线 */
}

/* 右侧代码示例保持原样 */
.vertical-toggle {
  background: #1e1e1e;
  border-radius: 6px;
  height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 20px;
}
.arrow-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.arrow-icon {
  color: #fff;
  font-size: 18px;
  margin-bottom: 6px;
}
.vertical-text {
  writing-mode: vertical-rl;
  font-size: 11px;
  font-weight: normal;
}
.code-sidebar.expanded {
  flex: 0.3;
  background: #1e1e1e;
  border-radius: 14px;
  height: 500px;
  display: flex;
  flex-direction: column;
  margin-left: 20px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
  padding: 6px 10px;
}
.collapse-toggle {
  cursor: pointer;
}
.selector {
  flex: 1;
  margin: 0 10px;
  display: flex;
  justify-content: center;
  position: relative;
}
.fake-select {
  background: #1e1e1e;
  color: #fff;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: normal;
}
.fake-select .caret {
  margin-left: 6px;
}
.dropdown {
  position: absolute;
  top: 28px;
  background: #1e1e1e;
  border-radius: 4px;
  color: #fff;
  min-width: 80px;
}
.dropdown .item {
  padding: 6px 10px;
  cursor: pointer;
}
.dropdown .item:hover {
  background: #333;
}
.copy-btn {
  color: #fff;
}
.code-box {
  flex: 1;
  background: #000;
  color: #eee;
  border-radius: 6px;
  padding: 10px;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  overflow-y: auto;
  height: 420px;
}
</style>