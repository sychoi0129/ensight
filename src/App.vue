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
          <select class="form-select" v-model.number="selectedRegionId">
            <option v-for="region in regions" :key="region.region_id" :value="region.region_id">
              {{ region.region_name }}
            </option>
          </select>
        </div>
        <div class="ctrl-group">
          <label class="form-label">날짜</label>
          <input type="date" class="form-select" v-model="selectedDate" />
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
          <img :src="tab.icon" :alt="tab.label" style="width:18px; height:18px; margin-right:6px; vertical-align:middle;" />
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="pill live">● {{ statusLabel }}</div>
        <div class="sidebar-model">{{ statusDetail }}</div>
      </div>
    </aside>

    <main class="main-content">
      <div class="page-header">
        <div>
          <div class="page-breadcrumb">Ensight ✦ 전국 전력 수요 예측 시스템</div>
          <div class="page-title">{{ currentTabLabel }}</div>
        </div>
        <div class="page-header-right">
          <span class="status-item">{{ selectedRegionName || "-" }}</span>
          <span class="status-item">{{ selectedDate }} {{ selectedTime }}</span>
        </div>
      </div>

      <div class="kpi-row">
        <div class="kpi-card ok">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">직전 전력</div>
              <div class="kpi-value">{{ latestPower }}</div>
              <div class="kpi-unit">kW · 선택 시간 기준</div>
            </div>
            <div class="kpi-icon blue"><img :src="powerIcon" alt="직전 전력" class="kpi-icon-img" /></div>
          </div>
        </div>
        <div class="kpi-card warn">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">피크 부하</div>
              <div class="kpi-value">{{ loadPeak }}</div>
              <div class="kpi-unit">kW · 일 구간 최대값</div>
            </div>
            <div class="kpi-icon blue"><img :src="peakIcon" alt="피크 부하" class="kpi-icon-img" /></div>
          </div>
        </div>
        <div class="kpi-card info">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">평균 기온</div>
              <div class="kpi-value">{{ avgTemp }}°</div>
              <div class="kpi-unit">°C · 선택 구간 평균</div>
            </div>
            <div class="kpi-icon blue"><img :src="tempIcon" alt="평균 기온" class="kpi-icon-img" /></div>
          </div>
        </div>
        <div class="kpi-card alert">
          <div class="kpi-card-inner">
            <div>
              <div class="kpi-tag">뉴스 이벤트</div>
              <div class="kpi-value">{{ newsKeywordCount }}</div>
              <div class="kpi-unit">해당 지역/날짜 키워드 카운트</div>
            </div>
            <div class="kpi-icon blue"><img :src="newsIcon" alt="뉴스 이벤트" class="kpi-icon-img" /></div>
          </div>
        </div>
      </div>

      <div class="content-area">
        <div v-if="apiError" class="panel" style="color:#f5365c;">API 연결 실패: {{ apiError }}</div>
        <div v-else-if="!isLoading && activeTab !== 'map' && compareSeries.length === 0" class="panel">조회된 데이터가 없습니다.</div>
        <MapTab
          v-else-if="activeTab === 'map'"
          :map-df="regionalMapDf"
        />
        <DemandTab
          v-else-if="activeTab === 'demand'"
          :series="compareSeries"
          :news-view="newsViewForDemand"
          :xai-result="xaiResultForDemand"
          :selected-date="selectedDate"
          :selected-time="selectedTime"
          :is-loading="isLoading"
        />
        <EssTab
          v-else
          :series="compareSeries"
          :metrics="compareMetrics"
          :selected-date="selectedDate"
          :selected-time="selectedTime"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'

const DemandTab = defineAsyncComponent(() => import('@/views/DemandTab.vue'))
const EssTab = defineAsyncComponent(() => import('@/views/EssTab.vue'))
const MapTab = defineAsyncComponent(() => import('@/views/MapTab.vue'))
import { summarizeXai } from '@/composables/useXai'
import { REGION_COORDS } from '@/constants/settings'
import demandIcon from '@/assets/images/icons/demand.png'
import mapIcon from '@/assets/images/icons/map.png'
import ESSIcon from '@/assets/images/icons/ESS.png'
import powerIcon from '@/assets/images/icons/power.png'
import peakIcon from '@/assets/images/icons/peak.png'
import tempIcon from '@/assets/images/icons/temperature.png'
import newsIcon from '@/assets/images/icons/news.png'

