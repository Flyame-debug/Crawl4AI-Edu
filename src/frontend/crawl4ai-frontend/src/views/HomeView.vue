<template>
  <div class="home-view">
    <h2>欢迎来到首页</h2>
    <p v-if="username">欢迎你，{{ username }}！</p>
    <p>这里可以展示一些系统概览信息，比如用户欢迎语、项目进度、统计数据等。</p>
  </div>
</template>

<script>
export default {
  name: 'HomeView',
  data() {
    return {
      username: ''
    }
  },
  mounted() {
    // 从 localStorage 获取用户名
    this.username = localStorage.getItem('username') || '游客'
  }
}
</script>

<style scoped>
.home-view {
  padding: 20px;
}
h2 {
  margin-bottom: 10px;
  color: #333;
}
p {
  font-size: 15px;
  color: #555;
}
</style>
