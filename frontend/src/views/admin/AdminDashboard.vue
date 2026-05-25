<template>
  <div>
    <NavBar active-menu="/admin/dashboard" />
    <div class="page-container">
      <div class="page-header"><h2>管理后台 - 数据面板</h2></div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card">
          <div class="stat-num">{{ dashboard['用户统计']?.['雇主数'] || 0 }}</div>
          <div class="stat-label">雇主数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ dashboard['用户统计']?.['从业者数'] || 0 }}</div>
          <div class="stat-label">从业者数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ dashboard['订单统计']?.['总订单数'] || 0 }}</div>
          <div class="stat-label">总订单数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ dashboard['订单统计']?.['已完成订单'] || 0 }}</div>
          <div class="stat-label">已完成</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ dashboard['订单统计']?.['匹配成功率'] || '0%' }}</div>
          <div class="stat-label">匹配成功率</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ dashboard['纠纷统计']?.['纠纷率'] || '0%' }}</div>
          <div class="stat-label">纠纷率</div>
        </div>
      </div>

      <!-- 详细数据 -->
      <el-row :gutter="16">
        <el-col :span="12">
          <div class="card-box">
            <h3 style="margin-bottom:12px">订单统计</h3>
            <el-descriptions direction="vertical" :column="2" border>
              <el-descriptions-item label="总订单数">{{ dashboard['订单统计']?.['总订单数'] || 0 }}</el-descriptions-item>
              <el-descriptions-item label="已完成">{{ dashboard['订单统计']?.['已完成订单'] || 0 }}</el-descriptions-item>
              <el-descriptions-item label="匹配成功率">{{ dashboard['订单统计']?.['匹配成功率'] || '0%' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="card-box">
            <h3 style="margin-bottom:12px">纠纷统计</h3>
            <el-descriptions direction="vertical" :column="2" border>
              <el-descriptions-item label="总纠纷数">{{ dashboard['纠纷统计']?.['总纠纷数'] || 0 }}</el-descriptions-item>
              <el-descriptions-item label="已判定">{{ dashboard['纠纷统计']?.['已判定纠纷'] || 0 }}</el-descriptions-item>
              <el-descriptions-item label="纠纷率">{{ dashboard['纠纷统计']?.['纠纷率'] || '0%' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>
      </el-row>

      <!-- 类别分布 -->
      <div class="card-box mt-16">
        <h3 style="margin-bottom:12px">服务类别分布</h3>
        <el-table :data="dashboard['类别分布'] || []" stripe>
          <el-table-column prop="类别" label="类别" />
          <el-table-column prop="订单数" label="订单数" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../../components/NavBar.vue'
import { getDashboard } from '../../api/admin'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const dashboard = ref({})

onMounted(async () => {
  try {
    const res = await getDashboard(userStore.token)
    dashboard.value = res.data || {}
  } catch { /* ignore */ }
})
</script>
