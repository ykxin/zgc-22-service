<template>
  <div>
    <NavBar active-menu="/worker/cert" />
    <div class="page-container" style="max-width:800px">
      <div class="page-header">
        <h2>AI资质核验</h2>
        <p>上传身份证、健康证、资格证，AI自动识别和校验，通过后生成信用评分</p>
      </div>

      <!-- 已有资质 -->
      <div class="card-box">
        <h3 style="margin-bottom:12px">我的资质</h3>
        <el-table :data="certs" stripe v-loading="loading">
          <el-table-column prop="cert_type" label="证件类型" width="120">
            <template #default="{ row }">
              {{ { id_card: '身份证', health_cert: '健康证', qualification: '资格证' }[row.cert_type] || row.cert_type }}
            </template>
          </el-table-column>
          <el-table-column prop="cert_number" label="证件编号" />
          <el-table-column prop="real_name" label="姓名" width="80" />
          <el-table-column prop="expire_date" label="有效期" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'passed' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
                {{ { pending: '待审核', passed: '已通过', expired: '已过期', rejected: '已驳回' }[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 上传资质 -->
      <div class="card-box">
        <h3 style="margin-bottom:16px">上传新资质</h3>
        <el-form label-width="80px">
          <el-form-item label="证件类型">
            <el-select v-model="certType" style="width:200px">
              <el-option label="身份证" value="id_card" />
              <el-option label="健康证" value="health_cert" />
              <el-option label="资格证" value="qualification" />
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
              上传并AI核验
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- OCR识别结果 -->
      <div v-if="ocrResult" class="card-box">
        <h3>AI识别结果</h3>
        <el-descriptions :column="2" border style="margin-top:12px">
          <el-descriptions-item v-for="(val, key) in ocrResult" :key="key" :label="key">
            {{ val }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { uploadCert as uploadCertApi, getCertList } from '../../api/certification'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const certs = ref([])
const loading = ref(false)
const certType = ref('id_card')
const selectedFile = ref(null)
const fileList = ref([])
const uploading = ref(false)
const ocrResult = ref(null)

onMounted(fetchCerts)

async function fetchCerts() {
  loading.value = true
  try {
    const res = await getCertList(userStore.token)
    certs.value = res.data || []
  } finally { loading.value = false }
}

function handleFileChange(file) {
  selectedFile.value = file.raw
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
    ElMessage.success(res.msg)
    fetchCerts()
    await userStore.fetchProfile()
    selectedFile.value = null
    fileList.value = []
  } finally { uploading.value = false }
}
</script>
