<template>
  <div>
    <!-- 토글 -->
    <div style="display:flex; gap:16px; margin-bottom:14px;">
      <label class="toggle-wrap">
        <input type="checkbox" v-model="showCi" />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        신뢰구간
      </label>
    </div>

    <!-- 상단: 차트(좌) + AI분석설명(우) -->
    <div class="row" style="gap:14px; align-items:stretch;">
      <div class="col-2 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">과거 7일의 전력 소모량</div>
        <div ref="chartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <div class="col-1 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">AI 분석 설명</div>
        <div class="xai-text-box" v-html="formattedText" style="flex:1; overflow-y:auto;"></div>
      </div>
    </div>

    <!-- 하단: 예측 테이블 + 요인 중요도 + 뉴스 이벤트 -->
    <div class="row" style="gap:14px; margin-top:16px; align-items:stretch;">

      <!-- 향후 12시간 예측 -->
      <div class="panel" style="flex:1; min-width:0;">
        <div class="section-label">향후 12시간의 전력 수요량 예측</div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:12px;">
          <div class="mini-stat">
            <div class="mini-stat-label">평균</div>
            <div class="mini-stat-value" style="color:#5e72e4;">{{ predMean }}</div>
          </div>
          <div class="mini-stat">
            <div class="mini-stat-label">피크</div>
            <div class="mini-stat-value" style="color:#f5365c;">{{ predMax }}</div>
          </div>
          <div class="mini-stat">
            <div class="mini-stat-label">최저</div>
            <div class="mini-stat-value" style="color:#2dce89;">{{ predMin }}</div>
          </div>
        </div>
        <div style="overflow-y:auto; max-height:220px;">
          <table style="width:100%; border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:2px solid var(--border);">
                <th style="padding:6px 8px; text-align:left; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">시각</th>
                <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">예측 ({{ demandDisplayScale.pUnit }})</th>
                <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">범위</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in forecastRows" :key="row.ts" style="border-bottom:1px solid var(--border);">
                <td style="padding:6px 8px; color:var(--text3); font-family:var(--mono); font-size:11px;">
                  {{ fmtForecastTs(row.ts) }}
                </td>
                <td style="padding:6px 8px; text-align:right; font-family:var(--mono); font-weight:600;"
                  :style="{
                    color: forecastStats && Number(row.pred_1_step) === forecastStats.max ? '#f5365c'
                        : forecastStats && Number(row.pred_1_step) === forecastStats.min ? '#2dce89'
                        : 'var(--text1)'
                  }"
                >
                  {{ formatDemandValue(row.pred_1_step) }}
                </td>
                <td style="padding:6px 8px; text-align:right; color:var(--text3); font-family:var(--mono); font-size:11px;">
                  {{ formatDemandValue((row.pred_1_step ?? 0) - 6) }} – {{ formatDemandValue((row.pred_1_step ?? 0) + 6) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 요인 중요도 -->
      <div class="panel" style="flex:1; min-width:0;">
        <div class="section-label">요인 중요도</div>
        <div ref="barEl" :style="{ width: '100%', height: `${barHeight}px` }"></div>
      </div>

      <!-- 뉴스 이벤트 -->
      <div class="panel" style="flex:1; min-width:0;">
        <div class="section-label">뉴스 이벤트 (상위 3건)</div>
        <p v-if="!newsView.length" style="color:var(--text3); font-size:11px;">
          선택 기간에 해당하는 뉴스 이벤트가 없습니다.
        </p>
        <div v-for="row in topNews" :key="String(row.timestamp)"
          class="news-card" :class="level(row.impact_score)">
          <span class="news-event-tag">{{ row.event_type }}</span>
          <div class="news-headline">{{ row.headline }}</div>
          <div class="news-summary">{{ row.summary }}</div>
          <div class="news-meta">{{ fmtDate(row.timestamp) }} · impact {{ row.impact_score.toFixed(2) }}</div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  series:       { type: Array,   default: () => [] },
  newsView:     { type: Array,   default: () => [] },
  xaiResult:    { type: Object,  default: () => ({ text: '', factors: [] }) },
  selectedDate: { type: String,  default: '' },
  selectedTime: { type: String,  default: '00:00' },
  isLoading:    { type: Boolean, default: false },
})

