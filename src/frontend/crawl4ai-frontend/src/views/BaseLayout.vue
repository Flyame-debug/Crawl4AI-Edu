<!--
  BaseLayout.vue
  网站整体布局组件，包含：
  - 左侧导航栏（固定，带可折叠 Logo：展开显示 EduSpider，折叠显示 E）
  - 顶端栏（固定，面包屑导航、用户信息）
  - 主内容区（router-view，可滚动）
-->

<template>
  <div class="base-layout">
    <!-- 左侧导航栏容器 -->
    <div class="sidebar" :class="{ collapsed: isCollapse }">
      <!-- 顶部 Logo -->
      <div class="sidebar-logo" @click="toggleCollapse">
        <span v-if="!isCollapse">EduSpider</span>
        <span v-else>E</span>
      </div>

      <el-menu
        :default-active="$route.path"
        router
        class="el-menu-vertical"
        :collapse="isCollapse"
      >
        <el-menu-item index="/home">
          <el-icon><House /></el-icon>
          <span v-if="!isCollapse">首页</span>
        </el-menu-item>

        <el-menu-item index="/guide">
          <el-icon><Document /></el-icon>
          <span v-if="!isCollapse">操作指南</span>
        </el-menu-item>

        <el-menu-item index="/templates">
          <el-icon><Folder /></el-icon>
          <span v-if="!isCollapse">模板页面</span>
        </el-menu-item>

        <el-menu-item index="/templates/create">
          <el-icon><Plus /></el-icon>
          <span v-if="!isCollapse">新建模板</span>
        </el-menu-item>

        <el-menu-item index="/tasks">
          <el-icon><Monitor /></el-icon>
          <span v-if="!isCollapse">任务监控</span>
        </el-menu-item>
      </el-menu>
    </div>

    <!-- 右侧区域 -->
    <div class="right-area">
      <!-- 顶端栏 -->
      <header class="top-bar">
        <!-- 面包屑导航 -->
        <app-breadcrumb class="breadcrumb" />

        <!-- 用户信息 -->
        <div class="user-info">
          <el-dropdown>
            <span class="el-dropdown-link">
              <el-avatar :icon="User" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <div class="content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script>
import AppBreadcrumb from '../components/AppBreadcrumb.vue'
import { House, Document, Folder, Plus, Monitor, User } from '@element-plus/icons-vue'

export default {
  name: 'BaseLayout',
  components: { AppBreadcrumb, House, Document, Folder, Plus, Monitor, User },
  data() {
    return {
      isCollapse: false
    }
  },
  methods: {
    toggleCollapse() {
      this.isCollapse = !this.isCollapse
    },
    logout() {
      alert('已退出登录')
      this.$router.push('/auth')
    }
  }
}
</script>

<style scoped>
.base-layout {
  display: flex;
  height: 100vh;
}

/* 左侧导航栏固定 */
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 200px;
  transition: width 0.3s;
  border-right: 1px solid #ddd;
  background-color: #fff;
}
.sidebar.collapsed {
  width: 64px;
}
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 18px;
  cursor: pointer;
  border-bottom: 1px solid #ddd;
}
.el-menu-vertical {
  border-right: none;
  min-height: calc(100vh - 60px);
}
.sidebar.collapsed .el-menu-item span {
  display: none;
}

/* 右侧区域整体偏移 */
.right-area {
  margin-left: 200px; /* 与 sidebar 宽度保持一致 */
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 顶栏固定在右侧区域顶部 */
.top-bar {
  position: fixed;
  top: 0;
  left: 200px; /* 与 sidebar 对齐 */
  right: 0;
  height: 60px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ddd;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 1000;
}
.breadcrumb {
  flex: 1;
  margin: 0 20px;
}
.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

/* 内容区滚动，顶栏高度留出 */
.content {
  margin-top: 60px; /* 留出顶栏空间 */
  padding: 20px;
}

/* ✅ 全局隐藏滚动条但保留滚动功能 */
html, body {
  overflow-y: scroll;   /* 保留纵向滚动 */
}
::-webkit-scrollbar {
  display: none;        /* Chrome / Edge / Safari 隐藏滚动条 */
}
body {
  scrollbar-width: none; /* Firefox 隐藏滚动条 */
  -ms-overflow-style: none; /* IE / Edge (旧版) 隐藏滚动条 */
}
</style>
