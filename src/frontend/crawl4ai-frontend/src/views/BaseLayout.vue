<!--
  BaseLayout.vue
  功能：系统总布局，包含粒子背景、左侧导航栏(AppSidebar)、右侧顶栏、面包屑导航、用户信息区和内容区。
  特点：负责整体框架和页面切换动画，调用 AppSidebar 组件并管理折叠状态。
  新增：引入 AppTour 组件实现新手引导，统一管理引导步骤数据（使用 id 选择器定位）。
-->

<template>
  <div class="base-layout">
    <!-- 粒子背景层 -->
    <canvas id="particle-canvas"></canvas>

    <!-- 左侧导航栏（仅用于菜单高亮，不包含引导面板） -->
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

    <!-- 新手引导组件（遮罩 + 高亮 + 提示卡片） -->
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
      // 引导步骤数据（顺序：首页→模板页面→新建模板→任务监控→操作指南→退出登录）
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
    this.initParticles()
    window.addEventListener('resize', this.resizeCanvas)

    // 首次登录引导
    if (!this.isGuest && !localStorage.getItem('tour_completed')) {
      this.tourActive = true
      this.$nextTick(() => {
        this.$refs.tour?.start()
      })
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCanvas)
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
    resizeCanvas() {
      const canvas = document.getElementById('particle-canvas')
      if (canvas) {
        canvas.width = window.innerWidth
        canvas.height = window.innerHeight
      }
    },
    initParticles() {
      const canvas = document.getElementById('particle-canvas')
      const ctx = canvas.getContext('2d')
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight

      const particles = Array.from({ length: 100 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.6,
        vy: (Math.random() - 0.5) * 0.6,
        radius: 2,
      }))

      function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        particles.forEach((p) => {
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
          ctx.fillStyle = 'rgba(200,200,255,0.7)'
          ctx.fill()
          p.x += p.vx
          p.y += p.vy
          if (p.x < 0 || p.x > canvas.width) p.vx *= -1
          if (p.y < 0 || p.y > canvas.height) p.vy *= -1
        })
        for (let i = 0; i < particles.length; i++) {
          for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x
            const dy = particles[i].y - particles[j].y
            const dist = Math.sqrt(dx * dx + dy * dy)
            if (dist < 120) {
              ctx.beginPath()
              ctx.strokeStyle = `rgba(180,180,255,${1 - dist / 120})`
              ctx.moveTo(particles[i].x, particles[i].y)
              ctx.lineTo(particles[j].x, particles[j].y)
              ctx.stroke()
            }
          }
        }
        requestAnimationFrame(draw)
      }
      draw()
    },

    // 引导结束回调
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
#particle-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
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

/* 动画效果 */
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