// VITE_API_BASE_URL: 호스트만 또는 .../api 까지 (중복 /api 방지)
function resolveApiRoot() {
  const raw = import.meta.env.VITE_API_BASE_URL
  const fallbackHost = "http://127.0.0.1:8000"
  if (raw == null || String(raw).trim() === "") return `${fallbackHost}/api`
  let base = String(raw).trim().replace(/\/$/, "")
  if (!base.endsWith("/api")) base = `${base}/api`
  return base
}

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`
  return `${resolveApiRoot()}${p}`
}

const regions = ref([])
const selectedRegionId = ref(null)
const selectedDate = ref("")
const selectedTime = ref("00:00")
const activeTab = ref("demand")

const compareSeries = ref([])
const compareMetrics = ref({})
const newsRows = ref([])
const weatherRows = ref([])
const regionalMapDf = ref([])
const apiError = ref("")
const isLoading = ref(false)
const apiConnected = ref(false)

const statusLabel = computed(() => {
  if (isLoading.value) return "Loading"
  if (apiError.value) return "API ERROR"
  if (apiConnected.value) return "API Connected"
  return "Idle"
})

const statusDetail = computed(() => {
  if (apiError.value) return apiError.value
  return "LIVE"
})

const selectedRegionName = computed(
  () => regions.value.find((r) => r.region_id === selectedRegionId.value)?.region_name ?? ""
)

const tabs = [
  { key: "demand", label: "전력 수요 예측", icon: demandIcon },
  { key: "map", label: "지역별 현황", icon: mapIcon },
  { key: "ess", label: "ESS 기능", icon: ESSIcon },
]
const currentTabLabel = computed(() => tabs.find((tab) => tab.key === activeTab.value)?.label ?? "대시보드")

const availableTimes = computed(() =>
  [...new Set(
    compareSeries.value
      .filter((row) => row.ts.slice(0, 10) === selectedDate.value)
      .map((row) => row.ts.slice(11, 16))
  )].sort()
)

const selectedSeriesPoint = computed(() => {
  if (!compareSeries.value.length) return null
  const found = compareSeries.value.find(
    (row) => row.ts.slice(0, 10) === selectedDate.value && row.ts.slice(11, 16) === selectedTime.value
  )
  return found ?? compareSeries.value[compareSeries.value.length - 1]
})

const latestPower = computed(() => {
  const value = selectedSeriesPoint.value?.actual
  return Number.isFinite(value) ? `${value.toFixed(1)}` : "—"
})

const loadPeak = computed(() => {
  const peak = compareMetrics.value?.peak_before_ess
  if (Number.isFinite(peak)) return `${peak.toFixed(1)}`
  if (!compareSeries.value.length) return "—"
  return `${Math.max(...compareSeries.value.map((row) => row.actual ?? 0)).toFixed(1)}`
})

const avgTemp = computed(() => {
  const getTemp = (row) =>
    Number(
      row.temperature ??
      row.temp ??
      row.air_temp ??
      row.ta ??
      row.mean_temp ??
      NaN
    )
  const vals = weatherRows.value.map(getTemp).filter(Number.isFinite)
  if (!vals.length) return "—"
  const value = vals.reduce((acc, v) => acc + v, 0) / vals.length
  return Number.isFinite(value) ? value.toFixed(2) : "—"
})

function getNewsRowDate(row) {
  return String(row.date ?? row.target_date ?? row.news_date ?? '').slice(0, 10)
}

function selectNewsRowsByDate(rows, selectedDateStr) {
  const rowsOfDay = rows.filter((row) => getNewsRowDate(row) === selectedDateStr)
  if (rowsOfDay.length) return rowsOfDay

  const candidates = rows
    .map((row) => ({ row, d: getNewsRowDate(row) }))
    .filter((item) => item.d && item.d <= selectedDateStr)
    .sort((a, b) => (a.d < b.d ? 1 : -1))

  if (!candidates.length) return []
  const fallbackDate = candidates[0].d
  return rows.filter((row) => getNewsRowDate(row) === fallbackDate)
}

const newsKeywordCount = computed(() => {
  if (!newsRows.value.length) return "0"
  const rowsOfDay = selectNewsRowsByDate(newsRows.value, selectedDate.value)
  if (!rowsOfDay.length) return "0"
  const keys = Object.keys(rowsOfDay[0] ?? {})
  const keywordLike = keys.filter((key) => key.toLowerCase().includes("keyword") && key.toLowerCase().includes("count"))
  const countLike = keys.filter((key) => key.toLowerCase().includes("count"))
  const targetKeys = keywordLike.length ? keywordLike : countLike
  if (!targetKeys.length) return String(rowsOfDay.length)

  const total = rowsOfDay.reduce((sum, row) => {
    const rowSum = targetKeys.reduce((acc, key) => acc + (Number(row[key]) || 0), 0)
    return sum + rowSum
  }, 0)
  return String(total)
})

const newsViewForDemand = computed(() => {
  if (!newsRows.value.length) return []
  const targetRows = selectNewsRowsByDate(newsRows.value, selectedDate.value)
  const expanded = []

  targetRows.forEach((row, idx) => {
    const rowDate = getNewsRowDate(row) || selectedDate.value
    const timestamp = new Date(`${rowDate}T12:00:00`)
    const keys = Object.keys(row ?? {})
    const countColumns = keys.filter((key) =>
      key.toLowerCase().endsWith('_count') &&
      !['region_id', 'model_id', 'run_id'].includes(key.toLowerCase())
    )

    if (countColumns.length) {
      countColumns.forEach((col) => {
        const countValue = Number(row[col] ?? 0)
        if (!Number.isFinite(countValue) || countValue <= 0) return
        const keyword = col.replace(/_count$/i, '')
        const impact = Math.max(0.3, Math.min(0.95, countValue / 10))
        expanded.push({
          timestamp,
          headline: `${keyword} 관련 키워드`,
          event_type: keyword,
          summary: `해당 키워드 카운트 ${countValue}건`,
          impact_score: Number(impact.toFixed(2)),
          keyword,
        })
      })
      return
    }

    const countValue = Number(
      row.keyword_count ??
      row.count ??
      row.news_count ??
      row.total_count ??
      row.keyword_cnt ??
      1
    )
    const impact = Math.max(0.3, Math.min(0.95, countValue / 10))
    const headline =
      row.keyword ??
      row.keyword_name ??
      row.event_type ??
      row.category ??
      `뉴스 키워드 ${idx + 1}`
    const eventType = String(row.event_type ?? headline ?? '뉴스')
    expanded.push({
      timestamp,
      headline: String(headline),
      event_type: eventType,
      summary: `해당 키워드 카운트 ${countValue}건`,
      impact_score: Number(impact.toFixed(2)),
      keyword: String(headline),
    })
  })

  return expanded.slice(0, 12)
})

const histDfForXai = computed(() =>
  compareSeries.value.map((row) => ({
    timestamp: new Date(row.ts),
    power_usage: Number(row.actual ?? 0),
  }))
)

const xaiResultForDemand = computed(() =>
  summarizeXai(histDfForXai.value, [], newsViewForDemand.value, 168)
)

function toDateString(value) {
  const d = new Date(value)
  const pad = (n) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function addDay(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + 1)
  return toDateString(d)
}

function subtractDays(dateStr, days) {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() - days)
  return toDateString(d)
}

function resolveRegionCoords(regionName) {
  if (REGION_COORDS[regionName]) return REGION_COORDS[regionName]

  const aliasMap = {
    "제주": "제주특별지사",
    "제주도": "제주특별지사",
    "제주특별자치도": "제주특별지사",
    "경기북부": "경기 북부",
  }
  const alias = aliasMap[regionName]
  if (alias && REGION_COORDS[alias]) return REGION_COORDS[alias]

  if (regionName.includes("제주")) return [33.4996, 126.5312]
  return null
}

async function fetchRegions() {
  try {
    const res = await fetch(apiUrl("/regions"))
    if (!res.ok) throw new Error(`regions API failed (${res.status})`)
    const data = await res.json()
    regions.value = data
    if (data.length && selectedRegionId.value == null) selectedRegionId.value = data[0].region_id
  } catch (err) {
    console.error("Failed to fetch regions", err)
    apiError.value = err instanceof Error ? err.message : String(err)
  }
}

async function fetchLatestDate(regionId) {
  const res = await fetch(`${apiUrl("/latest-date")}?region_id=${regionId}`)
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(`latest-date API failed (${res.status}): ${txt}`)
  }
  const data = await res.json()
  return data.latest_date ?? null
}

async function setLatestDateForRegion() {
  if (!selectedRegionId.value) return
  try {
    const latestDate = await fetchLatestDate(selectedRegionId.value)
    if (latestDate) {
      selectedDate.value = latestDate
    } else if (!selectedDate.value) {
      selectedDate.value = toDateString(new Date())
    }
  } catch (err) {
    console.error("Failed to fetch latest date", err)
    if (!selectedDate.value) selectedDate.value = toDateString(new Date())
  }
}

async function fetchNewsCount() {
  if (!selectedRegionId.value || !selectedDate.value) return
  const startDate = subtractDays(selectedDate.value, 6)
  const endDate = addDay(selectedDate.value)
  const url =
    `${apiUrl("/news-count")}?region_id=${selectedRegionId.value}` +
    `&start=${startDate}&end=${endDate}`
  try {
    const res = await fetch(url)
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`news-count API failed (${res.status}): ${txt}`)
    }
    const data = await res.json()
    newsRows.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error("Failed to fetch news-count", err)
    newsRows.value = []
  }
}

async function fetchWeather() {
  if (!selectedRegionId.value || !selectedDate.value) return
  const startDate = subtractDays(selectedDate.value, 6)
  const endDate = addDay(selectedDate.value)
  const url =
    `${apiUrl("/weather")}?region_id=${selectedRegionId.value}` +
    `&start=${startDate}&end=${endDate}`
  try {
    const res = await fetch(url)
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`weather API failed (${res.status}): ${txt}`)
    }
    const data = await res.json()
    weatherRows.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error("Failed to fetch weather", err)
    weatherRows.value = []
  }
}

async function fetchCompare() {
  if (!selectedRegionId.value || !selectedDate.value) return
  isLoading.value = true
  apiError.value = ""
  const startDate = subtractDays(selectedDate.value, 6)
  const endDate = addDay(selectedDate.value)
  const url =
    `${apiUrl("/compare")}?region_id=${selectedRegionId.value}` +
    `&start=${startDate}&end=${endDate}`

  try {
    const res = await fetch(url)
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`compare API failed (${res.status}): ${txt}`)
    }
    const data = await res.json()
    compareSeries.value = Array.isArray(data.series) ? data.series : []
    compareMetrics.value = data.metrics ?? {}
    apiConnected.value = true

    if (availableTimes.value.length && !availableTimes.value.includes(selectedTime.value)) {
      selectedTime.value = availableTimes.value[0]
    }
  } catch (err) {
    console.error("Failed to fetch compare", err)
    apiConnected.value = false
    compareSeries.value = []
    compareMetrics.value = {}
    apiError.value = err instanceof Error ? err.message : String(err)
  } finally {
    isLoading.value = false
  }
}

async function fetchRegionalStatus() {
  if (!regions.value.length || !selectedDate.value) return
  const endDate = addDay(selectedDate.value)
  const url =
    `${apiUrl("/metrics-bulk")}?start=${selectedDate.value}&end=${endDate}`

  try {
    const res = await fetch(url)
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`metrics-bulk API failed (${res.status}): ${txt}`)
    }
    const rows = await res.json()
    const metricsByRegion = new Map(
      (Array.isArray(rows) ? rows : []).map((m) => [m.region_id, m]),
    )

    regionalMapDf.value = regions.value
      .map((region) => {
        const metric = metricsByRegion.get(region.region_id)
        if (!metric) return null
        const coords = resolveRegionCoords(region.region_name)
        if (!coords) return null
        return {
          region: region.region_name,
          lat: coords[0],
          lng: coords[1],
          avg_load: Number(metric.peak_before_ess ?? 0),
        }
      })
      .filter((row) => row && Number.isFinite(row.avg_load))
  } catch (err) {
    console.error("Failed to fetch regional status", err)
    regionalMapDf.value = []
  }
}

onMounted(async () => {
  await fetchRegions()
  await setLatestDateForRegion()
  if (selectedDate.value && selectedRegionId.value) {
    await Promise.all([fetchCompare(), fetchNewsCount(), fetchWeather(), fetchRegionalStatus()])
  }
})

watch(selectedRegionId, async () => {
  const prevDate = selectedDate.value
  await setLatestDateForRegion()
  if (selectedDate.value === prevDate && selectedDate.value) {
    await Promise.all([fetchCompare(), fetchNewsCount(), fetchWeather(), fetchRegionalStatus()])
  }
})

watch(selectedDate, async (newDate, oldDate) => {
  if (!selectedRegionId.value || !newDate || newDate === oldDate) return
  await Promise.all([fetchCompare(), fetchNewsCount(), fetchWeather(), fetchRegionalStatus()])
})
</script>
