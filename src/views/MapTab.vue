<template>
  <div>
    <div class="row" style="gap:14px;">
      <div class="col-2 panel">
        <div class="section-label">지역별 평균 전력 수요</div>
        <div ref="mapEl" style="width:100%; height:420px;"></div>
      </div>
      <div class="col-1 panel">
        <div class="section-label">지역 랭킹</div>
        <div ref="barEl" style="width:100%; height:420px;"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({ mapDf: { type: Array, default: () => [] } })
const mapEl = ref(null)
const barEl = ref(null)

const BASE = { paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'#0a0a0f', font:{family:'Pretendard',color:'#9090b8',size:10}, margin:{l:8,r:8,t:12,b:8} }
const HOVER = { bgcolor:'#141420', bordercolor:'#2a2a3e', font:{color:'#f0f0f5',size:11} }

async function draw() {
  await nextTick()
  const P = window.Plotly
  if (!P || !mapEl.value || !barEl.value || !props.mapDf.length) return

  P.react(mapEl.value, [{
    type: 'scattergeo',
    lat: props.mapDf.map(r => r.lat),
    lon: props.mapDf.map(r => r.lng),
    text: props.mapDf.map(r => `${r.region}  ${r.avg_load.toFixed(1)} MW`),
    mode: 'markers+text', textposition: 'top center',
    textfont: { size: 9, color: '#9090b8' },
    marker: {
      size: props.mapDf.map(r => Math.max(8, r.avg_load / 5)),
      color: props.mapDf.map(r => r.avg_load),
      colorscale: [[0,'#14142a'],[0.4,'#5865f2'],[1,'#c0b0ff']],
      showscale: true,
      colorbar: { title:{text:'MW',font:{color:'#9090b8',size:10}}, thickness:8, len:0.5, tickfont:{color:'#9090b8',size:9} },
      line: { color: '#2a2a3e', width: 0.5 },
    },
    hovertemplate: '%{text}<extra></extra>',
  }], {
    ...BASE, height: 420,
    geo: {
      scope: 'asia', center: { lat: 36.5, lon: 127.8 }, projection: { scale: 18 },
      showland: true, landcolor: '#141420',
      showcoastlines: true, coastlinecolor: '#2a2a3e',
      showframe: false, bgcolor: 'rgba(0,0,0,0)',
      showocean: true, oceancolor: '#0a0a0f',
    },
    hoverlabel: HOVER,
  })

  const sorted = [...props.mapDf].sort((a,b) => a.avg_load - b.avg_load)
  P.react(barEl.value, [{
    type: 'bar', orientation: 'h',
    x: sorted.map(r => r.avg_load),
    y: sorted.map(r => r.region),
    marker: {
      color: sorted.map(r => r.avg_load),
      colorscale: [[0,'#14142a'],[0.4,'#5865f2'],[1,'#c0b0ff']],
      opacity: 0.85,
    },
    hovertemplate: '%{y}: %{x:.1f} MW<extra></extra>',
  }], {
    ...BASE, height: 420,
    margin: { l: 90, r: 16, t: 12, b: 36 },
    xaxis: { title:{text:'MW',font:{color:'#9090b8',size:10}}, gridcolor:'#1e1e2e', linecolor:'#1e1e2e', tickfont:{color:'#9090b8',size:10} },
    yaxis: { automargin:true, gridcolor:'#1e1e2e', linecolor:'#1e1e2e', tickfont:{color:'#c8c8e0',size:11} },
    hoverlabel: HOVER,
  })
}

onMounted(() => { const t=setInterval(()=>{if(window.Plotly){clearInterval(t);draw()}},100) })
watch(() => props.mapDf, draw)
</script>
