<template>
  <div>
    <NavBar active-menu="/worker/checkin" />
    <div class="page-container" style="max-width:800px">
      <div class="page-header">
        <h2>服务打卡</h2>
        <p>按SOP步骤逐项打卡，上传照片验证，AI自动验收打分</p>
      </div>

      <!-- 选择订单 -->
      <div class="card-box">
        <el-form inline>
          <el-form-item label="选择订单">
            <el-select v-model="selectedOrderId" placeholder="请选择进行中的订单" style="width:300px" @change="loadSop">
              <el-option v-for="o in activeOrders" :key="o.id" :label="`${o.order_no} - ${o.service_category}`" :value="o.id" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="startService" :disabled="!selectedOrderId">
              开始服务
            </el-button>
          </el-form-item>
          <el-form-item>
            <el-button @click="loadActiveOrders">刷新订单</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- SOP打卡步骤 -->
      <div v-if="sopSteps.length > 0 && serviceStarted" class="card-box">
        <h3 style="margin-bottom:8px">SOP服务步骤</h3>
        <p style="color:#909399;margin-bottom:16px">请按顺序完成每项，上传照片可获得额外加分</p>
        <div v-for="step in sopSteps" :key="step.step_order" class="card-box" style="background:#fafafa">
          <div class="flex-between">
            <div>
              <strong>{{ step.step_order }}. {{ step.name }}</strong>
              <span style="color:#909399;margin-left:12px;font-size:13px">满分{{ step.default_score }}分</span>
            </div>
            <div class="flex-center" style="gap:8px">
              <el-upload
                :auto-upload="false"
                :show-file-list="false"
                :on-change="(file) => uploadStepPhoto(step, file)"
                accept="image/*"
              >
                <el-button size="small">拍照</el-button>
              </el-upload>
              <el-button
                size="small"
                :type="step.done ? 'success' : 'default'"
                @click="toggleStep(step)"
              >
                {{ step.done ? '已完成' : '标记完成' }}
              </el-button>
            </div>
          </div>
          <p v-if="step.description" style="color:#909399;font-size:13px;margin-top:4px">{{ step.description }}</p>
          <div v-if="step.photo">
            <el-tag size="small" type="success" style="margin-top:8px">照片已上传</el-tag>
          </div>
        </div>
      </div>

      <!-- AI验收 -->
      <div v-if="serviceStarted" style="text-align:center;margin-top:20px">
        <el-button type="primary" size="large" :loading="accepting" @click="submitAcceptance">
          AI智能验收
        </el-button>
        <p style="color:#909399;margin-top:8px">完成所有步骤后点击验收，AI将自动打分</p>
      </div>

      <!-- 视频分析 -->
      <div v-if="serviceStarted" class="card-box" style="margin-top:20px">
        <h3 style="margin-bottom:12px">服务视频分析</h3>
        <el-form inline>
          <el-form-item label="上传视频">
            <el-upload
              :auto-upload="false"
              :limit="1"
              :on-change="handleVideoChange"
              :file-list="videoList"
              accept="video/mp4,video/quicktime"
            >
              <el-button>选择视频</el-button>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="videoUploading" @click="uploadVideo">
              上传并分析
            </el-button>
          </el-form-item>
        </el-form>
        <div style="color:#909399;font-size:12px;margin-top:8px">
          支持 MP4/MOV，单个文件不超过 500MB
        </div>
      </div>

      <div v-if="videoResult" class="card-box">
        <h3>视频分析结果</h3>
        <el-descriptions :column="2" border style="margin-top:12px">
          <el-descriptions-item label="综合评分">{{ videoResult.video_score }}</el-descriptions-item>
          <el-descriptions-item label="SOP覆盖率">{{ (videoResult.sop_coverage_rate * 100).toFixed(0) }}%</el-descriptions-item>
          <el-descriptions-item label="与打卡一致">
            {{ videoResult.consistency_with_checkin ? '是' : '否' }}
          </el-descriptions-item>
          <el-descriptions-item label="分析时间">{{ videoResult.analyzed_at || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:12px">
          <h4 style="margin-bottom:8px">识别到的操作</h4>
          <el-tag v-for="(item, idx) in videoResult.action_summary || []" :key="idx" style="margin:2px">
            {{ item }}
          </el-tag>
          <el-empty v-if="!videoResult.action_summary || !videoResult.action_summary.length" description="暂无记录" :image-size="60" />
        </div>
        <div style="margin-top:12px">
          <h4 style="margin-bottom:8px">风险提示</h4>
          <el-alert
            v-for="(alert, idx) in videoResult.risk_alerts || []"
            :key="idx"
            :title="`${alert.timestamp} ${alert.description}`"
            type="warning"
            show-icon
            :closable="false"
            style="margin-top:8px"
          />
          <el-empty v-if="!videoResult.risk_alerts || !videoResult.risk_alerts.length" description="暂无风险提示" :image-size="60" />
        </div>
      </div>

      <!-- 验收结果 -->
      <div v-if="acceptanceResult" class="card-box">
        <h3>验收结果</h3>
        <div style="text-align:center;margin:20px 0">
          <div style="font-size:48px;font-weight:700" :style="{ color: acceptanceResult.total_score >= 80 ? '#67c23a' : acceptanceResult.total_score >= 60 ? '#e6a23c' : '#f56c6c' }">
            {{ acceptanceResult.total_score }}
          </div>
          <div style="font-size:16px;color:#909399">综合得分 · {{ acceptanceResult.grade }}</div>
        </div>
        <el-table :data="acceptanceResult.details" stripe size="small">
          <el-table-column prop="步骤" label="步骤" />
          <el-table-column prop="满分" label="满分" width="80" />
          <el-table-column prop="得分" label="得分" width="80" />
          <el-table-column label="完成" width="80">
            <template #default="{ row }">{{ row['完成'] ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column label="有图" width="80">
            <template #default="{ row }">{{ row['有图片'] ? '是' : '否' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getOrders, getSops, doCheckin, doAcceptance } from '../../api/order'
import { uploadServiceVideo } from '../../api/video'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const activeOrders = ref([])
const selectedOrderId = ref(null)
const serviceStarted = ref(false)
const sopSteps = ref([])
const accepting = ref(false)
const acceptanceResult = ref(null)
const videoFile = ref(null)
const videoList = ref([])
const videoUploading = ref(false)
const videoResult = ref(null)

onMounted(loadActiveOrders)

async function loadActiveOrders() {
  try {
    const res = await getOrders(userStore.token, { page_size: 50 })
    activeOrders.value = (res.data?.list || []).filter(o => o.status === 'accepted' || o.status === 'in_progress')
  } catch { /* ignore */ }
}

async function loadSop() {
  const order = activeOrders.value.find(o => o.id === selectedOrderId.value)
  if (!order) return
  try {
    const res = await getSops(order.service_category)
    const categorySops = res.data?.[order.service_category] || []
    sopSteps.value = categorySops.map(s => ({ ...s, done: false, photo: null, photoFile: null }))
  } catch { /* ignore */ }
}

function startService() {
  if (!selectedOrderId.value) return
  serviceStarted.value = true
  acceptanceResult.value = null
  videoResult.value = null
}

function toggleStep(step) {
  step.done = !step.done
}

function uploadStepPhoto(step, file) {
  step.photo = file.name
  step.photoFile = file.raw
}

function handleVideoChange(file) {
  videoFile.value = file.raw
  videoList.value = [file]
}

async function uploadVideo() {
  if (!selectedOrderId.value) {
    ElMessage.warning('请先选择订单')
    return
  }
  if (!videoFile.value) {
    ElMessage.warning('请选择视频文件')
    return
  }
  videoUploading.value = true
  try {
    const formData = new FormData()
    formData.append('token', userStore.token)
    formData.append('order_id', selectedOrderId.value)
    formData.append('file', videoFile.value)
    const res = await uploadServiceVideo(formData)
    videoResult.value = res.data?.analysis_result || null
    ElMessage.success('视频已上传并完成分析')
    videoFile.value = null
    videoList.value = []
  } finally { videoUploading.value = false }
}

async function submitAcceptance() {
  // 先提交打卡记录
  const checkinPromises = sopSteps.value.map(step =>
    doCheckinForm(step)
  )
  await Promise.all(checkinPromises)

  // 执行AI验收
  accepting.value = true
  try {
    const res = await doAcceptance(selectedOrderId.value, userStore.token)
    acceptanceResult.value = res.data
    ElMessage.success(`验收完成，得分：${res.data.total_score}`)
  } finally { accepting.value = false }
}

async function doCheckinForm(step) {
  const formData = new FormData()
  formData.append('token', userStore.token)
  formData.append('order_id', selectedOrderId.value)
  formData.append('step_name', step.name)
  formData.append('step_order', step.step_order)
  formData.append('is_done', step.done ? 1 : 0)
  if (step.photoFile) {
    formData.append('file', step.photoFile)
  }
  try {
    await doCheckin(formData)
  } catch { /* ignore */ }
}
</script>
