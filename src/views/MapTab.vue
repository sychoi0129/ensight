<template>
  <div>
    <div class="row" style="gap:14px;">
      <div class="panel" style="flex:1.2; min-width:0;">
        <div class="section-label">지역별 피크 부하 현황</div>
        <div ref="mapEl" style="width:100%; height:420px; border-radius:10px; overflow:hidden; position:relative;">
          <div v-if="!mapDf.length" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8898aa;font-size:13px;">
            데이터 없음
          </div>
        </div>
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
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { ColumnLayer } from '@deck.gl/layers'
import { MapboxOverlay } from '@deck.gl/mapbox'

const props = defineProps({ mapDf: { type: Array, default: () => [] } })
const mapEl = ref(null)
const barEl = ref(null)
let barChart = null
let mapInstance = null
let deckOverlay = null

// ── 색상 보간 (낮음: #8b9ef0 → 높음: #c0b0ff → 최고: #f5365c)
function loadColor(normalized) {
  const r1 = 139, g1 = 158, b1 = 240
  const r2 = 192, g2 = 176, b2 = 255
  const r = Math.round(r1 + (r2 - r1) * normalized)
  const g = Math.round(g1 + (g2 - g1) * normalized)
  const b = Math.round(b1 + (b2 - b1) * normalized)
  return [r, g, b, 210]
}

function buildLayer() {
  const maxLoad = Math.max(...props.mapDf.map(r => r.avg_load), 1)
  return new ColumnLayer({
    id: 'peak-load',
    data: props.mapDf,
    diskResolution: 24,
    radius: 18000,
    extruded: true,
    pickable: true,
    elevationScale: 80,
    getPosition: d => [d.lng, d.lat],
    getElevation: d => d.avg_load,
    getFillColor: d => loadColor(d.avg_load / maxLoad),
    getLineColor: [255, 255, 255, 60],
    lineWidthMinPixels: 1,
  })
}

function buildTooltip({ object }) {
  if (!object) return null
  return {
    html: `<div style="background:#1a1a2e;padding:8px 12px;border-radius:8px;font-family:Pretendard;color:#fff;font-size:12px;">
      <b>${object.region}</b><br/>
      <span style="color:#c0b0ff;">피크 부하 ${object.avg_load.toFixed(1)} kW</span>
    </div>`,
    style: { background: 'none', border: 'none', padding: 0 },
  }
}

async function drawMap() {
  await nextTick()
  if (!mapEl.value || !props.mapDf.length) return

  const layer = buildLayer()

  if (mapInstance && deckOverlay) {
    deckOverlay.setProps({ layers: [layer] })
    return
  }

  mapInstance = new maplibregl.Map({
    container: mapEl.value,
    style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
    center: [127.8, 36.2],
    zoom: 6.2,
    pitch: 30,
    bearing: 0,
    attributionControl: false,
  })

  deckOverlay = new MapboxOverlay({
    interleaved: false,
    layers: [layer],
    getTooltip: buildTooltip,
  })

  mapInstance.addControl(deckOverlay)
}

// ── 바 차트 (xAxis max 동적)
async function drawBar() {
  await nextTick()
  if (!barEl.value || !props.mapDf.length) return
  if (!barChart) barChart = echarts.init(barEl.value)

  const sorted = [...props.mapDf].sort((a, b) => a.avg_load - b.avg_load)
  const maxVal = Math.max(...sorted.map(r => r.avg_load), 1)
  const xMax = Math.ceil(maxVal * 1.15 / 100) * 100  // 최대값 +15% 올림

  barChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 10, right: 70, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      min: 0,
      max: xMax,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: {
        color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard',
        formatter: v => `${Math.round(v)}`,
      },
      splitLine: { lineStyle: { color: '#2a2a3e', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: sorted.map(r => r.region),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 8,
      padding: [8, 12],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      formatter: p => `<b>${p.name}</b><br/><span style="color:#c0b0ff;">${p.value.toFixed(1)} kW</span>`,
    },
    series: [{
      type: 'bar',
      data: sorted.map(r => ({
        value: r.avg_load,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#8b9ef0' },
            { offset: 1, color: '#5865f2' },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
      })),
      barMaxWidth: 22,
      label: {
        show: true, position: 'right',
        color: '#8898aa', fontSize: 10, fontFamily: 'JetBrains Mono',
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
onUnmounted(() => {
  barChart?.dispose()
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    deckOverlay = null
  }
})
watch(() => props.mapDf, draw, { deep: true })
</script>