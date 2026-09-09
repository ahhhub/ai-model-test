<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="never">
          <div class="card-title"><span>发起新评测</span></div>
          <el-form label-position="top">
            <el-form-item label="评测名称">
              <el-input v-model="createForm.name" placeholder="例如：第一轮模型对比" />
            </el-form-item>
            <el-form-item label="参与模型（可多选）" required>
              <el-select v-model="createForm.model_ids" multiple collapse-tags style="width: 100%"
                placeholder="选择参与评测的模型">
                <el-option v-for="m in models" :key="m.id" :label="`${m.display_name}（${m.name}）`" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="测试项目（可多选）" required>
              <el-select v-model="createForm.suite_ids" multiple collapse-tags style="width: 100%"
                placeholder="选择测试项目">
                <el-option v-for="s in suites" :key="s.id" :label="`${s.name}（${s.question_count} 题）`" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="题目难度">
              <el-select v-model="createForm.difficulty" style="width: 100%">
                <el-option label="全部难度" value="" />
                <el-option v-for="(label, key) in DIFF" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
            <el-form-item label="裁判模型（用于主观题自动评分）">
              <el-select v-model="createForm.judge_model_id" clearable style="width: 100%" placeholder="可选，不选则主观题跳过评分">
                <el-option v-for="m in models" :key="m.id" :label="`${m.display_name}（${m.name}）`" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-button type="primary" style="width: 100%" :loading="creating" @click="create">
              <el-icon><VideoPlay /></el-icon>&nbsp;开始评测
            </el-button>
          </el-form>
          <el-alert type="warning" :closable="false" style="margin-top: 12px"
            title="提示：评测将真实调用所选模型的 API 并产生费用，多模态题需要模型支持图像输入。" />
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never">
          <div class="card-title">
            <span>评测历史</span>
            <el-button size="small" @click="loadRuns"><el-icon><Refresh /></el-icon>&nbsp;刷新</el-button>
          </div>
          <el-table :data="runs" v-loading="loading" border stripe @row-click="openDetail" style="cursor: pointer">
            <el-table-column prop="id" label="ID" width="55" />
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column label="难度" width="90">
              <template #default="{ row }">{{ row.difficulty ? DIFF[row.difficulty] || row.difficulty : '全部' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)">{{ statusName(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" min-width="160">
              <template #default="{ row }">
                <el-progress :percentage="row.total ? Math.round(row.done / row.total * 100) : 0"
                  :status="row.status === 'completed' ? 'success' : undefined" :stroke-width="14" />
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160" />
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="danger" text @click.stop="remove(row)">删除</el-button>
                <el-button v-if="row.status === 'running'" size="small" type="warning" text @click.stop="stop(row)">停止</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-drawer v-model="detailVisible" :title="detailRun ? `评测 #${detailRun.id} ${detailRun.name}` : '评测详情'" size="78%">
      <template v-if="detailRun">
        <el-progress v-if="detailRun.status === 'running'" :percentage="detailRun.total ? Math.round(detailRun.done / detailRun.total * 100) : 0" :stroke-width="16" striped striped-flow />
        <h4>各模型得分（0-100）</h4>
        <el-table :data="summaryRows" border size="small" style="margin-bottom: 16px">
          <el-table-column prop="model_name" label="模型" min-width="140" fixed />
          <el-table-column v-for="s in resultSuites" :key="s.id" :label="s.name" min-width="120">
            <template #default="{ row }">
              <span v-if="row.suites[s.key]">{{ row.suites[s.key].score }}</span>
              <span v-else style="color:#c0c4cc">—</span>
            </template>
          </el-table-column>
          <el-table-column label="总分" width="90" sortable prop="overall">
            <template #default="{ row }"><b>{{ row.overall ?? '—' }}</b></template>
          </el-table-column>
          <el-table-column label="总耗时" width="100">
            <template #default="{ row }">{{ row.total_seconds != null ? row.total_seconds + ' s' : '—' }}</template>
          </el-table-column>
          <el-table-column label="平均耗时" width="100">
            <template #default="{ row }">{{ row.avg_seconds != null ? row.avg_seconds + ' s' : '—' }}</template>
          </el-table-column>
          <el-table-column label="输出速度" width="110">
            <template #default="{ row }">{{ row.speed != null ? row.speed + ' tok/s' : '—' }}</template>
          </el-table-column>
        </el-table>
        <h4>答题明细</h4>
        <el-table :data="detailRows" border size="small" max-height="520">
          <el-table-column prop="model_name" label="模型" width="150" fixed />
          <el-table-column prop="suite_name" label="题库" width="130" />
          <el-table-column prop="question_title" label="题目" min-width="150" show-overflow-tooltip />
          <el-table-column label="得分" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.error" type="danger" size="small">错误</el-tag>
              <el-tag v-else :type="(row.score ?? 0) >= (row.max_score ?? 1) ? 'success' : 'info'" size="small">
                {{ row.score }} / {{ row.max_score }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="latency_ms" label="耗时" width="90">
            <template #default="{ row }">{{ row.latency_ms != null ? row.latency_ms + ' ms' : '—' }}</template>
          </el-table-column>
          <el-table-column label="模型回答 / 错误信息" min-width="280">
            <template #default="{ row }">
              <el-popover placement="left" width="480" trigger="click">
                <template #reference>
                  <el-link type="primary">{{ row.error ? row.error : (row.answer || '').slice(0, 60) || '—' }}</el-link>
                </template>
                <div style="white-space: pre-wrap; max-height: 400px; overflow: auto">{{ row.error || row.answer }}</div>
                <div v-if="row.detail" style="margin-top: 8px; color: #909399">{{ row.detail }}</div>
              </el-popover>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const models = ref([])
const suites = ref([])
const runs = ref([])
const loading = ref(false)
const creating = ref(false)
const detailVisible = ref(false)
const detailRun = ref(null)
const detailData = ref(null)
let pollTimer = null

const createForm = reactive({ name: '', model_ids: [], suite_ids: [], judge_model_id: null, difficulty: '' })
const DIFF = { easy: '简单', medium: '中等', medium_high: '中高', hard: '高难', extreme: '极难' }

const statusName = s => ({ pending: '排队中', running: '运行中', completed: '已完成', stopped: '已停止', failed: '失败' })[s] || s
const statusType = s => ({ pending: 'info', running: 'warning', completed: 'success', stopped: 'info', failed: 'danger' })[s] || 'info'

const resultSuites = computed(() => detailData.value?.suites || [])
const summaryRows = computed(() => {
  if (!detailData.value) return []
  const { models: ms, results } = detailData.value
  return ms.map(m => {
    const rows = results.filter(r => r.model_id === m.id)
    const bySuite = {}
    for (const s of resultSuites.value) {
      const vals = rows.filter(r => r.suite_id === s.id && r.max_score && r.error === '')
      if (vals.length) bySuite[s.key] = { score: Math.round(vals.reduce((a, b) => a + b.score / b.max_score, 0) / vals.length * 1000) / 10 }
    }
    const suiteScores = Object.values(bySuite).map(v => v.score)
    const overall = suiteScores.length ? Math.round(suiteScores.reduce((a, b) => a + b, 0) / suiteScores.length * 10) / 10 : null
    const okRows = rows.filter(r => !r.error && r.latency_ms != null)
    const totalMs = okRows.reduce((a, b) => a + b.latency_ms, 0)
    const tokens = okRows.reduce((a, b) => a + (b.output_tokens || 0), 0)
    return {
      model_id: m.id,
      model_name: m.display_name || m.name,
      suites: bySuite,
      overall,
      total_seconds: okRows.length ? Math.round(totalMs / 100) / 10 : null,
      avg_seconds: okRows.length ? Math.round(totalMs / okRows.length / 100) / 10 : null,
      speed: totalMs && tokens ? Math.round(tokens / (totalMs / 1000)) : null
    }
  }).sort((a, b) => (b.overall ?? -1) - (a.overall ?? -1))
})
const detailRows = computed(() => {
  if (!detailData.value) return []
  const ms = Object.fromEntries(detailData.value.models.map(m => [m.id, m.display_name || m.name]))
  const ss = Object.fromEntries(detailData.value.suites.map(s => [s.id, s.name]))
  const qs = {}
  return detailData.value.results.map(r => ({
    ...r,
    model_name: ms[r.model_id],
    suite_name: ss[r.suite_id],
    question_title: r.question_id
  }))
})

async function loadBase() {
  models.value = await api.listModels()
  suites.value = await api.listSuites()
}

async function loadRuns() {
  loading.value = true
  try { runs.value = await api.listRuns() } finally { loading.value = false }
}

async function create() {
  if (!createForm.model_ids.length) { ElMessage.warning('请选择参与模型'); return }
  if (!createForm.suite_ids.length) { ElMessage.warning('请选择测试项目'); return }
  creating.value = true
  try {
    const run = await api.createRun({ ...createForm })
    ElMessage.success('评测已开始')
    createForm.name = ''
    loadRuns()
    startPolling(run.id)
    openDetailById(run.id)
  } finally { creating.value = false }
}

function startPolling(runId) {
  stopPolling()
  pollTimer = setInterval(async () => {
    const run = await api.getRun(runId)
    if (run.status === 'completed' || run.status === 'stopped' || run.status === 'failed') {
      stopPolling()
      loadRuns()
      if (detailVisible.value && detailRun.value?.id === runId) openDetailById(runId)
    }
    if (detailVisible.value && detailRun.value?.id === runId && run.status === 'running') {
      detailData.value = await api.getResults(runId)
    }
  }, 2500)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function openDetail(row) { await openDetailById(row.id) }

async function openDetailById(id) {
  detailVisible.value = true
  detailRun.value = await api.getRun(id)
  detailData.value = await api.getResults(id)
}

async function stop(row) {
  await api.stopRun(row.id)
  ElMessage.success('已请求停止')
  loadRuns()
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除评测「${row.name}」及其所有结果吗？`, '提示', { type: 'warning' })
  await api.deleteRun(row.id)
  ElMessage.success('已删除')
  loadRuns()
}

onMounted(async () => {
  await Promise.all([loadBase(), loadRuns()])
  const running = runs.value.find(r => r.status === 'running')
  if (running) startPolling(running.id)
})

onBeforeUnmount(stopPolling)
</script>
