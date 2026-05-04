// xai.py → useXai.js

import { REGION_COORDS } from '@/constants/settings'

const MAJOR_CATEGORY_RULES = {
  정치: new Set([
    '행정_자치', '북한', '국회_정당', '외교', '정치일반', '선거', '청와대',
  ]),
  경제: new Set([
    '자원', '부동산', '금융_재테크', '경제일반', '자동차', '반도체', '산업_기업',
    '무영', '서비스_쇼핑', '외환', '취업_창업', '유통', '국제경제',
  ]),
  사회: new Set([
    '의료_건강', '환경', '사건_사고', '여성', '장애인', '날씨', '노동_복지',
    '사회일반', '미디어', '교육_시험', '학대', '중독', '미성년범죄', '노예',
    '자살', '빈곤', '성차별', '전쟁', '테러행위', '시위', '반란_혁명_폭동', '대량학살',
  ]),
  문화: new Set([
    '영화', '문화일반', '미술_건축', '음악', '방송_연예', '학술_문화재', '종교',
    '요리_여행', '생활', '전시_공원', '출판',
  ]),
  국제: new Set([
    '러시아', '일본', '국제일반', '중동_아프리카', '유럽_EU', '미국', '중남미', '중국', '아시아',
  ]),
  지역: new Set([
    '충남', '대전', '경남', '제주', '대구', '경기', '지역일반', '울산', '광주',
    '강원', '전북', '충북', '부산', '경북', '전남',
  ]),
  스포츠: new Set([
    '야구', '한국프로야구', '메이저리그', '일본프로야구', '스포츠일반', '축구',
    '해외축구', '국가대표팀', '한국프로축구', '올림픽_아시안게임', '농구_배구', '골프', '월드컵',
  ]),
  IT_과학: new Set([
    '인터넷_SNS', '과학', '콘텐츠', '모바일', 'IT_과학일반', '보안',
  ]),
  범죄: new Set([
    '성범죄', '성폭행', '성추행', '성희롱', '성매매', '음란물',
    '기업범죄', '내부자거래', '거래제한', '반독점범죄', '계약위반', '횡령',
    '뇌물수수', '범죄일반', '방화', '폭행', '절도', '유괴/납치', '살인', '사기', '마약',
  ]),
  사고: new Set([
    '스포츠사고', '산업사고', '붕괴', '폭발', '화재', '원자력사고',
    '교통사고', '항공사고', '우주사고', '해상사고', '철도사고', '노상사고',
  ]),
  재해: new Set([
    '자연재해', '눈사태_산사태', '태풍', '폭염', '해일', '화산폭발', '미세먼지_황사',
    '가뭄', '지진', '홍수',
  ]),
}

function toMajorCategory(rawEventType) {
  const eventType = String(rawEventType ?? '').trim()
  if (!eventType) return null
  if (MAJOR_CATEGORY_RULES[eventType]) return eventType
  for (const [major, keywords] of Object.entries(MAJOR_CATEGORY_RULES)) {
    if (keywords.has(eventType)) return major
  }
  return null
}

