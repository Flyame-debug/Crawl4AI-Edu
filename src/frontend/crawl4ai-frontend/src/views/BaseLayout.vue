<!--
  BaseLayout.vue
  功能：系统总布局，包含淡雅漂浮球体背景、左侧导航栏(AppSidebar)、右侧顶栏、面包屑导航、用户信息区和内容区。
  特点：侧边栏和顶栏半透明毛玻璃效果浮于背景之上，负责整体框架和页面切换动画。
  新增：引入 AppTour 组件实现新手引导，统一管理引导步骤数据（使用 id 选择器定位）。
-->

<template>
  <div class="base-layout">
    <!-- 淡雅漂浮球体背景层 -->
    <div class="bg-spheres">
      <div class="bg-sphere bg-sphere-1"></div>
      <div class="bg-sphere bg-sphere-2"></div>
      <div class="bg-sphere bg-sphere-3"></div>
      <div class="bg-sphere bg-sphere-4"></div>
      <div class="bg-sphere bg-sphere-5"></div>
      <div class="bg-sphere bg-sphere-6"></div>
    </div>

    <!-- 左侧导航栏 -->
    <AppSidebar
      :isCollapse="isCollapse"
      :tourActive="tourActive"
      :tourStep="tourStep"
      @toggle-collapse="toggleCollapse"
    />

    <!-- 右侧区域 -->
    <div class="right-area" :class="isCollapse ? 'collapsed' : 'expanded'">
      <header class="top-bar" :class="isCollapse ? 'collapsed' : 'expanded'">
        <app-breadcrumb class="breadcrumb" />
        <div id="user-info-area" class="user-info">
          <!-- 登录用户：显示头像 -->
          <el-dropdown v-if="!isGuest">
            <span class="el-dropdown-link">
              <el-avatar src="/profilephoto.png" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 游客：显示登录按钮 -->
          <el-button v-else type="primary" @click="goLogin">登录</el-button>
        </div>
      </header>
      <div class="content">
        <transition name="fade-slide" mode="out-in">
          <router-view />
        </transition>
      </div>
    </div>

    <!-- 新手引导组件 -->
    <AppTour
      ref="tour"
      :steps="tourSteps"
      @update-step="tourStep = $event"
      @finish="onTourFinish"
    />
  </div>
</template>

<script>
import AppBreadcrumb from '../components/AppBreadcrumb.vue'
import AppSidebar from '../components/AppSidebar.vue'
import AppTour from '../components/AppTour.vue'

export default {
  name: 'BaseLayout',
  components: { AppBreadcrumb, AppSidebar, AppTour },
  data() {
    return {
      isCollapse: false,
      isGuest: true,
      // 新手引导状态
      tourActive: false,
      tourStep: 0,
      // 引导步骤数据
      tourSteps: [
        {
          title: '首页入口',
          selector: '#menu-home',
          content: '欢迎来到 EduSpider！这是首页，您可以在这里查看数据概览和常用功能的快捷入口。',
          placement: 'right',
        },
        {
          title: '模板管理',
          selector: '#menu-templates',
          content: '这里陈列了所有的采集模板，您可以浏览、搜索并使用它们来快速开始数据采集任务。',
          placement: 'right',
        },
        {
          title: '新建模板',
          selector: '#menu-templates-create',
          content: '发挥创造力！在这里，您可以配置目标网址和强大的 AI 提取规则，打造专属的采集模板。',
          placement: 'right',
        },
        {
          title: '任务监控',
          selector: '#menu-tasks',
          content: '在这里，您可以实时查看所有采集任务的进展、状态，并导出您需要的数据。',
          placement: 'right',
        },
        {
          title: '操作指南',
          selector: '#menu-guide',
          content: '详细的使用方法和操作说明可以在这里找到，帮助您快速上手系统。',
          placement: 'right',
        },
        {
          title: '退出登录',
          selector: '#user-info-area',
          content: '点击右上角用户头像，选择"退出登录"即可安全退出系统。',
          placement: 'bottom',
        },
      ],
    }
  },
  mounted() {
    this.checkLoginStatus()
    window.addEventListener('resize', this.handleResize)

    // 首次登录引导
    if (!this.isGuest && !localStorage.getItem('tour_completed')) {
      this.tourActive = true
      this.$nextTick(() => {
        this.$refs.tour?.start()
      })
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
  },
  methods: {
    checkLoginStatus() {
      this.isGuest = !localStorage.getItem('token')
    },
    toggleCollapse() {
      this.isCollapse = !this.isCollapse
    },
    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      this.isGuest = true
      this.$router.push('/auth')
    },
    goLogin() {
      this.$router.push('/auth')
    },
    handleResize() {
      // 窗口大小变化时球体自动适应，无需额外操作
    },
    onTourFinish() {
      this.tourActive = false
      this.tourStep = 0
    },
  },
}
</script>

