<template>
  <div>
    <NavBar active-menu="/employer/booking" />
    <div class="page-container">
      <div class="page-header">
        <h2>预约服务</h2>
        <p>选择服务类别和时间，查看可匹配的从业者并发起预约</p>
      </div>
      <div class="card-box">
        <el-form inline>
          <el-form-item label="服务类别">
            <el-select v-model="category" style="width:140px">
              <el-option label="保洁" value="保洁" />
              <el-option label="育儿" value="育儿" />
              <el-option label="养老陪护" value="养老陪护" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchRecommend">查看推荐从业者</el-button>
          </el-form-item>
        </el-form>
      </div>
      <div v-if="workers.length > 0">
        <el-table :data="workers" stripe style="width:100%">
          <el-table-column prop="nickname" label="姓名" width="100" />
          <el-table-column prop="skills" label="技能" />
          <el-table-column prop="experience_years" label="经验(年)" width="80" />
          <el-table-column prop="credit_score" label="信用分" width="80" />
          <el-table-column prop="match_score" label="匹配分" width="80" />
          <el-table-column label="风险等级" width="90">
            <template #default="{ row }">
              <el-tag :type="row.risk_level === '低' ? 'success' : row.risk_level === '中' ? 'warning' : 'danger'" size="small">
                {{ row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openDialog(row)">预约</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="确认预约" width="420px">
      <el-form label-width="80px">
        <el-form-item label="从业者">{{ selected?.nickname }}</el-form-item>
        <el-form-item label="服务日期">
          <el-date-picker v-model="formDate" type="date" placeholder="选择日期" format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="服务时段">
          <el-select v-model="formTime" placeholder="选择时段">
            <el-option label="上午 8:00-12:00" value="上午" />
            <el-option label="下午 14:00-18:00" value="下午" />
            <el-option label="全天" value="全天" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formRemark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getRecommend, createBooking } from '../../api/matching'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const category = ref('保洁')
const workers = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const selected = ref(null)
const formDate = ref(null)
const formTime = ref('')
const formRemark = ref('')

async function fetchRecommend() {
  try {
    const res = await getRecommend(userStore.token, category.value)
    workers.value = res.data || []
  } catch { /* ignore */ }
}

function openDialog(row) {
  selected.value = row
  formDate.value = null
  formTime.value = ''
  formRemark.value = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formDate.value || !formTime.value) {
    ElMessage.warning('请选择日期和时段')
    return
  }
  submitting.value = true
  try {
    const yyyy = formDate.value.getFullYear()
    const mm = String(formDate.value.getMonth() + 1).padStart(2, '0')
    const dd = String(formDate.value.getDate()).padStart(2, '0')
    const serviceDate = `${yyyy}-${mm}-${dd}`
    await createBooking(userStore.token, {
      worker_id: selected.value.worker_id,
      service_category: category.value,
      service_date: serviceDate,
      service_time: formTime.value,
      remark: formRemark.value,
    })
    ElMessage.success('预约已发送')
    dialogVisible.value = false
  } finally { submitting.value = false }
}
</script>
