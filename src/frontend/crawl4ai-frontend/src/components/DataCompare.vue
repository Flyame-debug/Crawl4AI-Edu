<template>
  <div class="data-compare">
    <!-- 标题栏 -->
    <div class="compare-header">
      <div class="header-left">
        <h3>🔍 数据清洗过程对比</h3>
        <span class="task-info">任务: {{ taskName }} | {{ taskTime }}</span>
      </div>
      <div class="header-right">
        <el-tag :type="statusType">{{ statusText }}</el-tag>
      </div>
    </div>

    <!-- 三栏对比 -->
    <el-row :gutter="16" class="compare-row">
      <!-- 第一栏：原始HTML -->
      <el-col :span="8">
        <div class="compare-panel raw-panel">
          <div class="panel-header">
            <span class="panel-title">📄 原始HTML</span>
            <div class="panel-actions">
              <el-button size="small" type="text" @click="copyContent('raw')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
              <el-tag size="small" type="info">爬虫采集</el-tag>
            </div>
          </div>
          <div class="panel-body">
            <pre v-html="highlightedRaw"></pre>
          </div>
          <div class="panel-footer">
            <span class="size-info">大小: {{ rawSize }}</span>
          </div>
        </div>
      </el-col>

      <!-- 第二栏：Markdown（清洗后） -->
      <el-col :span="8">
        <div class="compare-panel markdown-panel">
          <div class="panel-header">
            <span class="panel-title">📝 清洗后 (Markdown)</span>
            <div class="panel-actions">
              <el-button size="small" type="text" @click="copyContent('markdown')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
              <el-tag size="small" type="success">AI清洗</el-tag>
            </div>
          </div>
          <div class="panel-body markdown-body" v-html="renderedMarkdown"></div>
          <div class="panel-footer">
            <span class="size-info">行数: {{ markdownLines }}</span>
          </div>
        </div>
      </el-col>

      <!-- 第三栏：结构化数据 -->
      <el-col :span="8">
        <div class="compare-panel structured-panel">
          <div class="panel-header">
            <span class="panel-title">📊 结构化数据</span>
            <div class="panel-actions">
              <el-button size="small" type="text" @click="copyContent('structured')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
              <el-tag size="small" type="primary">最终结果</el-tag>
            </div>
          </div>
          <div class="panel-body">
            <pre v-html="highlightedStructured"></pre>
          </div>
          <div class="panel-footer">
            <span class="size-info">字段: {{ structuredFields }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 数据统计 -->
    <div class="compare-stats">
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="stat-item">
            <span class="stat-value">{{ rawLines }}</span>
            <span class="stat-label">原始行数</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item success">
            <span class="stat-value">{{ cleanLines }}</span>
            <span class="stat-label">清洗后行数</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item success">
            <span class="stat-value">{{ fieldCount }}</span>
            <span class="stat-label">提取字段</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item primary">
            <span class="stat-value">{{ compressionRate }}%</span>
            <span class="stat-label">数据压缩率</span>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 导出按钮 -->
    <div class="compare-actions">
      <el-button type="primary" @click="exportData('html')">
        <el-icon><Download /></el-icon> 导出HTML
      </el-button>
      <el-button type="success" @click="exportData('markdown')">
        <el-icon><Download /></el-icon> 导出Markdown
      </el-button>
      <el-button type="warning" @click="exportData('json')">
        <el-icon><Download /></el-icon> 导出JSON
      </el-button>
      <el-button type="info" @click="exportData('all')">
        <el-icon><Download /></el-icon> 导出全部
      </el-button>
    </div>
  </div>
</template>

<script>
import { CopyDocument, Download } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { getTaskPreview } from '@/api/tasks'
import * as XLSX from 'xlsx'

export default {
  name: 'DataCompare',
  components: { CopyDocument, Download },
  props: {
    taskId: {
      type: String,
      required: true
    },
    taskName: {
      type: String,
      default: '未命名任务'
    },
    taskTime: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      rawHtml: '',
      markdown: '',
      structuredData: null,
      loading: false,
      statusText: '已完成',
      statusType: 'success'
    }
  },
  computed: {
    highlightedRaw() {
      if (!this.rawHtml) return '<span style="color:#888;">暂无数据</span>'
      // 简单的HTML语法高亮
      return this.escapeHtml(this.rawHtml)
        .replace(/(&lt;\/?[a-z]+[^&gt;]*&gt;)/gi, '<span style="color:#569CD6;">$1</span>')
        .replace(/(&lt;!--.*?--&gt;)/g, '<span style="color:#6A9955;">$1</span>')
        .replace(/("[^"]*")/g, '<span style="color:#CE9178;">$1</span>')
    },
    highlightedStructured() {
      if (!this.structuredData) return '<span style="color:#888;">暂无数据</span>'
      const jsonStr = JSON.stringify(this.structuredData, null, 2)
      return this.syntaxHighlightJson(jsonStr)
    },
    renderedMarkdown() {
      if (!this.markdown) return '<span style="color:#888;">暂无数据</span>'
      return marked(this.markdown)
    },
    rawSize() {
      if (!this.rawHtml) return '0 KB'
      const size = new Blob([this.rawHtml]).size
      return size > 1024 ? `${(size / 1024).toFixed(1)} KB` : `${size} B`
    },
    markdownLines() {
      if (!this.markdown) return 0
      return this.markdown.split('\n').length
    },
    rawLines() {
      if (!this.rawHtml) return 0
      return this.rawHtml.split('\n').length
    },
    cleanLines() {
      if (!this.markdown) return 0
      return this.markdown.split('\n').filter(line => line.trim()).length
    },
    fieldCount() {
      if (!this.structuredData) return 0
      return Object.keys(this.structuredData).length
    },
    structuredFields() {
      if (!this.structuredData) return 0
      return Object.keys(this.structuredData).join(', ')
    },
    compressionRate() {
      if (!this.rawHtml || !this.structuredData) return 0
      const rawLen = this.rawHtml.length
      const cleanLen = JSON.stringify(this.structuredData).length
      if (rawLen === 0) return 0
      return Math.round((1 - cleanLen / rawLen) * 100)
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        const res = await getTaskPreview(this.taskId, 1)
        if (res.data.code === 200) {
          const data = res.data.data
          this.rawHtml = data.raw_html || ''
          this.markdown = data.markdown || ''
          if (data.preview && data.preview.length > 0) {
            this.structuredData = data.preview[0].extracted_data || data.preview[0]
          }
        }
      } catch (error) {
        console.error('获取数据失败:', error)
      } finally {
        this.loading = false
      }
    },
    escapeHtml(html) {
      if (!html) return ''
      return html
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
    },
    syntaxHighlightJson(json) {
      if (!json) return ''
      return json
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?)/g, (match) => {
          if (/:$/.test(match)) {
            return `<span style="color:#9CDCFE;">${match}</span>`
          }
          return `<span style="color:#CE9178;">${match}</span>`
        })
        .replace(/\b(true|false|null)\b/g, '<span style="color:#569CD6;">$1</span>')
        .replace(/\b(\d+)\b/g, '<span style="color:#B5CEA8;">$1</span>')
    },
    copyContent(type) {
      let content = ''
      if (type === 'raw') content = this.rawHtml
      else if (type === 'markdown') content = this.markdown
      else if (type === 'structured') content = JSON.stringify(this.structuredData, null, 2)
      
      if (!content) {
        this.$message.warning('暂无数据可复制')
        return
      }
      
      navigator.clipboard.writeText(content)
      this.$message.success('已复制到剪贴板')
    },
    async exportData(format) {
      try {
        if (format === 'html') {
          this.downloadFile(this.rawHtml, `preview_${this.taskId}.html`, 'text/html')
        } else if (format === 'markdown') {
          this.downloadFile(this.markdown, `preview_${this.taskId}.md`, 'text/markdown')
        } else if (format === 'json') {
          const content = JSON.stringify(this.structuredData, null, 2)
          this.downloadFile(content, `preview_${this.taskId}.json`, 'application/json')
        } else if (format === 'all') {
          // 导出所有格式的zip包
          await this.exportAll()
        }
        this.$message.success(`导出成功: ${format}`)
      } catch (error) {
        console.error('导出失败:', error)
        this.$message.error('导出失败')
      }
    },
    downloadFile(content, filename, mimeType) {
      const blob = new Blob([content], { type: mimeType + ';charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(link.href)
    },
    async exportAll() {
      // 简单实现：分别下载三个文件
      this.downloadFile(this.rawHtml, `preview_${this.taskId}.html`, 'text/html')
      setTimeout(() => {
        this.downloadFile(this.markdown, `preview_${this.taskId}.md`, 'text/markdown')
      }, 500)
      setTimeout(() => {
        const content = JSON.stringify(this.structuredData, null, 2)
        this.downloadFile(content, `preview_${this.taskId}.json`, 'application/json')
      }, 1000)
    }
  }
}
</script>

<style scoped>
.data-compare {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.compare-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.task-info {
  color: #909399;
  font-size: 13px;
}

.compare-row {
  height: 500px;
}

.compare-panel {
  height: 100%;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-body {
  flex: 1;
  overflow: auto;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.6;
}

.panel-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.raw-panel .panel-body {
  background: #1e1e1e;
  color: #d4d4d4;
}

.markdown-panel .panel-body {
  background: #fafafa;
  color: #303133;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 0.5em 0 0.2em 0;
}

.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
}

.structured-panel .panel-body {
  background: #f0f8f0;
  color: #303133;
}

.panel-footer {
  padding: 6px 14px;
  background: #fafafa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}

.compare-stats {
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.stat-item.success .stat-value {
  color: #67c23a;
}

.stat-item.primary .stat-value {
  color: #409EFF;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.compare-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>