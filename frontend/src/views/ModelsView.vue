<template>
  <div>
    <el-card shadow="never">
      <div class="card-title">
        <span>已接入模型</span>
        <el-button type="primary" @click="openDialog()">
          <el-icon><Plus /></el-icon>&nbsp;添加模型
        </el-button>
      </div>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 12px"
        title="填写模型调用名称与 API Key 即可添加，兼容所有 OpenAI 协议服务（可自定义 Base URL，如 DeepSeek、通义千问、智谱等）。" />
      <el-table :data="models" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="display_name" label="展示名称" min-width="140" />
        <el-table-column prop="name" label="模型调用名称" min-width="160" />
        <el-table-column prop="base_url" label="Base URL" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.base_url || 'https://api.openai.com/v1' }}</template>
        </el-table-column>
        <el-table-column label="思考模式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.disable_thinking ? 'success' : 'warning'" size="small">
              {{ row.disable_thinking ? '已关闭' : '开启' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="API Key" min-width="120">
          <template #default="{ row }">{{ row.api_key ? '••••' + row.api_key.slice(-4) : '—' }}</template>
        </el-table-column>
        <el-table-column label="连通性" width="130">
          <template #default="{ row }">
            <el-tag v-if="testState[row.id] === 'testing'" type="info">测试中…</el-tag>
            <el-tag v-else-if="testState[row.id] === 'ok'" type="success">✓ 正常</el-tag>
            <el-tag v-else-if="testState[row.id] === 'fail'" type="danger">✗ 失败</el-tag>
            <el-tag v-else type="warning">未测试</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="testConnect(row)">测试连接</el-button>
            <el-button size="small" type="primary" plain @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑模型' : '添加模型'" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="展示名称" required>
          <el-input v-model="form.display_name" placeholder="例如：GPT-4o / DeepSeek-V3" />
        </el-form-item>
        <el-form-item label="模型调用名称" required>
          <el-input v-model="form.name" placeholder="例如：gpt-4o / deepseek-chat" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="留空默认 https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API Key" required>
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="关闭思考模式">
          <el-switch v-model="form.disable_thinking" />
          <div style="color:#909399; font-size:12px; margin-left: 8px">
            默认开启：调用时发送关闭思考参数（兼容不支持该参数的供应商会自动降级）
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialogVisible" title="连通性测试" width="520px">
      <template v-if="testResult">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="结果">
            <el-tag :type="testResult.ok ? 'success' : 'danger'">{{ testResult.ok ? '连接成功' : '连接失败' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="延迟">{{ testResult.latency_ms ?? '—' }} ms</el-descriptions-item>
          <el-descriptions-item label="模型回复">{{ testResult.reply || testResult.error || '—' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const models = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const testResult = ref(null)
const testState = reactive({})

const form = reactive({ id: null, display_name: '', name: '', base_url: '', api_key: '', disable_thinking: true })

async function load() {
  loading.value = true
  try { models.value = await api.listModels() } finally { loading.value = false }
}

function openDialog(row) {
  Object.assign(form, row
    ? { id: row.id, display_name: row.display_name, name: row.name, base_url: row.base_url, api_key: row.api_key, disable_thinking: !!row.disable_thinking }
    : { id: null, display_name: '', name: '', base_url: '', api_key: '', disable_thinking: true })
  dialogVisible.value = true
}

async function save() {
  if (!form.display_name || !form.name || !form.api_key) {
    ElMessage.warning('请填写展示名称、模型调用名称与 API Key')
    return
  }
  if (form.id) await api.updateModel(form.id, form)
  else await api.addModel(form)
  dialogVisible.value = false
  ElMessage.success('保存成功')
  load()
}

async function testConnect(row) {
  testState[row.id] = 'testing'
  testDialogVisible.value = true
  testResult.value = null
  const res = await api.testModel(row.id)
  testResult.value = res
  testState[row.id] = res.ok ? 'ok' : 'fail'
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除模型「${row.display_name}」吗？`, '提示', { type: 'warning' })
  await api.deleteModel(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>
