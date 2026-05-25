<template>
  <div>
    <NavBar active-menu="/admin/sops" />
    <div class="page-container" style="max-width:900px">
      <div class="page-header flex-between">
        <div>
          <h2>SOP服务标准管理</h2>
          <p>管理保洁、育儿、养老陪护三大类服务标准步骤</p>
        </div>
        <el-button type="primary" @click="showAddDialog">新增步骤</el-button>
      </div>

      <el-tabs v-model="activeCategory" @tab-change="fetchSops">
        <el-tab-pane label="保洁" name="保洁" />
        <el-tab-pane label="育儿" name="育儿" />
        <el-tab-pane label="养老陪护" name="养老陪护" />
      </el-tabs>

      <el-table :data="sops" stripe v-loading="loading" row-key="id">
        <el-table-column prop="step_order" label="序号" width="60" />
        <el-table-column prop="name" label="步骤名称" width="150" />
        <el-table-column prop="description" label="步骤说明" />
        <el-table-column prop="default_score" label="默认分值" width="100" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '上架' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button
              size="small"
              :type="row.status === 1 ? 'warning' : 'success'"
              @click="handleToggle(row)"
            >
              {{ row.status === 1 ? '下架' : '上架' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑步骤' : '新增步骤'" width="450px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="服务类别">
          <el-select v-model="form.category" :disabled="!!editingId">
            <el-option label="保洁" value="保洁" />
            <el-option label="育儿" value="育儿" />
            <el-option label="养老陪护" value="养老陪护" />
          </el-select>
        </el-form-item>
        <el-form-item label="步骤名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="步骤序号"><el-input-number v-model="form.step_order" :min="1" :max="20" /></el-form-item>
        <el-form-item label="步骤说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="默认分值"><el-input-number v-model="form.default_score" :min="1" :max="50" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveSop">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NavBar from '../../components/NavBar.vue'
import { getAdminSops, createSop, updateSop, toggleSop } from '../../api/admin'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const activeCategory = ref('保洁')
const sops = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({ category: '保洁', name: '', step_order: 1, description: '', default_score: 10 })

onMounted(fetchSops)

async function fetchSops() {
  loading.value = true
  try {
    const res = await getAdminSops(userStore.token, activeCategory.value)
    sops.value = res.data || []
  } finally { loading.value = false }
}

function showAddDialog() {
  editingId.value = null
  form.category = activeCategory.value
  form.name = ''
  form.step_order = sops.value.length + 1
  form.description = ''
  form.default_score = 10
  dialogVisible.value = true
}

function showEditDialog(row) {
  editingId.value = row.id
  form.category = row.category
  form.name = row.name
  form.step_order = row.step_order
  form.description = row.description
  form.default_score = row.default_score
  dialogVisible.value = true
}

async function saveSop() {
  if (!form.name) { ElMessage.warning('请输入步骤名称'); return }
  saving.value = true
  try {
    if (editingId.value) {
      await updateSop(editingId.value, userStore.token, form)
    } else {
      await createSop(userStore.token, form)
    }
    ElMessage.success(editingId.value ? '修改成功' : '新增成功')
    dialogVisible.value = false
    fetchSops()
  } finally { saving.value = false }
}

async function handleToggle(row) {
  try {
    await toggleSop(row.id, userStore.token)
    ElMessage.success('状态已切换')
    fetchSops()
  } catch { /* ignore */ }
}
</script>
