<template>
  <div>
    <NavBar active-menu="/worker/cert" />
    <div class="page-container" style="max-width:980px">
      <div class="page-header">
        <h2>资质可信标签</h2>
        <p>AI识别材料并生成候选标签，平台人工审核后正式生效</p>
      </div>

      <div class="card-box" v-if="profile">
        <div class="flex-between mb-16">
          <h3>我的资质画像</h3>
          <el-tag :type="profile.qualification_summary.qualification_completeness === 'high' ? 'success' : 'warning'">
            完整度 {{ completenessText(profile.qualification_summary.qualification_completeness) }}
          </el-tag>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-tag
            v-for="tag in profile.visible_tags"
            :key="`${tag.tag_code}-${tag.source_id}`"
            :type="tag.status === 'active' ? 'success' : tag.status === 'warning' ? 'warning' : 'danger'"
          >
            {{ tag.tag_name }} · {{ trustText(tag.trust_level) }}
          </el-tag>
          <el-empty v-if="!profile.visible_tags.length" description="暂无已展示标签" :image-size="60" />
        </div>
        <el-alert
          v-for="warning in profile.risk_warnings"
          :key="`${warning.code}-${warning.document_id}`"
          :title="warning.message"
          type="warning"
          show-icon
          :closable="false"
          style="margin-top:12px"
        />
      </div>

      <div class="card-box">
        <h3 style="margin-bottom:12px">我的资质材料</h3>
        <el-table :data="certs" stripe v-loading="loading">
          <el-table-column label="材料类型" min-width="140">
            <template #default="{ row }">
              {{ row.doc_name || certTypeText(row.cert_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="cert_number" label="证件编号" min-width="150" />
          <el-table-column prop="expire_date" label="有效期" width="120" />
          <el-table-column label="AI置信度" width="100">
            <template #default="{ row }">
              {{ row.ai_confidence ? Math.round(row.ai_confidence * 100) + '%' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">
                {{ statusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="候选标签" min-width="180">
            <template #default="{ row }">
              <el-tag
                v-for="tag in row.suggested_tags || []"
                :key="tag.tag_code"
                size="small"
                style="margin:2px"
              >
                {{ tag.tag_name || tag.tag_code }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="card-box">
        <h3 style="margin-bottom:16px">上传新资质</h3>
        <el-form label-width="90px">
          <el-form-item label="材料类型">
            <el-select v-model="certType" style="width:260px">
              <el-option v-for="item in certTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="证件图片">
            <el-upload
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :file-list="fileList"
              list-type="picture"
              accept="image/*"
            >
              <el-button type="primary">选择图片</el-button>
              <template #tip>
                <div style="color:#909399;font-size:12px">仅支持 JPG/PNG 格式，大小不超过 5MB</div>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="uploading" @click="uploadCert" :disabled="!selectedFile">
              上传并AI识别
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-if="ocrResult" class="card-box">
        <h3>AI识别结果</h3>
        <el-descriptions :column="2" border style="margin-top:12px">
          <el-descriptions-item label="置信度">
            {{ Math.round((ocrResult.confidence || 0) * 100) }}%
          </el-descriptions-item>
          <el-descriptions-item label="下一步">等待人工审核</el-descriptions-item>
          <el-descriptions-item
            v-for="(val, key) in ocrResult.extracted_fields || {}"
            :key="key"
            :label="fieldLabel(key)"
          >
            {{ val || '-' }}
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:12px">
          <el-tag v-for="tag in ocrResult.suggested_tags || []" :key="tag.tag_code" style="margin:2px">
            {{ tag.tag_name || tag.tag_code }}
          </el-tag>
        </div>
        <el-alert
          v-for="flag in ocrResult.risk_flags || []"
          :key="flag.code"
          :title="flag.message"
          type="warning"
          show-icon
          :closable="false"
          style="margin-top:12px"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { uploadCert as uploadCertApi, getCertList, getQualificationProfile } from '../../api/certification'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const certs = ref([])
const profile = ref(null)
const loading = ref(false)
const certType = ref('id_card')
const selectedFile = ref(null)
const fileList = ref([])
const uploading = ref(false)
const ocrResult = ref(null)

const certTypeOptions = [
  { label: '身份证实名核验', value: 'id_card' },
  { label: '健康证明/体检报告', value: 'health_certificate' },
  { label: '无犯罪记录证明', value: 'no_criminal_record' },
  { label: '背景核查授权', value: 'background_check_authorization' },
  { label: '家政服务证书', value: 'housekeeping_certificate' },
  { label: '母婴护理证书', value: 'maternity_matron_certificate' },
  { label: '育婴照护证书', value: 'infant_care_certificate' },
  { label: '养老护理证书', value: 'elderly_care_certificate' },
  { label: '病患陪护证书', value: 'medical_caregiver_certificate' },
  { label: '基础急救证书', value: 'first_aid_certificate' },
  { label: '服务保险/意外险', value: 'insurance_policy' },
]

onMounted(async () => {
  await fetchCerts()
  await fetchQualificationProfile()
})

async function fetchCerts() {
  loading.value = true
  try {
    const res = await getCertList(userStore.token)
    certs.value = res.data || []
  } finally { loading.value = false }
}

async function fetchQualificationProfile() {
  const providerId = userStore.user?.id
  if (!providerId) return
  try {
    const res = await getQualificationProfile(providerId)
    profile.value = res.data
  } catch { /* ignore */ }
}

function handleFileChange(file) {
  selectedFile.value = file.raw
  fileList.value = [file]
}

async function uploadCert() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择证件图片')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('token', userStore.token)
    formData.append('cert_type', certType.value)
    formData.append('file', selectedFile.value)
    const res = await uploadCertApi(formData)
    ocrResult.value = res.data?.ocr_result
    ElMessage.success('AI已识别，等待平台人工审核')
    await fetchCerts()
    await fetchQualificationProfile()
    await userStore.fetchProfile()
    selectedFile.value = null
    fileList.value = []
  } finally { uploading.value = false }
}

function certTypeText(type) {
  return certTypeOptions.find(item => item.value === type)?.label || {
    health_cert: '健康证',
    qualification: '资格证',
  }[type] || type
}

function statusText(status) {
  return { pending: '待审核', passed: '已通过', expired: '已过期', rejected: '已驳回' }[status] || status
}

function statusType(status) {
  return status === 'passed' ? 'success' : status === 'rejected' ? 'danger' : status === 'expired' ? 'danger' : 'warning'
}

function trustText(level) {
  return { 1: '本人填写', 2: '已上传', 3: 'AI识别', 4: '平台审核', 5: '权威核验' }[level] || '待确认'
}

function completenessText(value) {
  return { high: '高', medium: '中', low: '低' }[value] || value
}

function fieldLabel(key) {
  return {
    doc_type: '证件类型',
    certificate_name: '证件名称',
    holder_name: '持证人姓名',
    certificate_no: '证件号码',
    issuing_authority: '发证机构',
    issue_date: '签发日期',
    expire_date: '有效期',
    level: '等级',
  }[key] || key
}
</script>
