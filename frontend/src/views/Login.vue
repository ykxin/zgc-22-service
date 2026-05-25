<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>AI家政平台</h1>
      <p class="subtitle">双向信任 · 智能匹配 · 公正透明</p>
      <el-form ref="formRef" :model="form" :rules="rules" size="large">
        <el-form-item prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" prefix-icon="Phone" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width:100%" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="text-center" style="margin-top:16px">
        <el-button link type="primary" @click="$router.push('/register')">还没有账号？立即注册</el-button>
      </div>
      <el-divider />
      <p style="color:#909399;font-size:12px;text-align:center">
        管理员登录：admin / admin123<br/>
        雇主测试：13800001111 / 123456<br/>
        从业者测试：13800002222 / 123456
      </p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api/auth'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({ phone: '', password: '' })
const rules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await login(form)
    userStore.setLogin(res.data)
    ElMessage.success('登录成功')
    if (res.data.user.role === 'employer') router.push('/employer/home')
    else if (res.data.user.role === 'worker') router.push('/worker/home')
    else if (res.data.user.role === 'admin') router.push('/admin/dashboard')
  } catch { /* 拦截器已处理 */ }
  finally { loading.value = false }
}
</script>
