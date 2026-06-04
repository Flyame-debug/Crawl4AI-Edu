/**
 * 应用入口文件 (main.js)
 *
 * 功能说明：
 * - 创建 Vue 应用实例
 * - 挂载全局状态管理 (Pinia)
 * - 挂载全局路由 (Vue Router)
 * - 挂载 Element Plus 组件库
 * - 挂载根组件 App.vue
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

// 引入 Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)

// 挂载全局状态管理
app.use(createPinia())

// 挂载路由
app.use(router)

// 挂载 Element Plus
app.use(ElementPlus)

// 挂载到 DOM 根节点
app.mount('#app')
