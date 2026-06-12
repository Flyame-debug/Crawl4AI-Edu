<template>
  <div class="template-detail">
    <!-- 模板标题和简介 -->
    <h2 v-if="!editMode">{{ template.name }}</h2>
    <p v-if="!editMode" class="subtitle">{{ template.description }}</p>

    <!-- 编辑模式 -->
    <div v-if="editMode" class="edit-form">
      <el-form label-position="top">
        <el-form-item label="模板标题">
          <el-input v-model="template.name" />
        </el-form-item>
        <el-form-item label="模板简介">
          <el-input v-model="template.description" type="textarea" />
        </el-form-item>
        <el-form-item label="种子URL">
          <el-input v-model="template.seed_url" />
        </el-form-item>

        <!-- AI提示词 -->
        <div class="prompt-inputs">
          <el-form-item
            v-for="(prompt, index) in template.prompts"
            :key="index"
            :label="'提示词 ' + (index + 1)"
          >
            <el-input
              v-model="template.prompts[index]"
              maxlength="20"
              show-word-limit
              placeholder="请输入提示词"
            />
            <small class="hint">请输入名词或短语</small>
          </el-form-item>
        </div>
      </el-form>
      <div class="edit-actions">
        <el-button type="primary" @click="saveChanges">保存修改</el-button>
        <el-button @click="editMode = false">取消</el-button>
      </div>
    </div>

    <!-- 控制按钮区 -->
    <div class="collect-buttons" v-if="!editMode">
      <el-button type="primary" @click="editMode = true">编辑模板</el-button>

      <el-button
        type="primary"
        :disabled="collectState === 'collecting'"
        @click="handleCollect"
      >
        {{ collectState === 'idle' ? '开始采集' : '继续采集' }}
      </el-button>

      <el-button
        v-if="collectState !== 'idle'"
        type="warning"
        circle
        :disabled="collectState === 'paused'"
        @click="pauseCollect"
      >
        <el-icon><VideoPause /></el-icon>
      </el-button>

      <el-button
        v-if="collectState !== 'idle'"
        type="danger"
        circle
        @click="endCollect"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <!-- 使用方法 -->
    <section class="usage" v-if="!editMode">
      <h3>使用方法</h3>
      <ul>
        <li>点击“编辑模板”按钮进入编辑模式，修改模板信息和提示词。</li>
        <li>编辑完成后点击“保存修改”按钮保存更改。</li>
        <li>点击“开始采集”按钮启动数据采集过程。</li>
        <li>采集中可以点击暂停或结束按钮控制采集状态。</li>
      </ul>  
      <p v-if="!template.prompts || !template.prompts.length">暂无提示词</p>
    </section>

    <!-- 注意事项 -->
    <section class="notes" v-if="!editMode">
      <h3>注意事项</h3>
      <p>{{ template.notes || '暂无注意事项' }}</p>
    </section>

    <!-- 进度显示 -->
    <section class="progress" v-if="!editMode && collectState === 'collecting'">
      <h3>采集进度</h3>
      <el-progress :percentage="progress" status="active"></el-progress>
      <p>{{ progressMessage }}</p>
    </section>

    <!-- 数据预览 -->
    <section class="preview" v-if="!editMode">
      <h3>采集数据预览</h3>
      <el-table v-if="previewData.length" :data="previewData" style="width: 100%">
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="title" label="职称" />
        <el-table-column prop="research" label="研究方向" />
        <el-table-column prop="email" label="邮箱" />
      </el-table>
      <p v-else>暂无数据</p>
    </section>
  </div>
</template>

<script>
import { VideoPause, Close } from '@element-plus/icons-vue'
import { getTemplateDetail, updateTemplate } from '@/api/templates'
import { startTask, pauseTask, stopTask, getTaskPreview, getTaskProgress } from '@/api/tasks'

