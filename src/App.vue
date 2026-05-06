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
              <div class="kpi-tag">평균 SOC</div>
              <div class="kpi-value">{{ avgSoc }}</div>
              <div class="kpi-unit">· metrics 기준</div>
            </div>
            <div class="kpi-icon blue"><img :src="tempIcon" alt="평균 SOC" class="kpi-icon-img" /></div>
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
          :metrics="compareMetrics"
          :selected-time="selectedTime"
          :is-loading="isLoading"
        />
        <EssTab
          v-else
          :series="compareSeries"
          :metrics="compareMetrics"
          :selected-time="selectedTime"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import DemandTab from '@/views/DemandTab.vue'
import EssTab from '@/views/EssTab.vue'
import MapTab from '@/views/MapTab.vue'
import { REGION_COORDS } from '@/constants/settings'
import powerIcon from '@/assets/images/icons/power.png'
import peakIcon from '@/assets/images/icons/peak.png'
import tempIcon from '@/assets/images/icons/temperature.png'
import newsIcon from '@/assets/images/icons/news.png'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

const regions = ref([])
const selectedRegionId = ref(null)
const selectedDate = ref("")
const selectedTime = ref("00:00")
const activeTab = ref("demand")

const compareSeries = ref([])
const compareMetrics = ref({})
const newsRows = ref([])
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
  { key: "demand", label: "전력 수요 예측" },
  { key: "map", label: "지역별 현황" },
  { key: "ess", label: "ESS 기능" },
]
const currentTabLabel = computed(() => tabs.find((tab) => tab.key === activeTab.value)?.label ?? "대시보드")

const availableTimes = computed(() =>
  [...new Set(compareSeries.value.map((row) => row.ts.slice(11, 16)))].sort()
)

const selectedSeriesPoint = computed(() => {
  if (!compareSeries.value.length) return null
  const found = compareSeries.value.find((row) => row.ts.slice(11, 16) === selectedTime.value)
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

const avgSoc = computed(() => {
  const value = compareMetrics.value?.avg_soc
  return Number.isFinite(value) ? value.toFixed(2) : "—"
})

const newsKeywordCount = computed(() => {
  if (!newsRows.value.length) return "0"
  const keys = Object.keys(newsRows.value[0] ?? {})
  const keywordLike = keys.filter((key) => key.toLowerCase().includes("keyword") && key.toLowerCase().includes("count"))
  const countLike = keys.filter((key) => key.toLowerCase().includes("count"))
  const targetKeys = keywordLike.length ? keywordLike : countLike
  if (!targetKeys.length) return String(newsRows.value.length)

  const total = newsRows.value.reduce((sum, row) => {
    const rowSum = targetKeys.reduce((acc, key) => acc + (Number(row[key]) || 0), 0)
    return sum + rowSum
  }, 0)
  return String(total)
})

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
    const res = await fetch(`${API_BASE_URL}/api/regions`)
    if (!res.ok) throw new Error(`regions API failed (${res.status})`)
    const data = await res.json()
    regions.value = data
    if (data.length && selectedRegionId.value == null) selectedRegionId.value = data[0].region_id
  } catch (err) {
    console.error("Failed to fetch regions", err)
    apiError.value = err instanceof Error ? err.message : String(err)
  }
}

async function fetchNewsCount() {
  if (!selectedRegionId.value || !selectedDate.value) return
  const endDate = addDay(selectedDate.value)
  const url =
    `${API_BASE_URL}/api/news-count?region_id=${selectedRegionId.value}` +
    `&start=${selectedDate.value}&end=${endDate}`
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

async function fetchCompare() {
  if (!selectedRegionId.value || !selectedDate.value) return
  isLoading.value = true
  apiError.value = ""
  const endDate = addDay(selectedDate.value)
  const url =
    `${API_BASE_URL}/api/compare?region_id=${selectedRegionId.value}` +
    `&start=${selectedDate.value}&end=${endDate}`

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
  const requests = regions.value.map(async (region) => {
    const url =
      `${API_BASE_URL}/api/metrics?region_id=${region.region_id}` +
      `&start=${selectedDate.value}&end=${endDate}`
    const res = await fetch(url)
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`metrics API failed (${res.status}): ${txt}`)
    }
    const metric = await res.json()
    const coords = resolveRegionCoords(region.region_name)
    if (!coords) return null
    return {
      region: region.region_name,
      lat: coords[0],
      lng: coords[1],
      avg_load: Number(metric.peak_before_ess ?? 0),
    }
  })

  try {
    const data = await Promise.all(requests)
    regionalMapDf.value = data.filter((row) => row && Number.isFinite(row.avg_load))
  } catch (err) {
    console.error("Failed to fetch regional status", err)
    regionalMapDf.value = []
  }
}

onMounted(async () => {
  selectedDate.value = "2013-01-02"
  await fetchRegions()
  await Promise.all([fetchCompare(), fetchNewsCount(), fetchRegionalStatus()])
})

watch([selectedRegionId, selectedDate], async () => {
  await Promise.all([fetchCompare(), fetchNewsCount(), fetchRegionalStatus()])
})
</script>
