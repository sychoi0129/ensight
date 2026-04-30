<template>
  <div>
    <div style="margin-bottom:14px;">
      <label class="form-label">기상 변수</label>
      <select class="form-select" v-model="selectedLabel" style="margin-top:4px;">
        <option v-for="l in metricLabels" :key="l">{{ l }}</option>
      </select>
    </div>

    <div class="panel" style="margin-bottom:12px;">
      <div class="section-label">{{ selectedLabel }} + 전력 사용량</div>
      <div ref="dualEl" style="width:100%; height:300px;"></div>
    </div>

    <div class="panel">
      <div class="section-label">{{ selectedLabel }} ↔ 전력 상관관계</div>
      <div ref="scatterEl" style="width:100%; height:240px;"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { WEATHER_METRIC_MAP } from '@/constants/settings'

const props = defineProps({
  weatherView: { type: Array, default: () => [] },
  histDf:      { type: Array, default: () => [] },
})

const metricLabels  = Object.keys(WEATHER_METRIC_MAP)
const selectedLabel = ref(metricLabels[0])
const metric        = computed(() => WEATHER_METRIC_MAP[selectedLabel.value])
const dualEl    = ref(null)
const scatterEl = ref(null)

const BASE = { paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'#ffffff', font:{family:'Pretendard',color:'#8898aa',size:10}, margin:{l:48,r:48,t:12,b:36} }
const AXIS = { gridcolor:'#e9ecef', linecolor:'#dee2e6', zerolinecolor:'#dee2e6', tickfont:{color:'#8898aa',size:10} }
const HOVER = { bgcolor:'#ffffff', bordercolor:'#dee2e6', font:{color:'#1a1a2e',size:11} }

async function draw() {
  await nextTick()
  const P = window.Plotly
  if (!P || !dualEl.value || !scatterEl.value) return

  const toISO = d => d instanceof Date ? d.toISOString() : String(d)

  P.react(dualEl.value, [
    {
      x: props.weatherView.map(r => toISO(r.timestamp)),
      y: props.weatherView.map(r => r[metric.value]),
      mode: 'lines', name: selectedLabel.value,
      line: { color: '#4ade80', width: 1.5 }, yaxis: 'y1',
    },
    {
      x: props.histDf.map(r => toISO(r.timestamp)),
      y: props.histDf.map(r => r.power_usage),
      mode: 'lines', name: '전력 사용량',
      line: { color: '#5865f2', width: 1.2, dash: 'dot' },
      opacity: 0.55, yaxis: 'y2',
    },
  ], {
    ...BASE, height: 300,
    xaxis: { ...AXIS, type: 'date' },
    yaxis: { ...AXIS, type: 'linear', title: { text: selectedLabel.value, font: { color: '#8898aa', size: 10 } } },
    yaxis2: { ...AXIS, type: 'linear', title: { text: 'MW', font: { color: '#8898aa', size: 10 } }, overlaying: 'y', side: 'right', gridcolor: 'rgba(0,0,0,0)' },
    legend: { orientation: 'h', y: 1.05, bgcolor: 'rgba(0,0,0,0)', font: { size: 10, color: '#8898aa' } },
    hoverlabel: HOVER,
  })

  const merged = props.histDf.map(h => {
    const w = props.weatherView.find(r => r.timestamp.getTime() === h.timestamp.getTime())
    return w ? { x: w[metric.value], y: h.power_usage } : null
  }).filter(Boolean)

  if (merged.length < 2) return

  const xv = merged.map(r => r.x), yv = merged.map(r => r.y), n = xv.length
  const sx = xv.reduce((a,b)=>a+b,0), sy = yv.reduce((a,b)=>a+b,0)
  const sxy = xv.reduce((s,x,i)=>s+x*yv[i],0), sx2 = xv.reduce((s,x)=>s+x*x,0)
  const m = (n*sxy-sx*sy)/(n*sx2-sx*sx), b = (sy-m*sx)/n
  const xmin = Math.min(...xv), xmax = Math.max(...xv)

  P.react(scatterEl.value, [
    { x: xv, y: yv, mode: 'markers', marker: { color: '#5e72e4', opacity: 0.25, size: 4 }, name: '데이터' },
    { x: [xmin,xmax], y: [m*xmin+b, m*xmax+b], mode: 'lines', line: { color: '#5e72e4', width: 1.5, dash: 'dot' }, name: '추세선' },
  ], {
    ...BASE, height: 240,
    xaxis: { ...AXIS, title: { text: selectedLabel.value, font:{color:'#8898aa',size:10} } },
    yaxis: { ...AXIS, type: 'linear', title: { text: 'MW', font:{color:'#8898aa',size:10} } },
    legend: { bgcolor:'rgba(0,0,0,0)', font:{size:10,color:'#8898aa'} },
    hoverlabel: HOVER,
  })
}

onMounted(() => { const t=setInterval(()=>{if(window.Plotly){clearInterval(t);draw()}},100) })
watch([()=>props.weatherView, ()=>props.histDf, selectedLabel], draw)
</script>
