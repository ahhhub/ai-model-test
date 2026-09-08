<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card shadow="never">
          <div class="card-title"><span>模型进步趋势（跨轮次对比）</span></div>
          <div style="display: flex; gap: 8px; margin-bottom: 12px">
            <el-select v-model="trendModel" style="width: 220px" placeholder="选择模型" @change="loadTrend">
              <el-option v-for="m in models" :key="m.id" :label="`${m.display_name}（${m.name}）`" :value="m.id" />
            </el-select>
            <el-select v-model="trendSuite" clearable style="width: 220px" placeholder="全部维度" @change="loadTrend">
              <el-option v-for="s in suites" :key="s.key" :label="s.name" :value="s.key" />
            </el-select>
          </div>
          <EChart :option="trendOption" height="360px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <div class="card-title"><span>多轮评测总分走势</span></div>
          <div style="display: flex; gap: 8px; margin-bottom: 12px">
            <el-select v-model="multiModelIds" multiple collapse-tags style="flex: 1" placeholder="选择多个模型对比" @change="loadMultiTrend">
              <el-option v-for="m in models" :key="m.id" :label="`${m.display_name}（${m.name}）`" :value="m.id" />
            </el-select>
          </div>
          <EChart :option="multiTrendOption" height="360px" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="card-title"><span>轮次对比（选择多轮已完成的评测）</span></div>
      <el-select v-model="compareRuns" multiple collapse-tags style="width: 480px; margin-bottom: 12px"
        placeholder="选择 2 轮以上评测" @change="loadRunCompare">
        <el-option v-for="r in completedRuns" :key="r.id" :label="`#${r.id} ${r.name}（${r.created_at}）`" :value="r.id" />
      </el-select>
      <el-table v-if="runCompareRows.length" :data="runCompareRows" border stripe size="small">
        <el-table-column prop="model_name" label="模型" min-width="140" fixed />
        <el-table-column v-for="c in runCompareCols" :key="c.runId" :label="`${c.runName} 总分`" min-width="120">
          <template #default="{ row }">
            <span v-if="row.scores[c.runId] != null">{{ row.scores[c.runId] }}</span>
            <span v-else style="color:#c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column label="进步幅度" min-width="110">
          <template #default="{ row }">
            <span v-if="row.delta != null" :style="{ color: row.delta > 0 ? '#67c23a' : row.delta < 0 ? '#f56c6c' : '#909399', fontWeight: 600 }">
              {{ row.delta > 0 ? '↑' : row.delta < 0 ? '↓' : '→' }} {{ Math.abs(row.delta) }}
            </span>
            <span v-else style="color:#c0c4cc">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="选择评测轮次后展示对比" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import EChart from '../components/EChart.vue'

const models = ref([])
const suites = ref([])
const completedRuns = ref([])
const trendModel = ref(null)
const trendSuite = ref(null)
const trendPoints = ref([])
const multiModelIds = ref([])
const multiTrend = ref({})
const compareRuns = ref([])
const runCompareData = ref({})

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 20, top: 20, bottom: 50 },
  xAxis: { type: 'category', data: trendPoints.value.map(p => `#${p.run_id} ${p.run_name.slice(0, 8)}`), axisLabel: { rotate: 25 } },
  yAxis: { type: 'value', max: 100, name: '得分' },
  series: [{
    type: 'line', smooth: true, data: trendPoints.value.map(p => p.score),
    markLine: { data: [{ type: 'average', name: '平均' }] },
    label: { show: true },
    areaStyle: { opacity: 0.15 }
  }]
}))

const multiTrendOption = computed(() => {
  const keys = Object.keys(multiTrend.value)
  const xData = keys.length ? multiTrend.value[keys[0]].map(p => `#${p.run_id}`) : []
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, type: 'scroll' },
    grid: { left: 50, right: 20, top: 30, bottom: 60 },
    xAxis: { type: 'category', data: xData },
    yAxis: { type: 'value', max: 100, name: '总分' },
    series: keys.map(k => ({
      name: k, type: 'line', smooth: true,
      data: multiTrend.value[k].map(p => p.score),
      connectNulls: true
    }))
  }
})

const runCompareRows = computed(() => {
  const data = runCompareData.value
  if (!data || !Object.keys(data).length) return []
  const runIds = compareRuns.value
  const modelMap = {}
  for (const runId of runIds) {
    const arr = data[runId] || []
    for (const row of arr) {
      if (!modelMap[row.model_id]) modelMap[row.model_id] = { model_id: row.model_id, model_name: row.model_name, scores: {} }
      modelMap[row.model_id].scores[runId] = row.overall
    }
  }
  return Object.values(modelMap).map(m => {
    const vals = runIds.map(id => m.scores[id]).filter(v => v != null)
    m.delta = vals.length >= 2 ? Math.round((vals[vals.length - 1] - vals[0]) * 10) / 10 : null
    return m
  }).sort((a, b) => (b.delta ?? -999) - (a.delta ?? -999))
})
const runCompareCols = computed(() => compareRuns.value.map(id => {
  const r = completedRuns.value.find(x => x.id === id)
  return { runId: id, runName: r ? `#${r.id} ${r.name}` : `#${id}` }
}))

async function loadTrend() {
  if (!trendModel.value) return
  trendPoints.value = await api.trend(trendModel.value, trendSuite.value || null)
}

async function loadMultiTrend() {
  multiTrend.value = {}
  const modelMap = Object.fromEntries(models.value.map(m => [m.id, m.display_name || m.name]))
  for (const id of multiModelIds.value) {
    const points = await api.trend(id, null)
    multiTrend.value[modelMap[id] || String(id)] = points
  }
}

async function loadRunCompare() {
  runCompareData.value = {}
  for (const id of compareRuns.value) {
    runCompareData.value[id] = await api.leaderboard(id)
  }
}

onMounted(async () => {
  models.value = await api.listModels()
  suites.value = await api.listSuites()
  const runs = await api.listRuns()
  completedRuns.value = runs.filter(r => r.status === 'completed')
  if (models.value.length) {
    trendModel.value = models.value[0].id
    loadTrend()
  }
})
</script>
