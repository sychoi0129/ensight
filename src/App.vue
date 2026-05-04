<template>
  <div class="app-shell">
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
          <select
            class="form-select"
            v-model.number="selectedRegionId"
            :disabled="!regionList.length"
          >
            <option
              v-for="r in regionList"
              :key="r.region_id"
              :value="r.region_id"
            >
              {{ r.region_name }}
            </option>
          </select>
        </div>
        <div class="ctrl-group">
          <label class="form-label">기준 일자</label>
          <input
            type="date"
            class="form-select"
            v-model="selectedIssueDate"
            :min="issueDateMin"
            :max="issueDateMax"
            :disabled="!timeRange"
            @change="refreshDashboard"
          />
        </div>
        <div class="ctrl-group">
          <label class="form-label">기준 시각</label>
          <select
            class="form-select"
            v-model.number="selectedIssueHour"
            :disabled="!timeRange"
            @change="refreshDashboard"
          >
            <option v-for="h in issueHourOptions" :key="h" :value="h">
              {{ pad2(h) }}
            </option>
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
        <div class="sidebar-model">API · DB</div>
      </div>
    </aside>

    <main class="main-content">
      <div class="page-header">
        <div>
          <div class="page-breadcrumb">Ensight ✦ 전국 전력 수요 예측 시스템</div>
          <div class="page-title">{{ tabs.find(t => t.key === activeTab)?.label }}</div>
        </div>
        <div class="page-header-right">
          <span class="status-item">{{ selectedRegionName }}</span>
          <span class="status-item">{{ selectedIssueDate }} {{ pad2(selectedIssueHour) }}</span>
        </div>
      </div>

      <div class="kpi-row">
        <div class="kpi-card ok">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">직전 전력</div>
              <div class="kpi-value">{{ latestPower }}</div>
              <div class="kpi-unit">MW · 마지막 입력값</div>
            </div>
            <div class="kpi-icon blue">
              <img :src="powerIcon" alt="직전 전력" class="kpi-icon-img" />
            </div>
          </div>
        </div>
        <div class="kpi-card warn">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">168step 피크</div>
              <div class="kpi-value">{{ loadPeak }}</div>
              <div class="kpi-unit">MW · 입력 구간 최대값</div>
            </div>
            <div class="kpi-icon blue">
              <img :src="peakIcon" alt="168step 피크" class="kpi-icon-img" />
            </div>
          </div>
        </div>
        <div class="kpi-card info">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">평균 기온</div>
              <div class="kpi-value">{{ avgTemp }}°</div>
              <div class="kpi-unit">°C · 168step 평균</div>
            </div>
            <div class="kpi-icon blue">
              <img :src="tempIcon" alt="평균 기온" class="kpi-icon-img" />
            </div>
          </div>
        </div>
        <div class="kpi-card alert">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">뉴스 이벤트</div>
              <div class="kpi-value">{{ newsMentionKpi }}</div>
              <div class="kpi-unit">뉴스 키워드 합계</div>
            </div>
            <div class="kpi-icon blue">
              <img :src="newsIcon" alt="뉴스 이벤트" class="kpi-icon-img" />
            </div>
          </div>
        </div>
      </div>

      <div class="content-area">
        <DemandTab
          v-if="activeTab === 'demand'"
          :hist-df="histDf"
          :forecast-df="forecastDf"
          :weather-view="weatherView"
          :news-view="newsView"
          :horizon="FORECAST_HOURS"
          :xai-result="xaiResult"
          power-unit="MW"
        />
        <MapTab
          v-else-if="activeTab === 'map'"
          :map-df="mapDf"
          power-unit="MW"
        />
        <WeatherTab
          v-else-if="activeTab === 'weather'"
          :weather-view="weatherView"
          :hist-df="histDf"
          power-unit="MW"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import {
  fetchRegions,
  fetchTimeRange,
  fetchDashboard,
  fetchMapSummary,
  toLocalIso,
  weatherRowsFromSnapshot,
  weatherRowsFromSeries,
  newsRowsFromDashboardNewsSeries,
  newsDayMentionTotal,
  histFromDashboard,
  forecastFromDashboard,
} from '@/api/client'
import { summarizeXai } from '@/composables/useXai'
import { REGION_COORDS } from '@/constants/settings'
import DemandTab  from '@/views/DemandTab.vue'
import MapTab     from '@/views/MapTab.vue'
import WeatherTab from '@/views/WeatherTab.vue'
import demandIcon from '@/assets/images/icons/demand.png'
import mapIcon from '@/assets/images/icons/map.png'
import weatherIcon from '@/assets/images/icons/weather.png'
import powerIcon from '@/assets/images/icons/power.png'
import peakIcon from '@/assets/images/icons/peak.png'
import tempIcon from '@/assets/images/icons/temperature.png'
import newsIcon from '@/assets/images/icons/news.png'

