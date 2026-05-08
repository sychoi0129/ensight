<template>
  <div>
    <div class="row" style="gap:14px;">
      <div class="panel" style="flex:1.2; min-width:0;">
        <div class="section-label">지역별 피크 부하 현황</div>
        <div ref="mapEl" style="width:100%; height:380px;"></div>
      </div>
      <div class="panel" style="flex:1.8; min-width:0;">
        <div class="section-label">지역 랭킹</div>
        <div ref="barEl" style="width:100%; height:420px;"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({ mapDf: { type: Array, default: () => [] } })
const mapEl = ref(null)
const barEl = ref(null)
let barChart = null

// 지도는 Plotly 유지 (scattergeo는 ECharts에서 별도 설정 필요)
async function drawMap() {
  await nextTick()
  const P = window.Plotly
  if (!P || !mapEl.value || !props.mapDf.length) return

  P.react(mapEl.value, [{
    type: 'scattergeo',
    lat: props.mapDf.map(r => r.lat),
    lon: props.mapDf.map(r => r.lng),
    text: props.mapDf.map(r => `${r.region}  ${r.avg_load.toFixed(1)} kW`),
    mode: 'markers+text', textposition: 'top center',
    textfont: { size: 9, color: '#8898aa' },
    marker: {
      size: props.mapDf.map(r => Math.max(8, r.avg_load / 5)),
      color: props.mapDf.map(r => r.avg_load),
      colorscale: [[0,'#e8ebfc'],[0.4,'#5865f2'],[1,'#c0b0ff']],
      showscale: true,
      colorbar: { title:{text:'kW',font:{color:'#8898aa',size:10}}, thickness:8, len:0.5, tickfont:{color:'#8898aa',size:9} },
      line: { color: '#c8d0da', width: 0.5 },
    },
    hovertemplate: '%{text}<extra></extra>',
  }], {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: '#ffffff',
    font: { family: 'Pretendard', color: '#8898aa', size: 10 },
    margin: { l: 0, r: 40, t: 8, b: 0 },
    height: 380,
    geo: {
      scope: 'asia', center: { lat: 36.5, lon: 127.8 }, projection: { scale: 18 },
      showland: true, landcolor: '#f0f2f5',
      showcoastlines: true, coastlinecolor: '#c8d0da',
      showframe: false, bgcolor: 'rgba(0,0,0,0)',
      showocean: true, oceancolor: '#dde8f0',
    },
    hoverlabel: { bgcolor: '#1a1a2e', bordercolor: 'transparent', font: { color: '#fff', size: 12 } },
  })
}

// 랭킹 바 차트는 ECharts
async function drawBar() {
  await nextTick()
  if (!barEl.value || !props.mapDf.length) return
  if (!barChart) barChart = echarts.init(barEl.value)

  const sorted = [...props.mapDf].sort((a, b) => a.avg_load - b.avg_load)
  barChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 10, right: 70, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1000,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: {
        color: '#8898aa',
        fontSize: 10,
        fontFamily: 'Pretendard',
        formatter: (v) => `${Math.round(v)}`,
      },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: sorted.map(r => r.region),
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
      formatter: p => `<b>${p.name}</b><br><span style="color:#c0b0ff;">${p.value.toFixed(1)} kW</span>`,
    },
    series: [{
      type: 'bar',
      data: sorted.map(r => ({
        value: r.avg_load,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#8b9ef0' },
            { offset: 1, color: '#5e72e4' },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
      })),
      barMaxWidth: 22,
      label: {
        show: true,
        position: 'right',
        color: '#8898aa',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        formatter: p => p.value.toFixed(1),
      },
    }],
  }, true)
}

async function draw() {
  await drawMap()
  await drawBar()
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => barChart?.dispose())
watch(() => props.mapDf, draw)
</script>
