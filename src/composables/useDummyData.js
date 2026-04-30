// loader.py → useDummyData.js
// 시드 고정 더미 데이터 생성 (Python numpy 로직을 JS로 재현)

import { REGION_ORDER, REGION_COORDS, REGION_FACILITIES } from '@/constants/settings'

const REGION_LOAD_BIAS = {
  '경기': 128, '경기 북부': 118, '서울': 135, '남서울': 126, '인천': 122,
  '광주전남': 104, '전북': 98, '강원': 92, '충북': 96, '대전충남': 108,
  '부산': 112, '대구경북': 109, '경남': 111, '제주특별지사': 84,
}

const REGION_TEMP_BIAS = {
  '경기': -0.5, '경기 북부': -1.2, '서울': -0.8, '남서울': -0.3, '인천': -0.6,
  '광주전남': 1.1, '전북': 0.8, '강원': -1.8, '충북': 0.1, '대전충남': 0.3,
  '부산': 1.5, '대구경북': 1.0, '경남': 1.2, '제주특별지사': 2.2,
}

const FACILITY_BIAS = {
  '건축기술': 18, '교육서비스업': 10, '방송업': 30, '금융업': 22,
  '금속 광업': 26, '국제 및 외국기관': 24, '기계 및 장비 제조업': 28,
  '보건업': 14, '부동산업': 12, '수도사업': 16,
}

// 간단한 시드 기반 난수 (Python rng seed=42 근사)
function seededRng(seed) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff
    return (s >>> 0) / 0xffffffff
  }
}

function normalApprox(rng, mean = 0, std = 1) {
  // Box-Muller
  const u1 = Math.max(rng(), 1e-10)
  const u2 = rng()
  return mean + std * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
}

function pick(arr, idx) {
  return arr[idx % arr.length]
}

function scoreByRange(min, max, seed) {
  const v = ((seed * 37 + 17) % 100) / 100
  return +(min + v * (max - min)).toFixed(2)
}

