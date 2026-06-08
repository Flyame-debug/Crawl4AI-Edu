<template>
  <div class="base-layout">
    <!-- 左侧导航栏容器 -->
    <div class="sidebar" :class="{ collapsed: isCollapse }">
      <el-menu
        :default-active="$route.path"
        router
        class="el-menu-vertical"
        :collapse="isCollapse"
      >
        <!-- 顶部 Logo -->
        <div class="sidebar-logo" @click="toggleCollapse">
          <span v-if="!isCollapse">教育数据采集平台</span>
          <span v-else>E</span>
        </div>

        <!-- 菜单项 -->
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
        <app-breadcrumb class="breadcrumb" />
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
.sidebar {
  width: 200px;
  transition: width 0.3s;
  border-right: 1px solid #ddd;
}
.sidebar.collapsed {
  width: 64px;
}
.sidebar-logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-weight: bold;
  cursor: pointer;
  border-bottom: 1px solid #ddd;
  user-select: none;
}
.el-menu-vertical {
  border-right: none;
  min-height: 100vh;
}
.sidebar.collapsed .el-menu-item span {
  display: none;
}
.right-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ddd;
  padding: 0 20px;
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
.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
</style>