const chartEl = ref(null)
const barEl   = ref(null)
let chart    = null
let barChart = null
const showCi = ref(true)

const POWER_MW_THRESHOLD_KW = 1000
const p2 = n => String(n).padStart(2, '0')

function fmtFixed2(n) {
  return n.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 예측 테이블 시각: YYYY년 MM월 DD일 HH시
function fmtForecastTs(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  return `${d.getFullYear()}년 ${p2(d.getMonth()+1)}월 ${p2(d.getDate())}일 ${p2(d.getHours())}시`
}

function fmtDate(d) {
  return `${d.getFullYear()}-${p2(d.getMonth()+1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`
}

// ── 시리즈 정렬
const sortedSeries = computed(() =>
  [...props.series].sort((a, b) => new Date(a.ts) - new Date(b.ts))
)

const anchorIndex = computed(() =>
  sortedSeries.value.findIndex(
    (row) => row.ts.slice(0, 10) === props.selectedDate && row.ts.slice(11, 16) === props.selectedTime
  )
)

const histRows = computed(() => {
  if (!sortedSeries.value.length) return []
  const idx = anchorIndex.value >= 0 ? anchorIndex.value : sortedSeries.value.length - 1
  return sortedSeries.value.slice(Math.max(0, idx - 167), idx + 1)
})

const forecastRows = computed(() => {
  if (!sortedSeries.value.length) return []
  const idx = anchorIndex.value >= 0 ? anchorIndex.value : sortedSeries.value.length - 1
  return sortedSeries.value.slice(idx + 1, idx + 13)
})

const forecastPlotRows = computed(() => {
  if (!forecastRows.value.length) return []
  const last = histRows.value[histRows.value.length - 1]
  if (!last) return forecastRows.value
  return [{ ts: last.ts, pred_1_step: last.actual }, ...forecastRows.value]
})

// ── 단위 스케일
const demandDisplayScale = computed(() => {
  const vals = []
  for (const row of [...histRows.value, ...forecastRows.value]) {
    for (const k of ['actual', 'pred_1_step']) {
      const v = Number(row[k])
      if (Number.isFinite(v)) vals.push(Math.abs(v))
    }
  }
  const maxVal = vals.length ? Math.max(...vals) : 0
  const useMW = maxVal >= POWER_MW_THRESHOLD_KW
  return { useMW, pFactor: useMW ? 0.001 : 1, pUnit: useMW ? 'MW' : 'kW' }
})

const forecastStats = computed(() => {
  const nums = forecastRows.value.map(r => Number(r.pred_1_step)).filter(Number.isFinite)
  if (!nums.length) return null
  return { min: Math.min(...nums), max: Math.max(...nums), mean: nums.reduce((a,b)=>a+b,0)/nums.length }
})

const predMean = computed(() => {
  const s = forecastStats.value
  if (!s) return '—'
  return `${fmtFixed2(s.mean * demandDisplayScale.value.pFactor)} ${demandDisplayScale.value.pUnit}`
})
const predMax = computed(() => {
  const s = forecastStats.value
  if (!s) return '—'
  return `${fmtFixed2(s.max * demandDisplayScale.value.pFactor)} ${demandDisplayScale.value.pUnit}`
})
const predMin = computed(() => {
  const s = forecastStats.value
  if (!s) return '—'
  return `${fmtFixed2(s.min * demandDisplayScale.value.pFactor)} ${demandDisplayScale.value.pUnit}`
})

function formatDemandValue(value) {
  if (!Number.isFinite(Number(value))) return '—'
  return fmtFixed2(Number(value) * demandDisplayScale.value.pFactor)
}

// ── AI 분석 텍스트 포맷
const formattedText = computed(() => {
  if (!props.xaiResult?.text) return '<div style="color:var(--text3);font-size:12px;">분석 결과가 없습니다.</div>'
  return props.xaiResult.text
    .split('\n')
    .map(line => {
      const t = line.trim()
      if (!t) return '<div style="height:8px;"></div>'
      if (t.startsWith('- '))
        return `<div class="xai-bullet">· ${t.slice(2)}</div>`
      if (/^\d+\./.test(t))
        return `<div class="xai-section-title">${t.replace(/^\d+\.\s*/, '')}</div>`
      if (t.startsWith('['))
        return `<div class="xai-tag-title">${t}</div>`
      return `<div class="xai-line">${t}</div>`
    })
    .join('')
})

// ── 뉴스
const topNews = computed(() =>
  [...props.newsView].sort((a, b) => b.impact_score - a.impact_score).slice(0, 3)
)
const level = s => s >= 0.7 ? 'high' : s >= 0.5 ? 'mid' : 'low'

// ── 요인 중요도
const visibleFactors = computed(() =>
  [...(props.xaiResult?.factors ?? [])]
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 12)
)
const barHeight = computed(() => 24 + Math.max(visibleFactors.value.length, 4) * 24)

