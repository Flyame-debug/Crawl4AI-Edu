<template>
  <div class="template-create">
    <el-tabs v-model="activeTab">
      <!-- 我的提交 -->
      <el-tab-pane label="我的提交" name="submissions">
        <el-table
          ref="submissionTable"
          :data="submissions"
          max-height="500"
          class="submission-table"
          v-loading="submissionLoading"
        >
          <el-table-column prop="name" label="模板名称" width="220" />
          <el-table-column label="提交时间" width="190">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="150">
            <template #default="scope">
              <el-tag v-if="scope.row.status === 'pending'" type="warning">待审核</el-tag>
              <el-tag v-else-if="scope.row.status === 'approved'" type="success">审核通过</el-tag>
              <el-tag v-else-if="scope.row.status === 'rejected'" type="danger">审核驳回</el-tag>
            </template>
          </el-table-column>
          <!-- 操作列不设宽度，自动填充剩余空间 -->
          <el-table-column label="操作">
            <template #default="scope">
              <div v-if="scope.row.status === 'pending'">
                <el-button size="small" @click="withdraw(scope.row.id)">撤回申请</el-button>
                <el-button size="small" @click="viewDetail(scope.row)">查看配置详情</el-button>
              </div>
              <div v-else-if="scope.row.status === 'approved'">
                <el-button size="small" @click="viewDetail(scope.row)">查看详情</el-button>
              </div>
              <div v-else-if="scope.row.status === 'rejected'">
                <el-button size="small" @click="viewReview(scope.row)">查看驳回原因</el-button>
                <el-button size="small" @click="editTemplate(scope.row)">重新编辑并提交</el-button>
                <el-button size="small" type="danger" @click="deleteSubmission(scope.row.id)">删除申请</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 新建模板 -->
      <el-tab-pane label="新建模板" name="create">
        <div class="section-title first">基础配置区（必填）</div>
        <el-card class="config-card" shadow="hover">
          <el-form ref="configForm" label-position="top" :model="form" :rules="rules" class="form-block">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入模板名称" />
            </el-form-item>

            <el-form-item label="目标网址" prop="seed_url">
              <el-input type="textarea" v-model="form.seed_url" placeholder="支持单行或多行批量导入" rows="3" />
            </el-form-item>

            <el-form-item label="页面渲染" prop="need_render">
              <el-switch v-model="form.need_render" />
            </el-form-item>

            <el-form-item label="等待加载（秒）" prop="wait_load">
              <el-input-number v-model="form.wait_load" :min="0" />
            </el-form-item>

            <el-form-item label="缓存开关" prop="enable_cache">
              <el-switch v-model="form.enable_cache" active-text="开启" inactive-text="关闭" />
            </el-form-item>

            <el-form-item label="超时时间（秒）" prop="timeout">
              <el-input-number v-model="form.timeout" :min="1" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- AI提取配置（可选） -->
        <div class="section-title">AI提取配置（可选）</div>
        <el-card class="config-card" shadow="hover">
          <el-form label-position="top" :model="form" :rules="rules" class="form-block">
            <el-form-item label="开启AI内容提取">
              <el-switch v-model="form.ai_enabled" />
            </el-form-item>
            <div v-if="form.ai_enabled">
              <el-form-item label="服务商选择" prop="ai_provider">
                <el-select v-model="form.ai_provider">
                  <el-option label="ollama" value="ollama" />
                  <el-option label="deepseek" value="deepseek" />
                  <el-option label="openai" value="openai" />
                </el-select>
              </el-form-item>
              <el-form-item label="模型名称" prop="ai_model">
                <el-input v-model="form.ai_model" placeholder="请输入模型名称" />
              </el-form-item>
              <el-form-item label="接口地址" prop="ai_api_url">
                <el-input v-model="form.ai_api_url" placeholder="http://127.0.0.1:11434" />
              </el-form-item>
              <el-form-item label="API KEY（可选）">
                <el-input v-model="form.ai_api_key" />
              </el-form-item>
              <el-form-item label="提取指令" prop="user_prompt">
                <el-input type="textarea" v-model="form.user_prompt" placeholder="请输入提取指令" />
              </el-form-item>
            </div>
          </el-form>
        </el-card>

        <!-- 分类标签 -->
        <div class="section-title">分类标签</div>
        <el-card class="config-card" shadow="hover">
          <el-form label-position="top" :model="form" class="form-block">
            <el-form-item label="模板分类">
              <el-select v-model="form.category" placeholder="请选择分类">
                <el-option label="教师信息" value="teacher" />
                <el-option label="课程信息" value="course" />
                <el-option label="新闻公告" value="news" />
                <el-option label="科研成果" value="research" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 提交按钮 -->
        <div class="actions">
          <el-button type="primary" @click="submitTemplate" :loading="submitting">
            {{ editingId ? '提交更新' : '提交审核' }}
          </el-button>
          <el-button @click="resetForm">重置表单</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 配置详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="模板配置详情"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-descriptions v-if="detailRow" :column="2" border>
        <el-descriptions-item label="模板名称">{{ detailRow.name }}</el-descriptions-item>
        <el-descriptions-item label="目标网址">{{ detailRow.seed_url }}</el-descriptions-item>
        <el-descriptions-item label="模板分类">{{ categoryLabel(detailRow.category) }}</el-descriptions-item>
        <el-descriptions-item label="页面渲染">{{ detailRow.need_render ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="等待加载（秒）">{{ detailRow.wait_load }}</el-descriptions-item>
        <el-descriptions-item label="缓存开关">{{ detailRow.enable_cache ? '开启' : '关闭' }}</el-descriptions-item>
        <el-descriptions-item label="超时时间（秒）">{{ detailRow.timeout }}</el-descriptions-item>
        <el-descriptions-item label="AI内容提取">{{ detailRow.ai_enabled ? '开启' : '关闭' }}</el-descriptions-item>
        <template v-if="detailRow.ai_enabled">
          <el-descriptions-item label="服务商">{{ detailRow.ai_provider }}</el-descriptions-item>
          <el-descriptions-item label="模型名称">{{ detailRow.ai_model }}</el-descriptions-item>
          <el-descriptions-item label="接口地址">{{ detailRow.ai_api_url }}</el-descriptions-item>
          <el-descriptions-item label="API KEY">{{ detailRow.ai_api_key || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="提取指令">{{ detailRow.user_prompt }}</el-descriptions-item>
        </template>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { getTemplateHistory, createTemplate, updateTemplate, deleteTemplate } from '@/api/templates'

export default {
  name: 'TemplateCreate',
  data() {
    return {
      activeTab: 'submissions',
      submissions: [],
      submissionLoading: false,
      detailVisible: false,
      detailRow: null,
      editingId: null,       // 非 null 时表示编辑模式（驳回重编）
      submitting: false,
      form: {
        name: '',
        seed_url: '',
        category: '',
        description: '',
        need_render: false,
        wait_load: 0,
        enable_cache: false,
        timeout: 30,
        ai_enabled: false,
        ai_provider: '',
        ai_model: '',
        ai_api_url: '',
        ai_api_key: '',
        user_prompt: ''
      },
      rules: {
        name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
        seed_url: [{ required: true, message: '请输入目标网址', trigger: 'blur' }],
        wait_load: [{ required: true, message: '请输入等待时间', trigger: 'blur' }],
        timeout: [{ required: true, message: '请输入超时时间', trigger: 'blur' }],
        ai_provider: [{ validator: (rule, value, callback) => {
          if (this.form.ai_enabled && !value) callback(new Error('请选择服务商'))
          else callback()
        }, trigger: 'change' }],
        ai_model: [{ validator: (rule, value, callback) => {
          if (this.form.ai_enabled && !value) callback(new Error('请输入模型名称'))
          else callback()
        }, trigger: 'blur' }],
        ai_api_url: [{ validator: (rule, value, callback) => {
          if (this.form.ai_enabled && !value) callback(new Error('请输入接口地址'))
          else callback()
        }, trigger: 'blur' }],
        user_prompt: [{ validator: (rule, value, callback) => {
          if (this.form.ai_enabled && !value) callback(new Error('请输入提取指令'))
          else callback()
        }, trigger: 'blur' }]
      }
    }
  },
  watch: {
    activeTab(val) {
      if (val === 'submissions') {
        this.$nextTick(() => {
          this.$refs.submissionTable?.doLayout()
        })
      }
    }
  },
  mounted() {
    this.fetchSubmissions()
  },
  methods: {
    // 获取我的提交（调用历史模板接口）
    async fetchSubmissions() {
      this.submissionLoading = true
      try {
        const res = await getTemplateHistory()
        if (res.data.code === 200) {
          this.submissions = res.data.data.results || res.data.data || []
        }
      } catch {
        console.warn('获取我的提交失败，使用测试假数据')
        this.loadMockSubmissions()
      } finally {
        this.submissionLoading = false
      }
    },
    // 假数据兜底
    loadMockSubmissions() {
      this.submissions = [
        {
          id: 1,
          name: '教师信息采集模板',
          seed_url: 'https://example.com/teachers',
          category: 'teacher',
          need_render: true,
          wait_load: 3,
          enable_cache: false,
          timeout: 30,
          ai_enabled: true,
          ai_provider: 'ollama',
          ai_model: 'qwen2:7b',
          ai_api_url: 'http://127.0.0.1:11434',
          ai_api_key: '',
          user_prompt: '提取教师姓名、职称、邮箱',
          status: 'pending',
          created_at: '2026-06-16T14:30:00'
        },
        {
          id: 2,
          name: '课程信息采集模板',
          seed_url: 'https://example.com/courses',
          category: 'course',
          need_render: false,
          wait_load: 0,
          enable_cache: true,
          timeout: 20,
          ai_enabled: false,
          ai_provider: '',
          ai_model: '',
          ai_api_url: '',
          ai_api_key: '',
          user_prompt: '',
          status: 'approved',
          created_at: '2026-06-15T09:15:00'
        },
        {
          id: 3,
          name: '新闻公告采集模板',
          seed_url: 'https://example.com/news',
          category: 'news',
          need_render: true,
          wait_load: 5,
          enable_cache: false,
          timeout: 45,
          ai_enabled: true,
          ai_provider: 'deepseek',
          ai_model: 'deepseek-chat',
          ai_api_url: 'https://api.deepseek.com/v1',
          ai_api_key: 'sk-xxxx',
          user_prompt: '提取新闻标题、发布时间、正文摘要',
          status: 'rejected',
          created_at: '2026-06-14T17:45:00',
          review_comment: '目标网站需要登录后才能访问，请提供可公开访问的地址'
        }
      ]
    },
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
    categoryLabel(category) {
      const map = {
        teacher: '教师信息',
        course: '课程信息',
        news: '新闻公告',
        research: '科研成果',
        other: '其他'
      }
      return map[category] || category
    },
    // 提交模板（新建 / 驳回重编）
    async submitTemplate() {
      const valid = await this.$refs.configForm.validate().catch(() => false)
      if (!valid) {
        this.$message.error('请填写所有必填项')
        return
      }
      this.submitting = true
      try {
        const payload = { ...this.form }
        let res
        if (this.editingId) {
          // 驳回重编：调用更新接口
          res = await updateTemplate(this.editingId, payload)
        } else {
          // 新建：调用创建接口
          res = await createTemplate(payload)
        }
        if (res.data.code === 200) {
          this.$message.success(this.editingId ? '更新成功，等待审核' : '提交成功，等待审核')
          this.activeTab = 'submissions'
          this.editingId = null
          this.resetForm()
          this.fetchSubmissions()
        } else {
          this.$message.error(res.data.msg || '提交失败')
        }
      } catch {
        this.$message.error('提交失败，请稍后重试')
      } finally {
        this.submitting = false
      }
    },
    resetForm() {
      this.$refs.configForm.resetFields()
      this.editingId = null
      this.form = {
        name: '',
        seed_url: '',
        category: '',
        description: '',
        need_render: false,
        wait_load: 0,
        enable_cache: false,
        timeout: 30,
        ai_enabled: false,
        ai_provider: '',
        ai_model: '',
        ai_api_url: '',
        ai_api_key: '',
        user_prompt: ''
      }
    },
    // 撤回申请（调用删除接口）
    async withdraw(id) {
      try {
        await this.$confirm('确认撤回该申请？', '提示', { type: 'warning' })
        await deleteTemplate(id)
        this.$message.success('撤回成功')
        this.fetchSubmissions()
      } catch (error) {
        if (error !== 'cancel') {
          // 接口失败时仍从本地移除（测试模式兜底）
          this.$message.success('撤回成功（测试模式）')
          this.submissions = this.submissions.filter(s => s.id !== id)
        }
      }
    },
    // 删除申请
    async deleteSubmission(id) {
      try {
        await this.$confirm('确认删除该申请？', '提示', { type: 'warning' })
        await deleteTemplate(id)
        this.$message.success('删除成功')
        this.fetchSubmissions()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.success('删除成功（测试模式）')
          this.submissions = this.submissions.filter(s => s.id !== id)
        }
      }
    },
    // 查看驳回原因
    viewReview(row) {
      if (row.review_comment) {
        this.$alert(row.review_comment, '驳回原因')
      } else {
        this.$message.warning('暂无驳回信息')
      }
    },
    // 查看配置详情弹窗
    viewDetail(row) {
      this.detailRow = { ...row }
      this.detailVisible = true
    },
    // 驳回重编：回填表单并切换到新建 Tab
    editTemplate(row) {
      this.editingId = row.id
      this.form = {
        name: row.name || '',
        seed_url: row.seed_url || '',
        category: row.category || '',
        description: row.description || '',
        need_render: row.need_render ?? false,
        wait_load: row.wait_load ?? 0,
        enable_cache: row.enable_cache ?? false,
        timeout: row.timeout ?? 30,
        ai_enabled: row.ai_enabled ?? false,
        ai_provider: row.ai_provider || '',
        ai_model: row.ai_model || '',
        ai_api_url: row.ai_api_url || '',
        ai_api_key: row.ai_api_key || '',
        user_prompt: row.user_prompt || ''
      }
      this.activeTab = 'create'
    }
  }
}
</script>

<style scoped>
.template-create {
  padding: 20px;
}

.el-tabs__content {
  margin-top: 40px;
}

.section-title.first {
  font-size: 15px;
  font-weight: 600;
  margin-top: 48px;
  margin-bottom: 22px;
  color: #333;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 22px;
  color: #333;
}

.config-card {
  padding: 20px;
  margin-bottom: 28px;
  border: 1px solid #eee;
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  background-color: #fff;
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}
.config-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.actions {
  margin-top: 32px;
  text-align: center;
}
.actions .el-button {
  border-radius: 8px;
  padding: 10px 20px;
}

/* 表格卡片（与卡片等宽，无悬停效果） */
.submission-table {
  margin-top: 32px;
  margin-bottom: 0;
  border: 1px solid #eee;
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  background-color: #fff;
  width: 100%;
  max-width: 100%;
  table-layout: fixed;
}

.submission-table th {
  background-color: #fafafa;
  font-weight: 600;
  color: #333;
}

.submission-table td {
  background-color: #fff;
  word-break: break-word;
}

.submission-table .el-table__row:hover {
  background-color: #f5f7fa;
}

/* 操作按钮间距微调 */
.el-table .el-button--small {
  margin: 2px 4px;
}
</style>