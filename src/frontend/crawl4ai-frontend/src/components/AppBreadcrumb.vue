<template>
  <el-breadcrumb :separator="'>'">
    <el-breadcrumb-item
      v-for="(item, index) in breadcrumbItems"
      :key="index"
      :to="item.path"
    >
      {{ item.meta?.breadcrumb }}
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script>
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import router from '../router/index.js'

export default {
  name: 'AppBreadcrumb',
  setup() {
    const route = useRoute()
    const breadcrumbItems = computed(() => {
      const matched = route.matched.filter(r => r.meta?.breadcrumb && r.path !== '/')
      const current = matched[matched.length - 1]

      // 如果是模板详情，手动插入父级“模板页面”
      if (current?.name === 'TemplateDetail' && current.meta?.parent) {
        const parentRoute = router.getRoutes().find(r => r.name === current.meta.parent)
        if (parentRoute) return [parentRoute, current]
      }

      return matched
    })
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
