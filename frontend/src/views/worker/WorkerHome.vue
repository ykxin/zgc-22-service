<template>
  <div>
    <NavBar active-menu="/worker/home" />
    <div class="page-container">
      <div class="page-header">
        <h2>工作台</h2>
        <p>欢迎回来，{{ user?.nickname }}！信用分：{{ user?.credit_score }} | 风险：{{ user?.risk_level }}</p>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card">
          <div class="stat-num">{{ stats.pending }}</div>
          <div class="stat-label">待接单</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.inProgress }}</div>
          <div class="stat-label">进行中</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ user?.credit_score || '-' }}</div>
          <div class="stat-label">信用评分</div>
        </div>
      </div>

      <!-- 到期提醒 -->
      <div v-if="expiringCerts.length > 0" class="card-box" style="background:#fef0f0;border:1px solid #fde2e2">
        <h4 style="color:#f56c6c">证件到期提醒</h4>
        <p v-for="c in expiringCerts" :key="c.cert_id" style="margin:4px 0">
          {{ c.cert_type }} 将于 {{ c.expire_date }} 到期（剩余{{ c.days_left }}天），请及时更新
        </p>
      </div>

      <!-- 待处理预约 -->
      <div class="card-box">
        <h3 style="margin-bottom:12px">待处理的预约</h3>
        <el-table :data="pendingOrders" stripe v-loading="loading">
          <el-table-column prop="order_no" label="订单编号" width="180" />
          <el-table-column prop="service_category" label="服务类别" width="100" />
          <el-table-column prop="service_date" label="服务日期" width="120" />
          <el-table-column prop="service_time" label="时段" width="80" />
          <el-table-column prop="address" label="地址" />
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button type="success" size="small" @click="handleAccept(row)">接单</el-button>
              <el-button type="danger" size="small" @click="handleReject(row)">拒绝</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && pendingOrders.length === 0" description="暂无待处理的预约" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getOrders } from '../../api/order'
import { acceptBooking, rejectBooking } from '../../api/matching'
import { checkExpiring } from '../../api/certification'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const user = ref(userStore.user)
const loading = ref(false)
const pendingOrders = ref([])
const expiringCerts = ref([])
const stats = reactive({ pending: 0, inProgress: 0, completed: 0 })

onMounted(async () => {
  await Promise.all([fetchOrders(), fetchExpiring(), fetchStats()])
})

async function fetchOrders() {
  loading.value = true
  try {
    const res = await getOrders(userStore.token, { status: 'pending' })
    pendingOrders.value = res.data.list
  } finally { loading.value = false }
}

async function fetchExpiring() {
  try {
    const res = await checkExpiring(userStore.token)
    expiringCerts.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchStats() {
  try {
    const [pendingRes, progressRes, completedRes] = await Promise.all([
      getOrders(userStore.token, { status: 'pending', page_size: 1 }),
      getOrders(userStore.token, { status: 'in_progress', page_size: 1 }),
      getOrders(userStore.token, { status: 'completed', page_size: 1 }),
    ])
    stats.pending = pendingRes.data?.total || 0
    stats.inProgress = progressRes.data?.total || 0
    stats.completed = completedRes.data?.total || 0
  } catch { /* ignore */ }
}

async function handleAccept(row) {
  try {
    await acceptBooking(row.id, userStore.token)
    ElMessage.success('已接单')
    fetchOrders()
    fetchStats()
  } catch { /* ignore */ }
}

async function handleReject(row) {
  try {
    await rejectBooking(row.id, userStore.token)
    ElMessage.success('已拒绝')
    fetchOrders()
    fetchStats()
  } catch { /* ignore */ }
}
</script>
