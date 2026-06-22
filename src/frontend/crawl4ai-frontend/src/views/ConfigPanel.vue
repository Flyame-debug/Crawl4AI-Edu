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
            rows="3"
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
import { CopyDocument } from '@element-plus/icons-vue'
import { generateRules } from '@/api/ai' 
import { startTask, getTaskPreview } from '@/api/tasks'

export default {
  name: 'ConfigPanel',
  components: { CopyDocument },
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
        timeout: 30
      },
      aiConfig: {
        enabled: true,
        provider: 'ollama',
        model: 'qwen2:7b',
        endpoint: 'http://localhost:11434',
        apiKey: '',
        prompts: []
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
    },
    toggleAdvanced() {
      this.advancedOpen = !this.advancedOpen
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
      const valid = await this.$refs.configForm.validate().catch(() => false)
      if (!valid) {
        this.$message.error('请填写所有必填项')
        return
      }
      this.submitting = true
      try {
            // ========== 新增：AI 生成规则 ==========
    // 如果有提取指令且 AI 开启，调用规则生成接口
    if (this.aiConfig.enabled && this.aiConfig.prompts.length > 0) {
      try {
        // 需要获取页面骨架（从目标网址获取），这里先用占位
        // 实际应该先抓取页面获取 HTML 骨架
        const skeleton = await this.fetchHtmlSkeleton(this.config.targetUrls)
        
        const ruleRes = await generateRules({
          user_prompt: this.aiConfig.prompts.join('\n'),
          html_skeleton: skeleton,
          ai_model: this.aiConfig.model,
          ai_api_url: this.aiConfig.endpoint
        })
        
        if (ruleRes.data.code === 200) {
          // 把生成的规则存入 advancedCode
          const ruleContent = ruleRes.data.data.rule_content
          this.advancedCode = ruleContent
          this.$message.success('AI 规则生成成功')
        }
      } catch (ruleError) {
        console.warn('AI 规则生成失败，使用默认规则:', ruleError)
        // 不阻塞流程
      }
    }
    // ======================================
        // 严格对齐接口文档：POST /api/tasks/start/ 只需6个字段
        const payload = {
          template_id: this.template.id || null,
          task_type: 'preview',
          user_prompt: this.aiConfig.prompts.join('\n'),
          ai_model: this.aiConfig.model,
          ai_api_url: this.aiConfig.endpoint,
          ai_api_key: this.aiConfig.apiKey,
          generated_rule: this.advancedCode  // ← 把生成的规则传给后端
        }
        const res = await startTask(payload)
        if (res.data.code === 200) {
          this.$message.success('预览采集任务已启动')
          this.previewVisible = true
          const taskId = res.data.data.task_id
          this.fetchPreviewData(taskId)
        } else {
          this.$message.error(res.data.msg || '启动失败')
        }
      } catch (error) {
        console.error('启动预览采集失败：', error)
        this.$message.error('启动失败，请稍后重试')
        this.previewVisible = true
        this.previewData = [
          { title: '示例数据', url: 'http://example.com', status: '成功' }
        ]
      } finally {
        this.submitting = false
      }
    },

    // 获取目标页面的 HTML 骨架（用于 AI 生成规则）
async fetchHtmlSkeleton(url) {
  try {
    // 方法1：通过后端代理获取页面内容
    const response = await fetch(`/api/proxy/html?skeleton=true&url=${encodeURIComponent(url)}`)
    if (response.ok) {
      const data = await response.json()
      return data.skeleton || '<div>示例页面结构</div>'
    }
  } catch (e) {
    console.warn('获取页面骨架失败:', e)
  }
  
  // 备用：返回一个简单的骨架
  return `<div class="teacher-info">
    <h3 class="name">姓名</h3>
    <span class="title">职称</span>
    <span class="email">邮箱</span>
  </div>`
},
    async fetchPreviewData(taskId) {
  this.previewLoading = true
  try {
    // 导入 getTaskPreview
    const { getTaskPreview } = await import('@/api/tasks')
    const limit = 10
    const previewRes = await getTaskPreview(taskId, limit)
    
    if (previewRes.data.code === 200) {
      const data = previewRes.data.data
      const previewList = data.preview || []
      
      // 转换为表格显示格式
      this.previewData = previewList.map(item => ({
        title: item.name || item.title || item.url || '未命名',
        url: item.url || '',
        status: item.extracted_data ? '成功' : '待清洗'
      }))
      
      // 显示总数
      if (data.total !== undefined) {
        this.$message.info(`共采集 ${data.total} 条预览数据`)
      }
    } else {
      this.$message.warning('暂无预览数据')
    }
  } catch (error) {
    console.error('获取预览数据失败：', error)
    this.previewData = []
  } finally {
    this.previewLoading = false
  }
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
</style>