// ── 차트 옵션
function buildOption() {
  if (!sortedSeries.value.length)
    return { xAxis: { type: 'time' }, yAxis: { type: 'value' }, series: [] }

  const scale = demandDisplayScale.value
  const allVals = [...histRows.value, ...forecastRows.value]
    .flatMap(r => [r.actual, r.pred_1_step])
    .filter(Number.isFinite)
  const yMin = allVals.length ? Math.floor(Math.min(...allVals) * 0.97) : undefined
  const yMax = allVals.length ? Math.ceil(Math.max(...allVals) * 1.03)  : undefined

  const series = [
    {
      name: '과거 사용량', type: 'line',
      data: histRows.value.map(r => [r.ts, r.actual]),
      symbol: 'none', smooth: 0.08,
      lineStyle: { color: '#5e72e4', width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[
        { offset:0, color:'rgba(94,114,228,0.2)' },
        { offset:1, color:'rgba(94,114,228,0.01)' },
      ])},
    },
    {
      name: '예측값', type: 'line',
      data: forecastPlotRows.value.map(r => [r.ts, r.pred_1_step]),
      symbol: 'none', smooth: 0.08,
      lineStyle: { color: '#11cdef', width: 2.5, type: 'dashed' },
      areaStyle: showCi.value ? { color: new echarts.graphic.LinearGradient(0,0,0,1,[
        { offset:0, color:'rgba(17,205,239,0.12)' },
        { offset:1, color:'rgba(17,205,239,0.01)' },
      ])} : undefined,
    },
  ]

  if (showCi.value && forecastRows.value.length) {
    series.push({
      name: '신뢰구간', type: 'line',
      data: forecastRows.value.map(r => [r.ts, (r.pred_1_step ?? 0) + 6]),
      lineStyle: { opacity: 0 },
      areaStyle: { color: 'rgba(17,205,239,0.05)', origin: 'auto' },
      symbol: 'none', silent: true, showInLegend: false,
    })
  }

  return {
    backgroundColor: 'transparent',
    grid: { left: 60, right: 20, top: 44, bottom: 36 },
    legend: {
      top: 8, left: 0,
      itemWidth: 24, itemHeight: 3,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard',
        formatter: v => { const d = new Date(v); return `${p2(d.getMonth()+1)}/${p2(d.getDate())}` },
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value', min: yMin, max: yMax,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: {
        fontSize: 10, fontFamily: 'Pretendard',
        formatter: v => {
          if (!Number.isFinite(v)) return ''
          const s = scale.useMW ? fmtFixed2(v * scale.pFactor) : `${Math.round(v)}`
          return Number.isFinite(yMin) && Math.abs(v - yMin) < 1e-4
            ? `{unit|${scale.pUnit}}{val|\u00A0${s}}`
            : `{val|${s}}`
        },
        rich: {
          unit: { color: '#1a1a1a', fontWeight: 700, fontSize: 10, fontFamily: 'Pretendard' },
          val:  { color: '#8898aa', fontWeight: 400, fontSize: 10, fontFamily: 'Pretendard' },
        },
      },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a2e', borderColor: 'transparent', borderRadius: 10, padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      axisPointer: { lineStyle: { color: '#dee2e6', type: 'dashed' } },
      formatter: params => {
        if (!params.length) return ''
        const d = new Date(params[0].value[0])
        const title = `${d.getFullYear()}-${p2(d.getMonth()+1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`
        return `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${title}</div>` +
          params.map(p => {
            const y = Number(p.value[1])
            if (!Number.isFinite(y)) return ''
            return `<div style="display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
              <span style="color:#a0a0c0;">${p.seriesName}</span>
              <b style="margin-left:auto;font-size:13px;">${fmtFixed2(y * scale.pFactor)} ${scale.pUnit}</b>
            </div>`
          }).join('')
      },
    },
    series,
  }
}

