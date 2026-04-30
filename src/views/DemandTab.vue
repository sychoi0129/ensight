<template>
  <div>
    <!-- 토글 -->
    <div style="display:flex; gap:16px; margin-bottom:14px;">
      <label class="toggle-wrap">
        <input type="checkbox" v-model="showCi" />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        신뢰구간
      </label>
      <label class="toggle-wrap">
        <input type="checkbox" v-model="showNews" />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        뉴스 오버레이
      </label>
    </div>

    <!-- 차트 + 표 -->
    <div class="row" style="gap:14px; align-items:stretch;">
      <div class="col-2 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">과거 7일의 전력 소모량</div>
        <div ref="chartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <div class="col-1" style="display:flex; flex-direction:column; gap:12px;">
        <div class="panel" style="flex:1;">
          <div class="section-label">향후 {{ horizon }}시간의 전력 수요량 예측</div>

          <!-- 요약 통계 -->
          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:14px;">
            <div class="mini-stat">
              <div class="mini-stat-label">평균</div>
              <div class="mini-stat-value" style="color:#5e72e4;">{{ predMean.toFixed(1) }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">피크</div>
              <div class="mini-stat-value" style="color:#f5365c;">{{ predMax.toFixed(1) }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">최저</div>
              <div class="mini-stat-value" style="color:#2dce89;">{{ predMin.toFixed(1) }}</div>
            </div>
          </div>

          <!-- 예측 테이블 -->
          <div style="overflow-y:auto; max-height:280px;">
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
              <thead>
                <tr style="border-bottom:2px solid var(--border);">
                  <th style="padding:6px 8px; text-align:left; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">시각</th>
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">예측 (W)</th>
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">범위</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, i) in forecastDf" :key="i"
                  style="border-bottom:1px solid var(--border);"
                >
                  <td style="padding:7px 8px; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    +{{ i+1 }}h
                  </td>
                  <td style="padding:7px 8px; text-align:right; font-family:var(--mono); font-weight:600;"
                    :style="{
                      color: row.prediction === predMax ? '#f5365c'
                          : row.prediction === predMin ? '#2dce89'
                          : 'var(--text1)'
                    }"
                  >
                    {{ row.prediction.toFixed(1) }}
                  </td>
                  <td style="padding:7px 8px; text-align:right; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    {{ row.lower.toFixed(1) }} – {{ row.upper.toFixed(1) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- XAI 섹션 -->
    <div style="margin-top:16px;">
      <XaiTab :xai-result="xaiResult" :news-view="newsView" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import XaiTab from '@/views/XaiTab.vue'
import * as echarts from 'echarts'

const props = defineProps({
  histDf:     { type: Array,  default: () => [] },
  forecastDf: { type: Array,  default: () => [] },
  newsView:   { type: Array,  default: () => [] },
  horizon:    { type: Number, default: 12 },
  xaiResult:  { type: Object, default: () => ({ text: '', factors: [] }) },
})

const showCi   = ref(true)
const showNews = ref(true)
const chartEl  = ref(null)
let chart = null

const predMean = computed(() =>
  props.forecastDf.length ? props.forecastDf.reduce((s, r) => s + r.prediction, 0) / props.forecastDf.length : 0
)
const predMax = computed(() => props.forecastDf.length ? Math.max(...props.forecastDf.map(r => r.prediction)) : 0)
const predMin = computed(() => props.forecastDf.length ? Math.min(...props.forecastDf.map(r => r.prediction)) : 0)

const fmtTime = d => {
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getMonth()+1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function buildOption() {
  const histX = props.histDf.map(r => r.timestamp)
  const histY = props.histDf.map(r => r.power_usage)
  const fcX   = props.forecastDf.map(r => r.timestamp)
  const fcY   = props.forecastDf.map(r => r.prediction)
  const allY  = [...histY, ...fcY]
  const yMin  = Math.min(...allY) * 0.97
  const yMax  = Math.max(...allY, ...(showCi.value ? props.forecastDf.map(r => r.upper) : [])) * 1.04

  const series = [
    {
      name: '과거 사용량',
      type: 'line',
      data: histX.map((x, i) => [x, histY[i]]),
      symbol: 'none',
      lineStyle: { color: '#5e72e4', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(94,114,228,0.2)' },
          { offset: 1, color: 'rgba(94,114,228,0.01)' },
        ]),
      },
      smooth: 0.25,
    },
    {
      name: '예측값',
      type: 'line',
      data: fcX.map((x, i) => [x, fcY[i]]),
      symbol: 'none',
      lineStyle: { color: '#11cdef', width: 2.5, type: 'dashed' },
      areaStyle: showCi.value ? {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(17,205,239,0.12)' },
          { offset: 1, color: 'rgba(17,205,239,0.01)' },
        ]),
      } : undefined,
      smooth: 0.25,
    },
  ]

  if (showCi.value && props.forecastDf.length) {
    series.push({
      name: '신뢰구간',
      type: 'line',
      data: fcX.map((x, i) => [x, props.forecastDf[i].upper]),
      lineStyle: { opacity: 0 },
      areaStyle: { color: 'rgba(17,205,239,0.05)', origin: 'auto' },
      symbol: 'none',
      silent: true,
      showInLegend: false,
    })
  }

  if (showNews.value && props.newsView.length) {
    series.push({
      name: '뉴스',
      type: 'scatter',
      data: props.newsView.map(r => ({
        value: [r.timestamp, yMin + (yMax - yMin) * 0.015],
        headline: r.headline,
        event_type: r.event_type,
      })),
      symbol: 'diamond',
      symbolSize: 12,
      itemStyle: { color: '#f5365c', borderColor: 'rgba(245,54,92,0.25)', borderWidth: 8 },
    })
  }

  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 44, bottom: 36 },
    legend: {
      top: 6, left: 0,
      itemWidth: 24, itemHeight: 3,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard',
        formatter: v => {
          const d = new Date(v), p = n => String(n).padStart(2,'0')
          return `${p(d.getMonth()+1)}/${p(d.getDate())}`
        },
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value', min: yMin, max: yMax,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard', formatter: v => Math.round(v) },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 10,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      axisPointer: { lineStyle: { color: '#dee2e6', type: 'dashed' } },
      formatter: params => {
        const news = params.find(p => p.seriesName === '뉴스')
        if (news) {
          return `<div style="font-weight:700;margin-bottom:4px;">${news.data.event_type}</div>
                  <div style="font-size:11px;color:#c0c0d8;">${news.data.headline}</div>`
        }
        const main = params.find(p => ['과거 사용량','예측값'].includes(p.seriesName))
        if (!main) return ''
        const d = new Date(main.value[0])
        const dot = main.seriesName === '예측값' ? '#11cdef' : '#5e72e4'
        return `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${fmtTime(d)}</div>
                <div style="display:flex;align-items:center;gap:6px;">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${dot};"></span>
                  <span style="color:#a0a0c0;">${main.seriesName}</span>
                  <b style="margin-left:auto;font-size:15px;">${main.value[1].toFixed(1)}</b>
                  <span style="color:#6a6a8a;font-size:11px;">W</span>
                </div>`
      },
    },
    series,
  }
}

async function draw() {
  await nextTick()
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption(buildOption(), true)
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => chart?.dispose())
watch([() => props.histDf, () => props.forecastDf, () => props.newsView, showCi, showNews], draw)
</script>