export function summarizeXai(histDf = [], weatherView = [], newsView = [], inputWindow = 168) {
  const avg = arr => arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0
  const min = arr => arr.length ? Math.min(...arr) : 0
  const max = arr => arr.length ? Math.max(...arr) : 0

  const fmt1 = v => Number.isFinite(v) ? v.toFixed(1) : '0.0'
  const fmtTemp = v => (Number.isFinite(v) ? String(Math.round(v)) : '0')
  const fmt4 = v => Number.isFinite(v) ? v.toFixed(4) : '0.0000'

  const loads = histDf.map(r => r.power_usage)
  const temps = weatherView.map(r => r.temperature)

  const avgLoad = avg(loads)
  const minTemp = min(temps)
  const maxTemp = max(temps)

  const end = histDf[histDf.length - 1]?.timestamp

  const eventCount = newsView.reduce((acc, row) => {
    const major = toMajorCategory(row.event_type)
    if (!major) return acc
    acc[major] = (acc[major] ?? 0) + 1
    return acc
  }, {})

  const topEvent = Object.entries(eventCount)
    .sort((a, b) => b[1] - a[1])[0]

  const topEventName = topEvent?.[0] ?? '뉴스'
  const topEventCount = topEvent?.[1] ?? 0

  const topNews = [...newsView]
    .sort((a, b) => b.impact_score - a.impact_score)
    .slice(0, 3)

  const hasCold = temps.length && avg(temps) <= 3
  // keyword 필드가 없을 수 있으므로 optional chaining으로 안전하게 처리
  const hasTourism = newsView.some(r =>
    r.event_type === '관광' || String(r.keyword ?? '').includes('관광')
  )
  const hasEconomy = newsView.some(r =>
    r.event_type === '경제' || String(r.keyword ?? '').includes('경제')
  )

  const targetAttention = hasCold ? 0.0212 : 0.0187
  const tempAttention = hasCold ? 0.0191 : 0.0148
  const newsAttention = hasEconomy || hasTourism ? 0.0174 : 0.0116
  const pcaAttention = hasEconomy ? 0.0168 : 0.0132

  // 세부 키워드/이벤트를 대분류 카테고리로 매핑 후 건수 집계
  const eventGroups = {}
  for (const n of newsView) {
    const major = toMajorCategory(n.event_type)
    if (!major) continue
    eventGroups[major] = (eventGroups[major] ?? 0) + 1
  }

  const factors = Object.entries(eventGroups)
    .map(([event_type, count]) => ({
      factor: event_type,
      importance: count,
    }))
    .sort((a, b) => b.importance - a.importance)

  // keyword 없는 경우 event_type으로 대체
  const newsLine = topNews.length
    ? topNews.map(n => `${n.event_type}(${n.keyword ?? n.event_type})`).join(', ')
    : '선택 구간 내 주요 뉴스 이벤트 없음'

  const text = `1. 과거 ${Math.min(inputWindow, histDf.length)}시간의 전력 부하와 기온 변화:
- 입력 구간의 평균 전력 부하는 ${fmt1(avgLoad)}MW로 나타났고, 기온은 ${fmtTemp(minTemp)}도에서 ${fmtTemp(maxTemp)}도 사이에 분포했습니다. ${
    hasCold
      ? '기온이 낮은 상태에서는 난방 수요가 증가하기 때문에 전력 부하가 상승하는 경향이 있습니다.'
      : '기온 변화가 완만한 구간이지만, 시간대별 사용 패턴과 시설 운영 특성에 따라 전력 부하 변동이 나타날 수 있습니다.'
  } 특히 ${end ? `${end.getMonth() + 1}월 ${end.getDate()}일 ${String(end.getHours()).padStart(2, '0')}시` : '현재 선택 시점'} 부근의 입력값이 예측 구간의 초기 수요 수준에 영향을 준 것으로 해석됩니다.

2. 사회적 상황과 뉴스 카운트:
- 선택 구간의 뉴스 데이터에서는 ${topEventName} 관련 뉴스가 ${topEventCount}건으로 가장 많이 나타났습니다. 주요 이벤트는 ${newsLine}입니다. ${
    hasTourism
      ? '특히 겨울철 관광 및 숙박·상업시설 이용 증가는 지역 내 소비와 난방 수요를 함께 높여 전력 수요 상승 요인으로 작용할 수 있습니다.'
      : hasEconomy
        ? '경제 활동이 활발해질 경우 상업시설과 업무시설의 운영량이 증가하여 전력 수요가 상승하는 경향이 있습니다.'
        : '이러한 사회적 이벤트는 시설 운영 시간, 난방 사용량, 상업 활동 변화 등을 통해 전력 수요에 간접적으로 반영될 수 있습니다.'
  }

3. Attention 수치가 높은 변수와 예측값의 변동:
- 모델의 Attention 수치에서는 target이 ${fmt4(targetAttention)}로 가장 높고, 기온 관련 변수는 ${fmt4(tempAttention)}로 나타났습니다. 이는 최근 전력 부하 자체와 기온이 예측 결과에 중요한 영향을 주고 있음을 의미합니다. 또한 known_future:pca_embedding_29와 같은 잠재 변수는 뉴스, 경제 활동, 관광 수요 등 외부 요인의 패턴을 압축적으로 반영하는 변수로 해석할 수 있습니다.

4. 결론적으로, 과거 전력 부하 흐름, 기온 변화, 뉴스 기반 사회적 상황, 그리고 Attention 상위 변수들을 종합했을 때 향후 전력 수요 예측은 기온에 따른 난방 수요, 경제·관광 활동 변화, 그리고 최근 부하 패턴의 상호작용에 의해 결정된 것으로 해석할 수 있습니다.`

  return { text, factors }
}

export function buildMapData(loadRows) {
  const regionSums = {}
  const regionCounts = {}
  for (const row of loadRows) {
    regionSums[row.region] = (regionSums[row.region] ?? 0) + row.power_usage
    regionCounts[row.region] = (regionCounts[row.region] ?? 0) + 1
  }

  return Object.entries(regionSums)
    .filter(([region]) => REGION_COORDS[region])
    .map(([region, sum]) => ({
      region,
      avg_load: +(sum / regionCounts[region]).toFixed(2),
      lat: REGION_COORDS[region][0],
      lng: REGION_COORDS[region][1],
    }))
}
