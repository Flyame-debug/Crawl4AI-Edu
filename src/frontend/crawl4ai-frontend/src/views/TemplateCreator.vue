<template>
  <div class="template-creator-page">
    <!-- 页面标题 -->
    <h2>新建模板</h2>

    <!-- 提示词输入区 -->
    <div class="prompt-inputs">
      <el-form label-position="top">
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
      </el-form>
    </div>

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
      prompts: ['', '', '', '', ''] // 五个输入框
    }
  },
  methods: {
    saveTemplate() {
      console.log('保存的提示词:', this.prompts)
      this.$message.success('模板已保存！')
      this.$router.push('/templates')
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
