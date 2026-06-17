<template>
  <div class="overview-panel">
    <!-- 概述信息标题区 -->
    <div class="section-title">概述信息</div>

    <!-- 工具信息表格 -->
    <el-table :data="toolInfo" border stripe size="default" class="styled-table">
      <el-table-column prop="name" label="字段" />
      <el-table-column prop="value" label="值" />
    </el-table>

    <!-- 分类标签 -->
    <div class="tags">
      <el-tag v-for="tag in info.tags" :key="tag" type="success">{{ tag }}</el-tag>
    </div>

    <!-- 请求参数表格 -->
    <el-table :data="params" border stripe size="default" class="styled-table">
      <el-table-column prop="name" label="参数名" />
      <el-table-column prop="desc" label="说明" />
    </el-table>

    <!-- 返回字段表格 -->
    <el-table :data="fields" border stripe size="default" class="styled-table">
      <el-table-column prop="name" label="字段名" />
      <el-table-column prop="desc" label="说明" />
    </el-table>

    <!-- 示例响应截图 -->
    <div class="example-box">
      <div class="example">
        <img src="https://via.placeholder.com/400x200?text=示例截图" alt="示例响应截图" />
        <p class="hint">这里将展示采集到的真实截图，当前为占位图</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'OverviewPanel',
  props: { template: Object },
  data() {
    return {
      toolInfo: [
        { name: '采集器名称', value: '教育数据采集' },
        { name: '使用的AI', value: 'deepseek-chat' },
        { name: '使用次数', value: '12' },
        { name: '更新时间', value: '2026-06-15' }
      ],
      info: {
        tags: ['教育', '电商', '科研']
      },
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
  }
}
</script>

<style scoped>
.overview-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 32px; /* 每个表格/板块之间间距更大，匀称 */
}

/* 标题区：和 TaskListPanel 对齐 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  height: 40px;
  display: flex;
  align-items: center;
  padding-left: 10px;
  margin-bottom: 0;
}

/* 表格美化：和 TaskListPanel 保持一致 */
.styled-table {
  border-radius: 8px;
  overflow: hidden;
  font-size: 14px; /* 字体稍大 */
}
.styled-table ::v-deep(.el-table__header-wrapper) {
  background-color: #f9f9f9;
}
.styled-table ::v-deep(.el-table__body tr:hover > td) {
  background-color: #f0f9ff !important;
}

/* 标签区 */
.tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* 示例响应加框 */
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
