import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '评测总览' } },
  { path: '/models', name: 'models', component: () => import('../views/ModelsView.vue'), meta: { title: '模型管理' } },
  { path: '/suites', name: 'suites', component: () => import('../views/SuitesView.vue'), meta: { title: '测试题库' } },
  { path: '/runs', name: 'runs', component: () => import('../views/RunsView.vue'), meta: { title: '发起评测' } },
  { path: '/reports', name: 'reports', component: () => import('../views/ReportsView.vue'), meta: { title: '数据报表' } }
]

export default createRouter({ history: createWebHashHistory(), routes })
