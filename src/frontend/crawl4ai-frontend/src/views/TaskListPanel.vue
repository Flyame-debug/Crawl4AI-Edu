<template>
  <div class="tasklist-panel" v-loading="loading">
    <!-- 搜索区 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="请输入任务名称搜索"
        clearable
        class="search-input"
      />
      <el-button type="primary" @click="fetchTasks">搜索</el-button>
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
        <el-table-column prop="task_name" label="任务名称" min-width="150">
          <template #default="scope">
            <span>
              <el-tag v-if="scope.row.task_type === 'preview'" size="small" type="warning" style="margin-right: 6px;">预览</el-tag>
              {{ scope.row.task_name || scope.row.task_id || '未命名任务' }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="duration" label="采集时长" width="100" />
        
        <el-table-column label="数据条数" width="120">
          <template #default="scope">
            <span>{{ scope.row.success_pages || 0 }} / {{ scope.row.total_pages || 0 }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" type="primary" @click="viewTask(scope.row)">查看</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { getTasks, deleteTask } from '@/api/tasks'

export default {
  name: 'TaskListPanel',
  props: {
    template: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      searchKeyword: '',
      tasks: [],
      loading: false
    }
  },
  computed: {
    filteredTasks() {
      if (!this.searchKeyword) return this.tasks
      const keyword = this.searchKeyword.toLowerCase()
      return this.tasks.filter(task =>
        task.task_name && task.task_name.toLowerCase().includes(keyword)
      )
    }
  },
  watch: {
    template: {
      handler() {
        this.fetchTasks()
      },
      deep: true,
      immediate: true
    }
  },
  mounted() {
    this.fetchTasks()
  },
  methods: {
    // ✅ 获取该模板下的所有任务
    async fetchTasks() {
      if (!this.template || !this.template.id) {
        console.warn('⚠️ 没有模板ID，无法获取任务列表')
        this.tasks = []
        return
      }
      
      this.loading = true
      try {
        const params = {
          template_id: this.template.id,  // ✅ 按模板ID筛选
          include_preview: 'true',         // ✅ 包含预览任务
          page: 1,
          page_size: 50
        }
        
        const res = await getTasks(params)
        console.log(`📥 模板 ${this.template.id} 的任务列表:`, res)
        
        if (res.data.code === 200) {
          this.tasks = res.data.data.results || []
          console.log(`✅ 加载了 ${this.tasks.length} 个任务`)
        } else {
          this.$message.error(res.data.msg || '获取任务列表失败')
        }
      } catch (error) {
        console.error('获取任务列表失败：', error)
        this.$message.error('获取任务列表失败')
        this.tasks = []
      } finally {
        this.loading = false
      }
    },
    
    resetSearch() {
      this.searchKeyword = ''
      // 不需要重新请求，因为 computed 会自动过滤
    },
    
    viewTask(row) {
      this.$router.push(`/task/${row.task_id}`)
    },
    
    async handleDelete(row) {
      try {
        await this.$confirm(`确认删除任务【${row.task_name || row.task_id}】？`, '删除确认', { type: 'warning' })
        await deleteTask(row.task_id)
        this.$message.success('删除成功')
        this.fetchTasks()  // 刷新列表
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除任务失败：', error)
          this.$message.error('删除失败')
        }
      }
    },
    
    getStatusText(status) {
      const map = {
        pending: '⏳ 等待中',
        running: '🔄 采集中',
        paused: '⏸️ 已暂停',
        stopped: '⏹️ 已停止',
        completed: '✅ 已完成',
        success: '✅ 成功',
        failed: '❌ 失败'
      }
      return map[status] || status
    },
    
    getStatusType(status) {
      const map = {
        pending: 'warning',
        running: 'primary',
        paused: 'info',
        stopped: 'info',
        completed: 'success',
        success: 'success',
        failed: 'danger'
      }
      return map[status] || 'info'
    },
    
    formatTime(dateStr) {
      if (!dateStr) return '-'
      try {
        const date = new Date(dateStr)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      } catch {
        return dateStr
      }
    }
  }
}
</script>

<style scoped>
.tasklist-panel {
  width: 100%;
  margin: 0 auto;
  padding: 20px 0;
}

.search-bar {
  display: flex;
  justify-content: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.search-input {
  width: 300px;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.wide-table {
  width: 100%;
}
</style>