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

  const newsData = [
    { timestamp: new Date('2014-12-03T09:00'), region: '서울', event_type: '한파', headline: '서울 한파 특보 발효', summary: '기온 급강하로 난방 수요 증가 가능성이 제기됨.', impact_score: 0.82 },
    { timestamp: new Date('2014-12-05T13:00'), region: '부산', event_type: '강풍', headline: '부산 강풍주의보', summary: '항만 물류 운영 차질 우려가 보도됨.', impact_score: 0.54 },
    { timestamp: new Date('2014-12-06T07:00'), region: '대구경북', event_type: '대설', headline: '대구경북 대설 예보', summary: '출근 시간대 전력 수요 변화 가능성이 언급됨.', impact_score: 0.67 },
    { timestamp: new Date('2014-12-08T18:00'), region: '광주전남', event_type: '폭우', headline: '광주전남 집중호우 영향', summary: '산업시설 운영 패턴 변동 가능성이 보도됨.', impact_score: 0.49 },
    { timestamp: new Date('2014-12-10T08:00'), region: '서울', event_type: '정책', headline: '동절기 에너지 절감 대책 발표', summary: '피크 시간대 사용량 분산 정책이 발표됨.', impact_score: 0.58 },
    { timestamp: new Date('2014-12-12T10:00'), region: '경기', event_type: '산업', headline: '경기권 산업단지 운영 조정', summary: '일부 제조시설 가동 조정에 따라 전력 수요 변동 가능성이 제기됨.', impact_score: 0.61 },
    { timestamp: new Date('2014-12-14T14:00'), region: '인천', event_type: '정비', headline: '인천 설비 정기점검 계획', summary: '설비 점검 일정으로 단기 부하 감소 가능성이 보도됨.', impact_score: 0.45 },
    { timestamp: new Date('2014-12-16T09:00'), region: '강원', event_type: '한파', headline: '강원 한파경보 강화', summary: '난방 수요 집중으로 지역 부하 상승 가능성이 큼.', impact_score: 0.76 },
    { timestamp: new Date('2014-12-18T11:00'), region: '충북', event_type: '폭설', headline: '충북 폭설 대비 비상체계', summary: '교통 차질과 설비 부하 변동 가능성이 함께 언급됨.', impact_score: 0.63 },
    { timestamp: new Date('2014-12-20T15:00'), region: '대전충남', event_type: '정책', headline: '대전충남 동절기 수요관리 강화', summary: '산업체 대상 전력 절감 권고가 발표됨.', impact_score: 0.52 },
    { timestamp: new Date('2014-12-22T10:00'), region: '경남', event_type: '산업', headline: '경남 제조업 생산 조정', summary: '생산 스케줄 조정으로 시간대별 수요 재분배 가능성이 제기됨.', impact_score: 0.59 },
    { timestamp: new Date('2014-12-24T08:00'), region: '제주특별지사', event_type: '기상', headline: '제주 강풍 및 해상 기상 악화', summary: '기상 악화로 일부 설비 운영 패턴 변동 가능성이 있음.', impact_score: 0.47 },
    { timestamp: new Date('2014-12-26T13:00'), region: '전북', event_type: '정비', headline: '전북 지역 설비 점검 확대', summary: '정기 정비 영향으로 일부 시설의 단기 부하 감소 가능성이 있음.', impact_score: 0.43 },
    { timestamp: new Date('2014-12-27T17:00'), region: '남서울', event_type: '산업', headline: '남서울권 상업시설 수요 집중', summary: '연말 상업활동 증가로 저녁 시간대 수요 피크 가능성이 제기됨.', impact_score: 0.66 },
  ]

  _cache = { loadDf: loadRows, weatherDf: weatherRows, newsDf: newsData }
  return _cache
}
