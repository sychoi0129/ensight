<template>
  <div class="app-shell">

    <!-- 사이드바 -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-mark">E</div>
        <div>
          <div class="logo-text">ensight</div>
          <div class="logo-sub">전력 수요 예측</div>
        </div>
      </div>

      <div class="sidebar-section-label">조회 조건</div>
      <div class="sidebar-controls">
        <div class="ctrl-group">
          <label class="form-label">지역</label>
          <select class="form-select" v-model="selectedRegion">
            <option v-for="r in regions" :key="r">{{ r }}</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label class="form-label">시설</label>
          <select class="form-select" v-model="selectedFacility">
            <option>전체</option>
            <option v-for="f in facilityOptions" :key="f">{{ f }}</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label class="form-label">날짜</label>
          <input type="date" class="form-select" v-model="selectedDate"
            :min="minDate" :max="maxDate" />
        </div>
        <div class="ctrl-group">
          <label class="form-label">시간</label>
          <select class="form-select" v-model="selectedTime">
            <option v-for="t in availableTimes" :key="t">{{ t }}</option>
          </select>
        </div>
      </div>

      <div class="sidebar-section-label" style="margin-top:24px;">메뉴</div>
      <nav class="sidebar-nav">
        <button
          v-for="tab in tabs" :key="tab.key"
          class="nav-item" :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="nav-icon">
            <img :src="tab.icon" :alt="tab.label" class="nav-icon-img" />
          </span>
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="pill live">● LIVE</div>
        <div class="sidebar-model">DUMMY · v0.1</div>
      </div>
    </aside>

    <!-- 메인 콘텐츠 -->
    <main class="main-content">

      <!-- 페이지 헤더 -->
      <div class="page-header">
        <div>
          <div class="page-breadcrumb">Pages / 대시보드</div>
          <div class="page-title">{{ tabs.find(t => t.key === activeTab)?.label }}</div>
        </div>
        <div class="page-header-right">
          <span class="status-item">{{ selectedRegion }}</span>
          <span class="status-item">{{ selectedDate }} {{ selectedTime }}</span>
        </div>
      </div>

      <!-- KPI 카드 -->
      <div class="kpi-row">
        <div class="kpi-card ok">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">직전 전력</div>
              <div class="kpi-value">{{ latestPower }}</div>
              <div class="kpi-unit">MW · 마지막 입력값</div>
            </div>
            <div class="kpi-icon" style="background:linear-gradient(135deg,#1a7f37,#4ade80)">⚡</div>
          </div>
        </div>
        <div class="kpi-card warn">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">168step 피크</div>
              <div class="kpi-value">{{ loadPeak }}</div>
              <div class="kpi-unit">MW · 입력 구간 최대값</div>
            </div>
            <div class="kpi-icon" style="background:linear-gradient(135deg,#9e6a03,#facc15)">📈</div>
          </div>
        </div>
        <div class="kpi-card info">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">평균 기온</div>
              <div class="kpi-value">{{ avgTemp }}°</div>
              <div class="kpi-unit">°C · 168step 평균</div>
            </div>
            <div class="kpi-icon" style="background:linear-gradient(135deg,#1d4ed8,#60a5fa)">🌡️</div>
          </div>
        </div>
        <div class="kpi-card alert">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">뉴스 이벤트</div>
              <div class="kpi-value">{{ newsView.length }}</div>
              <div class="kpi-unit">건 · 168step 기준</div>
            </div>
            <div class="kpi-icon" style="background:linear-gradient(135deg,#b91c1c,#f87171)">📰</div>
          </div>
        </div>
      </div>

      <div class="content-area">
        <DemandTab
          v-if="activeTab === 'demand'"
          :hist-df="histDf"
          :forecast-df="forecastDf"
          :news-view="newsView"
          :horizon="HORIZON"
          :xai-result="xaiResult"
        />

        <MapTab
          v-else-if="activeTab === 'map'"
          :map-df="mapDf"
        />

        <WeatherTab
          v-else-if="activeTab === 'weather'"
          :weather-view="weatherView"
          :hist-df="histDf"
        />
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDummyData }   from '@/composables/useDummyData'
import { makeForecast }   from '@/composables/useForecast'
import { summarizeXai, buildMapData } from '@/composables/useXai'
import { REGION_ORDER }   from '@/constants/settings'
import DemandTab  from '@/views/DemandTab.vue'
import MapTab     from '@/views/MapTab.vue'
import WeatherTab from '@/views/WeatherTab.vue'
import demandIcon from '@/assets/images/icons/demand.png'
import mapIcon from '@/assets/images/icons/map.png'
import weatherIcon from '@/assets/images/icons/weather.png'

const INPUT_WINDOW = 168
const HORIZON = 12

