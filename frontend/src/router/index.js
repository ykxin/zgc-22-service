import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue') },
  // 雇主端
  { path: '/employer/home', name: 'EmployerHome', component: () => import('../views/employer/EmployerHome.vue') },
  { path: '/employer/booking', name: 'Booking', component: () => import('../views/employer/Booking.vue') },
  { path: '/employer/orders', name: 'MyOrders', component: () => import('../views/employer/MyOrders.vue') },
  { path: '/employer/profile', name: 'Profile', component: () => import('../views/employer/Profile.vue') },
  // 从业者端
  { path: '/worker/home', name: 'WorkerHome', component: () => import('../views/worker/WorkerHome.vue') },
  { path: '/worker/cert', name: 'Certification', component: () => import('../views/worker/Certification.vue') },
  { path: '/worker/checkin', name: 'CheckIn', component: () => import('../views/worker/CheckIn.vue') },
  { path: '/worker/orders', name: 'WorkerOrders', component: () => import('../views/worker/WorkerOrders.vue') },
  // 管理后台
  { path: '/admin/dashboard', name: 'AdminDashboard', component: () => import('../views/admin/AdminDashboard.vue') },
  { path: '/admin/users', name: 'UserManage', component: () => import('../views/admin/UserManage.vue') },
  { path: '/admin/orders', name: 'OrderManage', component: () => import('../views/admin/OrderManage.vue') },
  { path: '/admin/sops', name: 'SopManage', component: () => import('../views/admin/SopManage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 - 未登录重定向
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const publicPages = ['/login', '/register']
  if (!token && !publicPages.includes(to.path)) {
    next('/login')
  } else if (token && to.path === '/') {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (user.role === 'employer') next('/employer/home')
    else if (user.role === 'worker') next('/worker/home')
    else if (user.role === 'admin') next('/admin/dashboard')
    else next('/login')
  } else {
    next()
  }
})

export default router
