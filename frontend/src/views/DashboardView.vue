<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 16px">
      <div class="card-title">
        <span>选择已完成的评测</span>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-select v-model="runId" style="width: 360px" placeholder="选择评测" @change="loadAll">
            <el-option v-for="r in completedRuns" :key="r.id" :label="`#${r.id} ${r.name}（${r.created_at}）`" :value="r.id" />
          </el-select>
          <el-button @click="goRuns">发起新评测</el-button>
        </div>
      </div>
      <el-alert v-if="!completedRuns.length" type="info" :closable="false" show-icon
        title="暂无已完成的评测。请先在「模型管理」添加模型，再到「发起评测」创建一轮评测。" />
    </el-card>

    <template v-if="runId">
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="12">
          <el-card shadow="never">
            <div class="card-title"><span>能力雷达图</span></div>
            <EChart :option="radarOption" height="360px" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <div class="card-title"><span>各维度得分对比</span></div>
            <EChart :option="barOption" height="360px" />
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never">
            <div class="card-title"><span>排行榜</span></div>
            <el-table :data="board" border stripe size="small">
              <el-table-column label="排名" width="70">
                <template #default="{ row }">
                  <el-tag v-if="row.rank === 1" type="warning" size="small">🥇</el-tag>
                  <el-tag v-else-if="row.rank === 2" size="small">🥈</el-tag>
                  <el-tag v-else-if="row.rank === 3" size="small">🥉</el-tag>
                  <span v-else>{{ row.rank }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="model_name" label="模型" min-width="130" />
              <el-table-column label="总分" width="90">
                <template #default="{ row }"><b>{{ row.overall ?? '—' }}</b></template>
              </el-table-column>
              <el-table-column v-for="s in radarSuites" :key="s.id" :label="s.name" min-width="105">
                <template #default="{ row }">
                  {{ row.suites[s.key] ? row.suites[s.key].score : '—' }}
                </template>
              </el-table-column>
              <el-table-column label="总耗时" width="100">
                <template #default="{ row }">
                  {{ row.total_latency_ms != null ? (Math.round(row.total_latency_ms / 100) / 10) + ' s' : '—' }}
                </template>
              </el-table-column>
              <el-table-column label="平均耗时" width="100">
                <template #default="{ row }">
                  {{ row.avg_latency_ms != null ? (Math.round(row.avg_latency_ms / 100) / 10) + ' s' : '—' }}
                </template>
              </el-table-column>
              <el-table-column label="输出速度" width="110">
                <template #default="{ row }">
                  {{ row.output_speed_tps != null ? row.output_speed_tps + ' tok/s' : '—' }}
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <div class="card-title"><span>模型差距矩阵（行 - 列 的总分差）</span></div>
            <EChart :option="heatOption" height="360px" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EChart from '../components/EChart.vue'

const router = useRouter()
const completedRuns = ref([])
const runId = ref(null)
const board = ref([])
const radarData = ref(null)
const compareData = ref(null)

const radarSuites = computed(() => radarData.value?.suites || [])

const radarOption = computed(() => ({
  tooltip: {},
  legend: { bottom: 0, type: 'scroll' },
  radar: {
    indicator: radarSuites.value.map(s => ({ name: s.name, max: 100 })),
    radius: '62%'
  },
  series: [{
    type: 'radar',
    data: (radarData.value?.series || []).map(s => ({ name: s.name, value: s.values }))
  }]
}))

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0, type: 'scroll' },
  grid: { left: 40, right: 20, top: 30, bottom: 60 },
  xAxis: { type: 'category', data: radarSuites.value.map(s => s.name), axisLabel: { interval: 0, rotate: 20 } },
  yAxis: { type: 'value', max: 100, name: '得分' },
  series: (radarData.value?.series || []).map(s => ({ name: s.name, type: 'bar', data: s.values, label: { show: true, position: 'top', fontSize: 10 } }))
}))

const heatOption = computed(() => {
  const names = compareData.value?.names || []
  const matrix = compareData.value?.matrix || []
  const data = []
  matrix.forEach((row, i) => row.diffs.forEach((v, j) => data.push([j, i, v])))
  return {
    tooltip: { formatter: p => `${names[p.value[0]]} − ${names[p.value[1]]} = ${p.value[2]} 分` },
    grid: { left: 120, right: 20, top: 20, bottom: 60 },
    xAxis: { type: 'category', data: names, splitArea: { show: true }, axisLabel: { rotate: 30 } },
    yAxis: { type: 'category', data: names, splitArea: { show: true } },
    visualMap: {
      min: -20, max: 20, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
      inRange: { color: ['#5470c6', '#f7f7f7', '#ee6666'] }
    },
    series: [{
      type: 'heatmap',
      data,
      label: { show: true, formatter: p => (p.value[2] === 0 ? '' : p.value[2]) }
    }]
  }
})

function goRuns() { router.push('/runs') }

async function loadAll() {
  if (!runId.value) return
  const [b, r, c] = await Promise.all([
    api.leaderboard(runId.value),
    api.radar(runId.value),
    api.compare(runId.value)
  ])
  board.value = b
  radarData.value = r
  compareData.value = c
}

onMounted(async () => {
  const runs = await api.listRuns()
  completedRuns.value = runs.filter(r => r.status === 'completed')
  if (completedRuns.value.length) {
    runId.value = completedRuns.value[0].id
    await loadAll()
  }
})
</script>
