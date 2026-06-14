<!-- BaseLayout.vue -->
<template>
  <div class="base-layout">
    <!-- 粒子背景层 -->
    <canvas id="particle-canvas"></canvas>

    <!-- 左侧导航栏容器 -->
    <div class="sidebar" :class="{ collapsed: isCollapse }">
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
        <el-menu-item index="/home"><el-icon><House /></el-icon><span v-if="!isCollapse">首页</span></el-menu-item>
        <el-menu-item index="/guide"><el-icon><Document /></el-icon><span v-if="!isCollapse">操作指南</span></el-menu-item>
        <el-menu-item index="/templates"><el-icon><Folder /></el-icon><span v-if="!isCollapse">模板页面</span></el-menu-item>
        <el-menu-item index="/templates/create"><el-icon><Plus /></el-icon><span v-if="!isCollapse">新建模板</span></el-menu-item>
        <el-menu-item index="/tasks"><el-icon><Monitor /></el-icon><span v-if="!isCollapse">任务监控</span></el-menu-item>
      </el-menu>
    </div>

    <!-- 右侧区域 -->
    <div class="right-area" :class="isCollapse ? 'collapsed' : 'expanded'">
      <header class="top-bar" :class="isCollapse ? 'collapsed' : 'expanded'">
        <app-breadcrumb class="breadcrumb" />
        <div class="user-info">
          <el-dropdown>
            <span class="el-dropdown-link"><el-avatar src="/profilephoto.png" /></span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <div class="content">
        <transition name="fade-slide" mode="out-in">
          <router-view />
        </transition>
      </div>
    </div>
  </div>
</template>

<script>
import AppBreadcrumb from '../components/AppBreadcrumb.vue'
import { House, Document, Folder, Plus, Monitor } from '@element-plus/icons-vue'

export default {
  name: 'BaseLayout',
  components: { AppBreadcrumb, House, Document, Folder, Plus, Monitor },
  data() {
    return { isCollapse: false }
  },
  mounted() {
    this.initParticles()
    window.addEventListener('resize', this.resizeCanvas)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCanvas)
  },
  methods: {
    toggleCollapse() { this.isCollapse = !this.isCollapse },
    logout() {
      alert('已退出登录')
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
        radius: 2
      }))

      function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        // 绘制粒子
        particles.forEach(p => {
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
          ctx.fillStyle = 'rgba(200,200,255,0.7)'
          ctx.fill()
          p.x += p.vx
          p.y += p.vy
          if (p.x < 0 || p.x > canvas.width) p.vx *= -1
          if (p.y < 0 || p.y > canvas.height) p.vy *= -1
        })
        // 粒子连线
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
    }
  }
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
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 0;
}

/* 侧边栏 */
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

/* 右侧区域 */
.right-area { flex: 1; display: flex; flex-direction: column; transition: margin-left 0.3s; z-index: 5; }
.right-area.expanded { margin-left: 200px; }
.right-area.collapsed { margin-left: 64px; }

/* 顶栏 */
.top-bar {
  position: fixed;
  top: 0; left: 200px; right: 0;
  height: 60px; padding: 0 20px;
  display: flex; justify-content: space-between; align-items: center;
  z-index: 20;
  transition: left 0.3s;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(6px);
  color: #000;
  animation: textFade 2s ease-in-out;
  box-shadow: inset 0 -1px 0 rgba(255,255,255,0.3);
}
.top-bar.collapsed { left: 64px; }

.breadcrumb { flex: 1; margin: 0 20px; color: #000; font-size: 16px; font-weight: 500; }
.user-info { display: flex; align-items: center; cursor: pointer; color: #000; }

/* 正文区 */
.content {
  margin-top: 60px; padding: 20px;
  flex: 1; background: transparent;
  display: flex; flex-direction: column;
  overflow-y: auto;
  border: none; box-shadow: none;
}

/* 页面切换动画 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.5s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(10px); }
.fade-slide-enter-to { opacity: 1; transform: translateY(0); }
.fade-slide-leave-from { opacity: 1; transform: translateY(0); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-10px); }

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes textFade {
  from { opacity: 0; letter-spacing: 2px; }
  to { opacity: 1; letter-spacing: normal; }
}
</style>