export default {
  name: 'TemplateDetail',
  components: { VideoPause, Close },
  data() {
    return {
      collectState: 'idle',
      editMode: false,
      taskId: null,
      template: { name: '', description: '', seed_url: '', prompts: ['', '', '', '', ''], notes: '' },
      previewData: [],
      progress: 0,
      progressMessage: '',
      progressTimer: null
    }
  },
  created() {
    const id = this.$route.params.id
    getTemplateDetail(id)
      .then(res => {
        if (res.data) {
          this.template = {
            ...res.data,
            prompts: res.data.prompts && res.data.prompts.length ? res.data.prompts : ['', '', '', '', '']
          }
          this.previewData = res.data.preview_data || []
        }
      })
      .catch(() => {
        this.$message.error('获取模板详情失败')
      })
  },
  beforeUnmount() {
    if (this.progressTimer) {
      clearInterval(this.progressTimer)
    }
  },
  methods: {
    async saveChanges() {
      const id = this.$route.params.id
      try {
        const res = await updateTemplate(id, this.template)
        this.template = {
          ...res.data,
          prompts: res.data.prompts || ['', '', '', '', '']
        }
        this.editMode = false
        this.$message.success('模板更新成功')
      } catch (e) {
        this.$message.error('模板更新失败')
      }
    },

    async handleCollect() {
      console.log('开始采集，模板ID:', this.$route.params.id)
      try {
        const res = await startTask({ 
          template_id: this.$route.params.id, 
          config: { max_depth: 3, max_concurrent: 5 } 
        })
        console.log('启动响应:', res.data)
        this.taskId = res.data.task_id
        this.collectState = 'collecting'
        this.$message.success(res.data.message || '任务已启动')
        this.fetchPreview()
        this.startProgressPolling()
      } catch (e) {
        console.error('启动失败:', e)
        this.$message.error('启动采集任务失败')
      }
    },

    async pauseCollect() {
      if (!this.taskId) return
      try {
        const res = await pauseTask(this.taskId)
        this.collectState = 'paused'
        this.$message.success(res.data.message || '任务已暂停')
        if (this.progressTimer) clearInterval(this.progressTimer)
      } catch (e) {
        this.$message.error('暂停任务失败')
      }
    },

    async endCollect() {
      if (!this.taskId) return
      try {
        const res = await stopTask(this.taskId)
        this.collectState = 'idle'
        this.previewData = []
        this.progress = 0
        this.progressMessage = ''
        this.$message.success(res.data.message || '任务已停止')
        if (this.progressTimer) clearInterval(this.progressTimer)
      } catch (e) {
        this.$message.error('停止任务失败')
      }
    },

    async fetchPreview() {
      if (!this.taskId) return
      try {
        const res = await getTaskPreview(this.taskId, 5)
        if (res.data && res.data.preview) {
          this.previewData = res.data.preview
        }
      } catch (e) {
        this.$message.error('获取采集数据预览失败')
      }
    },

    startProgressPolling() {
      if (this.progressTimer) clearInterval(this.progressTimer)
      this.progressTimer = setInterval(async () => {
        if (!this.taskId || this.collectState !== 'collecting') return
        try {
          const res = await getTaskProgress(this.taskId)
          console.log('进度更新:', res.data)
          
          if (res.data) {
            this.progress = res.data.percent || 0
            this.progressMessage = res.data.message || ''
            
            if (res.data.status === 'completed') {
              this.collectState = 'idle'
              this.progress = 100
              this.progressMessage = '采集完成！'
              clearInterval(this.progressTimer)
              this.$message.success('采集任务已完成')
              this.fetchPreview()
            } else if (res.data.status === 'failed') {
              this.collectState = 'idle'
              clearInterval(this.progressTimer)
              this.$message.error('采集任务失败')
              this.fetchPreview()
            } else if (res.data.status === 'stopped') {
              this.collectState = 'idle'
              clearInterval(this.progressTimer)
              this.$message.info('采集任务已停止')
            }
          }
        } catch (e) {
          console.error('获取任务进度失败:', e)
        }
      }, 3000)
    }
  }
}
</script><template>
  <div class="template-detail">
    <!-- 模板标题和简介 -->
    <h2 v-if="!editMode">{{ template.name }}</h2>
    <p v-if="!editMode" class="subtitle">{{ template.description }}</p>

    <!-- 编辑模式 -->
    <div v-if="editMode" class="edit-form">
      <el-form label-position="top">
        <el-form-item label="模板标题">
          <el-input v-model="template.name" />
        </el-form-item>
        <el-form-item label="模板简介">
          <el-input v-model="template.description" type="textarea" />
        </el-form-item>
        <el-form-item label="种子URL">
          <el-input v-model="template.seed_url" />
        </el-form-item>

        <!-- AI提示词 -->
        <div class="prompt-inputs">
          <el-form-item
            v-for="(prompt, index) in template.prompts"
            :key="index"
            :label="'提示词 ' + (index + 1)"
          >
            <el-input
              v-model="template.prompts[index]"
              maxlength="20"
              show-word-limit
              placeholder="请输入提示词"
            />
            <small class="hint">请输入名词或短语</small>
          </el-form-item>
        </div>
      </el-form>
      <div class="edit-actions">
        <el-button type="primary" @click="saveChanges">保存修改</el-button>
        <el-button @click="editMode = false">取消</el-button>
      </div>
    </div>

    <!-- 控制按钮区 -->
    <div class="collect-buttons" v-if="!editMode">
      <el-button type="primary" @click="editMode = true">编辑模板</el-button>

      <el-button
        type="primary"
        :disabled="collectState === 'collecting'"
        @click="handleCollect"
      >
        {{ collectState === 'idle' ? '开始采集' : '继续采集' }}
      </el-button>

      <el-button
        v-if="collectState !== 'idle'"
        type="warning"
        circle
        :disabled="collectState === 'paused'"
        @click="pauseCollect"
      >
        <el-icon><VideoPause /></el-icon>
      </el-button>

      <el-button
        v-if="collectState !== 'idle'"
        type="danger"
        circle
        @click="endCollect"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <!-- 使用方法 -->
    <section class="usage" v-if="!editMode">
      <h3>使用方法</h3>
      <ul>
        <li>点击“编辑模板”按钮进入编辑模式，修改模板信息和提示词。</li>
        <li>编辑完成后点击“保存修改”按钮保存更改。</li>
        <li>点击“开始采集”按钮启动数据采集过程。</li>
        <li>采集中可以点击暂停或结束按钮控制采集状态。</li>
      </ul>  
      <p v-if="!template.prompts || !template.prompts.length">暂无提示词</p>
    </section>

    <!-- 注意事项 -->
    <section class="notes" v-if="!editMode">
      <h3>注意事项</h3>
      <p>{{ template.notes || '暂无注意事项' }}</p>
    </section>

    <!-- 进度显示 -->
    <section class="progress" v-if="!editMode && collectState === 'collecting'">
      <h3>采集进度</h3>
      <el-progress :percentage="progress" status="active"></el-progress>
      <p>{{ progressMessage }}</p>
    </section>

    <!-- 数据预览 -->
    <section class="preview" v-if="!editMode">
      <h3>采集数据预览</h3>
      <el-table v-if="previewData.length" :data="previewData" style="width: 100%">
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="title" label="职称" />
        <el-table-column prop="research" label="研究方向" />
        <el-table-column prop="email" label="邮箱" />
      </el-table>
      <p v-else>暂无数据</p>
    </section>
  </div>
