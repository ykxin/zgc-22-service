<template>
  <div>
    <NavBar active-menu="/admin/users" />
    <div class="page-container">
      <div class="page-header">
        <h2>用户管理</h2>
      </div>

      <div class="card-box">
        <el-form inline>
          <el-form-item label="角色">
            <el-select v-model="filterRole" @change="fetchUsers" clearable placeholder="全部" style="width:130px">
              <el-option label="雇主" value="employer" />
              <el-option label="从业者" value="worker" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <el-table :data="users" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="nickname" label="昵称" width="100" />
        <el-table-column prop="real_name" label="真实姓名" width="100" />
        <el-table-column label="角色" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ { employer: '雇主', worker: '从业者', admin: '管理员' }[row.role] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="credit_score" label="信用分" width="80" />
        <el-table-column label="风险" width="70">
          <template #default="{ row }">
            <el-tag :type="row.risk_level === '低' ? 'success' : row.risk_level === '中' ? 'warning' : 'danger'" size="small">{{ row.risk_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">{{ row.status === 1 ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" :type="row.status === 1 ? 'danger' : 'success'" @click="toggleStatus(row)">
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top:16px;justify-content:center"
        background layout="prev, pager, next" :total="total" :page-size="pageSize"
        v-model:current-page="page" @current-change="fetchUsers"
      />

      <!-- 资质审核子模块 -->
      <div class="page-header mt-16"><h2>资质审核</h2></div>
      <el-table :data="certifications" stripe v-loading="certLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="cert_type" label="证件类型" width="100">
          <template #default="{ row }">
            {{ { id_card: '身份证', health_cert: '健康证', qualification: '资格证' }[row.cert_type] }}
          </template>
        </el-table-column>
        <el-table-column prop="cert_number" label="证件编号" />
        <el-table-column prop="real_name" label="姓名" width="80" />
        <el-table-column prop="expire_date" label="有效期" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'passed' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
              {{ { pending: '待审核', passed: '已通过', expired: '已过期', rejected: '已驳回' }[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" type="success" size="small" @click="reviewCert(row, 'passed')">通过</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" size="small" @click="reviewCert(row, 'rejected')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getUsers, toggleUser, getCertifications, reviewCert as reviewCertApi } from '../../api/admin'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const users = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const pageSize = ref(10)
const filterRole = ref('')
const certifications = ref([])
const certLoading = ref(false)

onMounted(() => { fetchUsers(); fetchCerts() })

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUsers(userStore.token, { role: filterRole.value || undefined, page: page.value, page_size: pageSize.value })
    users.value = res.data.list
    total.value = res.data.total
  } finally { loading.value = false }
}

async function toggleStatus(row) {
  try {
    await toggleUser(row.id, userStore.token)
    ElMessage.success('状态已更新')
    fetchUsers()
  } catch { /* ignore */ }
}

async function fetchCerts() {
  certLoading.value = true
  try {
    const res = await getCertifications(userStore.token, { page_size: 100 })
    certifications.value = res.data.list
  } finally { certLoading.value = false }
}

async function reviewCert(row, status) {
  try {
    await reviewCertApi(row.id, userStore.token, { status })
    ElMessage.success('已' + (status === 'passed' ? '通过' : '驳回'))
    fetchCerts()
  } catch { /* ignore */ }
}
</script>
