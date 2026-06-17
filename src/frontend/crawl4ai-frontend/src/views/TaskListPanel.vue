<template>
  <div class="tasklist-panel">
    <!-- 搜索区 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="请输入任务ID或关键字"
        clearable
        class="search-input"
      />
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <!-- 横向滚动容器 -->
    <div class="table-wrapper">
      <el-table
        :data="filteredTasks"
        border
        stripe
        size="default"
        class="wide-table"
        style="table-layout:auto;"
      >
        <el-table-column prop="id" label="任务ID" width="120" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column prop="duration" label="采集时长" width="120" />
        <el-table-column prop="successRate" label="成功率" width="100" />
        <el-table-column prop="fileSize" label="文件大小" width="120" />
        <el-table-column prop="logs" label="执行记录" width="180" />
        <el-table-column label="操作" width="160">
          <template #default="scope">
            <el-button size="small" type="primary" @click="viewTask(scope.row)">查看</el-button>
            <el-button size="small" type="danger" @click="deleteTask(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TaskListPanel',
  data() {
    return {
      searchKeyword: '',
      tasks: [
        {
          id: 'T20260615001',
          status: '成功',
          createdAt: '2026-06-15 10:00',
          duration: '12s',
          successRate: '100%',
          fileSize: '2MB',
          logs: '执行成功'
        },
        {
          id: 'T20260614002',
          status: '失败',
          createdAt: '2026-06-14 09:30',
          duration: '8s',
          successRate: '0%',
          fileSize: '0MB',
          logs: '网络错误'
        },
        {
          id: 'T20260613003',
          status: '成功',
          createdAt: '2026-06-13 14:20',
          duration: '15s',
          successRate: '95%',
          fileSize: '3MB',
          logs: '部分页面超时'
        },
        {
          id: 'T20260612004',
          status: '进行中',
          createdAt: '2026-06-12 16:45',
          duration: '--',
          successRate: '--',
          fileSize: '--',
          logs: '正在采集'
        }
      ]
    }
  },
  computed: {
    filteredTasks() {
      if (!this.searchKeyword) return this.tasks
      return this.tasks.filter(task =>
        task.id.includes(this.searchKeyword)
      )
    }
  },
  methods: {
    handleSearch() {
      this.$message.success('搜索完成')
    },
    resetSearch() {
      this.searchKeyword = ''
    },
    viewTask(row) {
      this.$router.push(`/task/${row.id}`)
    },
    deleteTask(row) {
      this.$message.error(`删除任务 ${row.id}（假数据）`)
    }
  }
}
</script>

<style scoped>
.tasklist-panel {
  width: 600px;          /* 外层卡片固定 */
  margin: 0 auto;
  padding: 20px 0;         /* 卡片内边距 */
}

/* 搜索区占满卡片宽度，内部控件固定 */
.search-bar {
  display: flex;  
  justify-content: center;
  gap: 30px;
  margin-bottom: 20px;
  width: 100%;           /* 紧贴卡片左右端 */
}
.search-input {
  flex: none;            /* 禁止被拉伸 */
  width: 580px;          /* 固定搜索框长度 */
}

/* 表格容器占满卡片宽度 */
.table-wrapper {
  width: 100%;           /* 紧贴卡片左右端 */
  overflow-x: auto;      /* 横向滚动 */
  position: relative;
}

/* 表格固定宽度，撑开滚动条 */
.wide-table {
  width: 1080px;         /* 固定表格宽度 */
  max-width: 1200px;
}
.table-wrapper ::v-deep(.el-table),
.table-wrapper ::v-deep(.el-table__inner),
.table-wrapper ::v-deep(.el-table__header),
.table-wrapper ::v-deep(.el-table__body) {
  padding-left: 0 !important;
  padding-right: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
/* 右侧渐变提示 */
.table-wrapper::after {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  width: 30px;
  height: 100%;
  pointer-events: none;
  background: linear-gradient(to left, #fff, transparent);
}
</style>
