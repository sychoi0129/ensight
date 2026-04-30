<template>
  <div class="row" style="gap:14px;">
    <div class="col-1">
      <div class="panel">
        <div class="section-label">AI 분석 설명</div>
        <div class="xai-box" v-html="formattedText"></div>
      </div>
    </div>
    <div class="col-1">
      <div class="panel" style="margin-bottom:12px;">
        <div class="section-label">요인 중요도</div>
        <div ref="barEl" style="width:100%; height:160px;"></div>
      </div>
      <div class="panel">
        <div class="section-label">뉴스 이벤트 (상위 3건)</div>
        <p v-if="!newsView.length" style="color:var(--text3); font-size:11px;">
          선택 기간에 해당하는 뉴스 이벤트가 없습니다.
        </p>
        <div v-for="row in topNews" :key="String(row.timestamp)"
          class="news-card" :class="level(row.impact_score)">
          <span class="news-event-tag">{{ row.event_type }}</span>
          <div class="news-headline">{{ row.headline }}</div>
          <div class="news-summary">{{ row.summary }}</div>
          <div class="news-meta">{{ fmt(row.timestamp) }} · impact {{ row.impact_score.toFixed(2) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  xaiResult: { type: Object, default: () => ({ text: '', factors: [] }) },
  newsView:  { type: Array,  default: () => [] },
})

const barEl = ref(null)
let barChart = null

const topNews = computed(() =>
  [...props.newsView].sort((a, b) => b.impact_score - a.impact_score).slice(0, 3)
)

const formattedText = computed(() => {
  if (!props.xaiResult.text) return ''
  return props.xaiResult.text
    .split('\n')
    .map(line => {
      const t = line.trim()
      if (!t) return '<br>'
      if (t.startsWith('- ')) return `<div style="padding-left:14px;margin:3px 0;">· ${t.slice(2)}</div>`
      if (/^\d+\./.test(t)) return `<div style="margin:8px 0 4px;font-weight:600;color:var(--text1);">${t}</div>`
      if (t.startsWith('[')) return `<div style="font-weight:700;color:var(--text1);margin-bottom:8px;">${t}</div>`
      return `<div style="margin:2px 0;">${t}</div>`
    })
    .join('')
})

const level = s => s >= 0.7 ? 'high' : s >= 0.5 ? 'mid' : 'low'
const fmt = d => {
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function draw() {
  await nextTick()
  if (!barEl.value || !props.xaiResult.factors.length) return
  if (!barChart) barChart = echarts.init(barEl.value)

  const s = [...props.xaiResult.factors].sort((a, b) => a.importance - b.importance)
  const maxImp = Math.max(...s.map(f => f.importance))

  const colors = s.map(f => {
    const r = f.importance / maxImp
    if (r >= 0.85) return '#5e72e4'
    if (r >= 0.65) return '#11cdef'
    if (r >= 0.45) return '#2dce89'
    return '#adb5bd'
  })

  barChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 10, right: 20, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      max: maxImp * 1.35,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'category',
      data: s.map(f => f.factor),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#4a5568', fontSize: 11, fontFamily: 'Pretendard' },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 8,
      padding: [8, 12],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      formatter: p => `<b>${p.name}</b><br><span style="color:#c0b0ff;">${p.value.toFixed(4)}</span>`,
    },
    series: [{
      type: 'bar',
      data: s.map((f, i) => ({ value: f.importance, itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] } })),
      barMaxWidth: 18,
      label: { show: false },
    }],
  }, true)
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => barChart?.dispose())
watch(() => props.xaiResult, () => setTimeout(draw, 50), { deep: true })
watch(() => props.newsView,  () => setTimeout(draw, 50))
</script>
