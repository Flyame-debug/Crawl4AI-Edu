<template>
  <div class="task-list-page">
    <!-- 主卡片 -->
    <el-card class="search-card" shadow="hover">
      <!-- 标题栏 -->
      <div class="filter-row">
        <div class="header-left">
          <h3>数据清洗过程对比</h3>
          <span class="task-info">任务: {{ taskName }} | {{ taskTime }}</span>
        </div>
        <div class="header-right">
          <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
        </div>
      </div>

      <!-- 三栏对比 -->
      <el-row :gutter="16" class="compare-row">
        <!-- 第一栏：原始HTML -->
        <el-col :span="8">
          <div class="compare-panel">
            <div class="panel-header">
              <span class="panel-title">原始 HTML</span>
              <div class="panel-actions">
                <el-button size="small" text @click="copyContent('raw')">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
                <el-tag size="small" type="info">爬虫采集</el-tag>
              </div>
            </div>
            <div class="panel-body raw-body">
              <pre v-html="highlightedRaw"></pre>
            </div>
            <div class="panel-footer">
              <span class="size-info">大小: {{ rawSize }}</span>
            </div>
          </div>
        </el-col>

        <!-- 第二栏：Markdown -->
        <el-col :span="8">
          <div class="compare-panel">
            <div class="panel-header">
              <span class="panel-title">清洗后 (Markdown)</span>
              <div class="panel-actions">
                <el-button size="small" text @click="copyContent('markdown')">
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
          <div class="compare-panel">
            <div class="panel-header">
              <span class="panel-title">结构化数据</span>
              <div class="panel-actions">
                <el-button size="small" text @click="copyContent('structured')">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
                <el-tag size="small" type="primary">最终结果</el-tag>
              </div>
            </div>
            <div class="panel-body structured-body">
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
            <div class="stat-item">
              <span class="stat-value">{{ cleanLines }}</span>
              <span class="stat-label">清洗后行数</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item">
              <span class="stat-value">{{ fieldCount }}</span>
              <span class="stat-label">提取字段</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item">
              <span class="stat-value">{{ compressionRate }}%</span>
              <span class="stat-label">数据压缩率</span>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 导出按钮 -->
      <div class="compare-actions">
        <el-button type="primary" plain @click="exportData('html')">
          <el-icon><Download /></el-icon> 导出 HTML
        </el-button>
        <el-button type="primary" plain @click="exportData('markdown')">
          <el-icon><Download /></el-icon> 导出 Markdown
        </el-button>
        <el-button type="primary" plain @click="exportData('json')">
          <el-icon><Download /></el-icon> 导出 JSON
        </el-button>
        <el-button type="primary" plain @click="exportData('all')">
          <el-icon><Download /></el-icon> 导出全部
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script>
import { CopyDocument, Download } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { getTaskPreview } from '@/api/tasks'

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
      if (!this.rawHtml) return '<span class="empty-text">暂无数据</span>'
      return this.escapeHtml(this.rawHtml)
        .replace(/(&lt;\/?[a-z]+[^&gt;]*&gt;)/gi, '<span class="tag-highlight">$1</span>')
        .replace(/(&lt;!--.*?--&gt;)/g, '<span class="comment-highlight">$1</span>')
        .replace(/("[^"]*")/g, '<span class="string-highlight">$1</span>')
    },
    highlightedStructured() {
      if (!this.structuredData) return '<span class="empty-text">暂无数据</span>'
      const jsonStr = JSON.stringify(this.structuredData, null, 2)
      return this.syntaxHighlightJson(jsonStr)
    },
    renderedMarkdown() {
      if (!this.markdown) return '<span class="empty-text">暂无数据</span>'
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
            return `<span class="json-key">${match}</span>`
          }
          return `<span class="json-string">${match}</span>`
        })
        .replace(/\b(true|false|null)\b/g, '<span class="json-boolean">$1</span>')
        .replace(/\b(\d+)\b/g, '<span class="json-number">$1</span>')
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
.task-list-page {
  padding: 20px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;
}

.search-card {
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  padding: 20px;
  background-color: #fff;
  width: 100%;
  box-sizing: border-box;
}

/* 标题行 */
.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.task-info {
  color: #909399;
  font-size: 13px;
}

.header-right {
  display: flex;
  align-items: center;
}

/* 三栏对比 - 改为自适应高度 */
.compare-row {
  display: flex;
  align-items: stretch;
  margin-bottom: 16px;
  min-height: 300px; /* 保持最小高度，不至于太扁 */
}

.compare-panel {
  height: 100%; /* 撑满行高 */
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
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
  color: #303133;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* panel-body 限制最大高度，内容多时滚动 */
.panel-body {
  flex: 1;
  overflow: auto;
  max-height: 400px; /* 可根据需要调整 */
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.6;
  background: #fafafa;
}

.panel-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #303133;
}

/* 原始 HTML 面板 - 保持深色背景便于阅读 */
.raw-body {
  background: #1e1e1e;
}

.raw-body pre {
  color: #d4d4d4;
}

/* 结构化数据面板 */
.structured-body {
  background: #fafafa;
}

.structured-body pre {
  color: #303133;
}

/* Markdown 渲染样式 */
.markdown-body {
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

/* 语法高亮颜色 */
.tag-highlight {
  color: #569CD6;
}
.comment-highlight {
  color: #6A9955;
}
.string-highlight {
  color: #CE9178;
}
.json-key {
  color: #9CDCFE;
}
.json-string {
  color: #CE9178;
}
.json-boolean {
  color: #569CD6;
}
.json-number {
  color: #B5CEA8;
}
.empty-text {
  color: #909399;
}

.panel-footer {
  padding: 6px 14px;
  background: #fafafa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}

/* 数据统计 */
.compare-stats {
  padding: 16px 20px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
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

.stat-label {
  font-size: 13px;
  color: #909399;
}

/* 导出按钮 */
.compare-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

/* 响应式 */
@media (max-width: 768px) {
  .compare-row {
    height: auto;
  }
  .compare-row .el-col {
    margin-bottom: 16px;
  }
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }
  .header-left {
    flex-wrap: wrap;
  }
}
</style>