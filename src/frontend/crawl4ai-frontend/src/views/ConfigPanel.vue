<template>
  <div class="config-panel">
    <!-- 基础配置区（必填） -->
    <div class="section-title">基础配置区（必填）</div>
    <el-card class="config-card" shadow="hover">
      <el-form ref="configForm" label-position="top" :model="config" :rules="rules" class="form-block">
        <el-form-item label="目标网址" prop="targetUrls">
          <el-input
            type="textarea"
            v-model="config.targetUrls"
            placeholder="支持单行或多行批量导入"
            :rows="3"
          />
        </el-form-item>
        <el-form-item label="页面渲染" prop="renderPage">
          <el-switch v-model="config.renderPage" />
        </el-form-item>
        <el-form-item label="等待加载（秒）" prop="waitTime">
          <el-input-number v-model="config.waitTime" :min="0" />
        </el-form-item>
        <el-form-item label="缓存开关">
          <el-switch v-model="config.cacheEnabled" active-text="开启" inactive-text="关闭" />
        </el-form-item>
        <el-form-item label="超时时间">
          <div class="timeout-row">
            <el-switch v-model="config.timeoutEnabled" />
            <el-input-number v-if="config.timeoutEnabled" v-model="config.timeout" :min="1" />
          </div>
        </el-form-item>
        <el-form-item label="保留原始数据">
          <el-switch v-model="config.keepRawData" active-text="是" inactive-text="否" />
          <span class="hint">开启后，采集结果将同时保留清洗前的原始内容</span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- AI提取配置（可选） -->
    <div class="section-title">AI提取配置（可选）</div>
    <el-card class="config-card" shadow="hover">
      <el-switch v-model="aiConfig.enabled" active-text="开启" inactive-text="关闭" />
      <el-form v-if="aiConfig.enabled" label-position="top" :model="aiConfig" class="form-block">
        <el-form-item label="服务商选择">
          <el-select v-model="aiConfig.provider" class="dark-select">
            <el-option label="ollama" value="ollama" />
            <el-option label="deepseek" value="deepseek" />
            <el-option label="openai" value="openai" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称">
          <el-select v-model="aiConfig.model" filterable allow-create default-first-option>
            <el-option label="qwen2:7b" value="qwen2:7b" />
            <el-option label="gpt-4" value="gpt-4" />
            <el-option label="deepseek-coder" value="deepseek-coder" />
          </el-select>
        </el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="aiConfig.endpoint" />
        </el-form-item>
        <el-form-item label="API KEY（可选）">
          <el-input v-model="aiConfig.apiKey" />
        </el-form-item>
        <el-form-item label="提取指令">
          <div v-for="(cmd, index) in aiConfig.prompts" :key="index" class="prompt-row">
            <el-input v-model="aiConfig.prompts[index]" placeholder="输入指令" />
            <el-button type="text" @click="removePrompt(index)">删除</el-button>
          </div>
          <el-button type="primary" size="small" @click="addPrompt">新增指令</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 高级代码配置（可选） -->
    <div class="section-title">高级代码配置（可选）</div>
    <el-card class="config-card" shadow="hover">
      <el-button type="primary" @click="toggleAdvanced">
        {{ advancedOpen ? '关闭高级配置' : '打开高级配置' }}
      </el-button>
      <div v-if="advancedOpen" class="editor-box">
        <div class="editor-header">
          <span class="lang-label">Python</span>
          <el-button type="text" size="small" @click="copyCode">
            <el-icon><CopyDocument /></el-icon>
          </el-button>
        </div>
        <el-input
          type="textarea"
          v-model="advancedCode"
          class="code-editor"
          :rows="12"
        />
      </div>
    </el-card>

    <!-- 操作按钮区 -->
    <div class="actions">
      <div v-if="generating" class="generating-status">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>🤖 AI正在分析网页结构并生成规则...</span>
        <span class="hint-text">（可能需要30-60秒，请耐心等待）</span>
      </div>
      <el-button type="primary" @click="previewCollect" :loading="submitting">
        {{ submitting ? '提交中...' : '开始预览采集' }}
      </el-button>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog 
      v-model="previewVisible" 
      title="采集预览" 
      width="60%" 
      :close-on-click-modal="false"
      @close="handleDialogClose"
    >
      <!-- 加载等待界面 -->
      <div v-if="previewLoading" class="preview-loading">
        <div class="loading-spinner">
          <el-icon class="is-loading" size="32"><Loading /></el-icon>
        </div>
        <div class="loading-text">
          <h3>🤖 正在执行预览采集</h3>
          <p>{{ loadingStatus }}</p>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: loadingProgress + '%' }"></div>
          </div>
          <p class="progress-text">{{ loadingProgress }}% ({{ loadingAttempts }}/30)</p>
          <p class="hint-text">⏳ 正在抓取页面内容，请耐心等待...</p>
        </div>
      </div>
      
      <!-- 结果展示 -->
      <div v-else class="markdown-body" v-html="previewHtml"></div>
      
      <!-- 预览弹窗 footer -->
