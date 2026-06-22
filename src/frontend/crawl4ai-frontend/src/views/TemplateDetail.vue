<template>
  <div class="template-detail" v-loading="loading">
    <!-- 顶部简介卡片 -->
    <el-card class="intro-card" shadow="hover">
      <h2>{{ template.name || '模板详情' }}</h2>
      <p>{{ template.description }}</p>
      <el-tag>{{ template.category || '未分类' }}</el-tag>
    </el-card>

    <div class="content-area">
      <!-- 左侧主体卡片 -->
      <div class="main-card" :class="{ shrink: codeExpanded }">
        <el-card shadow="hover">
          <el-tabs v-model="activeTab" type="card">
            <el-tab-pane label="配置" name="config">
              <!-- ✅ 添加 ref -->
              <ConfigPanel 
                ref="configPanel" 
                :template="template" 
                @rule-generated="updateRule" 
                @rule-saved="onRuleSaved"
              />
            </el-tab-pane>
            <el-tab-pane label="概述信息" name="overview">
              <OverviewPanel :template="template" />
            </el-tab-pane>
            <el-tab-pane label="任务列表" name="tasks">
              <TaskListPanel :template="template" />
            </el-tab-pane>
            <el-tab-pane label="统计" name="stats">
              <StatsPanel :template="template" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>

      <!-- 右侧代码示例 -->
      <div class="code-sidebar" :class="{ expanded: codeExpanded }">
        <div v-if="!codeExpanded" class="vertical-toggle" @click="toggleCode">
          <div class="arrow-left">
            <el-icon class="arrow-icon"><ArrowLeft /></el-icon>
            <span class="vertical-text">&lt;/&gt; 代码示例</span>
          </div>
        </div>
        <div v-else class="code-expanded">
          <div class="toolbar">
            <el-icon class="arrow-icon collapse-toggle" @click="toggleCode"><ArrowRight /></el-icon>
            <div class="selector">
              <div class="fake-select" @click="showMenu = !showMenu">
                {{ codeTab }}
                <el-icon class="caret"><ArrowDown /></el-icon>
              </div>
              <div v-if="showMenu" class="dropdown">
                <div class="item" @click="selectTab('XPath')">XPath</div>
                <div class="item" @click="selectTab('CSS')">CSS</div>
              </div>
            </div>
            <el-button type="text" class="copy-btn" @click="copyCode">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </div>
          <div class="code-box">
            <!-- ✅ 显示 AI 生成的规则 -->
            <pre v-if="codeTab === 'XPath'">{{ xpathExample || '等待AI生成规则...' }}</pre>
            <pre v-else>{{ cssExample || '等待AI生成规则...' }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ConfigPanel from './ConfigPanel.vue'
import OverviewPanel from './OverviewPanel.vue'
import TaskListPanel from './TaskListPanel.vue'
import StatsPanel from './StatsPanel.vue'
import { CopyDocument, ArrowLeft, ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { getTemplateDetail } from '@/api/templates'

export default {
  name: 'TemplateDetail',
  components: { 
    ConfigPanel, 
    OverviewPanel, 
    TaskListPanel, 
    StatsPanel, 
    CopyDocument, 
    ArrowLeft, 
    ArrowRight, 
    ArrowDown 
  },
  data() {
    return {
      activeTab: 'config',
      codeExpanded: false,
      codeTab: 'XPath',
      showMenu: false,
      template: {
        id: null,
        name: '',
        description: '',
        category: '',
        crawler_rule: '',
        seed_url: '',
        ai_model: '',
        ai_api_url: '',
        user_prompt: '',
        config: {}
      },
      loading: false,
      xpathExample: '',
      cssExample: `.course-list > div > h3`,
      hasError: false  // ✅ 新增：错误状态标志
    }
  },
  methods: {
    async fetchDetail() {
      const id = this.$route.params.id
      if (!id) {
        this.$message.warning('缺少模板ID')
        return
      }
      
      this.loading = true
      this.hasError = false  // ✅ 重置错误状态
      
      try {
        const res = await getTemplateDetail(id)
        console.log('📥 模板详情响应:', res)  // ✅ 添加日志，便于调试
        
        // ✅ 更严格的响应检查
        if (res && res.data) {
          if (res.data.code === 200) {
            // ✅ 成功获取数据
            const data = res.data.data || {}
            this.template = {
              id: data.id || id,
              name: data.name || '未命名模板',
              description: data.description || '',
              category: data.category || '未分类',
              crawler_rule: data.crawler_rule || '',
              seed_url: data.seed_url || '',
              ai_model: data.ai_model || 'qwen2:7b',
              ai_api_url: data.ai_api_url || 'http://localhost:11434',
              user_prompt: data.user_prompt || '',
              config: data.config || {},
              tags: data.tags || [],
              usage_count: data.usage_count || 0,
              created_at: data.created_at,
              updated_at: data.updated_at
            }
            
            // ✅ 如果有保存的规则，显示在右侧边栏
        if (this.template.crawler_rule) {
          this.xpathExample = this.template.crawler_rule
          console.log('✅ 加载已保存的规则:', this.xpathExample.substring(0, 100) + '...')
        }
        
        console.log('✅ 模板加载成功:', this.template.name)
        
        // ✅ 延迟同步到 ConfigPanel
        this.$nextTick(() => {
          if (this.$refs.configPanel) {
            // 如果有保存的规则，同步到高级代码框
            if (this.template.crawler_rule) {
              this.$refs.configPanel.advancedCode = this.template.crawler_rule
              console.log('✅ 同步规则到 ConfigPanel')
            }
            // 填充表单数据
            if (this.template.seed_url) {
              this.$refs.configPanel.fillFormFromTemplate(this.template)
            }
          }
        })
          } else {
            // ✅ API 返回错误码
            this.hasError = true
            console.warn('⚠️ API返回错误:', res.data.msg)
            this.$message.warning(res.data.msg || '获取模板详情失败')
            
            // ✅ 设置默认数据，但标记为错误状态
            this.template = {
              id: id,
              name: '模板加载失败',
              description: '请检查网络或联系管理员',
              category: '未知'
            }
          }
        } else {
          // ✅ 响应格式异常
          this.hasError = true
          console.warn('⚠️ 响应格式异常:', res)
          this.$message.warning('数据格式异常，请刷新重试')
        }
        
      } catch (error) {
        // ✅ 网络异常或其他错误
        this.hasError = true
        console.error('❌ 获取模板详情失败:', error)
        
        // ✅ 只在真正出错时才显示错误提示
        if (error.response) {
          // 服务器返回错误状态码
          this.$message.error(`服务器错误: ${error.response.status}`)
        } else if (error.request) {
          // 请求发出但没有收到响应
          this.$message.error('网络连接失败，请检查网络')
        } else {
          // 请求配置出错
          this.$message.error('请求配置错误，请刷新重试')
        }
        
        // ✅ 设置兜底数据，但标记为错误状态
        this.template = {
          id: id,
          name: '模板加载失败',
          description: '请刷新页面重试',
          category: '未知',
          crawler_rule: ''
        }
        
      } finally {
        this.loading = false
        
        // ✅ 延迟同步到 ConfigPanel
        this.$nextTick(() => {
          if (this.$refs.configPanel) {
            // 如果有保存的规则，同步到 ConfigPanel
            if (this.template.crawler_rule) {
              this.$refs.configPanel.advancedCode = this.template.crawler_rule
            }
            // 如果有模板数据，填充到表单
            if (this.template.seed_url) {
              this.$refs.configPanel.fillFormFromTemplate(this.template)
            }
          }
        })
      }
    },
    
     toggleCode() {
    console.log('🔄 切换代码面板，当前状态:', this.codeExpanded)
    this.codeExpanded = !this.codeExpanded
    this.showMenu = false
    
    // ✅ 展开时自动生成规则
    if (this.codeExpanded) {
      console.log('📂 代码面板已展开，准备生成规则...')
      
      // 等待 DOM 更新
      this.$nextTick(() => {
        if (this.$refs.configPanel) {
          console.log('🔍 找到 ConfigPanel 组件')
          
          // 检查 ConfigPanel 的状态
          const configPanel = this.$refs.configPanel
          console.log('📊 ConfigPanel 状态:', {
            hasUrl: !!(configPanel.config && configPanel.config.targetUrls),
            targetUrls: configPanel.config?.targetUrls,
            hasPrompts: !!(configPanel.aiConfig && configPanel.aiConfig.prompts && 
                          configPanel.aiConfig.prompts.some(p => p.trim())),
            prompts: configPanel.aiConfig?.prompts,
            aiEnabled: configPanel.aiConfig?.enabled
          })
          
          const hasUrl = configPanel.config && configPanel.config.targetUrls
          const hasPrompts = configPanel.aiConfig && 
                            configPanel.aiConfig.prompts && 
                            configPanel.aiConfig.prompts.some(p => p.trim())
          
          if (hasUrl && hasPrompts && configPanel.aiConfig.enabled) {
            console.log('🚀 触发 AI 规则生成...')
            configPanel.generateRule()
          } else {
            console.warn('⚠️ 条件不满足:', {
              hasUrl,
              hasPrompts,
              aiEnabled: configPanel.aiConfig?.enabled
            })
            this.$message.info('请先在配置面板填写目标网址、开启AI并填写提取指令')
          }
        } else {
          console.error('❌ 未找到 ConfigPanel 组件引用')
        }
      })
    } else {
      console.log('📂 代码面板已折叠')
    }
  },
    
    updateRule(rule) {
  if (!rule) {
    console.warn('⚠️ 收到空规则')
    return
  }
  
  console.log('📥 收到规则:', rule)
  
  try {
    // 尝试解析JSON
    const parsed = JSON.parse(rule)
    console.log('📥 解析后的 JSON:', parsed)
    
    // ✅ 如果是JSON对象，取第一个值作为XPath示例
    if (typeof parsed === 'object' && parsed !== null) {
      const values = Object.values(parsed)
      if (values.length > 0 && typeof values[0] === 'string') {
        this.xpathExample = values[0]
        // ✅ 尝试转换第一个XPath为CSS选择器
        this.cssExample = this.xpathToCss(values[0])
        console.log('✅ 更新 xpathExample 为:', this.xpathExample)
        console.log('✅ 更新 cssExample 为:', this.cssExample)
        this.$forceUpdate()
        return
      }
    }
  } catch (e) {
    console.log('📥 不是 JSON，直接作为 XPath')
    this.xpathExample = rule
    this.cssExample = this.xpathToCss(rule)
    this.$forceUpdate()
  }
},

// ✅ 新增：XPath转CSS选择器的方法
xpathToCss(xpath) {
  if (!xpath) return '.course-list > div > h3'
  
  let css = xpath
    // 移除 /text() 后缀
    .replace(/\/text\(\)$/, '')
    // 移除 // 前缀
    .replace(/^\/\//, '')
    // 处理 [@class='xxx'] 
    .replace(/\[@class='([^']+)'\]/g, '.$1')
    // 处理 [@id='xxx']
    .replace(/\[@id='([^']+)'\]/g, '#$1')
    // 处理 [@attr='value'] 
    .replace(/\[@([^=']+)='([^']+)'\]/g, '[$1="$2"]')
    // 将 / 替换为 > 
    .replace(/\//g, ' > ')
    // 移除多余的 > 
    .replace(/\s*>\s*>\s*/g, ' > ')
  
  // 如果结果为空，返回默认值
  return css || '.course-list > div > h3'
},
    
    onRuleSaved(data) {
      console.log('✅ 规则已保存到模板:', data)
      this.$message.success('AI规则已保存')
      // 刷新模板数据
      this.fetchDetail()
    },
    
    copyCode() {
      const text = this.codeTab === 'XPath' ? this.xpathExample : this.cssExample
      if (!text || text === '等待AI生成规则...') {
        this.$message.warning('没有可复制的代码，请先生成AI规则')
        return
      }
      navigator.clipboard.writeText(text).then(() => {
        this.$message.success('代码已复制')
      }).catch(() => {
        this.$message.error('复制失败，请手动复制')
      })
    },
    
    selectTab(tab) {
      this.codeTab = tab
      this.showMenu = false
    }
  },
  mounted() {
    this.fetchDetail()
  }
}
</script>

<style scoped>
.template-detail {
  padding: 20px;
}

.intro-card {
  border-radius: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  margin-left: auto;
  margin-right: auto;
  width: 100%;
}

.content-area {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 20px;
}

.main-card {
  flex: 1;
  display: flex;
  justify-content: center;
  transition: flex 0.3s ease;
  border-radius: 20px;
}

.main-card.shrink {
  flex: 0.7;
}

.main-card > .el-card {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  border-radius: 20px;
}

::v-deep(.el-tabs__item.is-active) {
  color: #409EFF !important;
  font-weight: 600;
  border-bottom: 3px solid #409EFF !important;
}

::v-deep(.el-tabs__item) {
  transition: all 0.3s ease;
}

::v-deep(.el-tabs__nav-wrap::after) {
  display: none;
}

/* 右侧代码示例 */
.vertical-toggle {
  background: #1e1e1e;
  border-radius: 6px;
  height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 20px;
  cursor: pointer;
  min-width: 40px;
}

.vertical-toggle:hover {
  background: #2d2d2d;
}

.arrow-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.arrow-icon {
  color: #fff;
  font-size: 18px;
  margin-bottom: 6px;
}

.vertical-text {
  writing-mode: vertical-rl;
  font-size: 11px;
  font-weight: normal;
}

.code-sidebar {
  flex: 0;
  transition: flex 0.3s ease;
}

.code-sidebar.expanded {
  flex: 0.4;
  min-width: 300px;
}

.code-expanded {
  background: #1e1e1e;
  border-radius: 14px;
  height: 500px;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
  padding: 6px 10px;
  border-bottom: 1px solid #333;
}

.collapse-toggle {
  cursor: pointer;
}

.selector {
  flex: 1;
  margin: 0 10px;
  display: flex;
  justify-content: center;
  position: relative;
}

.fake-select {
  background: #1e1e1e;
  color: #fff;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: normal;
}

.fake-select .caret {
  margin-left: 6px;
}

.dropdown {
  position: absolute;
  top: 28px;
  background: #1e1e1e;
  border-radius: 4px;
  color: #fff;
  min-width: 80px;
  z-index: 100;
}

.dropdown .item {
  padding: 6px 10px;
  cursor: pointer;
}

.dropdown .item:hover {
  background: #333;
}

.copy-btn {
  color: #fff;
}

.copy-btn:hover {
  color: #409EFF;
}

.code-box {
  flex: 1;
  background: #000;
  color: #eee;
  border-radius: 6px;
  padding: 10px;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  overflow-y: auto;
  height: 420px;
}

.code-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Courier New', monospace;
  color: #00ff00;
}
</style>