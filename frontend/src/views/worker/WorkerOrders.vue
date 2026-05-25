<template>
  <div>
    <NavBar active-menu="/worker/orders" />
    <div class="page-container">
      <div class="page-header"><h2>我的订单</h2></div>

      <div class="card-box">
        <el-radio-group v-model="filterStatus" @change="fetchOrders">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pending">待接单</el-radio-button>
          <el-radio-button value="accepted">已接单</el-radio-button>
          <el-radio-button value="in_progress">服务中</el-radio-button>
          <el-radio-button value="done">待评价</el-radio-button>
          <el-radio-button value="completed">已完成</el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="orders" stripe v-loading="loading">
        <el-table-column prop="order_no" label="订单编号" width="180" />
        <el-table-column prop="service_category" label="服务类别" width="100" />
        <el-table-column prop="service_date" label="服务日期" width="120" />
        <el-table-column prop="service_time" label="时段" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="'status-' + row.status">{{ statusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="acceptance_score" label="验收分" width="80" />
        <el-table-column prop="price" label="金额" width="80" />
        <el-table-column label="操作" min-width="200">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" type="success" size="small" @click="handleAccept(row)">接单</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" size="small" @click="handleReject(row)">拒绝</el-button>
            <el-button v-if="row.status === 'accepted'" type="primary" size="small" @click="startService(row)">开始服务</el-button>
            <el-button v-if="row.status === 'done'" type="success" size="small" @click="openReview(row)">评价</el-button>
            <el-button size="small" type="warning" @click="openDispute(row)">纠纷</el-button>
            <el-button size="small" @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top:16px;justify-content:center"
        background layout="prev, pager, next" :total="total" :page-size="pageSize"
        v-model:current-page="page" @current-change="fetchOrders"
      />
    </div>

    <!-- 评价弹窗 -->
    <el-dialog v-model="reviewVisible" title="评价雇主" width="400px">
      <el-form>
        <el-form-item label="评分"><el-rate v-model="reviewForm.rating" :max="5" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="reviewForm.content" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="reviewForm.tags" placeholder="如：沟通顺畅,尊重人" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="reviewing" @click="submitReview">提交</el-button>
      </template>
    </el-dialog>

    <!-- 纠纷弹窗 -->
    <el-dialog v-model="disputeVisible" title="发起纠纷" width="400px">
      <el-form>
        <el-form-item label="类型">
          <el-select v-model="disputeForm.dispute_type">
            <el-option label="服务质量" value="service_quality" />
            <el-option label="薪资争议" value="salary" />
            <el-option label="物品损耗" value="item_damage" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="disputeForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button type="warning" :loading="disputing" @click="submitDispute">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getOrders, getOrderDetail, updateOrderStatus } from '../../api/order'
import { acceptBooking, rejectBooking } from '../../api/matching'
import { createDispute, createReview } from '../../api/dispute'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const router = useRouter()
const orders = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const filterStatus = ref('')
const reviewVisible = ref(false)
const reviewing = ref(false)
const reviewForm = reactive({ order_id: 0, rating: 5, content: '', tags: '' })
const disputeVisible = ref(false)
const disputing = ref(false)
const disputeForm = reactive({ order_id: 0, dispute_type: 'service_quality', description: '' })

const statusLabel = (s) => ({ pending: '待接单', accepted: '已接单', in_progress: '服务中', done: '待评价', completed: '已完成', cancelled: '已取消' }[s] || s)

onMounted(fetchOrders)

async function fetchOrders() {
  loading.value = true
  try {
    const res = await getOrders(userStore.token, { page: page.value, page_size: pageSize.value, status: filterStatus.value || undefined })
    orders.value = res.data.list
    total.value = res.data.total
  } finally { loading.value = false }
}

async function handleAccept(row) {
  try {
    await acceptBooking(row.id, userStore.token)
    ElMessage.success('已接单')
    fetchOrders()
  } catch { /* ignore */ }
}

async function handleReject(row) {
  try {
    await rejectBooking(row.id, userStore.token)
    ElMessage.success('已拒绝')
    fetchOrders()
  } catch { /* ignore */ }
}

async function startService(row) {
  try {
    await updateOrderStatus(row.id, 'in_progress', userStore.token)
    ElMessage.success('服务已开始')
    router.push('/worker/checkin')
  } catch { /* ignore */ }
}

async function viewDetail(row) {
  try {
    const res = await getOrderDetail(row.id, userStore.token)
    ElMessage.info(JSON.stringify(res.data, null, 2))
  } catch { /* ignore */ }
}

function openReview(row) {
  reviewForm.order_id = row.id
  reviewForm.rating = 5
  reviewForm.content = ''
  reviewForm.tags = ''
  reviewVisible.value = true
}

async function submitReview() {
  reviewing.value = true
  try {
    await createReview(userStore.token, reviewForm)
    ElMessage.success('评价成功')
    reviewVisible.value = false
    fetchOrders()
  } finally { reviewing.value = false }
}

function openDispute(row) {
  disputeForm.order_id = row.id
  disputeVisible.value = true
}

async function submitDispute() {
  disputing.value = true
  try {
    await createDispute(userStore.token, disputeForm)
    ElMessage.success('纠纷已提交')
    disputeVisible.value = false
  } finally { disputing.value = false }
}
</script>
