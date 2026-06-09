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

      <!-- 提示词输入区 -->
      <div class="prompt-inputs">
        <el-form-item
          v-for="(prompt, index) in prompts"
          :key="index"
          :label="'提示词 ' + (index + 1)"
        >
          <el-input
            v-model="prompts[index]"
            maxlength="8"
            show-word-limit
            placeholder="请输入提示词"
          />
          <small class="hint">请输入名词</small>
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
export default {
  name: 'TemplateCreator',
  data() {
    return {
      title: '',
      description: '',
      prompts: ['', '', '', '', ''] // 五个输入框
    }
  },
  methods: {
    saveTemplate() {
      if (!this.title.trim()) {
        this.$message.error('模板标题不能为空')
        return
      }
      const newTemplate = {
        name: this.title,
        description: this.description || '暂无简介'
      }
      console.log('保存的提示词:', this.prompts)

      this.$message.success('模板已保存！')
      // 跳转并传递新模板数据
      this.$router.push({
        path: '/templates',
        query: { newTemplate: JSON.stringify(newTemplate) }
      })
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
