<template>
  <div>
    <NavBar active-menu="/employer/home" />
    <div class="page-container">
      <div class="page-header">
        <h2>AI智能推荐</h2>
        <p>基于您的画像，为您匹配最合适的家政从业者</p>
      </div>

      <!-- 服务类别选择 -->
      <div class="card-box">
        <el-radio-group v-model="serviceCategory" size="large">
          <el-radio-button value="保洁">保洁</el-radio-button>
          <el-radio-button value="育儿">育儿</el-radio-button>
          <el-radio-button value="养老陪护">养老陪护</el-radio-button>
        </el-radio-group>
        <el-button type="primary" style="margin-left:16px" :loading="loading" @click="fetchRecommend">
          开始匹配
        </el-button>
      </div>

      <!-- 匹配结果 -->
      <div v-if="matches.length > 0">
        <h3 style="margin-bottom:16px">为您匹配到 {{ matches.length }} 位从业者</h3>
        <div v-for="m in matches" :key="m.worker_id" class="card-box">
          <div class="flex-between" style="flex-wrap:wrap">
            <div style="flex:1;min-width:250px">
              <div class="flex-center" style="gap:12px;margin-bottom:8px">
                <el-avatar :size="50">{{ m.nickname?.[0] || '从' }}</el-avatar>
                <div>
                  <strong>{{ m.nickname }}</strong>
                  <span style="margin-left:8px;color:#909399;font-size:13px">{{ m.experience_years }}年经验</span>
                </div>
              </div>
              <p style="margin:4px 0;color:#606266">技能：{{ m.skills || '未填写' }}</p>
              <p style="color:#909399;font-size:13px">{{ m.address }}</p>
            </div>
            <div style="width:200px;text-align:center">
              <div style="font-size:28px;color:#409eff;font-weight:700">{{ m.match_score }}</div>
              <div style="font-size:12px;color:#909399">匹配得分</div>
              <div class="match-bar" style="margin-top:8px">
                <div class="match-bar-inner" :style="{ width: m.match_score + '%', background: m.match_score >= 80 ? '#67c23a' : m.match_score >= 60 ? '#e6a23c' : '#f56c6c' }"></div>
              </div>
            </div>
            <div style="width:120px;text-align:center">
              <div>信用分 <strong>{{ m.credit_score }}</strong></div>
              <el-tag :type="m.risk_level === '低' ? 'success' : m.risk_level === '中' ? 'warning' : 'danger'" size="small" style="margin-top:8px">
                风险{{ m.risk_level }}
              </el-tag>
              <el-button type="primary" size="small" style="margin-top:12px" @click="showBookDialog(m)">
                预约
              </el-button>
            </div>
          </div>
          <!-- 匹配详情 -->
          <el-collapse style="margin-top:12px">
            <el-collapse-item title="匹配详情">
              <div v-for="(val, key) in m.match_details" :key="key" style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f0f0f0">
                <span>{{ key }}</span>
                <span style="color:#409eff">{{ val }}分</span>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <el-empty v-else-if="!loading" description="请选择服务类别后点击开始匹配" />
    </div>

    <!-- 预约弹窗 -->
    <el-dialog v-model="bookVisible" title="确认预约" width="420px">
      <el-form :model="bookForm" label-width="80px">
        <el-form-item label="从业者">{{ selectedWorker?.nickname }}</el-form-item>
        <el-form-item label="服务类别">{{ serviceCategory }}</el-form-item>
        <el-form-item label="服务日期">
          <el-date-picker v-model="bookForm.service_date" type="date" placeholder="选择日期" format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="服务时段">
          <el-select v-model="bookForm.service_time" placeholder="选择时段">
            <el-option label="上午 8:00-12:00" value="上午" />
            <el-option label="下午 14:00-18:00" value="下午" />
            <el-option label="全天 8:00-18:00" value="全天" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务地址">
          <el-input v-model="bookForm.address" placeholder="请输入服务地址" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="bookForm.remark" type="textarea" :rows="2" placeholder="特殊要求说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bookVisible = false">取消</el-button>
        <el-button type="primary" :loading="booking" @click="confirmBooking">确认预约</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getRecommend, createBooking } from '../../api/matching'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const router = useRouter()
const serviceCategory = ref('保洁')
const loading = ref(false)
const matches = ref([])
const bookVisible = ref(false)
const booking = ref(false)
const selectedWorker = ref(null)

const bookForm = reactive({
  service_date: null,
  service_time: '',
  address: '',
  remark: '',
})

async function fetchRecommend() {
  loading.value = true
  try {
    const res = await getRecommend(userStore.token, serviceCategory.value)
    matches.value = res.data || []
  } finally { loading.value = false }
}

function showBookDialog(worker) {
  selectedWorker.value = worker
  bookForm.service_date = null
  bookForm.service_time = ''
  bookForm.address = userStore.user?.address || ''
  bookForm.remark = ''
  bookVisible.value = true
}

function formatDate(date) {
  if (!date) return ''
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

async function confirmBooking() {
  if (!bookForm.service_date || !bookForm.service_time) {
    ElMessage.warning('请选择服务日期和时段')
    return
  }
  if (!bookForm.address && !userStore.user?.address) {
    ElMessage.warning('请填写服务地址')
    return
  }
  booking.value = true
  try {
    await createBooking(userStore.token, {
      worker_id: selectedWorker.value.worker_id,
      service_category: serviceCategory.value,
      service_date: formatDate(bookForm.service_date),
      service_time: bookForm.service_time,
      address: bookForm.address || userStore.user?.address || '',
      remark: bookForm.remark,
    })
    ElMessage.success('预约已发送')
    bookVisible.value = false
    router.push('/employer/orders')
  } finally { booking.value = false }
}
</script>
