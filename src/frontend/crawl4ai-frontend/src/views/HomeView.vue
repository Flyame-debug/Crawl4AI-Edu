<template>
  <div class="home-view">
    <!-- 欢迎语区块 -->
    <section class="welcome-section">
      <h2>欢迎您，{{ username }}，今天想要做些什么？</h2>
      <p v-if="isGuest" class="guest-tip" @click="goLogin">登录后体验完整内容</p>
    </section>

    <!-- 功能展示区块 -->
    <section class="feature-section">
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
    <section class="entry-section">
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
      animationFrames: [] // 存储所有动画帧ID，用于销毁时取消
    }
  },
  mounted() {
    this.username = localStorage.getItem('username') || '游客'
    this.isGuest = !localStorage.getItem('token')

    // 启动数字动画
    this.featureCards.forEach(card => {
      if (card.number !== null) {
        this.animateNumber(card.title, card.number)
      }
    })
  },
  beforeUnmount() {
    // 取消所有未完成的动画帧，防止内存泄漏
    this.animationFrames.forEach(id => cancelAnimationFrame(id))
  },
  methods: {
    goLogin() {
      this.$router.push('/auth')
    },
    goGuide() {
      this.$router.push('/guide')
    },
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
    }
  }
}
</script>

<style scoped>
.home-view {
  padding: 50px;
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

.quick-start {
  text-align: right;
  font-size: 15px;
  color: #409EFF;
  cursor: pointer;
  margin-top: 30px;
}

/* 淡入动画 */
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