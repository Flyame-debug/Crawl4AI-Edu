<!--
  AppSidebar.vue
  功能：左侧导航栏组件，包含系统 Logo、菜单项（首页、操作指南、模板、新建模板、任务监控）。
  特点：支持折叠/展开，通过 props 接收 isCollapse 状态，并通过事件通知父组件。
  新增：菜单项添加 id 供引导定位；配合新手引导高亮。
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
      <!-- 0: 首页入口 -->
      <el-menu-item
        id="menu-home"
        index="/home"
        :class="{ 'tour-highlight': tourActive && tourStep === 0 }"
      >
        <el-icon><House /></el-icon>
        <span v-if="!isCollapse">首页</span>
      </el-menu-item>

      <!-- 4: 操作指南（引导顺序在任务监控之后） -->
      <el-menu-item
        id="menu-guide"
        index="/guide"
        :class="{ 'tour-highlight': tourActive && tourStep === 4 }"
      >
        <el-icon><Document /></el-icon>
        <span v-if="!isCollapse">操作指南</span>
      </el-menu-item>

      <!-- 1: 模板页面（引导第2步） -->
      <el-menu-item
        id="menu-templates"
        index="/templates"
        :class="{ 'tour-highlight': tourActive && tourStep === 1 }"
      >
        <el-icon><Folder /></el-icon>
        <span v-if="!isCollapse">模板页面</span>
      </el-menu-item>

      <!-- 2: 新建模板（引导第3步） -->
      <el-menu-item
        id="menu-templates-create"
        index="/templates/create"
        :class="{ 'tour-highlight': tourActive && tourStep === 2 }"
      >
        <el-icon><Plus /></el-icon>
        <span v-if="!isCollapse">新建模板</span>
      </el-menu-item>

      <!-- 3: 任务监控（引导第4步） -->
      <el-menu-item
        id="menu-tasks"
        index="/tasks"
        :class="{ 'tour-highlight': tourActive && tourStep === 3 }"
      >
        <el-icon><Monitor /></el-icon>
        <span v-if="!isCollapse">任务监控</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script>
import { House, Document, Folder, Plus, Monitor } from '@element-plus/icons-vue'

export default {
  name: 'AppSidebar',
  components: { House, Document, Folder, Plus, Monitor },
  props: {
    isCollapse: { type: Boolean, default: false },
    // 新手引导相关：是否激活引导，以及当前步骤索引
    tourActive: { type: Boolean, default: false },
    tourStep: { type: Number, default: 0 },
  },
  emits: ['toggle-collapse'],
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 200px;
  transition: width 0.3s;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(12px);
  border-radius: 0;
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.3);
  z-index: 10;
  display: flex;
  flex-direction: column;
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
  color: #000;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(8px);
  animation: textFade 2s ease-in-out;
  flex-shrink: 0;
}

.el-menu-vertical {
  border-right: none;
  min-height: 0;
  flex: 1;
  background: transparent;
  overflow-y: auto;
}
.el-menu-item {
  color: #333;
  transition: background-color 0.3s, color 0.3s;
}
.el-menu-item.is-active {
  background-color: rgba(230, 240, 255, 0.8);
  color: #409eff;
}
.el-menu-item:hover {
  background-color: rgba(230, 240, 255, 0.8);
  color: #409eff;
}
.sidebar.collapsed .el-menu-item span {
  display: none;
}

/* 新手引导：菜单项高亮动画 */
.tour-highlight {
  background-color: rgba(64, 158, 255, 0.15) !important;
  border-left: 3px solid #409eff;
  animation: tourMenuPulse 1.5s ease-in-out infinite;
  /* 确保高亮项在遮罩层上方可见 */
  position: relative;
  z-index: 11;
}

@keyframes tourMenuPulse {
  0%,
  100% {
    background-color: rgba(64, 158, 255, 0.15);
  }
  50% {
    background-color: rgba(64, 158, 255, 0.3);
  }
}

@keyframes textFade {
  from {
    opacity: 0;
    letter-spacing: 2px;
  }
  to {
    opacity: 1;
    letter-spacing: normal;
  }
}
</style>