</template>

<script>
import { VideoPause, Close } from '@element-plus/icons-vue'
import { getTemplateDetail, updateTemplate } from '@/api/templates'
import { startTask, pauseTask, stopTask, getTaskPreview, getTaskProgress } from '@/api/tasks'

export default {
  name: 'TemplateDetail',
  components: { VideoPause, Close },
  data() {
    return {
      collectState: 'idle',
      editMode: false,
      taskId: null,
      template: { name: '', description: '', seed_url: '', prompts: ['', '', '', '', ''], notes: '' },
      previewData: [],
      progress: 0,
      progressMessage: '',
      progressTimer: null
    }
  },
  created() {
    const id = this.$route.params.id
    getTemplateDetail(id)
      .then(res => {
        if (res.data) {
          this.template = {
            ...res.data,
            prompts: res.data.prompts && res.data.prompts.length ? res.data.prompts : ['', '', '', '', '']
          }
          this.previewData = res.data.preview_data || []
        }
      })
      .catch(() => {
        this.$message.error('获取模板详情失败')
      })
  },
  beforeUnmount() {
    if (this.progressTimer) {
      clearInterval(this.progressTimer)
    }
  },
  methods: {
    async saveChanges() {
      const id = this.$route.params.id
      try {
        const res = await updateTemplate(id, this.template)
        this.template = {
          ...res.data,
          prompts: res.data.prompts || ['', '', '', '', '']
        }
        this.editMode = false
        this.$message.success('模板更新成功')
      } catch (e) {
        this.$message.error('模板更新失败')
      }
    },
    async handleCollect() {
      try {
        const res = await startTask({ template_id: this.$route.params.id, config: { max_depth: 3, max_concurrent: 5 } })
        this.taskId = res.data.task_id
        this.collectState = 'collecting'
        this.$message.success(res.data.message || '任务已启动')
        this.fetchPreview()
        this.startProgressPolling()
      } catch (e) {
        this.$message.error('启动采集任务失败')
      }
    },
    async pauseCollect() {
      if (!this.taskId) return
      try {
        const res = await pauseTask(this.taskId)
        this.collectState = 'paused'
        this.$message.success(res.data.message || '任务已暂停')
        if (this.progressTimer) clearInterval(this.progressTimer)
      } catch (e) {
        this.$message.error('暂停任务失败')
      }
    },
    async endCollect() {
      if (!this.taskId) return
      try {
        const res = await stopTask(this.taskId)
        this.collectState = 'idle'
        this.previewData = []
        this.progress = 0
        this.progressMessage = ''
        this.$message.success(res.data.message || '任务已停止')
        if (this.progressTimer) clearInterval(this.progressTimer)
      } catch (e) {
        this.$message.error('停止任务失败')
      }
    },
    async fetchPreview() {
      if (!this.taskId) return
      try {
        const res = await getTaskPreview(this.taskId, 5)
        if (res.data && res.data.preview) {
          this.previewData = res.data.preview
        }
      } catch (e) {
        this.$message.error('获取采集数据预览失败')
      }
    },
    startProgressPolling() {
      if (this.progressTimer) clearInterval(this.progressTimer)
      this.progressTimer = setInterval(async () => {
        if (!this.taskId || this.collectState !== 'collecting') return
        try {
          const res = await getTaskProgress(this.taskId)
          if (res.data) {
            this.progress = res.data.percent
            this.progressMessage = res.data.message
          }
        } catch (e) {
          this.$message.error('获取任务进度失败')
        }
      }, 5000)
    }
  }
}
</script>

<style scoped>
.template-detail {
  padding: 20px;
}
.subtitle {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
}
.collect-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.edit-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}
.prompt-inputs {
  margin-top: 20px;
}
.hint {
  font-size: 12px;
  color: #888;
}
section {
  margin-top: 20px;
}
.progress {
  margin-top: 20px;
}
.preview {
  margin-top: 20px;
}
.notes {
  margin-top: 20px;
}
.usage {
  margin-top: 20px;
}
</style>
