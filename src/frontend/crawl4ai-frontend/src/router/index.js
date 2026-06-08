/**
 * 路由配置文件 (index.js)
 * 
 * 功能说明：
 * - 定义前端页面的路由映射关系
 * - 管理页面跳转与导航逻辑
 * - 使用 Vue Router 提供的 createRouter 和 createWebHistory
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
import TemplateDetail from '../views/TemplateDetail.vue'

const routes = [
  { path: '/', redirect: '/auth' },
  { path: '/auth', name: 'Auth', component: LoginRegister, meta: { breadcrumb: '登录注册' } },
  {
    path: '/',
    component: BaseLayout,
    children: [
      { path: 'home', name: 'Home', component: HomeView, meta: { breadcrumb: '首页' } },
      { path: 'guide', name: 'Guide', component: Guide, meta: { breadcrumb: '操作指南' } },
      { path: 'templates', name: 'TemplateManager', component: TemplateManager, meta: { breadcrumb: '模板页面' } },
      { path: 'templates/:id', name: 'TemplateDetail', component: TemplateDetail, meta: { breadcrumb: '模板详情' } },
      { path: 'create-template', name: 'TemplateCreator', component: TemplateCreator, meta: { breadcrumb: '新建模板' } },
      { path: 'tasks', name: 'TaskMonitor', component: TaskMonitor, meta: { breadcrumb: '任务监控' } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
