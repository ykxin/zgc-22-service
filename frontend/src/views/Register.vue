<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>用户注册</h1>
      <p class="subtitle">加入AI家政平台，开启智能服务体验</p>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" label-width="80px">
        <el-form-item label="用户角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="employer">雇主</el-radio>
            <el-radio value="worker">从业者</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item v-if="form.role === 'worker'" label="验证码" prop="smsCode">
          <el-input v-model="form.smsCode" placeholder="输入验证码" style="width:60%">
            <template #append>
              <el-button :disabled="countdown > 0" @click="sendSmsCode">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少6位" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="rePassword">
          <el-input v-model="form.rePassword" type="password" placeholder="再次输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width:100%" :loading="loading" @click="handleRegister">
            注 册
          </el-button>
        </el-form-item>
      </el-form>
      <div class="text-center">
        <el-button link type="primary" @click="$router.push('/login')">已有账号？去登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sendSms, register } from '../api/auth'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const countdown = ref(0)

const form = reactive({
  role: 'employer',
  phone: '',
  smsCode: '',
  nickname: '',
  password: '',
  rePassword: '',
})

const validateRePass = (rule, value, callback) => {
  if (value !== form.password) callback(new Error('两次密码不一致'))
  else callback()
}

const rules = {
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
  smsCode: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
  rePassword: [{ required: true, message: '请确认密码', trigger: 'blur' }, { validator: validateRePass, trigger: 'blur' }],
}

async function sendSmsCode() {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    ElMessage.warning('请先输入正确的手机号')
    return
  }
  try {
    await sendSms(form.phone)
    ElMessage.success('验证码已发送（查看控制台）')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch { /* ignore */ }
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const data = {
      phone: form.phone,
      password: form.password,
      role: form.role,
      nickname: form.nickname,
    }
    if (form.role === 'worker') {
      data.sms_code = form.smsCode
    }
    await register(data)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch { /* ignore */ }
  finally { loading.value = false }
}
</script>
