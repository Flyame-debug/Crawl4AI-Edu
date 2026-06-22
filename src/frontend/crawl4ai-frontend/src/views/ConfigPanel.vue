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

        <!-- 页面渲染：只保留开关 -->
        <el-form-item label="页面渲染" prop="renderPage">
          <el-switch v-model="config.renderPage" />
        </el-form-item>

        <el-form-item label="等待加载（秒）" prop="waitTime">
          <el-input-number v-model="config.waitTime" :min="0" />
        </el-form-item>

        <el-form-item label="缓存开关">
          <el-switch v-model="config.cacheEnabled" active-text="开启" inactive-text="关闭" />
        </el-form-item>

        <!-- 超时时间：开关 + 输入框 -->
        <el-form-item label="超时时间">
          <div class="timeout-row">
            <el-switch v-model="config.timeoutEnabled" />
            <el-input-number v-if="config.timeoutEnabled" v-model="config.timeout" :min="1" />
          </div>
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
        <!-- 多条提取指令 -->
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
      <!-- ✅ 新增：生成中的进度提示 -->
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
    <el-dialog v-model="previewVisible" title="采集预览" width="60%">
      <div class="preview-content" v-loading="previewLoading">
        <div class="markdown-preview">
          <p v-if="previewData.length === 0 && !previewLoading">暂无预览数据</p>
          <p v-for="(item, idx) in previewData" :key="idx">### {{ item.title }}</p>
        </div>
        <el-table :data="previewData" style="margin-top: 20px;">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="url" label="网址" />
          <el-table-column prop="status" label="状态">
            <template #default="scope">
              <el-tag :type="scope.row.status === '成功' ? 'success' : 'danger'">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="resetConfig">重新配置</el-button>
        <el-button type="primary" @click="continueCollect">继续</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { CopyDocument,Loading } from '@element-plus/icons-vue'
import { generateRules } from '@/api/ai' 
import { startTask, getTaskPreview } from '@/api/tasks'

