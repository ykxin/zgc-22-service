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

      <div class="page-header mt-16"><h2>资质审核</h2></div>
      <el-table :data="certifications" stripe v-loading="certLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column label="材料类型" min-width="140">
          <template #default="{ row }">{{ row.doc_name || certTypeText(row.cert_type) }}</template>
        </el-table-column>
        <el-table-column prop="cert_number" label="证件编号" min-width="150" />
        <el-table-column prop="real_name" label="姓名" width="90" />
        <el-table-column prop="expire_date" label="有效期" width="120" />
        <el-table-column label="AI置信度" width="100">
          <template #default="{ row }">{{ row.ai_confidence ? Math.round(row.ai_confidence * 100) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险提示" min-width="160">
          <template #default="{ row }">
            <el-tag
              v-for="flag in row.risk_flags || []"
              :key="flag.code"
              :type="flag.severity === 'high' ? 'danger' : 'warning'"
              size="small"
              style="margin:2px"
            >
              {{ flag.code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openReview(row)">审核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="reviewDialogVisible" title="资质材料审核" width="720px">
      <template v-if="selectedCert">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="材料">{{ selectedCert.doc_name || certTypeText(selectedCert.cert_type) }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusText(selectedCert.status) }}</el-descriptions-item>
          <el-descriptions-item label="持有人">{{ selectedCert.real_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="证件编号">{{ selectedCert.cert_number || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发证机构">{{ selectedCert.issuing_authority || '-' }}</el-descriptions-item>
          <el-descriptions-item label="有效期">{{ selectedCert.expire_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="AI置信度">{{ selectedCert.ai_confidence ? Math.round(selectedCert.ai_confidence * 100) + '%' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="图片路径">{{ selectedCert.image_url || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top:12px">
          <el-tag v-for="tag in selectedCert.suggested_tags || []" :key="tag.tag_code" style="margin:2px">
            {{ tag.tag_name || tag.tag_code }}
          </el-tag>
        </div>

        <el-alert
          v-for="flag in selectedCert.risk_flags || []"
          :key="flag.code"
          :title="flag.message"
          :type="flag.severity === 'high' ? 'error' : 'warning'"
          show-icon
          :closable="false"
          style="margin-top:12px"
        />

        <el-input
          v-model="reviewComment"
          type="textarea"
          :rows="3"
          placeholder="审核意见"
          style="margin-top:16px"
        />
      </template>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="warning" @click="reviewCert(selectedCert, 'expired')">标记过期</el-button>
        <el-button type="danger" @click="reviewCert(selectedCert, 'rejected')">驳回</el-button>
        <el-button type="success" @click="reviewCert(selectedCert, 'passed')">通过</el-button>
      </template>
    </el-dialog>
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
const reviewDialogVisible = ref(false)
const selectedCert = ref(null)
const reviewComment = ref('')

const certTypeMap = {
  id_card: '身份证实名核验',
  health_cert: '健康证',
  health_certificate: '健康证明',
  qualification: '资格证',
  no_criminal_record: '无犯罪记录证明',
  background_check_authorization: '背景核查授权',
  housekeeping_certificate: '家政服务证书',
  maternity_matron_certificate: '母婴护理证书',
  infant_care_certificate: '育婴照护证书',
  elderly_care_certificate: '养老护理证书',
  medical_caregiver_certificate: '病患陪护证书',
  first_aid_certificate: '基础急救证书',
  insurance_policy: '服务保险',
}

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

function openReview(row) {
  selectedCert.value = row
  reviewComment.value = row.review_comment || row.reject_reason || ''
  reviewDialogVisible.value = true
}

async function reviewCert(row, status) {
  if (!row) return
  try {
    await reviewCertApi(row.id, userStore.token, {
      status,
      review_comment: reviewComment.value,
      reject_reason: status === 'rejected' ? reviewComment.value : undefined,
    })
    ElMessage.success('已' + (status === 'passed' ? '通过' : status === 'expired' ? '标记过期' : '驳回'))
    reviewDialogVisible.value = false
    await fetchCerts()
    await fetchUsers()
  } catch { /* ignore */ }
}

function certTypeText(type) {
  return certTypeMap[type] || type
}

function statusText(status) {
  return { pending: '待审核', passed: '已通过', expired: '已过期', rejected: '已驳回' }[status] || status
}

function statusType(status) {
  return status === 'passed' ? 'success' : status === 'rejected' ? 'danger' : status === 'expired' ? 'danger' : 'warning'
}
</script>
