import axios from 'axios'

const http = axios.create({ baseURL: '', timeout: 300000 })

export default {
  // 模型
  listModels: () => http.get('/api/models').then(r => r.data),
  addModel: data => http.post('/api/models', data).then(r => r.data),
  updateModel: (id, data) => http.put(`/api/models/${id}`, data).then(r => r.data),
  deleteModel: id => http.delete(`/api/models/${id}`).then(r => r.data),
  testModel: id => http.post(`/api/models/${id}/test`).then(r => r.data),
  // 题库
  listSuites: () => http.get('/api/suites').then(r => r.data),
  listQuestions: suiteId => http.get(`/api/suites/${suiteId}/questions`).then(r => r.data),
  addQuestion: (suiteId, data) => http.post(`/api/suites/${suiteId}/questions`, data).then(r => r.data),
  deleteQuestion: id => http.delete(`/api/questions/${id}`).then(r => r.data),
  // 评测
  listRuns: () => http.get('/api/runs').then(r => r.data),
  createRun: data => http.post('/api/runs', data).then(r => r.data),
  getRun: id => http.get(`/api/runs/${id}`).then(r => r.data),
  stopRun: id => http.post(`/api/runs/${id}/stop`).then(r => r.data),
  deleteRun: id => http.delete(`/api/runs/${id}`).then(r => r.data),
  getResults: id => http.get(`/api/runs/${id}/results`).then(r => r.data),
  // 报表
  leaderboard: runId => http.get('/api/reports/leaderboard', { params: { run_id: runId } }).then(r => r.data),
  radar: runId => http.get('/api/reports/radar', { params: { run_id: runId } }).then(r => r.data),
  compare: runId => http.get('/api/reports/compare', { params: { run_id: runId } }).then(r => r.data),
  trend: (modelId, suiteKey) => http.get('/api/reports/trend', { params: { model_id: modelId, suite_key: suiteKey || undefined } }).then(r => r.data)
}
