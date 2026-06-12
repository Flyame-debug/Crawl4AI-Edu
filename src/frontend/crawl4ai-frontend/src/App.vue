/**
 * App.vue
 *
 * 功能说明：
 * - 应用的根组件，作为 Vue 项目的入口
 * - 只负责渲染 <router-view />，由路由决定加载 BaseLayout 或其他页面
 * - 避免重复挂载 BaseLayout，防止出现两个导航栏
 */

<template>
  <router-view />
</template>

<script>
export default {
  name: 'AppRoot'
}
</script>

<style>
/* 全局样式可以放这里 */
body {
  margin: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f9f9f9;
}
</style>