<template #footer>
  <!-- 重新配置 -->
  <el-button @click="handleResetConfig" :loading="stoppingPreview">
    {{ stoppingPreview ? '正在停止...' : '重新配置' }}
  </el-button>
  
  <!-- ✅ 正式采集（原"继续"按钮） -->
  <el-button 
    type="primary" 
    @click="continueCollect" 
    :disabled="!hasPreviewData || formalCollecting"
    :loading="formalCollecting"
    size="large"
  >
    {{ formalCollecting ? '采集中...' : '🚀 正式采集' }}
  </el-button>
</template>
    </el-dialog>
  </div>
</template>

<script>
import { CopyDocument, Loading } from '@element-plus/icons-vue'
import { generateRules } from '@/api/ai'
import { startTask, getTaskPreview, stopTask ,getTasks } from '@/api/tasks'
import { marked } from 'marked'

export default {
  name: 'ConfigPanel',
  components: { CopyDocument, Loading },
  props: {
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      formalCollecting: false,
      config: {
        targetUrls: '',
        renderPage: true,
        waitTime: 3,
        cacheEnabled: false,
        timeoutEnabled: false,
        keepRawData: false,
        timeout: 30
      },
      aiConfig: {
        enabled: true,
        provider: 'ollama',
        model: 'qwen2:7b',
        endpoint: 'http://localhost:11434',
        apiKey: '',
        prompts: ['提取教师姓名、职称、研究方向、邮箱']
      },
      advancedCode: `# 示例代码
import requests

def fetch_data(url):
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.text
    else:
        return None`,
      advancedOpen: false,
      previewVisible: false,
      previewLoading: false,
      previewHtml: '',
      submitting: false,
      generating: false,
      _generating: false,
      stoppingPreview: false,
      currentTaskId: null,
      loadingStatus: '⏳ 正在启动爬虫...',
      loadingProgress: 0,
      loadingAttempts: 0,
      hasPreviewData: false,
      rules: {
        targetUrls: [{ required: true, message: '请输入目标网址', trigger: 'blur' }],
        renderPage: [{ required: true, message: '请选择页面渲染方式', trigger: 'change' }],
        waitTime: [{ required: true, message: '请输入等待时间', trigger: 'blur' }]
      }
    }
  },
  watch: {
    template: {
      handler(newVal) {
        if (newVal && newVal.id) {
          this.fillFormFromTemplate(newVal)
        }
      },
      immediate: true,
      deep: true
    }
  },
  computed: {
  previewDataCount() {
    // 从预览数据中统计
    return this.hasPreviewData ? this.previewData?.length || 0 : 0
  }
},
  methods: {
    fillFormFromTemplate(tpl) {
      if (tpl.seed_url) this.config.targetUrls = tpl.seed_url
      if (tpl.need_render !== undefined) this.config.renderPage = tpl.need_render
      if (tpl.wait_load !== undefined) this.config.waitTime = tpl.wait_load
      if (tpl.enable_cache !== undefined) this.config.cacheEnabled = tpl.enable_cache
      if (tpl.timeout) {
        this.config.timeoutEnabled = true
        this.config.timeout = tpl.timeout
      }
      if (tpl.ai_enabled !== undefined) this.aiConfig.enabled = tpl.ai_enabled
      if (tpl.ai_provider) this.aiConfig.provider = tpl.ai_provider
      if (tpl.ai_model) this.aiConfig.model = tpl.ai_model
      if (tpl.ai_api_url) this.aiConfig.endpoint = tpl.ai_api_url
      if (tpl.ai_api_key) this.aiConfig.apiKey = tpl.ai_api_key
      if (tpl.user_prompt) this.aiConfig.prompts = [tpl.user_prompt]
      if (tpl.crawler_rule) {
        this.advancedCode = tpl.crawler_rule
        console.log('✅ 加载已有规则:', tpl.crawler_rule.substring(0, 100) + '...')
      }
      if (tpl.keep_raw_data !== undefined) this.config.keepRawData = tpl.keep_raw_data
    },

    toggleAdvanced() {
      this.advancedOpen = !this.advancedOpen
    },

    // ===== AI 自动生成规则 =====
    async autoGenerateScript() {
      if (this._generating) {
        console.log('⏸ 正在生成中，请等待...')
        return
      }
      this.generating = true
      this._generating = true
      this.$message({
        message: '🤖 AI正在生成规则，请稍候...',
        type: 'info',
        duration: 0
      })
      try {
        const validPrompts = this.aiConfig.prompts.filter(p => p.trim())
        if (!this.aiConfig.enabled || validPrompts.length === 0) {
          this.$message.warning('请先开启AI并填写提取指令')
          return
        }
        if (!this.config.targetUrls) {
          this.$message.warning('请先填写目标网址')
          return
        }
        console.log('🔄 调用 AI 生成脚本...')
        const skeleton = await this.fetchHtmlSkeleton(this.config.targetUrls)
        const ruleRes = await generateRules({
          user_prompt: validPrompts.join('\n'),
          html_skeleton: skeleton,
          ai_model: this.aiConfig.model,
          ai_api_url: this.aiConfig.endpoint,
          template_id: this.template.id || null
        })
        this.$message.closeAll()
        if (ruleRes.data && ruleRes.data.code === 200) {
          const ruleContent = ruleRes.data.data.rule_content
          this.advancedCode = ruleContent
          this.$emit('rule-generated', ruleContent)
          if (this.template.id) {
            await this.saveRuleToTemplate(this.template.id, ruleContent)
          }
          this.$message.success('AI 规则生成成功！')
        } else {
          this.$message.warning('AI规则生成失败，请检查服务是否运行')
        }
      } catch (error) {
        console.error('❌ AI 规则生成失败:', error)
        this.$message.error('AI规则生成失败: ' + (error.message || '未知错误'))
      } finally {
        this.generating = false
        this._generating = false
      }
    },

    async fetchHtmlSkeleton(url) {
      try {
        const apiUrl = '/api/proxy/html/?skeleton=true&url=' + encodeURIComponent(url)
        console.log('🔗 请求HTML骨架:', apiUrl)
        const response = await fetch(apiUrl, {
          headers: { 'Authorization': 'Bearer ' + (localStorage.getItem('token') || '') }
        })
        if (response.ok) {
          const data = await response.json()
          console.log('📄 HTML骨架响应:', data)
          if (data.data && data.data.skeleton) {
            const skeleton = this.extractSkeleton(data.data.skeleton)
            return skeleton
          }
        }
      } catch (e) {
        console.warn('获取页面骨架失败:', e)
      }
      return this.getDefaultSkeleton()
    },

    extractSkeleton(html) {
      const parser = new DOMParser()
      const doc = parser.parseFromString(html, 'text/html')
      function cleanNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
          return node.textContent.trim() ? '[text]' : ''
        }
        if (node.nodeType === Node.ELEMENT_NODE) {
          const attrs = []
          if (node.className) attrs.push(`class="${node.className}"`)
          if (node.id) attrs.push(`id="${node.id}"`)
          const attrStr = attrs.length ? ' ' + attrs.join(' ') : ''
          const children = Array.from(node.childNodes).map(cleanNode).filter(Boolean)
          if (children.length === 0) return `<${node.tagName.toLowerCase()}${attrStr}/>`
          return `<${node.tagName.toLowerCase()}${attrStr}>${children.join('')}</${node.tagName.toLowerCase()}>`
        }
        return ''
      }
      return cleanNode(doc.body) || this.getDefaultSkeleton()
    },

    getDefaultSkeleton() {
      return `<div class="teacher-info">
    <h3 class="name">姓名</h3>
    <span class="title">职称</span>
    <span class="department">院系</span>
    <span class="email">邮箱</span>
    <div class="research">研究方向</div>
  </div>`
    },

    generateRule() {
      console.log('🔄 generateRule 被调用')
      if (!this.aiConfig.enabled) {
        this.$message.warning('请先开启AI提取配置')
        return
      }
      if (this.aiConfig.prompts.filter(p => p.trim()).length === 0) {
        this.$message.warning('请填写至少一条提取指令')
        return
      }
      if (!this.config.targetUrls) {
        this.$message.warning('请填写目标网址')
        return
      }
      this.autoGenerateScript()
    },

    async saveRuleToTemplate(templateId, ruleContent) {
      try {
        const token = localStorage.getItem('token') || ''
        const response = await fetch('/api/templates/' + templateId + '/save_rule/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ crawler_rule: ruleContent })
        })
        const data = await response.json()
        if (data.code === 200) {
          console.log('✅ 规则已保存到模板')
          this.$emit('rule-saved', { templateId, ruleContent })
        }
      } catch (error) {
        console.warn('保存规则到模板失败:', error)
      }
    },

    copyCode() {
      navigator.clipboard.writeText(this.advancedCode)
      this.$message.success('代码已复制')
    },

    addPrompt() {
      this.aiConfig.prompts.push('')
    },

    removePrompt(index) {
      this.aiConfig.prompts.splice(index, 1)
    },

    // ===== 预览采集 =====
    async previewCollect() {
  // ✅ 检查是否有正在运行的预览任务
  const valid = await this.$refs.configForm.validate().catch(() => false)
  if (!valid) {
    this.$message.error('请填写所有必填项')
    return
  }

  // ✅ 先检查是否有正在运行的预览任务
  try {
    const res = await getTasks({ task_type: 'preview', status: 'running', include_preview: 'true' })
    if (res.data.code === 200) {
      const runningTasks = res.data.data.results || []
      if (runningTasks.length > 0) {
        await this.$confirm(
          `检测到 ${runningTasks.length} 个预览任务正在运行，是否先停止它们再重新开始？`,
          '预览任务冲突',
          { 
            type: 'warning',
            confirmButtonText: '停止并重新开始',
            cancelButtonText: '取消'
          }
        )
        // 停止所有运行中的预览任务
        for (const task of runningTasks) {
          await stopTask(task.task_id)
        }
        await new Promise(resolve => setTimeout(resolve, 2000)) // 等待停止完成
        this.$message.success('已停止所有预览任务')
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('检查预览任务失败:', error)
    } else {
      return // 用户取消
    }
  }

      this.submitting = true
      try {
        const templateId = this.template?.id || this.$route?.params?.id
        console.log('🔍 使用的模板ID:', templateId)

        const payload = {
          template_id: templateId || null,
          task_type: 'preview',
          user_prompt: this.aiConfig.prompts.join('\n'),
          ai_model: this.aiConfig.model,
          ai_api_url: this.aiConfig.endpoint,
          ai_api_key: this.aiConfig.apiKey,
          generated_rule: this.advancedCode,
          keep_raw_data: this.config.keepRawData,
          seed_url: this.config.targetUrls,
        }

        console.log('📤 启动任务请求:', JSON.stringify(payload, null, 2))
        const res = await startTask(payload)

        if (res.data && res.data.code === 200) {
          this.$message.success('预览采集任务已启动')
          this.previewVisible = true
          const taskId = res.data.data?.task_id || res.data.data?.id
          this.currentTaskId = taskId

          if (taskId) {
            await this.fetchPreviewData(taskId)
          } else {
            this.previewHtml = marked('### 示例采集结果\n\n- 未获取到任务ID')
          }
        } else {
          this.$message.error(res.data?.msg || '启动失败')
        }
      } catch (error) {
        console.error('❌ 启动预览采集失败:', error)
        this.$message.error('启动失败，请稍后重试')
        this.previewVisible = true
        this.previewHtml = marked('### 示例采集结果\n\n- 标题：示例数据\n- 网址：http://example.com')
      } finally {
        this.submitting = false
      }
    },

    async fetchPreviewData(taskId) {
  this.previewLoading = true
  this.hasPreviewData = false
  this.loadingAttempts = 0
  this.loadingProgress = 0
  this.loadingStatus = '⏳ 正在启动爬虫...'
  this.currentTaskId = taskId
  
  const maxAttempts = 30
  const maxPages = 5
  
  // ✅ 首次获取到数据后，再等几秒看有没有更多数据
  let firstDataTime = null
  const extraWaitSeconds = 3  // 首次拿到数据后再等3秒
  
  while (this.loadingAttempts < maxAttempts) {
    if (!this.previewLoading) {
      console.log('⏹️ 预览已停止，退出轮询')
      return
    }
    
    this.loadingAttempts++
    
    try {
      const res = await getTaskPreview(taskId, 10)
      console.log('📥 预览数据响应:', res)

      if (res.data && res.data.code === 200) {
        const previewList = res.data.data?.preview || []
        const total = res.data.data?.total || 0
        
        const currentPages = previewList.length
        this.loadingProgress = Math.min(Math.round((currentPages / maxPages) * 100), 90)
        
        if (currentPages > 0) {
          this.loadingStatus = `⏳ 已获取 ${currentPages} 条数据...`
          
          // ✅ 首次拿到数据，记录时间
          if (!firstDataTime) {
            firstDataTime = Date.now()
          }
          
          // ✅ 拿到数据后等 extraWaitSeconds 秒，给爬虫多一点时间
          const waited = (Date.now() - firstDataTime) / 1000
          if (waited >= extraWaitSeconds || currentPages >= maxPages) {
            this.loadingProgress = 100
            this.loadingStatus = '✅ 采集完成！'
            await new Promise(resolve => setTimeout(resolve, 300))
            this.previewHtml = this.renderPreviewData(previewList, total)
            this.hasPreviewData = true
            this.previewLoading = false
            this.$message.success(`✅ 已加载 ${previewList.length} 条预览数据`)
            return
          }
          
          this.loadingStatus = `⏳ 已获取 ${currentPages} 条，等待更多数据... (${Math.round(extraWaitSeconds - waited)}s)`
        } else {
          this.loadingStatus = `⏳ 正在抓取页面 (${this.loadingAttempts}/${maxAttempts})...`
        }
      }
      
    } catch (error) {
      console.error('❌ 获取预览数据失败:', error)
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000))
  }
  
  // 超时兜底：有数据就展示
  this.previewLoading = false
  try {
    const lastRes = await getTaskPreview(taskId, 10)
    const previewList = lastRes.data?.data?.preview || []
    if (previewList.length > 0) {
      this.previewHtml = this.renderPreviewData(previewList, lastRes.data.data?.total || 0)
      this.hasPreviewData = true
      this.$message.warning(`⚠️ 仅获取到 ${previewList.length} 条数据`)
      return
    }
  } catch (e) {}
  
  this.previewHtml = this.renderTimeoutMessage()
  this.$message.warning('预览任务超时，请检查后端日志')
},

    renderPreviewData(previewList, total) {
      let html = `### 📊 采集预览 (共 ${total || previewList.length} 条)\n\n`
      
      previewList.forEach((item, idx) => {
        html += `#### 记录 ${idx + 1}\n\n`
        html += `- **URL**: ${item.url || '未知'}\n`
        html += `- **分类**: ${item.category || '未知'}\n`
        
        const extractedData = item.extracted_data || {}
        if (extractedData.content) {
          if (extractedData.method) {
            const methodLabels = {
              'ai_ollama': '🤖 AI提取',
              'ai_ollama_fixed': '🤖 AI提取+规则修正',
              'rule_fallback': '📋 规则兜底',
              'extraction_error': '⚠️ 提取失败'
            }
            html += `- **数据来源**: ${methodLabels[extractedData.method] || extractedData.method}\n`
          }
          if (extractedData.confidence) {
            const confidenceLabels = {
              'high': '🟢 高',
              'medium': '🟡 中',
              'low': '🔴 低'
            }
            html += `- **置信度**: ${confidenceLabels[extractedData.confidence] || extractedData.confidence}\n`
          }
          html += `\n${extractedData.content}\n`
        } else {
          html += `- **数据**: 待处理\n`
        }
        html += '\n---\n\n'
      })
      
      return marked(html)
    },

    // ✅ 停止预览任务并关闭弹窗
    async handleResetConfig() {
      if (this.previewLoading && this.currentTaskId) {
        try {
          this.stoppingPreview = true
          this.$message.info('正在停止预览任务...')
          
          const res = await stopTask(this.currentTaskId)
          console.log('🛑 停止预览任务响应:', res)
          
          if (res.data.code === 200) {
            this.$message.success('预览任务已停止')
          } else {
            this.$message.warning(res.data.msg || '停止任务失败')
          }
        } catch (error) {
          console.error('❌ 停止预览任务失败:', error)
          this.$message.warning('停止任务失败，将关闭预览')
        } finally {
          this.stoppingPreview = false
          this.previewLoading = false
          this.currentTaskId = null
        }
      }
      
      this.previewVisible = false
      this.$message.info('已返回基础配置')
    },

    // ✅ 弹窗关闭时停止任务
    handleDialogClose() {
      if (this.previewLoading && this.currentTaskId) {
        this.handleResetConfig()
      } else {
        this.previewVisible = false
      }
    },

    renderTimeoutMessage() {
      return `
        <div style="text-align:center;padding:30px;">
          <div style="font-size:48px;margin-bottom:16px;">⏰</div>
          <p style="color:#E6A23C;font-size:16px;font-weight:500;">预览任务超时</p>
          <p style="color:#909399;font-size:14px;margin-top:8px;">请检查爬虫是否正常运行，或目标网站是否可访问</p>
          <p style="color:#c0c4cc;font-size:12px;margin-top:12px;">提示：可在 Django 终端查看详细日志</p>
        </div>
      `
    },

    resetConfig() {
      if (this.previewLoading && this.currentTaskId) {
        this.handleResetConfig()
      } else {
        this.previewVisible = false
        this.$message.info('已返回基础配置')
      }
    },

    // ✅ 正式采集（原 continueCollect）
  async continueCollect() {
    // 检查是否有预览数据
    if (!this.hasPreviewData) {
      this.$message.warning('请先完成预览采集')
      return
    }
    
    try {
      await this.$confirm(
        '确认启动正式采集？\n将使用当前配置采集所有数据。',
        '正式采集确认',
        { type: 'info' }
      )
      
      this.formalCollecting = true
      this.$message.info('正在启动正式采集任务...')
      
      const templateId = this.template?.id || this.$route?.params?.id
      
      const payload = {
        template_id: templateId || null,
        task_type: 'formal',  // ✅ 正式采集
        user_prompt: this.aiConfig.prompts.join('\n'),
        ai_model: this.aiConfig.model,
        ai_api_url: this.aiConfig.endpoint,
        ai_api_key: this.aiConfig.apiKey,
        generated_rule: this.advancedCode,
        keep_raw_data: this.config.keepRawData,
        config: {
          max_depth: 3,
          max_concurrent: 10
        }
      }
      
      console.log('📤 正式采集请求:', JSON.stringify(payload, null, 2))
      
      const res = await startTask(payload)
      
      if (res.data && res.data.code === 200) {
        this.$message.success('正式采集任务已启动！')
        this.previewVisible = false
        
        // ✅ 跳转到任务监控页面
        this.$router.push('/tasks')
      } else {
        this.$message.error(res.data?.msg || '启动失败')
      }
    } catch (error) {
      if (error !== 'cancel') {
        console.error('❌ 正式采集启动失败:', error)
        this.$message.error('启动失败：' + (error.message || '未知错误'))
      }
    } finally {
      this.formalCollecting = false
    }
  },
  }
}
</script>

