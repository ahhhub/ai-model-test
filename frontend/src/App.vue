<template>
  <el-container class="layout">
    <el-aside width="210px" class="aside">
      <div class="logo">
        <el-icon size="22" color="#409EFF"><DataAnalysis /></el-icon>
        <span>AI 模型评测平台</span>
      </div>
      <el-menu :default-active="$route.path" router class="menu">
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon><span>评测总览</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Cpu /></el-icon><span>模型管理</span>
        </el-menu-item>
        <el-menu-item index="/suites">
          <el-icon><Collection /></el-icon><span>测试题库</span>
        </el-menu-item>
        <el-menu-item index="/runs">
          <el-icon><VideoPlay /></el-icon><span>发起评测</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><TrendCharts /></el-icon><span>数据报表</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title }}</span>
        <span class="hint">支持 OpenAI 协议模型 · 多模态 / 情感 / 编程 / 逻辑 / 通用能力评测</span>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
body { font-family: "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; }
.layout { height: 100%; }
.aside { background: #fff; border-right: 1px solid #e6e8eb; display: flex; flex-direction: column; }
.logo { display: flex; align-items: center; gap: 8px; padding: 18px 16px; font-weight: 700; font-size: 15px; color: #303133; border-bottom: 1px solid #f0f2f5; }
.menu { border-right: none; flex: 1; }
.header { background: #fff; border-bottom: 1px solid #e6e8eb; display: flex; align-items: center; gap: 16px; }
.header .title { font-size: 17px; font-weight: 600; color: #303133; }
.header .hint { font-size: 12px; color: #909399; }
.main { padding: 16px; overflow: auto; }
.card-title { display: flex; align-items: center; justify-content: space-between; font-weight: 600; margin-bottom: 4px; }
.code-box { background:#1e1e2e; color:#d4d4d4; padding:12px; border-radius:6px; font-family:Consolas,monospace; font-size:12px; max-height:260px; overflow:auto; white-space:pre-wrap; }
</style>