function generateNewsData() {
  const rows = []

  const regions = [
    '경기', '경기 북부', '서울', '남서울', '인천',
    '광주전남', '전북', '강원', '충북', '대전충남',
    '부산', '대구경북', '경남', '제주특별지사',
  ]

  const eventTemplates = [
    {
      event_type: '경제',
      keyword: '경제 활동',
      direction: 'increase',
      attention_hint: 'known_future:pca_embedding_29',
      score: [0.58, 0.82],
      headlines: [
        '{region} 지역 소비 심리 회복세',
        '{region} 연말 경제 활동 증가 전망',
        '{region} 상업시설 매출 증가세',
        '{region} 업무·상업지구 유동 인구 증가',
      ],
      summaries: [
        '경제 활동과 소비 증가가 상업시설 운영 확대와 전력 수요 상승으로 이어질 가능성이 있음.',
        '연말 소비와 업무 활동 증가로 낮 시간대 전력 부하가 상승할 수 있음.',
        '지역 내 경제 활동이 활발해지면서 상업 및 업무시설의 전력 사용량 증가 가능성이 제기됨.',
      ],
    },
    {
      event_type: '관광',
      keyword: '관광 수요',
      direction: 'increase',
      attention_hint: 'known_future:pca_embedding_17',
      score: [0.52, 0.78],
      headlines: [
        '{region} 겨울 관광객 증가',
        '{region} 스키장·리조트 방문객 확대',
        '{region} 연말 관광 수요 집중',
        '{region} 숙박·레저시설 이용 증가',
      ],
      summaries: [
        '겨울철 관광객 유입으로 숙박, 난방, 상업시설 전력 수요가 증가할 가능성이 있음.',
        '스키장과 리조트 방문객 증가가 지역 내 소비와 전력 사용량 상승으로 이어질 수 있음.',
        '관광 수요 확대에 따라 야간 및 주말 시간대 전력 부하 변동 가능성이 있음.',
      ],
    },
    {
      event_type: '한파',
      keyword: '기온 하락',
      direction: 'increase',
      attention_hint: 'known_future:temperature',
      score: [0.68, 0.91],
      headlines: [
        '{region} 한파 특보 발효',
        '{region} 아침 최저기온 급락',
        '{region} 강추위 지속 전망',
        '{region} 난방 수요 증가 우려',
      ],
      summaries: [
        '기온 하락으로 난방 사용량이 늘면서 전력 수요가 상승할 가능성이 큼.',
        '낮은 기온이 유지되면서 주거 및 상업시설의 난방 부하 증가가 예상됨.',
        '한파 영향으로 오전 시간대와 저녁 시간대 전력 피크가 확대될 수 있음.',
      ],
    },
    {
      event_type: '대설',
      keyword: '적설',
      direction: 'increase',
      attention_hint: 'known_future:snow_weather',
      score: [0.56, 0.83],
      headlines: [
        '{region} 대설 예보',
        '{region} 출근길 눈 예보',
        '{region} 폭설 대비 비상근무 체계 가동',
        '{region} 적설 영향으로 교통 차질 우려',
      ],
      summaries: [
        '대설과 교통 지연 가능성으로 시설 운영 패턴과 난방 수요가 함께 변동할 수 있음.',
        '눈 예보로 출근 시간대 전력 사용 패턴이 평소와 다르게 나타날 가능성이 있음.',
        '제설 작업과 난방 수요가 동시에 증가하면서 지역 전력 부하 상승 가능성이 있음.',
      ],
    },
    {
      event_type: '산업',
      keyword: '산업 가동률',
      direction: 'increase',
      attention_hint: 'known_future:pca_embedding_08',
      score: [0.50, 0.77],
      headlines: [
        '{region} 산업단지 생산 일정 조정',
        '{region} 제조시설 가동률 변동',
        '{region} 연말 생산 물량 증가',
        '{region} 주요 사업장 전력 사용 증가 전망',
      ],
      summaries: [
        '산업시설의 생산 일정 조정으로 시간대별 전력 수요가 달라질 가능성이 있음.',
        '연말 생산 물량 증가가 제조업 전력 사용량 상승으로 이어질 수 있음.',
        '일부 제조시설의 가동 확대가 지역 부하 증가 요인으로 작용할 수 있음.',
      ],
    },
    {
      event_type: '정책',
      keyword: '수요관리',
      direction: 'decrease',
      attention_hint: 'known_future:demand_response',
      score: [0.42, 0.64],
      headlines: [
        '{region} 동절기 에너지 절감 대책 발표',
        '{region} 피크 시간대 수요관리 강화',
        '{region} 공공기관 난방온도 관리 강화',
        '{region} 전력 사용량 분산 캠페인 시행',
      ],
      summaries: [
        '피크 시간대 전력 사용량을 줄이기 위한 수요관리 정책이 추진됨.',
        '공공기관과 산업체 대상 절감 권고로 일부 시간대 부하 완화 가능성이 있음.',
        '전력 사용량 분산 정책이 단기 피크를 낮추는 요인으로 작용할 수 있음.',
      ],
    },
    {
      event_type: '정비',
      keyword: '설비 점검',
      direction: 'decrease',
      attention_hint: 'known_future:maintenance',
      score: [0.35, 0.58],
      headlines: [
        '{region} 주요 설비 정기점검 예정',
        '{region} 전력 관련 시설 점검 실시',
        '{region} 산업시설 일부 라인 점검',
        '{region} 설비 정비로 단기 부하 감소 가능',
      ],
      summaries: [
        '정기 점검 일정으로 일부 시설의 전력 사용량이 일시적으로 감소할 가능성이 있음.',
        '설비 점검과 운영 조정으로 특정 시간대 부하가 낮아질 수 있음.',
        '유지보수 작업에 따라 시설 가동 패턴이 일시적으로 변화할 것으로 보임.',
      ],
    },
  ]

  const times = ['07:00', '10:00', '13:00', '17:00', '20:00']

  let idx = 0

  for (let day = 2; day <= 28; day++) {
    for (let t = 0; t < times.length; t++) {
      const region = pick(regions, day + t * 3 + idx)
      const template = pick(eventTemplates, day + t + idx)

      rows.push({
        timestamp: new Date(`2014-12-${String(day).padStart(2, '0')}T${times[t]}`),
        region,
        event_type: template.event_type,
        keyword: template.keyword,
        direction: template.direction,
        attention_hint: template.attention_hint,
        headline: pick(template.headlines, idx).replace('{region}', region),
        summary: pick(template.summaries, day + idx),
        impact_score: scoreByRange(template.score[0], template.score[1], day + t + idx),
      })

      idx++
    }
  }

  // 특정 샘플 설명이 잘 나오도록 강원 / 관광 / 한파 / 경제 뉴스는 의도적으로 조금 더 보강
  rows.push(
    {
      timestamp: new Date('2014-12-17T08:00'),
      region: '강원',
      event_type: '한파',
      keyword: '기온 하락',
      direction: 'increase',
      attention_hint: 'known_future:temperature',
      headline: '강원 아침 기온 급락으로 난방 수요 증가',
      summary: '강원 지역의 낮은 기온이 지속되면서 난방 부하와 오전 시간대 전력 수요가 증가할 가능성이 있음.',
      impact_score: 0.88,
    },
    {
      timestamp: new Date('2014-12-17T11:00'),
      region: '강원',
      event_type: '관광',
      keyword: '겨울 관광',
      direction: 'increase',
      attention_hint: 'known_future:pca_embedding_17',
      headline: '강원 스키장 방문객 증가세',
      summary: '겨울철 스키장과 리조트 방문객 증가가 숙박, 상업시설, 난방 수요 확대로 이어질 수 있음.',
      impact_score: 0.79,
    },
    {
      timestamp: new Date('2014-12-17T14:00'),
      region: '강원',
      event_type: '경제',
      keyword: '지역 소비',
      direction: 'increase',
      attention_hint: 'known_future:pca_embedding_29',
      headline: '강원 관광지 중심 소비 활동 확대',
      summary: '관광객 유입에 따른 지역 소비 증가가 상업시설 전력 사용량 상승 요인으로 작용할 가능성이 있음.',
      impact_score: 0.74,
    }
  )

  return rows.sort((a, b) => a.timestamp - b.timestamp)
}


