<template>
  <el-menu
    class="app-nav"
    :default-active="activeMenu"
    mode="horizontal"
    @select="handleSelect"
  >
    <el-menu-item index="brand" class="app-nav__brand">
      <el-icon><House /></el-icon>
      AI家政双向信任匹配平台
    </el-menu-item>
    <div class="app-nav__spacer"></div>
    <template v-for="item in menuItems" :key="item.index">
      <el-menu-item :index="item.index">
        <el-icon><component :is="item.icon" /></el-icon>
        {{ item.label }}
      </el-menu-item>
    </template>
    <el-menu-item index="logout">
      <el-icon><SwitchButton /></el-icon>
      退出登录
    </el-menu-item>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { House, SwitchButton } from '@element-plus/icons-vue'

const props = defineProps({
  activeMenu: { type: String, default: '' }
})

const router = useRouter()
const userStore = useUserStore()

const menuItems = computed(() => {
  const role = userStore.role
  if (role === 'employer') {
    return [
      { index: '/employer/home', label: '首页推荐', icon: 'HomeFilled' },
      { index: '/employer/booking', label: '预约服务', icon: 'Calendar' },
      { index: '/employer/orders', label: '我的订单', icon: 'Document' },
      { index: '/employer/profile', label: '个人中心', icon: 'User' },
    ]
  } else if (role === 'worker') {
    return [
      { index: '/worker/home', label: '工作台', icon: 'HomeFilled' },
      { index: '/worker/orders', label: '我的订单', icon: 'Document' },
      { index: '/worker/cert', label: '资质认证', icon: 'Stamp' },
      { index: '/worker/checkin', label: '服务打卡', icon: 'Checked' },
    ]
  } else if (role === 'admin') {
    return [
      { index: '/admin/dashboard', label: '数据面板', icon: 'DataAnalysis' },
      { index: '/admin/users', label: '用户管理', icon: 'UserFilled' },
      { index: '/admin/orders', label: '订单管理', icon: 'Document' },
      { index: '/admin/sops', label: 'SOP管理', icon: 'Setting' },
    ]
  }
  return []
})

function handleSelect(index) {
  if (index === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (index !== 'brand') {
    router.push(index)
  }
}
</script>
