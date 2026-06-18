<!--
  AppSidebar.vue
  功能：左侧导航栏组件，包含系统 Logo、菜单项（首页、操作指南、模板、新建模板、任务监控）。
  特点：支持折叠/展开，通过 props 接收 isCollapse 状态，并通过事件通知父组件。
-->

<template>
  <div class="sidebar" :class="{ collapsed: isCollapse }">
    <div class="sidebar-logo" @click="$emit('toggle-collapse')">
      <span v-if="!isCollapse">EduSpider</span>
      <span v-else>E</span>
    </div>

    <el-menu
      :default-active="$route.path"
      router
      class="el-menu-vertical"
      :collapse="isCollapse"
    >
      <el-menu-item index="/home"><el-icon><House /></el-icon><span v-if="!isCollapse">首页</span></el-menu-item>
      <el-menu-item index="/guide"><el-icon><Document /></el-icon><span v-if="!isCollapse">操作指南</span></el-menu-item>
      <el-menu-item index="/templates"><el-icon><Folder /></el-icon><span v-if="!isCollapse">模板页面</span></el-menu-item>
      <el-menu-item index="/templates/create"><el-icon><Plus /></el-icon><span v-if="!isCollapse">新建模板</span></el-menu-item>
      <el-menu-item index="/tasks"><el-icon><Monitor /></el-icon><span v-if="!isCollapse">任务监控</span></el-menu-item>
    </el-menu>
  </div>
</template>

<script>
import { House, Document, Folder, Plus, Monitor } from '@element-plus/icons-vue'

export default {
  name: 'AppSidebar',
  props: {
    isCollapse: { type: Boolean, default: false }
  },
  components: { House, Document, Folder, Plus, Monitor }
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0; top: 0; bottom: 0;
  width: 200px;
  transition: width 0.3s;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(12px);
  border-radius: 0;
  box-shadow: inset -1px 0 0 rgba(255,255,255,0.3);
  z-index: 10;
}
.sidebar.collapsed { width: 64px; }

.sidebar-logo {
  height: 60px;
  display: flex; align-items: center; justify-content: center;
  font-weight: bold; font-size: 18px;
  cursor: pointer; color: #000;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(8px);
  animation: textFade 2s ease-in-out;
}

.el-menu-vertical { border-right: none; min-height: calc(100vh - 60px); background: transparent; }
.el-menu-item { color: #333; transition: background-color 0.3s, color 0.3s; }
.el-menu-item.is-active { background-color: rgba(230,240,255,0.8); color: #409EFF; }
.el-menu-item:hover { background-color: rgba(230,240,255,0.8); color: #409EFF; }
.sidebar.collapsed .el-menu-item span { display: none; }

@keyframes textFade {
  from { opacity: 0; letter-spacing: 2px; }
  to { opacity: 1; letter-spacing: normal; }
}
</style>
