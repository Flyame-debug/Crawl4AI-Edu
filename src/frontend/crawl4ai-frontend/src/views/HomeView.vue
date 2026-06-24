<template>
  <div class="home-view">
    <!-- 欢迎语区块 -->
    <section class="welcome-section" ref="welcomeSection">
      <h2>欢迎您，{{ username }}，今天想要做些什么？</h2>
      <p v-if="isGuest" class="guest-tip" @click="goLogin">登录后体验完整内容</p>
    </section>

    <!-- 功能展示区块 -->
    <section class="feature-section" ref="featureSection">
      <transition-group name="fade" tag="div" class="feature-cards">
        <div class="card" v-for="item in featureCards" :key="item.title">
          <div class="card-content">
            <el-icon :size="42"><component :is="item.icon" /></el-icon>
            <h3>{{ item.title }}</h3>
            <p v-if="item.number !== null" class="number">{{ animatedNumbers[item.title] }}</p>
            <p class="desc">{{ item.desc }}</p>
          </div>
        </div>
      </transition-group>
    </section>

    <!-- 系统入口区块 -->
    <section class="entry-section" ref="entrySection">
      <transition-group name="fade" tag="div" class="entry-cards">
        <div class="entry-card" v-for="item in entryCards" :key="item.title" @click="handleEntry(item)">
          <div class="entry-content">
            <el-icon :size="40"><component :is="item.icon" /></el-icon>
            <div class="entry-text">
              <h4>{{ item.title }}</h4>
              <p>{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </transition-group>
    </section>

    <!-- 底部快速开始 -->
    <footer class="quick-start" @click="goGuide">
      快速开始？
    </footer>

    <!-- 产品效果展示（放在最下面） -->
    <section class="showcase-section" ref="showcaseSection">
      <h2 class="showcase-title">产品效果展示</h2>
      <div class="showcase-card">
        <img 
          src="/show.png" 
          alt="产品效果展示" 
          class="showcase-image"
          @error="handleImageError"
        />
        <p class="showcase-hint">系统运行截图，展示数据采集与可视化效果</p>
      </div>
    </section>
  </div>
</template>

<script>
import { Histogram, Collection, PieChart, Folder, Plus, List } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

export default {
  name: 'HomeView',
  data() {
    return {
      username: '',
      isGuest: true,
      featureCards: [
        { title: '智能采集', icon: Histogram, number: 12340, desc: '已采集数据条数' },
        { title: '教育数据', icon: Collection, number: null, desc: '覆盖高校课程信息、科研成果' },
        { title: '可视化分析', icon: PieChart, number: 25, desc: '已生成图表' }
      ],
      entryCards: [
        { title: '采集模板', icon: Folder, desc: '浏览和选择已有模板', route: '/templates' },
        { title: '新建模板', icon: Plus, desc: '创建新的采集任务模板', route: '/templates/create' },
        { title: '任务列表', icon: List, desc: '查看和管理采集任务', route: '/tasks' }
      ],
      animatedNumbers: {},
      animationFrames: [],
      observer: null,
    }
  },
  mounted() {
    this.username = localStorage.getItem('username') || '游客'
    this.isGuest = !localStorage.getItem('token')

    this.featureCards.forEach(card => {
      if (card.number !== null) {
        this.animateNumber(card.title, card.number)
      }
    })

    this.initScrollAnimation()
  },
  beforeUnmount() {
    this.animationFrames.forEach(id => cancelAnimationFrame(id))
    if (this.observer) {
      this.observer.disconnect()
    }
  },
  methods: {
    goLogin() { this.$router.push('/auth') },
    goGuide() { this.$router.push('/guide') },
    handleEntry(item) {
      if (this.isGuest) {
        ElMessageBox.confirm('请先登录！', '提示', {
          confirmButtonText: '登录',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          this.$router.push('/auth')
        }).catch(() => {})
      } else {
        this.$router.push(item.route)
      }
    },
    animateNumber(key, target) {
      let current = 0
      const step = target / 300
      const update = () => {
        current += step
        if (current >= target) {
          this.animatedNumbers[key] = target
        } else {
          this.animatedNumbers[key] = Math.floor(current)
          const frameId = requestAnimationFrame(update)
          this.animationFrames.push(frameId)
        }
      }
      update()
    },
    handleImageError() {
      console.warn('产品展示图片加载失败，请检查 public/show.png 是否存在')
    },
    initScrollAnimation() {
      const sections = [
        this.$refs.welcomeSection,
        this.$refs.featureSection,
        this.$refs.entrySection,
        this.$refs.showcaseSection,
      ].filter(Boolean)

      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            // 进入视口添加 visible 类，离开则移除，这样每次进入都有动画
            if (entry.isIntersecting) {
              entry.target.classList.add('visible')
            } else {
              entry.target.classList.remove('visible')
            }
          })
        },
        {
          threshold: 0.1,
          rootMargin: '0px 0px -50px 0px',
        }
      )

      sections.forEach((section) => {
        this.observer.observe(section)
      })
    },
  }
}
</script>

