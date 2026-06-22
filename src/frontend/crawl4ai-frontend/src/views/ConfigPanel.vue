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

    <!-- 预览弹窗（Markdown 渲染） -->
    <el-dialog v-model="previewVisible" title="采集预览" width="60%" :close-on-click-modal="false">
      <div v-if="previewLoading" v-loading="previewLoading" style="min-height: 100px;"></div>
      <div v-else class="markdown-body" v-html="previewHtml"></div>
      <template #footer>
        <el-button @click="resetConfig">重新配置</el-button>
        <el-button type="primary" @click="continueCollect">继续</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { CopyDocument } from '@element-plus/icons-vue'
import { startTask, getTaskPreview } from '@/api/tasks'
import { marked } from 'marked'

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
      previewHtml: '',   // 替换原来的 previewData
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
        const payload = {
          template_id: this.template.id || null,
          task_type: 'preview',
          user_prompt: this.aiConfig.prompts.join('\n'),
          ai_model: this.aiConfig.model,
          ai_api_url: this.aiConfig.endpoint,
          ai_api_key: this.aiConfig.apiKey
        }
        const res = await startTask(payload)
        if (res.data.code === 200) {
          this.$message.success('预览采集任务已启动')
          this.previewVisible = true
          // 尝试直接从响应中获取 extracted_data
          const extracted = res.data.data?.extracted_data || ''
          if (extracted && typeof extracted === 'string') {
            this.previewHtml = marked(extracted)
          } else {
            // 否则调用预览接口获取（传入 task_id 或 id）
            const taskId = res.data.data?.task_id || res.data.data?.id
            if (taskId) {
              await this.fetchPreviewData(taskId)
            } else {
              this.previewHtml = '<p>未获取到任务ID，无法显示预览</p>'
            }
          }
        } else {
          this.$message.error(res.data.msg || '启动失败')
        }
      } catch (error) {
        console.error('启动预览采集失败：', error)
        this.$message.error('启动失败，显示示例数据')
        this.previewVisible = true
        this.previewHtml = marked('### 示例采集结果\n\n- 标题：示例数据\n- 网址：http://example.com')
      } finally {
        this.submitting = false
      }
    },
    async fetchPreviewData(taskId) {
      this.previewLoading = true
      try {
        const res = await getTaskPreview(taskId, 10) // 后端限制10行
        if (res.data.code === 200) {
          const extracted = res.data.data?.extracted_data || ''
          if (extracted && typeof extracted === 'string') {
            this.previewHtml = marked(extracted)
          } else {
            this.previewHtml = '<p>暂无预览数据</p>'
          }
        } else {
          this.previewHtml = '<p>获取预览失败</p>'
        }
      } catch (error) {
        console.error('获取预览数据失败：', error)
        this.previewHtml = '<p>获取预览失败</p>'
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

/* 新增：Markdown 渲染样式 */
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
</style>