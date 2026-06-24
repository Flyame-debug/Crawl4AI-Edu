<template>
  <div class="overview-panel">
    <!-- 概述信息标题区 -->
    <div class="section-title">概述信息</div>

    <!-- 工具信息表格（动态数据） -->
    <el-table :data="toolInfo" border stripe size="default" class="styled-table">
      <el-table-column prop="name" label="字段" />
      <el-table-column prop="value" label="值" />
    </el-table>

    <!-- 分类标签（动态数据） -->
    <div class="tags">
      <el-tag v-for="tag in tags" :key="tag" type="success">{{ tag }}</el-tag>
    </div>

    <!-- 请求参数表格（暂留占位，文档无单独接口） -->
    <el-table :data="params" border stripe size="default" class="styled-table">
      <el-table-column prop="name" label="参数名" />
      <el-table-column prop="desc" label="说明" />
    </el-table>

    <!-- 返回字段表格（暂留占位） -->
    <el-table :data="fields" border stripe size="default" class="styled-table">
      <el-table-column prop="name" label="字段名" />
      <el-table-column prop="desc" label="说明" />
    </el-table>

  </div>
</template>

<script>
export default {
  name: 'OverviewPanel',
  props: {
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      // 占位数据：请求参数和返回字段暂无接口，暂时保留
      params: [
        { name: 'keyword', desc: '搜索关键词' },
        { name: 'pageSize', desc: '每页返回数量' },
        { name: 'pageIndex', desc: '分页索引' }
      ],
      fields: [
        { name: 'title', desc: '内容标题' },
        { name: 'summary', desc: '内容摘要' },
        { name: 'source', desc: '来源网站' }
      ]
    }
  },
  computed: {
    // 动态工具信息：从模板数据生成
    toolInfo() {
      const tpl = this.template || {}
      return [
        { name: '采集器名称', value: tpl.name || '未知' },
        { name: '使用的AI', value: tpl.ai_model || '未使用' },
        { name: '使用次数', value: tpl.usage_count ?? '0' },
        { name: '更新时间', value: this.formatTime(tpl.updated_at) || '未知' }
      ]
    },
    // 动态分类标签
    tags() {
      const tpl = this.template || {}
      const list = []
      if (tpl.category) list.push(this.categoryLabel(tpl.category))
      if (tpl.tags && Array.isArray(tpl.tags)) {
        list.push(...tpl.tags)
      }
      return list.length ? list : ['暂无分类']
    }
  },
  methods: {
    // 时间格式化
    formatTime(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${day} ${hours}:${minutes}`
    },
    // 分类中文映射
    categoryLabel(category) {
      const map = {
        teacher: '教师信息',
        course: '课程信息',
        news: '新闻公告',
        research: '科研成果',
        other: '其他'
      }
      return map[category] || category
    }
  }
}
</script>

<style scoped>
.overview-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  height: 40px;
  display: flex;
  align-items: center;
  padding-left: 10px;
  margin-bottom: 0;
}

.styled-table {
  border-radius: 8px;
  overflow: hidden;
  font-size: 14px;
}
.styled-table ::v-deep(.el-table__header-wrapper) {
  background-color: #f9f9f9;
}
.styled-table ::v-deep(.el-table__body tr:hover > td) {
  background-color: #f0f9ff !important;
}

.tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.example-box {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  background: #fafafa;
}
.example {
  text-align: center;
}
.example img {
  max-width: 100%;
  border: 1px solid #ccc;
  border-radius: 6px;
}
.hint {
  font-size: 13px;
  color: #666;
  margin-top: 10px;
  display: block;
}
</style>