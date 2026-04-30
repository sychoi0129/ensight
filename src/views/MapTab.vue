<template>
  <div>
    <div class="row" style="gap:14px;">
      <div class="panel" style="flex:1.2; min-width:0;">
        <div class="section-label">지역별 평균 전력 수요</div>
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
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({ mapDf: { type: Array, default: () => [] } })
const mapEl = ref(null)
const barEl = ref(null)

const BASE = { paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'#ffffff', font:{family:'Pretendard',color:'#8898aa',size:10}, margin:{l:8,r:8,t:12,b:8} }
const HOVER = { bgcolor:'#ffffff', bordercolor:'#dee2e6', font:{color:'#1a1a2e',size:11} }

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
    textfont: { size: 9, color: '#8898aa' },
    marker: {
      size: props.mapDf.map(r => Math.max(8, r.avg_load / 5)),
      color: props.mapDf.map(r => r.avg_load),
      colorscale: [[0,'#e8ebfc'],[0.4,'#5865f2'],[1,'#c0b0ff']],
      showscale: true,
      colorbar: { title:{text:'MW',font:{color:'#8898aa',size:10}}, thickness:8, len:0.5, tickfont:{color:'#8898aa',size:9} },
      line: { color: '#c8d0da', width: 0.5 },
    },
    hovertemplate: '%{text}<extra></extra>',
  }], {
    ...BASE, height: 420,
    geo: {
      scope: 'asia', center: { lat: 36.5, lon: 127.8 }, projection: { scale: 18 },
      showland: true, landcolor: '#f0f2f5',
      showcoastlines: true, coastlinecolor: '#c8d0da',
      showframe: false, bgcolor: 'rgba(0,0,0,0)',
      showocean: true, oceancolor: '#dde8f0',
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
      colorscale: [[0,'#e8ebfc'],[0.4,'#5865f2'],[1,'#c0b0ff']],
      opacity: 0.85,
    },
    hovertemplate: '%{y}: %{x:.1f} MW<extra></extra>',
  }], {
    ...BASE, height: 420,
    margin: { l: 90, r: 16, t: 12, b: 36 },
    xaxis: {
      title:{text:'MW',font:{color:'#8898aa',size:10}},
      range: [
        Math.min(...sorted.map(r => r.avg_load)) * 0.95,
        Math.max(...sorted.map(r => r.avg_load)) * 1.02,
      ],
      gridcolor:'#e9ecef',
      linecolor:'#dee2e6',
      tickfont:{color:'#8898aa',size:10} },
    yaxis: { automargin:true, gridcolor:'#e9ecef', linecolor:'#dee2e6', tickfont:{color:'#4a5568',size:11} },
    hoverlabel: HOVER,
  })
}

onMounted(() => { const t=setInterval(()=>{if(window.Plotly){clearInterval(t);draw()}},100) })
watch(() => props.mapDf, draw)
</script>
