/**
 * 路由配置文件 (index.js)
 * 
 * 功能说明：
 * - 定义前端页面的路由映射关系
 * - 管理页面跳转与导航逻辑
 * - 使用 Vue Router 提供的 createRouter 和 createWebHistory
 * 
 * 注意事项：
 * - 每个路由对应 views 文件夹下的页面组件
 * - 只能有一个默认导出 (export default router)
 */

import { createRouter, createWebHistory } from 'vue-router'

// 导入页面视图
import LoginRegister from '../views/LoginRegister.vue'
import BaseLayout from '../views/BaseLayout.vue'
import HomeView from '../views/HomeView.vue'
import Guide from '../views/Guide.vue'
import TemplateManager from '../views/TemplateManager.vue'
import TemplateCreator from '../views/TemplateCreator.vue'
import TaskMonitor from '../views/TaskMonitor.vue'

const routes = [
  { path: '/', redirect: '/auth' },
  { path: '/auth', name: 'Auth', component: LoginRegister },
  {
    path: '/',
    component: BaseLayout,
    children: [
      { path: 'home', name: 'Home', component: HomeView },
      { path: 'guide', name: 'Guide', component: Guide },
      { path: 'templates', name: 'TemplateManager', component: TemplateManager },
      { path: 'create-template', name: 'TemplateCreator', component: TemplateCreator },
      { path: 'tasks', name: 'TaskMonitor', component: TaskMonitor }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
