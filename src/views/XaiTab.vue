<template>
  <div class="row" style="gap:14px;">
    <div class="col-1">
      <div class="panel" style="margin-bottom:12px;">
        <div class="section-label">AI 분석 설명</div>
        <div class="xai-box">{{ xaiResult.text }}</div>
      </div>
      <div class="panel">
        <div class="section-label">요인 중요도</div>
        <div ref="barEl" style="width:100%; height:200px;"></div>
      </div>
    </div>
    <div class="col-1">
      <div class="panel">
        <div class="section-label">뉴스 이벤트</div>
        <p v-if="!newsView.length" style="color:#5a5a7a; font-size:11px;">
          선택 기간에 해당하는 뉴스 이벤트가 없습니다.
        </p>
        <div v-for="row in sortedNews" :key="String(row.timestamp)"
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
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  xaiResult: { type: Object, default: () => ({ text: '', factors: [] }) },
  newsView:  { type: Array,  default: () => [] },
})

const barEl = ref(null)
const sortedNews = computed(() => [...props.newsView].sort((a,b) => b.timestamp-a.timestamp))
const level = s => s >= 0.7 ? 'high' : s >= 0.5 ? 'mid' : 'low'
const fmt = d => { const p=n=>String(n).padStart(2,'0'); return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}` }

async function draw() {
  await nextTick()
  const P = window.Plotly
  if (!P || !barEl.value || !props.xaiResult.factors.length) return
  const s = [...props.xaiResult.factors].sort((a,b) => a.importance-b.importance)
  P.react(barEl.value, [{
    x: s.map(f => f.importance), y: s.map(f => f.factor),
    orientation: 'h', type: 'bar',
    marker: { color: s.map(f => f.importance >= 0.5 ? '#f87171' : f.importance >= 0.3 ? '#facc15' : '#4ade80'), opacity: 0.8 },
    text: s.map(f => `${(f.importance*100).toFixed(0)}%`),
    textposition: 'outside', textfont: { size: 10, color: '#9090b8' },
    hovertemplate: '%{y}: %{x:.0%}<extra></extra>',
  }], {
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'#0a0a0f',
    font:{family:'Pretendard',color:'#9090b8',size:10},
    margin:{l:140,r:60,t:8,b:24}, height:200, bargap:0.5,
    xaxis:{range:[0,1.2],tickformat:'.0%',gridcolor:'#1e1e2e',linecolor:'#1e1e2e',tickfont:{color:'#9090b8',size:9}},
    yaxis:{gridcolor:'#1e1e2e',linecolor:'#1e1e2e',tickfont:{color:'#c8c8e0',size:11}},
    hoverlabel:{bgcolor:'#141420',bordercolor:'#2a2a3e',font:{color:'#f0f0f5',size:11}},
  })
}

onMounted(() => { const t=setInterval(()=>{if(window.Plotly){clearInterval(t);draw()}},100) })
watch(() => props.xaiResult, draw)
</script>
