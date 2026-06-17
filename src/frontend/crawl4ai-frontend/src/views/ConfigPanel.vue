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
      <el-button type="primary" @click="previewCollect">开始预览采集</el-button>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" title="采集预览" width="60%">
      <div class="preview-content">
        <div class="markdown-preview">
          <p>### 假数据示例</p>
          <p>这里展示采集到的 Markdown/HTML 内容片段。</p>
        </div>
        <el-table :data="previewData" style="margin-top: 20px;">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="url" label="网址" />
          <el-table-column prop="status" label="状态" />
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

export default {
  name: 'ConfigPanel',
  components: { CopyDocument },
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
      previewData: [
        { title: '课程公告示例', url: 'http://example.com/course', status: '成功' },
        { title: '新闻示例', url: 'http://example.com/news', status: '失败' }
      ],
      rules: {
        targetUrls: [{ required: true, message: '请输入目标网址', trigger: 'blur' }],
        renderPage: [{ required: true, message: '请选择页面渲染方式', trigger: 'change' }],
        waitTime: [{ required: true, message: '请输入等待时间', trigger: 'blur' }]
      }
    }
  },
  methods: {
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
    previewCollect() {
      this.$refs.configForm.validate(valid => {
        if (valid) {
          this.previewVisible = true
        } else {
          this.$message.error('请填写所有必填项')
        }
      })
    },
    resetConfig() {
      this.previewVisible = false
      this.$message.info('已返回基础配置')
    },
    continueCollect() {
      this.previewVisible = false
      this.$message.success('继续进行整体爬取工作')
      // 跳转到任务监控界面
      this.$router.push('/tasks')
    }
  }
}
</script>


<style scoped>
.config-panel {
  padding: 20px;
}

/* 标题区域：纯文字，不加背景色或边框 */
.section-title {
  font-size: 15px;
  font-weight: 600;
  height: 60px;
  display: flex;
  align-items: center;
  padding-left: 10px;
  margin-bottom: 10px;
}

/* 内容卡片 */
.config-card {
  padding: 20px;
  border: 1px solid #eee;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  margin-bottom: 20px;
}

/* 表单区 */
.form-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 开关按钮单独一行 */
.switch-row {
  margin-bottom: 0;
}

/* 提示文字：小字，换行显示在按钮下面 */
.hint {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  display: block;
}

/* 提取指令输入行 */
.prompt-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

/* 超时时间：开关和输入框分隔 */
.timeout-row {
  display: flex;
  align-items: center;
  gap: 12px; /* 开关和输入框隔开一点 */
}

/* 操作按钮区 */
.actions {
  margin-top: 20px;
  text-align: center;
}

/* 预览弹窗中的 Markdown 区域 */
.markdown-preview {
  background: #f5f5f5;
  padding: 10px;
  margin-bottom: 10px;
}

/* 高级代码编辑器整体容器 */
.editor-box {
  margin-top: 15px;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
}

/* 编辑器顶部工具栏 */
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

/* 可编辑代码区（el-input textarea） */
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

/* AI配置下拉框黑色风格 */
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

