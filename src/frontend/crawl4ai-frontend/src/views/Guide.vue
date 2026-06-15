<template>
  <div class="guide-page">
    <h2 class="page-title">操作指南</h2>

    <!-- 操作指南四个卡片，两列两行 -->
    <transition-group name="fade" tag="div" class="card-row two-column">
      <div class="guide-card" v-for="item in guideSections" :key="item.title">
        <div class="card-header">
          <el-icon :size="28"><component :is="item.icon" /></el-icon>
          <h3>{{ item.title }}</h3>
        </div>
        <div class="card-body">
          <p>{{ item.content }}</p>
        </div>
      </div>
    </transition-group>

    <!-- 常见问题卡片 -->
    <h2 class="page-title">常见问题</h2>
    <transition-group name="fade" tag="div" class="faq-row">
      <div class="guide-card" v-for="(q, index) in faqList" :key="index">
        <div class="card-header">
          <el-icon :size="22"><component :is="faqIcon" /></el-icon>
          <h3>问题 {{ index + 1 }}</h3>
        </div>
        <div class="card-body">
          <p class="faq-question">{{ q.question }}</p>
          <p class="faq-answer">{{ q.answer }}</p>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script>
import { Guide, Folder, Plus, List, QuestionFilled } from '@element-plus/icons-vue'

export default {
  name: 'GuidePage',
  data() {
    return {
      guideSections: [
        { title: '快速开始', icon: Guide, content: '登录成功后，您可以通过左侧导航栏进入不同的功能模块，例如首页、模板管理、新建模板和任务监控。' },
        { title: '模板管理', icon: Folder, content: '在“模板页面”中，您可以查看已有的模板，进行编辑或删除操作。' },
        { title: '新建模板', icon: Plus, content: '点击“新建模板”可以创建新的采集任务模板，配置采集规则和参数。' },
        { title: '任务监控', icon: List, content: '在“任务监控”中，您可以查看采集任务的执行状态，监控进度并查看结果。' }
      ],
      faqList: [
        { question: '如何退出登录？', answer: '点击右上角用户头像，选择“退出登录”。' },
        { question: '如何修改密码？', answer: '后续会在用户菜单中提供“修改密码”功能。' },
        { question: '如何联系管理员？', answer: '请通过系统提供的反馈渠道。' }
      ],
      faqIcon: QuestionFilled
    }
  }
}
</script>

<style scoped>
.guide-page {
  padding: 20px 60px 60px;  /* 上方缩小，下方留白 */
  min-height: 100vh;
  box-sizing: border-box;
  position: relative;
}

/* 页面底部统一留白 */
.guide-page::after {
  content: "";
  display: block;
  height: 40px; /* 调小底部留白 */
}

.page-title {
  font-size: 24px;
  font-weight: bold;
  text-align: center;
  margin: 20px 0 25px;
  color: #333;
  letter-spacing: 1px;
}

/* 操作指南卡片区：两列两行 */
.card-row.two-column {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 50px;
  margin-bottom: 70px;
}

.guide-card {
  background: #fff;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.06);
  transition: transform 0.3s, box-shadow 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center; 
  justify-content: center;
  text-align: center;
  min-height: 150px;
}

.guide-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 18px rgba(0,0,0,0.12);
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.card-header h3 {
  font-size: 17px;
  font-weight: 600;
  color: #333;
}

.card-body p {
  font-size: 14px;
  color: #555;
  line-height: 1.6;
}

/* 常见问题卡片区：三卡片一行 */
.faq-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 50px;
  margin-bottom: 40px; /* FAQ 与底部留白叠加，保证空间 */
}

.faq-question {
  font-size: 15px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
  text-align: center;
}

.faq-answer {
  font-size: 14px;
  color: #555;
  text-align: justify;
  line-height: 1.6;
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