let _cache = null

export function useDummyData() {
  if (_cache) return _cache

  const rng = seededRng(42)
  const norm = (mean, std) => normalApprox(rng, mean, std)

  // 28일 = 672시간
  const N = 24 * 28
  const startTs = new Date('2014-12-01T00:00:00')
  const timestamps = Array.from({ length: N }, (_, i) => {
    const d = new Date(startTs)
    d.setHours(d.getHours() + i)
    return d
  })

  const loadRows = []
  const weatherRows = []

  for (const region of REGION_ORDER) {
    if (!REGION_COORDS[region]) continue

    const daily = timestamps.map((_, i) => 20 * Math.sin(i * 2 * Math.PI / 24 - 1.3))
    const weekly = timestamps.map((_, i) => 10 * Math.sin(i * 2 * Math.PI / (24 * 7)))

    const temp = timestamps.map((_, i) =>
      +(3 + (REGION_TEMP_BIAS[region] ?? 0)
        + 6 * Math.sin(i * 2 * Math.PI / 24 - 1.9)
        + norm(0, 1.2)).toFixed(2)
    )
    const rain = temp.map(() => +Math.max(0, norm(0.4, 1.0)).toFixed(2))
    const wind = temp.map(() => +Math.max(0, norm(2.5, 0.7)).toFixed(2))
    const hum  = temp.map(() => +Math.min(100, Math.max(20, 55 + norm(0, 10))).toFixed(2))

    timestamps.forEach((ts, i) => {
      weatherRows.push({
        timestamp: ts,
        region,
        temperature: temp[i],
        rainfall: rain[i],
        wind_speed: wind[i],
        humidity: hum[i],
      })
    })

    const facilities = REGION_FACILITIES[region] ?? ['교육서비스업', '보건업']
    for (const facility of facilities) {
      timestamps.forEach((ts, i) => {
        const load = +(
          (REGION_LOAD_BIAS[region] ?? 100)
          + (FACILITY_BIAS[facility] ?? 0)
          + daily[i]
          + weekly[i]
          + 1.7 * Math.max(0, 18 - temp[i])
          + 1.1 * rain[i]
          + norm(0, 5)
        ).toFixed(2)
        loadRows.push({ timestamp: ts, region, facility, power_usage: load })
      })
    }
  }

  const newsData = generateNewsData()

  _cache = { loadDf: loadRows, weatherDf: weatherRows, newsDf: newsData }
  return _cache
}