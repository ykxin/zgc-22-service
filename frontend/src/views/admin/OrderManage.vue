<template>
  <div>
    <NavBar active-menu="/admin/orders" />
    <div class="page-container">
      <div class="page-header"><h2>订单管理</h2></div>
      <el-table :data="orders" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="order_no" label="订单编号" width="180" />
        <el-table-column prop="employer_id" label="雇主ID" width="80" />
        <el-table-column prop="worker_id" label="从业者ID" width="80" />
        <el-table-column prop="service_category" label="服务类别" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="'status-' + row.status">{{ statusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="acceptance_score" label="验收分" width="80" />
        <el-table-column prop="price" label="金额" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        style="margin-top:16px;justify-content:center"
        background layout="prev, pager, next" :total="total" :page-size="pageSize"
        v-model:current-page="page" @current-change="fetchOrders"
      />

      <!-- 纠纷管理 -->
      <div class="page-header mt-16"><h2>纠纷管理</h2></div>
      <el-table :data="disputes" stripe v-loading="disputeLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="order_id" label="订单ID" width="80" />
        <el-table-column prop="dispute_type" label="类型" width="100">
          <template #default="{ row }">
            {{ { service_quality: '服务质量', salary: '薪资', item_damage: '物品损耗' }[row.dispute_type] }}
          </template>
        </el-table-column>
        <el-table-column prop="responsible_party" label="责任方" width="80">
          <template #default="{ row }">
            {{ { employer: '雇主', worker: '从业者', both: '双方' }[row.responsible_party] || row.responsible_party }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'judged' ? 'success' : 'warning'" size="small">
              {{ { pending: '待处理', judged: '已判定', executed: '已执行' }[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../../components/NavBar.vue'
import { getAllOrders, getAllDisputes } from '../../api/admin'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const orders = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const pageSize = ref(10)
const disputes = ref([])
const disputeLoading = ref(false)

const statusLabel = (s) => ({ pending: '待接单', accepted: '已接单', in_progress: '服务中', done: '待评价', completed: '已完成', cancelled: '已取消' }[s] || s)

onMounted(() => { fetchOrders(); fetchDisputes() })

async function fetchOrders() {
  loading.value = true
  try {
    const res = await getAllOrders(userStore.token, { page: page.value, page_size: pageSize.value })
    orders.value = res.data.list
    total.value = res.data.total
  } finally { loading.value = false }
}

async function fetchDisputes() {
  disputeLoading.value = true
  try {
    const res = await getAllDisputes(userStore.token, { page_size: 50 })
    disputes.value = res.data.list
  } finally { disputeLoading.value = false }
}
</script>
