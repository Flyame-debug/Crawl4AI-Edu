<template>
  <div v-if="visible" class="tour-overlay">
    <!-- 高亮框：镂空效果 + 脉冲动画 -->
    <div v-if="targetRect" class="tour-highlight" :style="highlightStyle">
      <div class="pulse-ring"></div>
    </div>

    <!-- 提示卡片：智能避让屏幕边界 -->
    <div v-if="targetRect" class="tour-tooltip" :style="tooltipStyle" @click.stop>
      <div class="tour-step-header">
        <span class="tour-step-badge">{{ currentStep + 1 }}</span>
        <span class="tour-step-title">{{ steps[currentStep].title }}</span>
      </div>
      <div class="tour-content">{{ steps[currentStep].content }}</div>
      <div class="tour-actions">
        <el-button v-if="currentStep > 0" size="small" @click="prev">上一步</el-button>
        <el-button v-if="currentStep < steps.length - 1" type="primary" size="small" @click="next">下一步</el-button>
        <el-button v-else type="primary" size="small" @click="finish">完成</el-button>
        <el-button size="small" @click="skip">跳过</el-button>
      </div>
      <div class="tour-progress-bar">{{ currentStep + 1 }} / {{ steps.length }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AppTour',
  props: {
    steps: { type: Array, required: true }
  },
  emits: ['update-step', 'finish'],
  data() {
    return {
      visible: false,
      currentStep: 0,
      targetRect: null
    }
  },
  computed: {
    highlightStyle() {
      if (!this.targetRect) return {}
      const pad = 8
      return {
        position: 'fixed',
        top: (this.targetRect.top - pad) + 'px',
        left: (this.targetRect.left - pad) + 'px',
        width: (this.targetRect.width + pad * 2) + 'px',
        height: (this.targetRect.height + pad * 2) + 'px',
        borderRadius: '10px',
        boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.6)',
        zIndex: 9999,
        pointerEvents: 'none'
      }
    },
    tooltipStyle() {
      if (!this.targetRect) return {}
      const rect = this.targetRect
      const placement = this.steps[this.currentStep]?.placement || 'right'
      const gap = 20
      const cardWidth = 340
      const winW = window.innerWidth
      const winH = window.innerHeight

      const style = {
        position: 'fixed',
        zIndex: 10000,
        maxWidth: cardWidth + 'px'
      }

      if (placement === 'bottom') {
        style.top = (rect.bottom + gap) + 'px'
        if (rect.left + cardWidth > winW) {
          style.right = Math.max(16, winW - rect.right) + 'px'
        } else {
          style.left = Math.max(16, rect.left) + 'px'
        }
      } else if (placement === 'left') {
        style.top = (rect.top + rect.height / 2) + 'px'
        style.right = (winW - rect.left + gap) + 'px'
        style.transform = 'translateY(-50%)'
      } else if (placement === 'top') {
        style.bottom = (winH - rect.top + gap) + 'px'
        if (rect.left + cardWidth > winW) {
          style.right = Math.max(16, winW - rect.right) + 'px'
        } else {
          style.left = Math.max(16, rect.left) + 'px'
        }
      } else {
        // 默认右侧
        style.top = (rect.top + rect.height / 2) + 'px'
        style.transform = 'translateY(-50%)'
        if (rect.right + gap + cardWidth <= winW) {
          style.left = (rect.right + gap) + 'px'
        } else {
          style.right = (winW - rect.left + gap) + 'px'
          style.transform = 'translateY(-50%)'
        }
      }
      return style
    }
  },
  methods: {
    async start() {
      this.visible = true
      this.currentStep = 0
      // 强制展开侧边栏
      const sidebar = document.querySelector('.sidebar')
      if (sidebar?.classList.contains('collapsed')) {
        sidebar.classList.remove('collapsed')
      }
      await this.$nextTick()
      this.locateTarget()
      this.$emit('update-step', this.currentStep)
    },

    locateTarget() {
      const step = this.steps[this.currentStep]
      if (!step || !step.selector) return

      // 直接使用选择器（现在都是 #id 形式）
      const el = document.querySelector(step.selector)
      if (!el) {
        console.warn('未找到目标元素:', step.selector)
        // 兜底位置：侧边栏第一个菜单项附近
        this.targetRect = {
          top: 120,
          left: 200,
          width: 120,
          height: 48,
          right: 320,
          bottom: 168
        }
        return
      }

      this.targetRect = el.getBoundingClientRect()
    },

    async next() {
      if (this.currentStep < this.steps.length - 1) {
        this.currentStep++
        await this.$nextTick()
        this.locateTarget()
        this.$emit('update-step', this.currentStep)
      }
    },
    async prev() {
      if (this.currentStep > 0) {
        this.currentStep--
        await this.$nextTick()
        this.locateTarget()
        this.$emit('update-step', this.currentStep)
      }
    },
    finish() {
      this.visible = false
      this.targetRect = null
      localStorage.setItem('tour_completed', 'true')
      this.$emit('finish')
    },
    skip() {
      this.visible = false
      this.targetRect = null
      localStorage.setItem('tour_completed', 'true')
      this.$emit('finish')
    }
  }
}
</script>

<style scoped>
.tour-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9998;
  pointer-events: all;
}

.tour-highlight {
  border: 3px solid #409eff;
  background: rgba(64, 158, 255, 0.08);
  box-sizing: border-box;
  pointer-events: none;
  animation: highlightPulse 2s infinite;
}

.pulse-ring {
  position: absolute;
  top: -8px;
  left: -8px;
  right: -8px;
  bottom: -8px;
  border: 2px solid rgba(64, 158, 255, 0.5);
  border-radius: 12px;
  animation: ringPulse 2s infinite;
  pointer-events: none;
}

@keyframes highlightPulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.2); }
  50% { box-shadow: 0 0 0 12px rgba(64, 158, 255, 0); }
}

@keyframes ringPulse {
  0% { opacity: 0.8; transform: scale(1); }
  100% { opacity: 0; transform: scale(1.06); }
}

.tour-tooltip {
  background: #ffffff;
  border-radius: 18px;
  padding: 26px 28px;
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.3);
  animation: tooltipFadeIn 0.35s ease;
  color: #303133;
  pointer-events: all;
}

.tour-step-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.tour-step-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.tour-step-title {
  font-size: 19px;
  font-weight: 600;
}

.tour-content {
  font-size: 14px;
  color: #606266;
  margin-bottom: 22px;
  line-height: 1.7;
  padding-left: 48px;
}

.tour-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
  padding-left: 48px;
}

.tour-progress-bar {
  font-size: 12px;
  color: #c0c4cc;
  text-align: right;
  margin-top: 10px;
  padding-left: 48px;
}

@keyframes tooltipFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>