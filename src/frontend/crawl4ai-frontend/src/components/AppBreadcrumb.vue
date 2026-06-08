/**
 * AppBreadcrumb.vue
 * 
 * 功能说明：
 * - 全局面包屑导航组件
 * - 根据当前路由的 matched 数组动态生成路径
 * - 优先显示路由配置中的 meta.breadcrumb 中文名字
 * - 如果没有配置 meta.breadcrumb，则显示路由的 name
 * 
 * 注意事项：
 * - 使用 computed 保证响应式更新
 */

<template>
  <el-breadcrumb separator=">">
    <el-breadcrumb-item
      v-for="(item, index) in breadcrumbItems"
      :key="index"
    >
      {{ item.meta?.breadcrumb || item.name }}
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

export default {
  name: 'AppBreadcrumb',
  setup() {
    const route = useRoute()
    // 响应式计算，每次路由变化都会更新
    const breadcrumbItems = computed(() =>
      route.matched.filter(r => r.meta && r.meta.breadcrumb)
    )
    return { breadcrumbItems }
  }
}
</script>

<style scoped>
.el-breadcrumb {
  font-size: 14px;
  margin-left: 20px;
}
</style>
