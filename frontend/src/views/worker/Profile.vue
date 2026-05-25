<template>
  <div>
    <NavBar active-menu="/worker/profile" />
    <div class="page-container" style="max-width:800px">
      <div class="page-header"><h2>个人主页</h2></div>

      <div class="card-box">
        <h3 style="margin-bottom:16px">基础信息</h3>
        <el-form :model="form" label-width="100px">
          <el-form-item label="手机号">
            <el-input :model-value="user?.phone" disabled />
          </el-form-item>
          <el-form-item label="昵称">
            <el-input v-model="form.nickname" />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="form.real_name" />
          </el-form-item>
          <el-form-item label="性别">
            <el-radio-group v-model="form.gender">
              <el-radio value="男">男</el-radio>
              <el-radio value="女">女</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="地址">
            <el-input v-model="form.address" />
          </el-form-item>
        </el-form>
      </div>

      <div class="card-box">
        <h3 style="margin-bottom:16px">技能画像</h3>
        <el-form :model="form" label-width="100px">
          <el-form-item label="技能标签">
            <el-input v-model="form.skills" placeholder="如：保洁,收纳,育儿" />
          </el-form-item>
          <el-form-item label="从业年限">
            <el-input-number v-model="form.experience_years" :min="0" :max="50" />
          </el-form-item>
          <el-form-item label="擅长场景">
            <el-input v-model="form.good_at" placeholder="如：深度保洁/新生儿护理" />
          </el-form-item>
          <el-form-item label="可服务时间">
            <el-input v-model="form.work_time" placeholder="如：工作日白天/周末全天" />
          </el-form-item>
        </el-form>
      </div>

      <el-button type="primary" :loading="saving" @click="saveProfile" style="width:100%">
        保存修改
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { updateProfile } from '../../api/auth'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const user = ref(userStore.user)
const saving = ref(false)
const form = reactive({
  nickname: user.value?.nickname || '',
  real_name: user.value?.real_name || '',
  gender: user.value?.gender || '',
  address: user.value?.address || '',
  skills: user.value?.skills || '',
  experience_years: user.value?.experience_years ?? 0,
  good_at: user.value?.good_at || '',
  work_time: user.value?.work_time || '',
})

async function saveProfile() {
  saving.value = true
  try {
    await updateProfile(userStore.token, form)
    await userStore.fetchProfile()
    user.value = userStore.user
    ElMessage.success('保存成功')
  } finally { saving.value = false }
}
</script>