export default {
  name: 'ConfigPanel',
  components: { CopyDocument,Loading },
  props: {
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      config: {
        targetUrls: '',
        renderPage: true,
        waitTime: 3,
        cacheEnabled: false,
        timeoutEnabled: false,
        timeout: 30,
        generating: false,  // 规则生成中状态
      },
      aiConfig: {
        enabled: true,
        provider: 'ollama',
        model: 'qwen2:7b',
        endpoint: 'http://localhost:11434',
        apiKey: '',
        prompts: ['提取教师姓名、职称、研究方向、邮箱']  // ✅ 添加默认指令
      },
      advancedCode: `# 示例假代码
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
      previewData: [],
      submitting: false,
      _generating: false,
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
  methods: {
    fillFormFromTemplate(tpl) {
      if (tpl.seed_url) {
        this.config.targetUrls = tpl.seed_url
      }
      if (tpl.need_render !== undefined) {
        this.config.renderPage = tpl.need_render
      }
      if (tpl.wait_load !== undefined) {
        this.config.waitTime = tpl.wait_load
      }
      if (tpl.enable_cache !== undefined) {
        this.config.cacheEnabled = tpl.enable_cache
      }
      if (tpl.timeout) {
        this.config.timeoutEnabled = true
        this.config.timeout = tpl.timeout
      }
      if (tpl.ai_enabled !== undefined) {
        this.aiConfig.enabled = tpl.ai_enabled
      }
      if (tpl.ai_provider) {
        this.aiConfig.provider = tpl.ai_provider
      }
      if (tpl.ai_model) {
        this.aiConfig.model = tpl.ai_model
      }
      if (tpl.ai_api_url) {
        this.aiConfig.endpoint = tpl.ai_api_url
      }
      if (tpl.ai_api_key) {
        this.aiConfig.apiKey = tpl.ai_api_key
      }
      if (tpl.user_prompt) {
        this.aiConfig.prompts = [tpl.user_prompt]
      }
      if (tpl.crawler_rule) {
        this.advancedCode = tpl.crawler_rule
        console.log('✅ fillFormFromTemplate 加载规则:', tpl.crawler_rule.substring(0, 100) + '...')
      }
    },
    
    toggleAdvanced() {
      this.advancedOpen = !this.advancedOpen
    },
    
    async autoGenerateScript() {
  if (this._generating) {
    console.log('⏸ 正在生成中，请等待...')
    return
  }
  // ✅ 设置生成中状态
  this.generating = true
  this.$message({
    message: '🤖 AI正在生成规则，请稍候...',
    type: 'info',
    duration: 0  // 不自动关闭
  })
  
  this._generating = true
  try {
    const validPrompts = this.aiConfig.prompts.filter(function(p) {
      return p.trim()
    })
    
    console.log('🔍 AI配置状态:', {
      enabled: this.aiConfig.enabled,
      prompts: validPrompts,
      model: this.aiConfig.model,
      endpoint: this.aiConfig.endpoint
    })
    
    if (!this.aiConfig.enabled || validPrompts.length === 0) {
      console.warn('⏸ AI未开启或没有提取指令')
      this.$message.warning('请先开启AI并填写提取指令')
      return
    }
    
    if (!this.config.targetUrls) {
      console.warn('⏸ 没有目标网址')
      this.$message.warning('请先填写目标网址')
      return
    }
    
    console.log('🔄 调用 AI 生成脚本...')
    console.log('📝 提取指令:', validPrompts)
    console.log('🌐 目标网址:', this.config.targetUrls)
    
    const skeleton = await this.fetchHtmlSkeleton(this.config.targetUrls)
    console.log('📄 获取到的HTML骨架:', skeleton.substring(0, 200) + '...')
    
    const ruleRes = await generateRules({
      user_prompt: validPrompts.join('\n'),
      html_skeleton: skeleton,
      ai_model: this.aiConfig.model,
      ai_api_url: this.aiConfig.endpoint,
      template_id: this.template.id || null
    })
    
    console.log('📥 AI规则生成响应:', ruleRes)
     // ✅ 关闭加载提示
    this.$message.closeAll()

    if (ruleRes.data && ruleRes.data.code === 200) {
      const ruleContent = ruleRes.data.data.rule_content
      console.log('✅ AI 规则生成成功:', ruleContent)
      
      // 更新高级代码框
      this.advancedCode = ruleContent
      
      // 通知父组件更新右侧边栏
      this.$emit('rule-generated', ruleContent)
      
      // 保存到模板
      if (this.template.id) {
        await this.saveRuleToTemplate(this.template.id, ruleContent)
      }
      
      this.$message.success('AI 规则生成成功！')
    } else {
      console.warn('⚠️ AI规则生成返回异常:', ruleRes)
      this.$message.warning('AI规则生成失败，请检查Ollama服务是否运行')
    }
  } catch (error) {
    console.error('❌ AI 规则生成失败:', error)
    this.$message.error('AI规则生成失败: ' + (error.message || '未知错误'))
  } finally {
    this._generating = false
  }
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
          this.$emit('rule-saved', { templateId: templateId, ruleContent: ruleContent })
        }
      } catch (error) {
        console.warn('保存规则到模板失败:', error)
      }
    },
    
    // 在 ConfigPanel.vue 中
generateRule() {
  console.log('🔄 generateRule 被调用')
  
  // 检查条件
  const validPrompts = this.aiConfig.prompts.filter(function(p) {
    return p.trim()
  })
  
  console.log('📊 generateRule 检查:', {
    validPrompts: validPrompts,
    targetUrls: this.config.targetUrls,
    aiEnabled: this.aiConfig.enabled
  })
  
  if (!this.aiConfig.enabled) {
    console.warn('⏸ AI未开启')
    this.$message.warning('请先开启AI提取配置')
    return
  }
  
  if (validPrompts.length === 0) {
    console.warn('⏸ 没有提取指令')
    this.$message.warning('请填写至少一条提取指令')
    return
  }
  
  if (!this.config.targetUrls) {
    console.warn('⏸ 没有目标网址')
    this.$message.warning('请填写目标网址')
    return
  }
  
  console.log('✅ 条件满足，开始生成规则...')
  this.autoGenerateScript()
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
    
    async previewCollect() {
  try {
    const valid = await this.$refs.configForm.validate()
    if (!valid) {
      this.$message.error('请填写所有必填项')
      return
    }
  } catch (error) {
    this.$message.error('请填写所有必填项')
    return
  }
  
  this.submitting = true
  try {
    const payload = {
      template_id: this.template.id || null,
      task_type: 'preview',
      user_prompt: this.aiConfig.prompts.join('\n'),
      ai_model: this.aiConfig.model,
      ai_api_url: this.aiConfig.endpoint,
      ai_api_key: this.aiConfig.apiKey,
      generated_rule: this.advancedCode
    }
    
    console.log('📤 启动任务请求:', payload)
    
    const res = await startTask(payload)
    console.log('📥 启动任务响应:', res)
    
    if (res.data && res.data.code === 200) {
      this.$message.success('预览采集任务已启动')
      this.previewVisible = true
      const taskId = res.data.data.task_id
      
      if (taskId) {
        await this.fetchPreviewData(taskId)  // ✅ 调用新方法
      } else {
        this.$message.warning('任务已启动，但未返回任务ID')
        this.previewData = [
          { title: '示例数据1', url: 'https://example.com/1', status: '待清洗' },
          { title: '示例数据2', url: 'https://example.com/2', status: '待清洗' }
        ]
      }
    } else {
      this.$message.error(res.data?.msg || '启动失败')
    }
  } catch (error) {
    console.error('❌ 启动预览采集失败:', error)
    this.$message.error('启动失败，请稍后重试')
    this.previewVisible = true
    this.previewData = [
      { title: '示例数据1', url: 'http://example.com/1', status: '待清洗' },
      { title: '示例数据2', url: 'http://example.com/2', status: '待清洗' }
    ]
  } finally {
    this.submitting = false
  }
},
    
    async fetchHtmlSkeleton(url) {
  try {
    // 使用代理获取真实网页内容
    const apiUrl = '/api/proxy/html/?skeleton=true&url=' + encodeURIComponent(url)
    console.log('🔗 请求HTML骨架:', apiUrl)
    
    const response = await fetch(apiUrl, {
      headers: {
        'Authorization': 'Bearer ' + (localStorage.getItem('token') || '')
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      console.log('📄 HTML骨架响应:', data)
      if (data.data && data.data.skeleton) {
        // 提取真实的 HTML 结构，去除文本内容
        const skeleton = this.extractSkeleton(data.data.skeleton)
        return skeleton
      }
    }
  } catch (error) {
    console.warn('获取页面骨架失败:', error)
  }
  
  // 如果失败，返回一个更好的示例结构
  return this.getDefaultSkeleton()
},
async fetchPreviewData(taskId) {
    this.previewLoading = true
    try {
      // 调用 getTaskPreview API
      const previewRes = await getTaskPreview(taskId, 10)
      console.log('📥 预览数据响应:', previewRes)
      
      if (previewRes.data && previewRes.data.code === 200) {
        const data = previewRes.data.data
        const previewList = data.preview || []
        
        this.previewData = previewList.map(function(item) {
          return {
            title: item.name || item.title || item.url || '未命名',
            url: item.url || '',
            status: item.extracted_data ? '成功' : '待清洗'
          }
        })
        
        if (data.total !== undefined) {
          this.$message.info('共采集 ' + data.total + ' 条预览数据')
        }
      } else {
        this.$message.warning('暂无预览数据')
        // 显示示例数据便于测试
        this.previewData = [
          { title: '示例数据1', url: 'https://example.com/1', status: '待清洗' },
          { title: '示例数据2', url: 'https://example.com/2', status: '待清洗' }
        ]
      }
    } catch (error) {
      console.error('❌ 获取预览数据失败:', error)
      this.$message.warning('获取预览数据失败，显示示例数据')
      this.previewData = [
        { title: '示例数据1', url: 'https://example.com/1', status: '待清洗' },
        { title: '示例数据2', url: 'https://example.com/2', status: '待清洗' }
      ]
    } finally {
      this.previewLoading = false
    }
  },
// ✅ 新增：提取 HTML 骨架（去除文本内容，保留结构）
extractSkeleton(html) {
  // 使用 DOMParser 解析 HTML
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  
  // 移除文本节点，只保留标签结构
  function cleanNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent.trim() ? '[text]' : ''
    }
    if (node.nodeType === Node.ELEMENT_NODE) {
      const attrs = []
      if (node.className) {
        attrs.push(`class="${node.className}"`)
      }
      if (node.id) {
        attrs.push(`id="${node.id}"`)
      }
      const attrStr = attrs.length ? ' ' + attrs.join(' ') : ''
      const children = Array.from(node.childNodes).map(cleanNode).filter(Boolean)
      if (children.length === 0) {
        return `<${node.tagName.toLowerCase()}${attrStr}/>`
      }
      return `<${node.tagName.toLowerCase()}${attrStr}>${children.join('')}</${node.tagName.toLowerCase()}>`
    }
    return ''
  }
  
  return cleanNode(doc.body) || this.getDefaultSkeleton()
},

// ✅ 新增：默认骨架
getDefaultSkeleton() {
  return `<div class="teacher-info">
    <h3 class="name">姓名</h3>
    <span class="title">职称</span>
    <span class="department">院系</span>
    <span class="email">邮箱</span>
    <div class="research">研究方向</div>
  </div>`
},
    resetConfig() {
      this.previewVisible = false
      this.$message.info('已返回基础配置')
    },
    
    continueCollect() {
      this.previewVisible = false
      this.$message.success('继续进行整体爬取工作')
      this.$router.push('/tasks')
    }
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

.switch-row {
  margin-bottom: 0;
}

.hint {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  display: block;
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

.markdown-preview {
  background: #f5f5f5;
  padding: 10px;
  margin-bottom: 10px;
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
</style>