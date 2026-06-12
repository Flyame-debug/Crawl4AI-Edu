<template>
  <div class="template-creator-page">
    <h2>新建模板</h2>

    <el-form label-position="top" class="form-area">
      <!-- 模板标题 -->
      <el-form-item label="模板标题">
        <el-input v-model="title" placeholder="请输入模板标题" />
      </el-form-item>

      <!-- 模板简介 -->
      <el-form-item label="模板简介">
        <el-input v-model="description" type="textarea" placeholder="请输入模板简介" />
      </el-form-item>

      <!-- 种子URL -->
      <el-form-item label="种子URL">
        <el-input v-model="seedUrl" placeholder="请输入种子URL" />
      </el-form-item>

      <!-- AI提示词（多个输入框） -->
      <div class="prompt-inputs">
        <el-form-item
          v-for="(prompt, index) in prompts"
          :key="index"
          :label="'提示词 ' + (index + 1)"
        >
          <el-input
            v-model="prompts[index]"
            maxlength="20"
            show-word-limit
            placeholder="请输入提示词"
          />
          <small class="hint">请输入名词或短语</small>
        </el-form-item>
      </div>
    </el-form>

    <!-- 操作按钮 -->
    <div class="actions">
      <el-button type="primary" @click="saveTemplate">保存模板</el-button>
      <el-button @click="goBack">返回模板页面</el-button>
    </div>
  </div>
</template>

<script>
import { createTemplate } from '@/api/templates'

export default {
  name: 'TemplateCreator',
  data() {
    return {
      title: '',
      description: '',
      seedUrl: '',
      prompts: ['', '', '', '', ''] // 五个提示词输入框
    }
  },
  methods: {
    async saveTemplate() {
      if (!this.title.trim() || !this.seedUrl.trim()) {
        this.$message.error('模板标题和种子URL不能为空')
        return
      }

      const newTemplate = {
        name: this.title,
        seed_url: this.seedUrl,
        tags: this.prompts.filter(p => p.trim() !== ''), // 多个提示词数组
        description: this.description || '暂无简介'
      }

      try {
        const res = await createTemplate(newTemplate)
        if (res.data && res.data.id) {
          this.$message.success(`模板【${res.data.name}】已创建`)
          this.$router.push('/templates')
        }
      } catch (e) {
        this.$message.error('模板创建失败')
      }
    },
    goBack() {
      this.$router.push('/templates')
    }
  }
}
</script>

<style scoped>
.template-creator-page {
  padding: 20px;
}
.form-area {
  margin-top: 20px;
}
.prompt-inputs {
  margin-top: 20px;
}
.hint {
  font-size: 12px;
  color: #888;
}
.actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}
</style>
