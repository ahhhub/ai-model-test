<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" style="height: 100%">
          <div class="card-title"><span>测试题库</span></div>
          <el-table :data="suites" v-loading="loading" border stripe highlight-current-row
            @current-change="selectSuite" ref="suiteTable">
            <el-table-column prop="name" label="题库名称" min-width="180" />
            <el-table-column prop="category" label="能力维度" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="tagType(row.category)">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="题目数" width="110">
              <template #default="{ row }">
                <span v-if="!diffFilter">{{ row.question_count }}</span>
                <span v-else :style="{ color: '#409EFF', fontWeight: 600 }">
                  {{ row.difficulty_counts?.[diffFilter] || 0 }} / {{ row.question_count }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" style="height: 100%">
          <div class="card-title">
            <span>{{ currentSuite ? `「${currentSuite.name}」题目` : '题目列表' }}</span>
            <el-button v-if="currentSuite" size="small" type="primary" @click="openAdd">
              <el-icon><Plus /></el-icon>&nbsp;添加自定义题目
            </el-button>
          </div>
          <div v-if="!currentSuite" class="empty-hint">← 点击左侧题库查看题目</div>
          <template v-else>
            <div style="margin-bottom: 10px">
              <el-radio-group v-model="diffFilter" size="small">
                <el-radio-button value="">全部</el-radio-button>
                <el-radio-button v-for="(label, key) in DIFF" :key="key" :value="key">{{ label }}</el-radio-button>
              </el-radio-group>
            </div>
            <el-scrollbar max-height="520px">
              <el-table :data="filteredQuestions" v-loading="qLoading" border size="small"
                @row-click="openDetail" style="cursor: pointer">
              <el-table-column type="index" label="#" width="45" />
              <el-table-column prop="title" label="题目" min-width="130" show-overflow-tooltip />
              <el-table-column label="类型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.judge ? 'warning' : 'info'">
                    {{ row.judge ? '裁判评分' : typeName(row.answer_type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="难度" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="diffTag(row.difficulty)">{{ DIFF[row.difficulty] || row.difficulty }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-popconfirm title="删除该题？" @confirm="removeQuestion(row)">
                    <template #reference><el-button size="small" type="danger" text @click.stop>删除</el-button></template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
            </el-scrollbar>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" title="添加自定义题目" width="640px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="题目名称">
          <el-input v-model="form.title" placeholder="可选" />
        </el-form-item>
        <el-form-item label="题目内容" required>
          <el-input v-model="form.prompt" type="textarea" :rows="4" placeholder="输入题目/提示词" />
        </el-form-item>
        <el-form-item label="题目类型" required>
          <el-select v-model="form.answer_type" style="width: 100%">
            <el-option label="选择题（自动判分）" value="choice" />
            <el-option label="数值题（自动判分）" value="number" />
            <el-option label="文本题（自动匹配）" value="text" />
            <el-option label="裁判评分题（主观题）" value="judge" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="form.difficulty" style="width: 100%">
            <el-option v-for="(label, key) in DIFF" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.answer_type === 'choice'" label="选项">
          <el-input v-model="optionsText" type="textarea" :rows="3" placeholder="每行一个选项，如：A. 巴黎" />
        </el-form-item>
        <el-form-item v-if="form.answer_type !== 'judge'" label="期望答案">
          <el-input v-model="expectedText" type="textarea" :rows="2"
            :placeholder="form.answer_type === 'number' ? '如：42（可多行填写多个可接受答案）' : '如：A（可多行填写多个可接受答案）'" />
        </el-form-item>
        <el-form-item v-if="form.answer_type === 'judge'" label="评分标准">
          <el-input v-model="form.rubric" type="textarea" :rows="3" placeholder="裁判打分依据，如：从准确性、完整性、表达质量三方面评分" />
        </el-form-item>
        <el-form-item label="图片 URL">
          <el-input v-model="form.image_url" placeholder="多模态题目可选，需为公开可访问的图片地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addQuestion">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="detailVisible" :title="detailQuestion?.title || '题目详情'" width="720px" top="6vh">
      <template v-if="detailQuestion">
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <el-tag size="small" :type="detailQuestion.judge ? 'warning' : 'info'">
            {{ detailQuestion.judge ? '裁判评分' : typeName(detailQuestion.answer_type) }}
          </el-tag>
          <el-tag size="small" :type="diffTag(detailQuestion.difficulty)">{{ DIFF[detailQuestion.difficulty] || detailQuestion.difficulty }}</el-tag>
          <el-tag v-if="detailQuestion.max_score > 1" size="small" type="danger">满分 {{ detailQuestion.max_score }}</el-tag>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="题干">
            <div style="white-space: pre-wrap">{{ detailQuestion.prompt }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailQuestion.image_url" label="图片">
            <el-image :src="detailQuestion.image_url" style="max-width: 320px; max-height: 220px" fit="contain" />
          </el-descriptions-item>
          <el-descriptions-item v-if="detailQuestion.options?.length" label="选项">
            <div v-for="(o, i) in detailQuestion.options" :key="i" :style="optionStyle(o)">{{ o }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="!detailQuestion.judge" label="标准答案">
            <b style="color: #67c23a">{{ formatExpected(detailQuestion) }}</b>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailQuestion.judge" label="评分标准">
            <div style="white-space: pre-wrap">{{ detailQuestion.rubric || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailQuestion.judge" label="期望/示例答案">
            <div style="white-space: pre-wrap">{{ detailQuestion.reference || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailQuestion.answer_type === 'code' && detailQuestion.test_harness?.length" label="测试用例">
            <div v-for="(t, i) in detailQuestion.test_harness" :key="i" style="font-family: Consolas, monospace; font-size: 12px">
              solution{{ t[0] }} → {{ t[1] }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailQuestion.answer_type === 'html' && detailQuestion.test_harness?.checks?.length" label="浏览器检查项">
            <div v-for="(c, i) in detailQuestion.test_harness.checks" :key="i">• {{ c.description }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const suites = ref([])
const questions = ref([])
const loading = ref(false)
const qLoading = ref(false)
const currentSuite = ref(null)
const dialogVisible = ref(false)
const suiteTable = ref(null)
const optionsText = ref('')
const expectedText = ref('')
const diffFilter = ref('')
const detailVisible = ref(false)
const detailQuestion = ref(null)

const DIFF = { easy: '简单', medium: '中等', medium_high: '中高', hard: '高难', extreme: '极难' }
const diffTag = d => ({ easy: 'success', medium: 'info', medium_high: 'warning', hard: 'danger', extreme: 'danger' })[d] || 'info'

const filteredQuestions = computed(() =>
  diffFilter.value ? questions.value.filter(q => q.difficulty === diffFilter.value) : questions.value
)

function openDetail(row) {
  detailQuestion.value = row
  detailVisible.value = true
}

function formatExpected(q) {
  if (q.answer_type === 'choice') {
    const letter = (q.expected || [])[0] || ''
    const opt = (q.options || []).find(o => o.startsWith(letter + '.')) || ''
    return opt ? `${opt}（${letter}）` : letter
  }
  return (q.expected || []).join(' / ') || '—'
}

function optionStyle(opt) {
  const letter = (detailQuestion.value?.expected || [])[0] || ''
  if (detailQuestion.value?.answer_type === 'choice' && opt.startsWith(letter + '.')) {
    return { color: '#67c23a', fontWeight: 700 }
  }
  return {}
}

const form = reactive({ title: '', prompt: '', answer_type: 'choice', image_url: '', rubric: '', difficulty: 'easy' })

const tagType = c => ({ multimodal: 'success', emotion: 'warning', coding: 'primary', logic: 'danger', general: 'info', math: '' })[c] || 'info'
const typeName = t => ({ choice: '选择题', number: '数值题', text: '文本题', code: '代码题', html: '前端题' })[t] || t

async function load() {
  loading.value = true
  try {
    suites.value = await api.listSuites()
    if (suites.value.length && suiteTable.value) {
      selectSuite(suites.value[0])
    }
  } finally { loading.value = false }
}

async function selectSuite(suite) {
  if (!suite) return
  currentSuite.value = suite
  diffFilter.value = ''
  qLoading.value = true
  try { questions.value = await api.listQuestions(suite.id) } finally { qLoading.value = false }
}

function openAdd() {
  Object.assign(form, { title: '', prompt: '', answer_type: 'choice', image_url: '', rubric: '', difficulty: 'easy' })
  optionsText.value = ''
  expectedText.value = ''
  dialogVisible.value = true
}

async function addQuestion() {
  if (!form.prompt.trim()) { ElMessage.warning('请填写题目内容'); return }
  const payload = {
    title: form.title,
    prompt: form.prompt,
    image_url: form.image_url,
    answer_type: form.answer_type === 'judge' ? 'text' : form.answer_type,
    options: form.answer_type === 'choice' ? optionsText.value.split('\n').map(s => s.trim()).filter(Boolean) : [],
    expected: form.answer_type === 'judge' ? [] : expectedText.value.split('\n').map(s => s.trim()).filter(Boolean),
    judge: form.answer_type === 'judge',
    max_score: form.answer_type === 'judge' ? 10 : 1,
    rubric: form.rubric,
    reference: '',
    difficulty: form.difficulty
  }
  await api.addQuestion(currentSuite.value.id, payload)
  dialogVisible.value = false
  ElMessage.success('已添加')
  selectSuite(currentSuite.value)
  load()
}

async function removeQuestion(row) {
  await api.deleteQuestion(row.id)
  ElMessage.success('已删除')
  selectSuite(currentSuite.value)
  load()
}

onMounted(load)
</script>

<style scoped>
.empty-hint { color: #909399; padding: 40px 0; text-align: center; }
</style>