const INPUT_WINDOW = 168
const FORECAST_HOURS = 24
/** API/DB는 kW 등으로 올 수 있음 — 화면은 MW (÷1000) */
const POWER_TO_MW = 0.001

function pad2(n) {
  return String(Number(n)).padStart(2, '0')
}

function toDateStr(d) {
  if (!d || !Number.isFinite(d.getTime())) return ''
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const issueHourOptions = Array.from({ length: 24 }, (_, i) => i)

function issueAsDate() {
  if (!selectedIssueDate.value) return null
  const h = Number(selectedIssueHour.value)
  if (!Number.isFinite(h) || h < 0 || h > 23) return null
  const p = n => String(n).padStart(2, '0')
  const d = new Date(`${selectedIssueDate.value}T${p(h)}:00:00`)
  return Number.isFinite(d.getTime()) ? d : null
}

function latLngForRegion(name, index, total) {
  const c = REGION_COORDS[name]
  if (c) return { lat: c[0], lng: c[1] }
  const angle = (2 * Math.PI * index) / Math.max(total, 1)
  const rad = 0.42 + (index % 5) * 0.06
  return {
    lat: 36.45 + rad * Math.cos(angle),
    lng: 127.85 + rad * Math.sin(angle),
  }
}

function mapSummaryToMapDf(apiRegions) {
  if (!apiRegions?.length) return []
  const n = apiRegions.length
  return apiRegions.map((r, i) => {
    const name = r.region_name
    const { lat, lng } = latLngForRegion(name, i, n)
    const samples = Number(r.sample_count ?? 0) || 0
    const avgField = r.avg_usage_value
    const latestField = r.latest_usage_value
    const avg =
      avgField != null && avgField !== '' ? Number(avgField) : NaN
    const latest =
      latestField != null && latestField !== '' ? Number(latestField) : NaN
    let vRaw
    if (samples > 0 && Number.isFinite(avg)) {
      vRaw = avg
    } else if (Number.isFinite(latest)) {
      vRaw = latest
    } else if (Number.isFinite(avg)) {
      vRaw = avg
    } else {
      vRaw = 0
    }
    return {
      region: name,
      avg_load: +(vRaw * POWER_TO_MW).toFixed(3),
      lat,
      lng,
    }
  })
}

const regionList = ref([])
const selectedRegionId = ref(null)
const timeRange = ref(null)
const selectedIssueDate = ref('')
const selectedIssueHour = ref(0)
const rawDashboard = ref(null)
const rawMapSummary = ref(null)
const activeTab = ref('demand')

const selectedRegionName = computed(() => {
  const r = regionList.value.find(x => x.region_id === selectedRegionId.value)
  return r?.region_name ?? '—'
})

const issueDateMin = computed(() =>
  timeRange.value?.min_ts ? toDateStr(new Date(timeRange.value.min_ts)) : '',
)
const issueDateMax = computed(() =>
  timeRange.value?.max_ts ? toDateStr(new Date(timeRange.value.max_ts)) : '',
)

const histDf = computed(() => {
  const rows = histFromDashboard(rawDashboard.value?.actual_series)
  return rows.map(r => ({ ...r, power_usage: r.power_usage * POWER_TO_MW }))
})

const forecastDf = computed(() => {
  const rows = forecastFromDashboard(rawDashboard.value?.forecast_series)
  return rows.map(r => ({
    ...r,
    prediction: r.prediction * POWER_TO_MW,
    lower: r.lower * POWER_TO_MW,
    upper: r.upper * POWER_TO_MW,
  }))
})

const weatherView = computed(() => {
  const d = rawDashboard.value
  if (!d) return []
  const name = selectedRegionName.value
  const fromSeries = weatherRowsFromSeries(d.weather_series, name)
  if (fromSeries.length) return fromSeries
  return weatherRowsFromSnapshot(histDf.value, d.weather, name)
})

function normalizeNewsDateKey(raw) {
  if (raw == null || raw === '') return ''
  if (typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}/.test(raw.trim())) return raw.trim().slice(0, 10)
  const d = new Date(raw)
  if (!Number.isFinite(d.getTime())) return ''
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/** 백엔드는 issue_ts 기준 뉴스 스냅샷을 (issue日 - 1일) news_date로 조회함 */
function prevCalendarDayKey(yyyyMmDd) {
  const head = typeof yyyyMmDd === 'string' ? yyyyMmDd.slice(0, 10) : ''
  if (!/^\d{4}-\d{2}-\d{2}$/.test(head)) return ''
  const d = new Date(`${head}T12:00:00`)
  if (!Number.isFinite(d.getTime())) return ''
  d.setDate(d.getDate() - 1)
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function buildNewsRows(dashboard, issueDateStr) {
  if (!dashboard) return []
  const name = selectedRegionName.value
  const dayKey = issueDateStr?.slice(0, 10)
  const snap = dashboard.news
  if (snap && (snap.topic_counts != null || snap.topic_count_sum != null)) {
    const day = snap.news_date ?? snap.newsDate
    if (day) {
      return newsRowsFromDashboardNewsSeries(
        [
          {
            region_id: snap.region_id,
            region_name: snap.region_name ?? name,
            news_date: day,
            topic_count_sum: snap.topic_count_sum,
            topic_counts: snap.topic_counts,
          },
        ],
        name,
      )
    }
  }
  const series = dashboard.news_series
  if (Array.isArray(series) && series.length && dayKey) {
    for (const dk of [dayKey, prevCalendarDayKey(dayKey)]) {
      if (!dk) continue
      const filtered = series.filter(
        row => normalizeNewsDateKey(row.news_date) === dk,
      )
      if (filtered.length) return newsRowsFromDashboardNewsSeries(filtered, name)
    }
  }
  return []
}

const newsView = computed(() =>
  buildNewsRows(rawDashboard.value, selectedIssueDate.value),
)

/** 이 issue_ts·선택 지역: 일일 행에서 키워드(topic_counts) 언급 건수 합 — 스냅샷 우선 */
const newsMentionKpi = computed(() => {
  const d = rawDashboard.value
  const day = selectedIssueDate.value?.slice(0, 10)
  if (!d || !day) return 0
  const snap = d.news
  if (snap && (snap.topic_counts != null || snap.topic_count_sum != null)) {
    return newsDayMentionTotal(snap)
  }
  const series = d.news_series
  if (!Array.isArray(series)) return 0
  for (const dk of [day, prevCalendarDayKey(day)]) {
    if (!dk) continue
    let sum = 0
    for (const row of series) {
      if (normalizeNewsDateKey(row.news_date) === dk) {
        sum += newsDayMentionTotal(row)
      }
    }
    if (sum > 0) return sum
  }
  return 0
})

const mapDf = computed(() => mapSummaryToMapDf(rawMapSummary.value?.regions))

const xaiResult = computed(() =>
  summarizeXai(histDf.value, weatherView.value, newsView.value, INPUT_WINDOW),
)

const latestPower = computed(() => {
  const s = rawDashboard.value?.summary
  if (s?.last_power != null && Number.isFinite(Number(s.last_power))) {
    return (Number(s.last_power) * POWER_TO_MW).toFixed(2)
  }
  if (histDf.value.length) {
    return histDf.value[histDf.value.length - 1].power_usage.toFixed(2)
  }
  return '—'
})

const loadPeak = computed(() =>
  histDf.value.length ? Math.max(...histDf.value.map(r => r.power_usage)).toFixed(2) : '—',
)

const avgTemp = computed(() => {
  const w = weatherView.value
  if (w.length) {
    const t = w.reduce((s, r) => s + r.temperature, 0) / w.length
    return t.toFixed(1)
  }
  const s = rawDashboard.value?.summary
  if (s?.temperature != null && Number.isFinite(Number(s.temperature))) {
    return Number(s.temperature).toFixed(1)
  }
  return '—'
})

const tabs = [
  { key: 'demand',  label: '전력 사용량 예측', icon: demandIcon },
  { key: 'map',     label: '지역별 현황', icon: mapIcon },
  { key: 'weather', label: '기상 분석', icon: weatherIcon },
]

async function refreshDashboard() {
  const id = selectedRegionId.value
  const d = issueAsDate()
  if (id == null || !d) return
  const iso = toLocalIso(d)
  const [dash, mapSum] = await Promise.all([
    fetchDashboard(id, iso, INPUT_WINDOW, 5, FORECAST_HOURS),
    fetchMapSummary(iso, INPUT_WINDOW),
  ])
  rawDashboard.value = dash
  rawMapSummary.value = mapSum
}

watch(selectedRegionId, async id => {
  if (id == null) return
  try {
    const tr = await fetchTimeRange(id)
    timeRange.value = tr
    const max = new Date(tr.max_ts)
    selectedIssueDate.value = toDateStr(max)
    selectedIssueHour.value = max.getHours()
    await refreshDashboard()
  } catch (e) {
    console.error(e)
    timeRange.value = null
    rawDashboard.value = null
    rawMapSummary.value = null
  }
})

onMounted(async () => {
  try {
    const regs = await fetchRegions()
    regionList.value = regs
    if (regs.length) selectedRegionId.value = regs[0].region_id
  } catch (e) {
    console.error(e)
  }
})
</script>