<style scoped>
.home-view {
  padding: 50px;
  max-width: 1200px;
  margin: 0 auto;
}

/* 初始状态隐藏，向下偏移 */
.welcome-section,
.feature-section,
.entry-section,
.showcase-section {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}

/* 可见状态 */
.welcome-section.visible,
.feature-section.visible,
.entry-section.visible,
.showcase-section.visible {
  opacity: 1;
  transform: translateY(0);
}

.welcome-section {
  margin-bottom: 60px;
  text-align: center;
}
.welcome-section h2 {
  font-size: 28px;
  color: #333;
}
.guest-tip {
  font-size: 15px;
  color: #409EFF;
  cursor: pointer;
  margin-top: 10px;
}

.feature-section {
  margin: 70px 0;
}
.feature-cards {
  display: flex;
  gap: 50px;
}
.card {
  flex: 1;
  padding: 35px;
  border-radius: 18px;
  background: linear-gradient(135deg, #eef3ff, #dce6ff);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  transition: transform 0.4s, box-shadow 0.4s;
}
.card:hover {
  transform: translateY(-10px) scale(1.03);
  box-shadow: 0 12px 28px rgba(0,0,0,0.12);
}
.card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.card h3 {
  margin: 18px 0;
  font-size: 22px;
  color: #333;
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card .number {
  font-size: 32px;
  font-weight: bold;
  color: #409EFF;
  margin: 14px 0;
}
.card .desc {
  font-size: 16px;
  color: #666;
}

.entry-section {
  margin: 70px 0;
}
.entry-cards {
  display: flex;
  gap: 40px;
}
.entry-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
  border-radius: 16px;
  background: linear-gradient(135deg, #fff, #f9f9f9);
  cursor: pointer;
  transition: background-color 0.3s, box-shadow 0.3s;
  text-align: center;
  min-height: 160px;
}
.entry-card:hover {
  background-color: #f0f8ff;
  box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}
.entry-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.entry-text h4 {
  margin: 0;
  font-size: 18px;
  color: #333;
}
.entry-text p {
  margin: 0;
  font-size: 15px;
  color: #666;
}

/* 产品效果展示 */
.showcase-section {
  margin: 70px 0;
  text-align: center;
}
.showcase-title {
  font-size: 22px;
  color: #333;
  margin-bottom: 30px;
  font-weight: 600;
}
.showcase-card {
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  overflow: hidden;
  background: #fff;
  padding: 20px;
  transition: transform 0.3s, box-shadow 0.3s;
}
.showcase-card:hover {
  box-shadow: 0 8px 24px rgba(64,158,255,0.12);
}
.showcase-image {
  width: 100%;
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid #eee;
  display: block;
}
.showcase-hint {
  font-size: 14px;
  color: #909399;
  margin-top: 12px;
  text-align: center;
}

.quick-start {
  text-align: right;
  font-size: 15px;
  color: #409EFF;
  cursor: pointer;
  margin-top: 30px;
}

/* 卡片列表淡入动画 */
.fade-enter-active, .fade-leave-active {
  transition: all 0.8s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}
.fade-enter-to {
  opacity: 1;
  transform: translateY(0);
}
.fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>