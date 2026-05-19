<template>
  <div>
    <div class="row" style="gap:14px;">
      <div class="panel" style="flex:1; min-width:0;">
        <div class="section-label">지역별 피크 부하 현황</div>
        <div ref="mapEl" style="width:100%; height:420px; border-radius:10px; overflow:hidden; position:relative;">
          <div v-if="!mapDf.length" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8898aa;font-size:13px;">
            데이터 없음
          </div>
        </div>
      </div>
      <div class="panel" style="flex:1; min-width:0;">
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
let mapInstance = null
let deckOverlay = null
let MaplibreCtor = null
let MapboxOverlayCtor = null
let ColumnLayerCtor = null

async function ensureMapLibs() {
  if (MaplibreCtor && MapboxOverlayCtor && ColumnLayerCtor) return
  const [maplibreMod, mapboxMod, layersMod] = await Promise.all([
    import('maplibre-gl'),
    import('@deck.gl/mapbox'),
    import('@deck.gl/layers'),
    import('maplibre-gl/dist/maplibre-gl.css'),
  ])
  MaplibreCtor = maplibreMod.Map ?? maplibreMod.default?.Map ?? maplibreMod.default
  MapboxOverlayCtor = mapboxMod.MapboxOverlay
  ColumnLayerCtor = layersMod.ColumnLayer
}

// ── 색상 보간: 낮음 #1a9bfc(하늘) → 중간 #a855f7(보라) → 높음 #ff3d5a(빨강)
function loadColor(normalized) {
  const t = Math.pow(Math.min(Math.max(normalized, 0), 1), 1.8)

  const stops = [
    [26,  155, 252, 200],
    [168,  85, 247, 220],
    [255,  61,  90, 240],
  ]

  let r, g, b, a
  if (t < 0.5) {
    const s = t / 0.5
    r = Math.round(stops[0][0] + (stops[1][0] - stops[0][0]) * s)
    g = Math.round(stops[0][1] + (stops[1][1] - stops[0][1]) * s)
    b = Math.round(stops[0][2] + (stops[1][2] - stops[0][2]) * s)
    a = Math.round(stops[0][3] + (stops[1][3] - stops[0][3]) * s)
  } else {
    const s = (t - 0.5) / 0.5
    r = Math.round(stops[1][0] + (stops[2][0] - stops[1][0]) * s)
    g = Math.round(stops[1][1] + (stops[2][1] - stops[1][1]) * s)
    b = Math.round(stops[1][2] + (stops[2][2] - stops[1][2]) * s)
    a = Math.round(stops[1][3] + (stops[2][3] - stops[1][3]) * s)
  }
  return [r, g, b, a]
}

async function drawMap() {
  await nextTick()
  if (!mapEl.value || !props.mapDf.length) return
  await ensureMapLibs()

  const maxLoad = Math.max(...props.mapDf.map(d => d.avg_load), 1)

  const layer = new ColumnLayerCtor({
    id: 'peak-load',
    data: props.mapDf,
    diskResolution: 32,
    radius: 14000,
    extruded: true,
    pickable: true,
    elevationScale: 60,
    getPosition: d => [d.lng, d.lat],
    getElevation: d => d.avg_load,
    getFillColor: d => loadColor(d.avg_load / maxLoad),
    getLineColor: [255, 255, 255, 80],
    lineWidthMinPixels: 1,
    material: { ambient: 0.35, diffuse: 0.8, shininess: 32, specularColor: [60, 100, 255] },
  })

  // 이미 맵이 있으면 레이어만 업데이트
  if (mapInstance && deckOverlay) {
    deckOverlay.setProps({ layers: [layer] })
    return
  }

  mapInstance = new MaplibreCtor({
    container: mapEl.value,
    style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
    center: [127.8, 36.2],
    zoom: 6.2,
    pitch: 45,
    bearing: -10,
    attributionControl: false,
  })

  deckOverlay = new MapboxOverlayCtor({
    interleaved: true,
    layers: [layer],
    getTooltip: ({ object }) =>
      object && {
        html: `<div style="background:rgba(15,20,50,0.92);padding:8px 12px;border-radius:8px;border:1px solid rgba(100,140,255,0.3);font-family:Pretendard;color:#fff;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,0.3);">
          <b>${object.region}</b><br/>
          <span style="color:#a78bfa;">피크 부하 ${object.avg_load.toFixed(1)} kW</span>
        </div>`,
        style: { background: 'none', border: 'none', padding: 0 },
      },
  })

  mapInstance.addControl(deckOverlay)
}

// ── 바 차트
async function drawBar() {
  await nextTick()
  if (!barEl.value || !props.mapDf.length) return
  if (!barChart) barChart = echarts.init(barEl.value)

  const sorted = [...props.mapDf].sort((a, b) => a.avg_load - b.avg_load)
  const maxVal = Math.max(...sorted.map(r => r.avg_load), 1)
  const xMax = Math.ceil(maxVal * 1.05 / 100) * 100

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
      splitLine: { lineStyle: { color: '#e9ecef', type: 'dashed' } },
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
      data: sorted.map(r => {
        const [rr, gg, bb] = loadColor(r.avg_load / maxVal)
        const hex = `#${[rr,gg,bb].map(v=>v.toString(16).padStart(2,'0')).join('')}`
        return {
          value: r.avg_load,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: hex + 'aa' },
              { offset: 1, color: hex },
            ]),
            borderRadius: [0, 4, 4, 0],
          },
        }
      }),
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
  mapInstance?.remove()
  mapInstance = null
  deckOverlay = null
})
watch(() => props.mapDf, draw, { deep: true })
</script>