<style scoped>
.base-layout {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #f7f9fc, #eceef7, #f3f6fb);
  position: relative;
  overflow: hidden;
}

/* ===== 淡雅漂浮球体背景（稍微明显一点） ===== */
.bg-spheres {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.bg-sphere {
  position: absolute;
  border-radius: 50%;
  filter: blur(3px);
  animation: bgFloat linear infinite alternate;
}

.bg-sphere-1 {
  width: 140px;
  height: 140px;
  top: 8%;
  left: 5%;
  background: radial-gradient(circle at 30% 30%, rgba(64,158,255,0.40), rgba(64,158,255,0.05));
  box-shadow: 0 0 50px rgba(64,158,255,0.35);
  animation-duration: 22s;
}

.bg-sphere-2 {
  width: 100px;
  height: 100px;
  top: 65%;
  left: 85%;
  background: radial-gradient(circle at 40% 40%, rgba(123,97,255,0.35), rgba(123,97,255,0.05));
  box-shadow: 0 0 45px rgba(123,97,255,0.30);
  animation-duration: 26s;
  animation-delay: -6s;
}

.bg-sphere-3 {
  width: 90px;
  height: 90px;
  top: 85%;
  left: 15%;
  background: radial-gradient(circle at 35% 35%, rgba(64,200,255,0.30), rgba(64,200,255,0.05));
  box-shadow: 0 0 40px rgba(64,200,255,0.28);
  animation-duration: 24s;
  animation-delay: -12s;
}

.bg-sphere-4 {
  width: 120px;
  height: 120px;
  top: 15%;
  left: 75%;
  background: radial-gradient(circle at 40% 40%, rgba(180,130,255,0.30), rgba(180,130,255,0.05));
  box-shadow: 0 0 50px rgba(180,130,255,0.28);
  animation-duration: 20s;
  animation-delay: -4s;
}

.bg-sphere-5 {
  width: 80px;
  height: 80px;
  top: 40%;
  left: 25%;
  background: radial-gradient(circle at 30% 30%, rgba(100,150,255,0.35), rgba(100,150,255,0.05));
  box-shadow: 0 0 35px rgba(100,150,255,0.30);
  animation-duration: 28s;
  animation-delay: -9s;
}

.bg-sphere-6 {
  width: 110px;
  height: 110px;
  top: 70%;
  left: 50%;
  background: radial-gradient(circle at 35% 35%, rgba(64,158,255,0.30), rgba(64,158,255,0.05));
  box-shadow: 0 0 45px rgba(64,158,255,0.28);
  animation-duration: 23s;
  animation-delay: -15s;
}

@keyframes bgFloat {
  0% {
    transform: translate(0, 0) rotate(0deg) scale(1);
  }
  25% {
    transform: translate(20px, -25px) rotate(8deg) scale(1.08);
  }
  50% {
    transform: translate(-12px, -10px) rotate(-3deg) scale(0.94);
  }
  75% {
    transform: translate(25px, 18px) rotate(5deg) scale(1.04);
  }
  100% {
    transform: translate(-8px, 22px) rotate(-2deg) scale(1);
  }
}

/* 右侧区域 */
.right-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s;
  z-index: 5;
}
.right-area.expanded {
  margin-left: 200px;
}
.right-area.collapsed {
  margin-left: 64px;
}

/* 顶栏 */
.top-bar {
  position: fixed;
  top: 0;
  left: 200px;
  right: 0;
  height: 60px;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 20;
  transition: left 0.3s;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(6px);
  color: #000;
  animation: textFade 2s ease-in-out;
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.3);
}
.top-bar.collapsed {
  left: 64px;
}

.breadcrumb {
  flex: 1;
  margin: 0 20px;
  color: #000;
  font-size: 16px;
  font-weight: 500;
}
.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #000;
}

/* 正文区 */
.content {
  margin-top: 60px;
  padding: 20px;
  flex: 1;
  background: transparent;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border: none;
  box-shadow: none;
}

/* 页面切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.5s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.fade-slide-enter-to {
  opacity: 1;
  transform: translateY(0);
}
.fade-slide-leave-from {
  opacity: 1;
  transform: translateY(0);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
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