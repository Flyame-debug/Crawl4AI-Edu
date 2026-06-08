/**
 * BaseLayout.vue
 * 
 * 功能说明：
 * - 全局布局组件，包含左侧导航栏、顶部栏和右侧内容区
 * - 左侧导航栏支持折叠/展开，折叠时只显示图标，不显示文字
 * - 顶部栏包含面包屑导航和用户信息（头像 + 下拉菜单）
 * - 右侧区域通过 <router-view /> 动态渲染页面内容
 * 
 * 使用场景：
 * - 所有页面都挂载在 BaseLayout 下，保证统一的导航和顶栏
 * 
 * 注意事项：
 * - 使用 Element Plus 的 el-menu 提供导航功能
 * - 使用 @element-plus/icons-vue 提供菜单图标
 */

<template>
  <div class="base-layout">
    <!-- 左侧导航栏容器 -->
    <div class="sidebar" :class="{ collapsed: isCollapse }">
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        :collapse="isCollapse"
        @select="handleSelect"
      >
        <!-- 顶部 Logo -->
        <div class="sidebar-logo" @click="toggleCollapse">
          <span v-if="!isCollapse">教育数据采集平台</span>
          <span v-else>E</span>
        </div>

        <!-- 菜单项：图标 + 文字（折叠时文字隐藏） -->
        <el-menu-item index="home">
          <el-icon><House /></el-icon>
          <span v-if="!isCollapse">首页</span>
        </el-menu-item>

        <el-menu-item index="guide">
          <el-icon><Document /></el-icon>
          <span v-if="!isCollapse">操作指南</span>
        </el-menu-item>

        <el-menu-item index="templates">
          <el-icon><Folder /></el-icon>
          <span v-if="!isCollapse">模板页面</span>
        </el-menu-item>

        <el-menu-item index="create-template">
          <el-icon><Plus /></el-icon>
          <span v-if="!isCollapse">新建模板</span>
        </el-menu-item>

        <el-menu-item index="tasks">
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
              <el-avatar icon="UserFilled" />
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
// 引入 Element Plus 图标
import { House, Document, Folder, Plus, Monitor } from '@element-plus/icons-vue'

export default {
  name: 'BaseLayout',
  components: { AppBreadcrumb, House, Document, Folder, Plus, Monitor },
  data() {
    return {
      isCollapse: false,   // 控制侧边栏折叠
      activeMenu: 'home'
    }
  },
  methods: {
    handleSelect(key) {
      this.activeMenu = key
      this.$router.push(`/${key}`)
    },
    toggleCollapse() {
      this.isCollapse = !this.isCollapse   // 点击 Logo 切换折叠状态
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

/* 左侧导航栏容器 */
.sidebar {
  width: 200px;
  transition: width 0.3s;
  border-right: 1px solid #ddd;
}
.sidebar.collapsed {
  width: 64px;
}

/* 顶部 Logo */
.sidebar-logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-weight: bold;
  cursor: pointer;
  border-bottom: 1px solid #ddd;
  user-select: none;
}

/* 菜单样式 */
.el-menu-vertical {
  border-right: none;
  min-height: 100vh;
}

/* 折叠时隐藏文字 */
.sidebar.collapsed .el-menu-item span {
  display: none;
}

/* 右侧区域 */
.right-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 顶端栏 */
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
}

/* 内容区 */
.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
</style>
