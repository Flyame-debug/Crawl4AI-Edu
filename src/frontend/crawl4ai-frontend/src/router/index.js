/**
 * 路由配置文件 (index.js)
 */

import { createRouter, createWebHistory } from 'vue-router'
import { ElMessageBox } from 'element-plus'

import LoginRegister from '../views/LoginRegister.vue'
import BaseLayout from '../views/BaseLayout.vue'
import HomeView from '../views/HomeView.vue'
import Guide from '../views/Guide.vue'
import TemplateManager from '../views/TemplateManager.vue'
import TemplateCreator from '../views/TemplateCreator.vue'
import TaskMonitor from '../views/TaskMonitor.vue'
import TemplateDetail from '../views/TemplateDetail.vue'
import TaskDetail from '@/views/TaskDetail.vue'
const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/auth',
    name: 'Auth',
    component: LoginRegister,
    meta: { breadcrumb: '登录注册', public: true } // 标记为公开路由
  },
  {
    path: '/',
    component: BaseLayout,
    children: [
      {
        path: 'home',
        name: 'Home',
        component: HomeView,
        meta: { breadcrumb: '首页', public: true } // 首页允许游客访问
      },
      {
        path: 'guide',
        name: 'Guide',
        component: Guide,
        meta: { breadcrumb: '操作指南' }
      },
      {
        path: 'templates',
        name: 'TemplateManager',
        component: TemplateManager,
        meta: { breadcrumb: '模板页面' }
      },
      {
        path: 'templates/create',
        name: 'TemplateCreator',
        component: TemplateCreator,
        meta: { breadcrumb: '新建模板' }
      },
      {
        path: 'templates/:id',
        name: 'TemplateDetail',
        component: TemplateDetail,
        meta: { breadcrumb: '模板详情', parent: 'TemplateManager' }
      },
      {
        path: 'tasks',
        name: 'TaskMonitor',
        component: TaskMonitor,
        meta: { breadcrumb: '任务监控' }
      },
      {
    path: '/task/:id',
    name: 'TaskDetail',
    component: TaskDetail,
    meta: { requiresAuth: true }
  }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ✅ 路由守卫：游客只能访问首页和登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token') // 登录后存储 token
  if (!to.meta.public && !token) {
    // 游客访问受限页面 → 弹窗提示
    ElMessageBox.confirm('请先登录！', '提示', {
      confirmButtonText: '登录',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      next('/auth') // 跳转登录页
    }).catch(() => {
      next('/home') // 返回首页
    })
  } else {
    next()
  }
})

export default router
