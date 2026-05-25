<template>
  <div>
    <NavBar active-menu="/employer/profile" />
    <div class="page-container" style="max-width:800px">
      <div class="page-header"><h2>个人中心</h2></div>
      <div class="card-box">
        <el-form :model="form" label-width="100px">
          <el-form-item label="手机号"><el-input :model-value="user?.phone" disabled /></el-form-item>
          <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
          <el-form-item label="真实姓名"><el-input v-model="form.real_name" /></el-form-item>
          <el-form-item label="性别">
            <el-radio-group v-model="form.gender">
              <el-radio value="男">男</el-radio><el-radio value="女">女</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
        </el-form>
      </div>

      <div class="card-box">
        <h3 style="margin-bottom:16px">家庭画像（影响匹配推荐）</h3>
        <el-form :model="form" label-width="100px">
          <el-form-item label="家庭成员">
            <el-input v-model="form.family_members" placeholder="如：夫妻2人+1个3岁小孩+1位老人" />
          </el-form-item>
          <el-form-item label="户型"><el-input v-model="form.house_type" placeholder="如：三室两厅" /></el-form-item>
          <el-form-item label="作息时间"><el-input v-model="form.schedule" placeholder="如：上午,下午" /></el-form-item>
          <el-form-item label="有老人"><el-switch v-model="form.has_elderly" :active-value="1" :inactive-value="0" /></el-form-item>
          <el-form-item label="有小孩"><el-switch v-model="form.has_children" :active-value="1" :inactive-value="0" /></el-form-item>
          <el-form-item label="有宠物"><el-switch v-model="form.has_pet" :active-value="1" :inactive-value="0" /></el-form-item>
        </el-form>
      </div>

      <!-- 自定义服务标准 -->
      <div class="card-box">
        <div class="flex-between" style="margin-bottom:12px">
          <h3>自定义服务标准</h3>
          <el-button type="primary" size="small" @click="showCustomDialog">新增要求</el-button>
        </div>
        <el-table :data="customStandards" size="small" stripe>
          <el-table-column prop="category" label="服务类别" width="100" />
          <el-table-column prop="name" label="要求名称" />
          <el-table-column prop="weight" label="权重" width="80" />
          <el-table-column prop="description" label="描述" />
        </el-table>
      </div>

      <el-button type="primary" :loading="saving" @click="saveProfile" style="width:100%">
        保存修改
      </el-button>
    </div>

    <el-dialog v-model="customVisible" title="新增自定义服务标准" width="400px">
      <el-form>
        <el-form-item label="服务类别">
          <el-select v-model="customForm.category">
            <el-option label="保洁" value="保洁" />
            <el-option label="育儿" value="育儿" />
            <el-option label="养老陪护" value="养老陪护" />
          </el-select>
        </el-form-item>
        <el-form-item label="要求名称"><el-input v-model="customForm.name" /></el-form-item>
        <el-form-item label="权重"><el-input-number v-model="customForm.weight" :min="0.1" :max="5" :step="0.1" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="customForm.description" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" @click="addCustom">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getProfile, updateProfile } from '../../api/auth'
import { getCustomStandards, createCustomStandard } from '../../api/order'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const user = ref(userStore.user)
const saving = ref(false)
const form = reactive({ ...user.value })
const customStandards = ref([])
const customVisible = ref(false)
const customForm = reactive({ category: '保洁', name: '', weight: 1.0, description: '' })

onMounted(async () => {
  await fetchCustomStandards()
})

async function fetchCustomStandards() {
  try {
    const res = await getCustomStandards(userStore.token)
    customStandards.value = res.data || []
  } catch { /* ignore */ }
}

async function saveProfile() {
  saving.value = true
  try {
    await updateProfile(userStore.token, form)
    await userStore.fetchProfile()
    user.value = userStore.user
    ElMessage.success('保存成功')
  } finally { saving.value = false }
}

function showCustomDialog() {
  customForm.category = '保洁'
  customForm.name = ''
  customForm.weight = 1.0
  customForm.description = ''
  customVisible.value = true
}

async function addCustom() {
  try {
    await createCustomStandard(userStore.token, customForm)
    ElMessage.success('已添加')
    customVisible.value = false
    fetchCustomStandards()
  } catch { /* ignore */ }
}
</script>