<style scoped>
.config-panel {
  padding: 20px;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  height: 60px;
  display: flex;
  align-items: center;
  padding-left: 10px;
  margin-bottom: 10px;
}
.config-card {
  padding: 20px;
  border: 1px solid #eee;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  margin-bottom: 20px;
}
.form-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.prompt-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.timeout-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.actions {
  margin-top: 20px;
  text-align: center;
}
.editor-box {
  margin-top: 15px;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
}
.editor-header {
  background: #2d2d2d;
  color: #ccc;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  font-size: 13px;
}
.lang-label {
  font-weight: 600;
}
.editor-header .el-button {
  color: #ccc;
  font-size: 14px;
  padding: 0;
}
.code-editor ::v-deep(.el-textarea__inner) {
  width: 100%;
  height: 300px;
  background: #1e1e1e;
  color: #eee;
  font-family: monospace;
  font-size: 13px;
  line-height: 1.5;
  border: none;
  border-radius: 0;
  resize: vertical;
  padding: 10px;
  box-shadow: none;
}
.dark-select ::v-deep(.el-input__inner) {
  background-color: #1e1e1e !important;
  color: #fff !important;
  border: none !important;
}
.dark-select ::v-deep(.el-select__caret) {
  color: #fff !important;
}
.dark-select-dropdown {
  background-color: #1e1e1e !important;
  color: #fff !important;
}
.dark-select-dropdown .el-select-dropdown__item {
  background-color: #1e1e1e !important;
  color: #fff !important;
}
.generating-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 20px;
  background: #f0f7ff;
  border-radius: 8px;
  border: 1px solid #b3d8ff;
  margin-bottom: 16px;
  color: #409EFF;
}
.generating-status .el-icon {
  font-size: 24px;
  color: #409EFF;
}
.hint-text {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
.markdown-body {
  padding: 10px;
  line-height: 1.7;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 1em;
  margin-bottom: 0.5em;
}
.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
.markdown-body :deep(th) {
  background-color: #f2f2f2;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 20px;
}

.loading-spinner {
  margin-bottom: 20px;
}

.loading-text {
  text-align: center;
}

.loading-text h3 {
  color: #303133;
  font-size: 18px;
  margin: 0 0 8px 0;
}

.loading-text p {
  color: #909399;
  font-size: 14px;
  margin: 4px 0;
}

.progress-bar {
  width: 300px;
  height: 8px;
  background: #ebeef5;
  border-radius: 4px;
  margin: 12px auto;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #409EFF, #67C23A);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 13px;
  color: #909399;
}

.hint-text {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 8px !important;
}
.hint {
  font-size: 12px;
  color: #909399;
  margin-left: 6px;
}
.preview-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 16px;
}

.result-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.data-count {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.result-actions {
  display: flex;
  gap: 8px;
}

.no-data-placeholder {
  padding: 40px 0;
}
</style>