const { loadDf, weatherDf, newsDf } = useDummyData()

const existingRegions = [...new Set(loadDf.map(r => r.region))]
const regions = REGION_ORDER.filter(r => existingRegions.includes(r))
const selectedRegion   = ref(regions[0])
const selectedFacility = ref('전체')
const activeTab = ref('demand')

const facilityOptions = computed(() =>
  [...new Set(loadDf.filter(r => r.region === selectedRegion.value).map(r => r.facility))].sort()
)
watch(selectedRegion, () => { selectedFacility.value = '전체' })

const tabs = [
  { key: 'demand',  label: '전력 사용량 예측', icon: demandIcon},
  { key: 'map',     label: '지역별 현황', icon: mapIcon},
  { key: 'weather', label: '기상 분석', icon: weatherIcon},
]

const baseHist = computed(() =>
  loadDf
    .filter(r => {
      if (r.region !== selectedRegion.value) return false
      if (selectedFacility.value !== '전체' && r.facility !== selectedFacility.value) return false
      return true
    })
    .sort((a, b) => a.timestamp - b.timestamp)
)

const toDateStr = d => { const p = n => String(n).padStart(2,'0'); return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}` }
const toTimeStr = d => { const p = n => String(n).padStart(2,'0'); return `${p(d.getHours())}:${p(d.getMinutes())}` }

const validAnchors   = computed(() => baseHist.value.slice(INPUT_WINDOW - 1))
const availableDates = computed(() => [...new Set(validAnchors.value.map(r => toDateStr(r.timestamp)))])
const minDate = computed(() => availableDates.value[0] ?? '')
const maxDate = computed(() => availableDates.value[availableDates.value.length - 1] ?? '')
const selectedDate = ref('')
const selectedTime = ref('')

watch(availableDates, dates => { if (dates.length) selectedDate.value = dates[dates.length - 1] }, { immediate: true })

const availableTimes = computed(() =>
  [...new Set(validAnchors.value.filter(r => toDateStr(r.timestamp) === selectedDate.value).map(r => toTimeStr(r.timestamp)))].sort()
)
watch(availableTimes, times => { if (times.length) selectedTime.value = times[times.length - 1] }, { immediate: true })

const anchorTs = computed(() => {
  if (!selectedDate.value || !selectedTime.value) return null
  return new Date(`${selectedDate.value}T${selectedTime.value}`)
})

const histDf = computed(() => {
  if (!anchorTs.value) return []
  const filtered = baseHist.value.filter(r => r.timestamp <= anchorTs.value)
  
  if (selectedFacility.value !== '전체') {
    return filtered.slice(-INPUT_WINDOW)
  }
  
  // 전체 선택 시 timestamp별 평균
  const grouped = new Map()
  for (const r of filtered) {
    const key = r.timestamp.getTime()
    if (!grouped.has(key)) grouped.set(key, { timestamp: r.timestamp, sum: 0, count: 0 })
    grouped.get(key).sum += r.power_usage
    grouped.get(key).count += 1
  }
  return [...grouped.values()]
    .sort((a, b) => a.timestamp - b.timestamp)
    .slice(-INPUT_WINDOW)
    .map(r => ({ ...r, power_usage: +(r.sum / r.count).toFixed(2) }))
})

const windowStart = computed(() => histDf.value[0]?.timestamp ?? null)
const windowEnd   = computed(() => histDf.value[histDf.value.length - 1]?.timestamp ?? null)

const weatherView = computed(() => {
  if (!windowStart.value) return []
  return weatherDf.filter(r => r.region === selectedRegion.value && r.timestamp >= windowStart.value && r.timestamp <= windowEnd.value)
})
const newsView = computed(() => {
  if (!windowStart.value) return []
  return newsDf.filter(r => r.region === selectedRegion.value && r.timestamp >= windowStart.value && r.timestamp <= windowEnd.value)
})

const forecastDf = computed(() => makeForecast(histDf.value, HORIZON))
const xaiResult  = computed(() => summarizeXai(histDf.value, weatherView.value, newsView.value, INPUT_WINDOW))
const mapDf      = computed(() => {
  if (!windowStart.value) return []
  return buildMapData(loadDf.filter(r => r.timestamp >= windowStart.value && r.timestamp <= windowEnd.value))
})

const latestPower = computed(() => histDf.value.length ? histDf.value[histDf.value.length - 1].power_usage.toFixed(1) : '—')
const loadPeak    = computed(() => histDf.value.length ? Math.max(...histDf.value.map(r => r.power_usage)).toFixed(1) : '—')
const avgTemp     = computed(() => weatherView.value.length ? (weatherView.value.reduce((s, r) => s + r.temperature, 0) / weatherView.value.length).toFixed(1) : '—')
</script>