// ── 요인 중요도 차트
async function drawBar() {
  await nextTick()
  if (!barEl.value || !visibleFactors.value.length) return
  if (!barChart) barChart = echarts.init(barEl.value)

  const s = [...visibleFactors.value].sort((a, b) => a.importance - b.importance)
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
    xAxis: { type: 'value', max: maxImp * 1.35, axisLine:{show:false}, axisTick:{show:false}, axisLabel:{show:false}, splitLine:{show:false} },
    yAxis: { type: 'category', data: s.map(f => f.factor), axisLine:{show:false}, axisTick:{show:false}, axisLabel:{color:'#4a5568',fontSize:11,fontFamily:'Pretendard'} },
    tooltip: {
      trigger: 'item', backgroundColor: '#1a1a2e', borderColor: 'transparent', borderRadius: 8, padding: [8,12],
      textStyle: { color:'#fff', fontSize:12, fontFamily:'Pretendard' },
      formatter: p => `<b>${p.name}</b><br><span style="color:#c0b0ff;">${Number(p.value).toLocaleString('ko-KR')}건</span>`,
    },
    series: [{
      type: 'bar',
      data: s.map((f,i) => ({ value: f.importance, itemStyle: { color: colors[i], borderRadius: [0,4,4,0] } })),
      barMaxWidth: 12, barCategoryGap: '45%', label: { show: false },
    }],
  }, true)
}

async function drawChart() {
  await nextTick()
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption(buildOption(), true)
}

function handleResize() {
  chart?.resize()
  barChart?.resize()
}

async function draw() {
  await drawChart()
  await drawBar()
}

onMounted(() => {
  setTimeout(draw, 100)
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  barChart?.dispose()
})
watch(() => props.xaiResult, () => setTimeout(drawBar, 50), { deep: true })
watch(() => props.newsView,  () => setTimeout(drawBar, 50))
watch(barHeight, () => setTimeout(drawBar, 50))
watch(
  [() => props.series, () => props.selectedDate, () => props.selectedTime, () => props.isLoading, showCi, demandDisplayScale],
  drawChart, { deep: true }
)
</script>

<style scoped>
.xai-text-box {
  font-size: 12px;
  line-height: 1.75;
  color: var(--text2);
  font-family: 'Pretendard', sans-serif;
}
:deep(.xai-line) {
  margin: 2px 0;
  color: var(--text2);
}
:deep(.xai-bullet) {
  padding-left: 14px;
  margin: 4px 0;
  color: var(--text2);
  position: relative;
}
:deep(.xai-section-title) {
  margin: 10px 0 4px;
  font-weight: 700;
  font-size: 13px;
  color: var(--text1);
  border-left: 3px solid #5865f2;
  padding-left: 8px;
}
:deep(.xai-tag-title) {
  font-weight: 700;
  font-size: 13px;
  color: #5865f2;
  margin-bottom: 6px;
}
</style>