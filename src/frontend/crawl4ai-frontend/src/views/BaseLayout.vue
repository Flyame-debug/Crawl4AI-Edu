<template>
  <div class="base-layout">
    <!-- 左侧导航栏 -->
    <el-menu
      default-active="home"
      class="el-menu-vertical"
      @select="handleSelect"
    >
      <el-menu-item index="home">首页</el-menu-item>
      <el-menu-item index="guide">操作指南</el-menu-item>
      <el-menu-item index="templates">模板页面</el-menu-item>
      <el-menu-item index="create-template">新建模板</el-menu-item>
      <el-menu-item index="tasks">任务监控</el-menu-item>
    </el-menu>

    <!-- 右侧区域 -->
    <div class="right-area">
      <!-- 顶端栏 -->
      <header class="top-bar">
        <div class="logo">教育数据采集平台</div>
        <div class="user-info">
          <!-- 用户头像 + 下拉菜单 -->
          <el-dropdown>
            <span class="el-dropdown-link">
              <el-avatar icon="UserFilled" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <div class="content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BaseLayout',
  methods: {
    handleSelect(key) {
      this.$router.push(`/${key}`)
    },
    logout() {
      // 模拟退出逻辑
      alert('已退出登录')
      this.$router.push('/auth')
    }
  }
}
</script>

<style scoped>
.base-layout {
  display: flex;
  height: 100vh;
}

/* 左侧导航栏贯穿全高 */
.el-menu-vertical {
  width: 200px;
  border-right: 1px solid #ddd;
}

/* 右侧区域：顶端栏 + 内容区 */
.right-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 顶端栏样式 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ddd;
  padding: 0 20px;
}
.logo {
  font-size: 18px;
  font-weight: bold;
}
.user-info {
  display: flex;
  align-items: center;
}

/* 内容区 */
.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
</style>
