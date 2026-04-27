<template>
  <div class="page-wrap">

    <!-- 탑바 -->
    <div class="topbar">
      <div class="logo-mark">E</div>
      <div>
        <span class="logo-text">ensight</span>
        <span class="logo-sub">전력 수요 예측 대시보드</span>
      </div>
      <div class="topbar-right">
        <div class="pill live">LIVE</div>
      </div>
    </div>

    <!-- 컨트롤 바 -->
    <div class="ctrl-bar">
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
      <div class="ctrl-divider"></div>
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

    <!-- KPI 카드 -->
    <div class="kpi-row">
      <div class="kpi-card ok">
        <div class="kpi-tag">
          <span class="kpi-dot" style="background:#4ade80"></span>직전 전력
        </div>
        <div class="kpi-value">{{ latestPower }}</div>
        <div class="kpi-unit">MW · 마지막 입력값</div>
      </div>
      <div class="kpi-card warn">
        <div class="kpi-tag">
          <span class="kpi-dot" style="background:#facc15"></span>168step 피크
        </div>
        <div class="kpi-value">{{ loadPeak }}</div>
        <div class="kpi-unit">MW · 입력 구간 최대값</div>
      </div>
      <div class="kpi-card info">
        <div class="kpi-tag">
          <span class="kpi-dot" style="background:#60a5fa"></span>평균 기온
        </div>
        <div class="kpi-value">{{ avgTemp }}°</div>
        <div class="kpi-unit">°C · 168step 평균</div>
      </div>
      <div class="kpi-card alert">
        <div class="kpi-tag">
          <span class="kpi-dot" style="background:#f87171"></span>뉴스 이벤트
        </div>
        <div class="kpi-value">{{ newsView.length }}</div>
        <div class="kpi-unit">건 · 168step 기준</div>
      </div>
    </div>

    <!-- 탭 바 -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs" :key="tab.key"
        class="tab-btn" :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <!-- 탭 콘텐츠 -->
    <div class="tab-content">
      <div v-show="activeTab === 'demand'">
        <DemandTab
          :hist-df="histDf" :forecast-df="forecastDf"
          :news-view="newsView" :horizon="HORIZON"
        />
      </div>
      <div v-show="activeTab === 'map'">
        <MapTab :map-df="mapDf" />
      </div>
      <div v-show="activeTab === 'weather'">
        <WeatherTab :weather-view="weatherView" :hist-df="histDf" />
      </div>
      <div v-show="activeTab === 'xai'">
        <XaiTab :xai-result="xaiResult" :news-view="newsView" />
      </div>
    </div>

    <!-- 상태 바 -->
    <div class="status-bar">
      <span class="status-item">REGION <span>{{ selectedRegion }}</span></span>
      <span class="status-item">FACILITY <span>{{ selectedFacility }}</span></span>
      <span class="status-item">INPUT <span>168 STEP</span></span>
      <span class="status-item">HORIZON <span>12 STEP</span></span>
      <span class="status-item">MODEL <span>DUMMY · v0.1</span></span>
      <span class="status-item right">{{ selectedDate }} {{ selectedTime }}</span>
    </div>

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
import XaiTab     from '@/views/XaiTab.vue'

const INPUT_WINDOW = 168
const HORIZON = 12

const { loadDf, weatherDf, newsDf } = useDummyData()

const existingRegions = [...new Set(loadDf.map(r => r.region))]
const regions = REGION_ORDER.filter(r => existingRegions.includes(r))
const selectedRegion   = ref(regions[0])
const selectedFacility = ref('전체')
const activeTab = ref('demand')

const tabs = [
  { key: 'demand',  label: '수요 & 예측' },
  { key: 'map',     label: '지역 현황' },
  { key: 'weather', label: '기상 분석' },
  { key: 'xai',     label: 'XAI / 뉴스' },
]

const facilityOptions = computed(() =>
  [...new Set(loadDf.filter(r => r.region === selectedRegion.value).map(r => r.facility))].sort()
)
watch(selectedRegion, () => { selectedFacility.value = '전체' })

const baseHist = computed(() =>
  loadDf
    .filter(r => {
      if (r.region !== selectedRegion.value) return false
      if (selectedFacility.value !== '전체' && r.facility !== selectedFacility.value) return false
      return true
    })
    .sort((a, b) => a.timestamp - b.timestamp)
)

const toDateStr = d => {
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`
}
const toTimeStr = d => {
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}

const validAnchors   = computed(() => baseHist.value.slice(INPUT_WINDOW - 1))
const availableDates = computed(() => [...new Set(validAnchors.value.map(r => toDateStr(r.timestamp)))])
const minDate = computed(() => availableDates.value[0] ?? '')
const maxDate = computed(() => availableDates.value[availableDates.value.length - 1] ?? '')
const selectedDate = ref('')
const selectedTime = ref('')

watch(availableDates, dates => {
  if (dates.length) selectedDate.value = dates[dates.length - 1]
}, { immediate: true })

const availableTimes = computed(() =>
  [...new Set(
    validAnchors.value
      .filter(r => toDateStr(r.timestamp) === selectedDate.value)
      .map(r => toTimeStr(r.timestamp))
  )].sort()
)
watch(availableTimes, times => {
  if (times.length) selectedTime.value = times[times.length - 1]
}, { immediate: true })

const anchorTs = computed(() => {
  if (!selectedDate.value || !selectedTime.value) return null
  return new Date(`${selectedDate.value}T${selectedTime.value}`)
})

const histDf = computed(() => {
  if (!anchorTs.value) return []
  return baseHist.value.filter(r => r.timestamp <= anchorTs.value).slice(-INPUT_WINDOW)
})

const windowStart = computed(() => histDf.value[0]?.timestamp ?? null)
const windowEnd   = computed(() => histDf.value[histDf.value.length - 1]?.timestamp ?? null)

const weatherView = computed(() => {
  if (!windowStart.value) return []
  return weatherDf.filter(r =>
    r.region === selectedRegion.value &&
    r.timestamp >= windowStart.value &&
    r.timestamp <= windowEnd.value
  )
})
const newsView = computed(() => {
  if (!windowStart.value) return []
  return newsDf.filter(r =>
    r.region === selectedRegion.value &&
    r.timestamp >= windowStart.value &&
    r.timestamp <= windowEnd.value
  )
})

const forecastDf = computed(() => makeForecast(histDf.value, HORIZON))
const xaiResult  = computed(() => summarizeXai(histDf.value, weatherView.value, newsView.value, INPUT_WINDOW))
const mapDf      = computed(() => {
  if (!windowStart.value) return []
  return buildMapData(loadDf.filter(r => r.timestamp >= windowStart.value && r.timestamp <= windowEnd.value))
})

const latestPower = computed(() => {
  if (!histDf.value.length) return '—'
  return histDf.value[histDf.value.length - 1].power_usage.toFixed(1)
})
const loadPeak = computed(() => {
  if (!histDf.value.length) return '—'
  return Math.max(...histDf.value.map(r => r.power_usage)).toFixed(1)
})
const avgTemp = computed(() => {
  if (!weatherView.value.length) return '—'
  return (weatherView.value.reduce((s, r) => s + r.temperature, 0) / weatherView.value.length).toFixed(1)
})
</script>
