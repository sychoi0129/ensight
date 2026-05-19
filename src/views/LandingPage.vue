<template>
  <div class="landing">

    <!-- NAV -->
    <nav class="lp-nav" :class="{ scrolled: isScrolled }">
      <a href="#" class="lp-nav-logo">
        <div class="lp-logo-mark">E</div>
        <div>
          <div class="lp-logo-text">Ensight ✦</div>
          <div class="lp-logo-sub">전국 지역별 전력 수요 예측 시스템</div>
        </div>
      </a>
      <div class="lp-nav-cta">
        <div class="lp-nav-links">
          <a href="#features">기능 소개</a>
          <a href="#how">작동 원리</a>
        </div>
        <button class="lp-btn-ghost" @click="goToDashboard">수요 예측 시작하기 →</button>
      </div>
    </nav>

    <!-- HERO -->
    <section class="lp-hero">
      <div class="lp-hero-bg"></div>
      <div class="lp-hero-overlay"></div>

      <!-- 전력망 SVG 배경 -->
      <svg class="lp-hero-grid" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="nodeGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#7b8ef0" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#5e72e4" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <g stroke="#5e72e4" stroke-width="0.8" opacity="0.5">
          <line x1="120" y1="80"  x2="380" y2="200"/><line x1="380" y1="200" x2="650" y2="120"/>
          <line x1="650" y1="120" x2="900" y2="280"/><line x1="900" y1="280" x2="1200" y2="180"/>
          <line x1="1200" y1="180" x2="1380" y2="300"/>
          <line x1="380" y1="200" x2="300" y2="420"/><line x1="300" y1="420" x2="560" y2="500"/>
          <line x1="560" y1="500" x2="900" y2="280"/><line x1="900" y1="280" x2="1050" y2="480"/>
          <line x1="1050" y1="480" x2="1200" y2="180"/>
          <line x1="300" y1="420" x2="200" y2="660"/><line x1="560" y1="500" x2="480" y2="720"/>
          <line x1="480" y1="720" x2="760" y2="680"/><line x1="760" y1="680" x2="1050" y2="480"/>
          <line x1="1050" y1="480" x2="1280" y2="620"/>
        </g>
        <g fill="#7b8ef0">
          <circle cx="120"  cy="80"  r="5"/><circle cx="380"  cy="200" r="7"/>
          <circle cx="650"  cy="120" r="5"/><circle cx="900"  cy="280" r="9"/>
          <circle cx="1200" cy="180" r="5"/><circle cx="1380" cy="300" r="4"/>
          <circle cx="300"  cy="420" r="6"/><circle cx="560"  cy="500" r="8"/>
          <circle cx="1050" cy="480" r="7"/><circle cx="200"  cy="660" r="4"/>
          <circle cx="480"  cy="720" r="5"/><circle cx="760"  cy="680" r="6"/>
          <circle cx="1280" cy="620" r="5"/>
        </g>
        <g fill="url(#nodeGrad)">
          <circle cx="900" cy="280" r="40" opacity="0.6"/>
          <circle cx="560" cy="500" r="28" opacity="0.4"/>
        </g>
      </svg>

      <div class="lp-hero-content">
        <div class="lp-eyebrow">
          <span class="lp-eyebrow-dot"></span>
          AI-Powered Grid Intelligence
        </div>
        <h1 class="lp-hero-title">
          전력망의 효율과 안정을<br>
          <em>데이터로 예측</em>합니다
        </h1>
        <p class="lp-hero-desc">
          Ensight는 Chronos-2 Transformer 기반 멀티모달 전력 수요 예측 시스템입니다.
          예측 데이터와 XAI 설명을 통합하여
          지역별 전력망의 안정적 운영을 지원합니다.
        </p>
        <div class="lp-hero-actions">
          <button class="lp-hero-btn-primary" @click="goToDashboard">수요 예측 시작하기 →</button>
          <a href="#how" class="lp-hero-btn-ghost">작동 원리 보기</a>
        </div>
      </div>

      <div class="lp-hero-stats">
        <div class="lp-stat-item">
          <div class="lp-stat-value">24<span>시간</span></div>
          <div class="lp-stat-label">예측 선행 구간</div>
        </div>
        <div class="lp-stat-item">
          <div class="lp-stat-value">14<span>개</span></div>
          <div class="lp-stat-label">전국 KEPCO 지역 관측소</div>
        </div>
        <div class="lp-stat-item">
          <div class="lp-stat-value">Chronos<span>-2</span></div>
          <div class="lp-stat-label">Foundation 모델</div>
        </div>
        <div class="lp-stat-item">
          <div class="lp-stat-value">3<span>종</span></div>
          <div class="lp-stat-label">멀티모달 입력</div>
        </div>
      </div>
    </section>

    <!-- FEATURES -->
    <section id="features" class="lp-section lp-section-gray">
      <div class="lp-section-inner">
        <div class="lp-section-header reveal" :class="{ visible: revealed.features }">
          <div class="lp-section-tag">Core Features</div>
          <h2 class="lp-section-title">전력 수요 예측을 위한<br>통합 인텔리전스</h2>
          <p class="lp-section-desc">시계열 분석부터 뉴스 기반 이벤트 감지, XAI 설명까지 — 전력망 의사결정에 필요한 모든 기능을 하나의 대시보드에서.</p>
        </div>
        <div class="lp-features-grid">
          <div v-for="(f, i) in features" :key="f.title"
               class="lp-feature-card reveal"
               :class="{ visible: revealed.features }"
               :style="{ transitionDelay: (i * 0.08) + 's' }">
            <div class="lp-feature-icon" :class="f.color">{{ f.icon }}</div>
            <div class="lp-feature-title">{{ f.title }}</div>
            <div class="lp-feature-desc">{{ f.desc }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- METRICS BANNER -->
    <section class="lp-metrics-banner">
      <div class="lp-metrics-inner">
        <div class="lp-metrics-text reveal" :class="{ visible: revealed.metrics }">
          <div class="lp-section-tag" style="color: var(--blue)">Performance</div>
          <h2 class="lp-section-title" style="color:#fff">데이터 기반의<br>정확한 예측</h2>
          <p class="lp-section-desc" style="color:rgba(255,255,255,0.6)">
            2012–2014년 KEPCO 실측 데이터로 검증된 모델. 전력 계통의 복잡한 패턴을 멀티모달 입력으로 포착합니다.
          </p>
        </div>
        <div class="lp-metrics-grid reveal" :class="{ visible: revealed.metrics }" style="transition-delay:.15s">
          <div v-for="m in metrics" :key="m.num" class="lp-metric-box">
            <div class="lp-metric-num">{{ m.num }}<small>{{ m.unit }}</small></div>
            <div class="lp-metric-label">{{ m.label }}</div>
            <div class="lp-metric-sub">{{ m.sub }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- HOW IT WORKS -->
    <section id="how" class="lp-section lp-section-white">
      <div class="lp-section-inner">
        <div class="lp-section-header reveal" :class="{ visible: revealed.how }" style="text-align:center; margin: 0 auto 56px; max-width: 700px;">
          <div class="lp-section-tag">How It Works</div>
          <h2 class="lp-section-title">4단계 예측 파이프라인</h2>
          <p class="lp-section-desc" style="margin:0 auto">원시 데이터 수집부터 설명 가능한 예측 결과 제공까지, Ensight의 분석 흐름을 확인하세요.</p>
        </div>
        <div class="lp-steps-grid">
          <div v-for="(s, i) in steps" :key="s.title"
               class="lp-step-item reveal"
               :class="{ visible: revealed.how }"
               :style="{ transitionDelay: (i * 0.1) + 's' }">
            <div class="lp-step-num">{{ String(i+1).padStart(2,'0') }}</div>
            <div class="lp-step-title">{{ s.title }}</div>
            <div class="lp-step-desc">{{ s.desc }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="lp-cta-section">
      <div class="lp-cta-box reveal" :class="{ visible: revealed.cta }">
        <div class="lp-cta-content">
          <h2 class="lp-cta-title">지금 바로 전력 수요를<br>예측해보세요</h2>
          <p class="lp-cta-desc">지역과 날짜를 선택하는 것만으로 Chronos-2 기반 24시간 전력 수요 예측과 XAI 분석 결과를 확인할 수 있습니다.</p>
          <div class="lp-cta-actions">
            <button class="lp-hero-btn-primary" @click="goToDashboard">수요 예측 시작하기 →</button>
            <a href="https://github.com" class="lp-hero-btn-ghost" target="_blank">GitHub 보기</a>
          </div>
        </div>
      </div>
    </section>

    <!-- FOOTER -->
    <footer class="lp-footer">
      <div>
        <div class="lp-footer-logo">Ensight</div>
        <div class="lp-footer-copy">전국 지역별 전력 수요 예측 시스템 · Capstone Project 2026</div>
      </div>
      <div class="lp-footer-links">
        <button @click="goToDashboard">대시보드</button>
        <a href="https://github.com" target="_blank">GitHub</a>
        <a href="#">팀 소개</a>
      </div>
    </footer>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isScrolled = ref(false)

function goToDashboard() {
  router.push('/dashboard')
}

// ── 스크롤 핸들러
function onScroll() {
  isScrolled.value = window.scrollY > 60
}

// ── Intersection Observer (스크롤 reveal)
const revealed = ref({ features: false, metrics: false, how: false, tech: false, cta: false })
let observer = null

onMounted(() => {
  window.addEventListener('scroll', onScroll)

  observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return
      const key = e.target.dataset.section
      if (key) revealed.value[key] = true
    })
  }, { threshold: 0.12 })

  document.querySelectorAll('[data-section]').forEach(el => observer.observe(el))

  // 섹션 헤더에 data-section 속성 동적 바인딩
  const sectionMap = {
    '#features .lp-section-header': 'features',
    '#features .lp-features-grid': 'features',
    '.lp-metrics-banner .lp-metrics-text': 'metrics',
    '.lp-metrics-banner .lp-metrics-grid': 'metrics',
    '#how .lp-section-header': 'how',
    '#how .lp-steps-grid': 'how',
    '#tech .reveal': 'tech',
    '.lp-cta-box': 'cta',
  }
  Object.entries(sectionMap).forEach(([sel, key]) => {
    document.querySelectorAll(sel).forEach(el => {
      el.dataset.section = key
      observer.observe(el)
    })
  })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  observer?.disconnect()
})

// ── 데이터
const features = [
  { icon: '🔮', color: 'purple', title: 'Chronos-2 예측 모델',   desc: 'Amazon의 Chronos-2 Transformer foundation 모델 기반. 과거 전력 패턴을 학습해 24시간 수요를 정밀하게 예측합니다.' },
  { icon: '🌤', color: 'blue',   title: '기상 데이터 통합',       desc: '기온·습도·풍속 등 기상 변수를 실시간으로 반영하여 계절적 부하 변동을 포착합니다.' },
  { icon: '📰', color: 'amber',  title: '뉴스 임베딩 분석',       desc: 'BigKinds API 기반 뉴스 데이터를 KLUE/RoBERTa로 임베딩, PCA 차원 축소 후 전력 수요 영향 이벤트를 자동 감지합니다.' },
  { icon: '🧠', color: 'green',  title: 'XAI 설명 가능성',        desc: '예측 결과의 근거를 자연어로 설명합니다. 어떤 변수가 예측에 얼마나 기여했는지 요인 중요도와 함께 제공합니다.' },
  { icon: '🗺', color: 'cyan',   title: '지역별 3D 현황 맵',      desc: 'deck.gl ColumnLayer 기반 3D 지도로 전국 14개 KEPCO 지역 관측소의 부하 현황을 직관적으로 시각화합니다.' },
  { icon: '⚡', color: 'pink',   title: 'ESS 운영 분석',          desc: '에너지저장장치(ESS) 가동 전후 피크 부하 변화를 비교 분석하여 배터리 운영 전략 수립을 지원합니다.' },
]

const metrics = [
  { num: '2012', unit: '–14', label: '학습 데이터 기간',   sub: 'KEPCO 실측 데이터' },
  { num: '1',    unit: 'hr',  label: '데이터 해상도',       sub: '시간 단위 전력 계측' },
  { num: '3',    unit: '종',  label: '멀티모달 피처',       sub: '전력·기상·뉴스 통합' },
  { num: 'FastAPI', unit: '', label: '백엔드 아키텍처',     sub: 'RESTful · uvicorn' },
]

const steps = [
  { title: '데이터 수집',        desc: 'KEPCO 전력 계측, KMA 기상 API, BigKinds 뉴스 API에서 실시간 데이터를 수집합니다.' },
  { title: '피처 엔지니어링',    desc: '기상 변수 정규화, 뉴스 임베딩(RoBERTa) 후 PCA 차원 축소로 핵심 피처를 추출합니다.' },
  { title: 'Chronos-2 추론',    desc: 'Foundation 모델이 과거 패턴과 멀티모달 피처를 통합해 24시간 전력 수요를 예측합니다.' },
  { title: 'XAI 설명 생성',     desc: '요인 중요도와 LLM 기반 자연어 해석을 결합해 예측 근거를 직관적으로 설명합니다.' },
]

const techs = [
  { name: 'Vue.js 3',       color: '#646cff' },
  { name: 'FastAPI',        color: '#0070f3' },
  { name: 'ECharts',        color: '#e33d28' },
  { name: 'deck.gl',        color: '#75b2dd' },
  { name: 'Plotly',         color: '#636efa' },
  { name: 'Chronos-2',      color: '#ff7043' },
  { name: 'KLUE/RoBERTa',   color: '#00b894' },
  { name: 'PCA',            color: '#6c63ff' },
  { name: 'MapLibre GL',    color: '#f7b731' },
  { name: 'CARTO Basemap',  color: '#2c3e50' },
  { name: 'BigKinds API',   color: '#e84393' },
  { name: 'Pretendard',     color: '#38bdf8' },
]
</script>

<style scoped>
/* ── 전체 랜딩 래퍼 ── */
.landing {
  font-family: 'Pretendard', -apple-system, sans-serif;
  background: #f4f5f7;
  color: #1a1a2e;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
  min-width: 1280px;
}

/* ── NAV ── */
.lp-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 200;
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 48px;
  background: rgba(14,14,44,0.72);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(255,255,255,0.07);
  transition: background .3s;
}
.lp-nav.scrolled { background: rgba(14,14,44,0.92); }

.lp-nav-logo { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.lp-logo-mark {
  width: 34px; height: 34px;
  background: linear-gradient(135deg, #7b8ef0, #4355c7);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; color: #fff;
}
.lp-logo-text { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.02em; }
.lp-logo-sub  { font-size: 10px; color: rgba(255,255,255,0.5); margin-top: 1px; font-family: 'JetBrains Mono'; }

.lp-nav-links { display: flex; align-items: center; gap: 32px; }
.lp-nav-links a { font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.7); text-decoration: none; transition: color .15s; }
.lp-nav-links a:hover { color: #fff; }

.lp-nav-cta { display: flex; align-items: center; gap: 32px; }

.lp-btn-ghost {
  padding: 8px 18px; border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.25); background: transparent;
  color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 500;
  font-family: 'Pretendard', sans-serif; cursor: pointer;
  transition: all .15s;
}
.lp-btn-ghost:hover { border-color: rgba(255,255,255,0.5); color: #fff; background: rgba(255,255,255,0.08); }

.lp-btn-primary {
  padding: 9px 20px; border-radius: 8px;
  background: #5e72e4; border: none; color: #fff;
  font-size: 13px; font-weight: 600; font-family: 'Pretendard', sans-serif; cursor: pointer;
  transition: background .15s, transform .1s;
  box-shadow: 0 4px 16px rgba(94,114,228,0.4);
}
.lp-btn-primary:hover { background: #7b8ef0; transform: translateY(-1px); }

/* ── HERO ── */
.lp-hero {
  position: relative; min-height: 100vh;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  overflow: hidden;
}
.lp-hero-bg {
  position: absolute; inset: 0; z-index: 0;
  background-image: url('https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=1920&q=80');
  background-size: cover; background-position: center;
  filter: brightness(0.32) saturate(0.6);
}
.lp-hero-overlay {
  position: absolute; inset: 0; z-index: 1;
  background:
    radial-gradient(ellipse 80% 60% at 50% 30%, rgba(94,114,228,0.18) 0%, transparent 70%),
    linear-gradient(180deg, rgba(14,14,44,0.55) 0%, rgba(14,14,44,0.3) 50%, rgba(14,14,44,0.85) 100%);
}
.lp-hero-grid {
  position: absolute; inset: 0; z-index: 2;
  opacity: 0.22; pointer-events: none;
}
.lp-hero-content {
  position: relative; z-index: 10;
  text-align: center; max-width: 820px; padding: 0 32px;
  animation: lpFadeUp .9s cubic-bezier(.22,1,.36,1) both;
  margin-top: 20px;
}
@keyframes lpFadeUp {
  from { opacity: 0; transform: translateY(32px); }
  to   { opacity: 1; transform: translateY(0); }
}

.lp-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(94,114,228,0.18);
  border: 1px solid rgba(94,114,228,0.35);
  border-radius: 100px; padding: 6px 16px;
  font-size: 12px; font-weight: 600; color: #7b8ef0;
  letter-spacing: .06em; text-transform: uppercase; margin-bottom: 28px;
  font-family: 'JetBrains Mono';
}
.lp-eyebrow-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #2dce89;
  animation: lpPulse 2s ease-in-out infinite;
}
@keyframes lpPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .5; transform: scale(.75); }
}

.lp-hero-title {
  font-size: clamp(38px, 5.5vw, 68px); font-weight: 800;
  color: #fff; line-height: 1.1; letter-spacing: -0.03em; margin-bottom: 22px; word-break: keep-all;
}
.lp-hero-title em {
  font-style: normal;
  background: linear-gradient(90deg, #7b8ef0 0%, #11cdef 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.lp-hero-desc {
  font-size: 17px; line-height: 1.75; color: rgba(255,255,255,0.65);
  max-width: 560px; margin: 0 auto 40px;
}
.lp-hero-actions { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }

.lp-hero-btn-primary {
  padding: 14px 32px; border-radius: 10px; background: #5e72e4;
  border: none; color: #fff; font-size: 15px; font-weight: 600;
  font-family: 'Pretendard', sans-serif; cursor: pointer; text-decoration: none;
  box-shadow: 0 6px 24px rgba(94,114,228,0.5); transition: all .15s; display: inline-block;
}
.lp-hero-btn-primary:hover { background: #7b8ef0; transform: translateY(-2px); box-shadow: 0 10px 32px rgba(94,114,228,0.55); }

.lp-hero-btn-ghost {
  padding: 14px 28px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.28); background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.85); font-size: 15px; font-weight: 500;
  font-family: 'Pretendard', sans-serif; cursor: pointer; text-decoration: none;
  backdrop-filter: blur(8px); transition: all .15s; display: inline-block;
}
.lp-hero-btn-ghost:hover { border-color: rgba(255,255,255,0.5); background: rgba(255,255,255,0.12); transform: translateY(-1px); }

.lp-hero-stats {
  position: absolute; bottom: 48px; left: 0; right: 0; z-index: 10;
  display: flex; justify-content: center; gap: 2px;
  animation: lpFadeUp 1.1s .3s cubic-bezier(.22,1,.36,1) both;
}
.lp-stat-item {
  background: rgba(255,255,255,0.07); backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 18px 36px; text-align: center; transition: background .2s;
}
.lp-stat-item:first-child { border-radius: 14px 0 0 14px; }
.lp-stat-item:last-child  { border-radius: 0 14px 14px 0; }
.lp-stat-item:hover { background: rgba(255,255,255,0.12); }
.lp-stat-value {
  font-size: 26px; font-weight: 700; font-family: 'JetBrains Mono';
  color: #fff; letter-spacing: -0.03em; line-height: 1;
}
.lp-stat-value span { font-size: 14px; color: #7b8ef0; margin-left: 2px; }
.lp-stat-label { font-size: 11px; color: rgba(255,255,255,0.45); margin-top: 5px; letter-spacing: .05em; }

/* ── 공통 섹션 ── */
.lp-section { padding: 100px 0; }
.lp-section-gray  { background: #f4f5f7; }
.lp-section-white { background: #fff; }
.lp-section-inner { max-width: 1200px; margin: 0 auto; padding: 0 48px; }
.lp-section-header { max-width: 560px; margin-bottom: 56px; }

.lp-section-tag {
  display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: #5e72e4;
  font-family: 'JetBrains Mono'; margin-bottom: 14px;
}
.lp-section-title {
  font-size: clamp(26px, 3vw, 40px); font-weight: 800; letter-spacing: -0.03em;
  color: #1a1a2e; line-height: 1.2; margin-bottom: 14px; word-break: keep-all;
}
.lp-section-desc { font-size: 16px; color: #6b7280; line-height: 1.75; word-break: keep-all; }

/* ── FEATURES ── */
.lp-features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.lp-feature-card {
  background: #fff; border: 1px solid #e9ecef; border-radius: 16px; padding: 28px 26px;
  transition: box-shadow .2s, transform .15s, opacity .7s ease, translate .7s ease;
  position: relative; overflow: hidden;
}
.lp-feature-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, #5e72e4, #11cdef);
  opacity: 0; transition: opacity .2s;
}
.lp-feature-card:hover { box-shadow: 0 8px 32px rgba(94,114,228,0.13); transform: translateY(-3px); }
.lp-feature-card:hover::before { opacity: 1; }

.lp-feature-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; margin-bottom: 18px;
}
.lp-feature-icon.purple { background: linear-gradient(135deg, #ede9fe, #ddd6fe); }
.lp-feature-icon.blue   { background: linear-gradient(135deg, #eff6ff, #dbeafe); }
.lp-feature-icon.green  { background: linear-gradient(135deg, #f0fdf4, #bbf7d0); }
.lp-feature-icon.amber  { background: linear-gradient(135deg, #fffbeb, #fde68a); }
.lp-feature-icon.pink   { background: linear-gradient(135deg, #fdf2f8, #f9d8f0); }
.lp-feature-icon.cyan   { background: linear-gradient(135deg, #ecfeff, #a5f3fc); }

.lp-feature-title { font-size: 15px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; letter-spacing: -0.01em; word-break: keep-all; }
.lp-feature-desc  { font-size: 13px; color: #6b7280; line-height: 1.65; word-break: keep-all; }

/* ── METRICS ── */
.lp-metrics-banner {
  background: linear-gradient(135deg, #1a1a4e 0%, #2d2d7e 50%, #3a3a9e 100%);
  padding: 80px 48px; position: relative; overflow: hidden;
}
.lp-metrics-banner::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 60% 80% at 30% 50%, rgba(94,114,228,0.25), transparent 60%),
              radial-gradient(ellipse 40% 60% at 80% 30%, rgba(17,205,239,0.12), transparent 50%);
}
.lp-metrics-inner {
  position: relative; max-width: 1200px; margin: 0 auto;
  display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center;
}
.lp-metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.lp-metric-box {
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
  border-radius: 14px; padding: 22px 20px; transition: background .2s;
}
.lp-metric-box:hover { background: rgba(255,255,255,0.13); }
.lp-metric-num {
  font-size: 32px; font-weight: 700; font-family: 'JetBrains Mono';
  letter-spacing: -0.04em; line-height: 1;
  background: linear-gradient(90deg, #fff, #a5b4fc);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.lp-metric-num small { font-size: 16px; opacity: .7; }
.lp-metric-label { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 6px; letter-spacing: .04em; }
.lp-metric-sub   { font-size: 11px; color: rgba(255,255,255,0.35); margin-top: 3px; font-family: 'JetBrains Mono'; }

/* ── HOW IT WORKS ── */
.lp-steps-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 0;
  position: relative;
}
.lp-steps-grid::before {
  content: ''; position: absolute; top: 28px; left: 10%; right: 10%; height: 1px;
  background: linear-gradient(90deg, transparent, #5e72e4, #11cdef, transparent);
  z-index: 0;
}
.lp-step-item { text-align: center; padding: 0 24px; position: relative; z-index: 1; }
.lp-step-num {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #5e72e4, #4355c7);
  color: #fff; font-size: 18px; font-weight: 700; font-family: 'JetBrains Mono';
  display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;
  box-shadow: 0 6px 20px rgba(94,114,228,0.4);
}
.lp-step-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; word-break: keep-all; }
.lp-step-desc  { font-size: 12px; color: #6b7280; line-height: 1.65; word-break: keep-all; }

/* ── TECH ── */
.lp-tech-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 40px; }
.lp-tech-pill {
  display: flex; align-items: center; gap: 6px;
  background: #fff; border: 1px solid #e9ecef; border-radius: 100px;
  padding: 8px 16px; font-size: 12px; font-weight: 600; color: #4a5568;
  font-family: 'JetBrains Mono'; transition: all .15s;
}
.lp-tech-pill:hover { border-color: #5e72e4; color: #5e72e4; background: #f0f2ff; }
.lp-tech-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

/* ── CTA ── */
.lp-cta-section { padding: 100px 48px; text-align: center; background: linear-gradient(180deg, #fff 0%, #f4f5f7 100%); }
.lp-cta-box {
  max-width: 640px; margin: 0 auto;
  background: linear-gradient(135deg, #1a1a4e, #2d2d7e);
  border-radius: 24px; padding: 60px 48px;
  box-shadow: 0 20px 60px rgba(26,26,78,0.25);
  position: relative; overflow: hidden;
}
.lp-cta-box::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 70% 70% at 50% 0%, rgba(94,114,228,0.3), transparent);
}
.lp-cta-content { position: relative; }
.lp-cta-title { font-size: 30px; font-weight: 800; color: #fff; letter-spacing: -0.03em; line-height: 1.2; margin-bottom: 14px; word-break: keep-all; }
.lp-cta-desc  { font-size: 15px; color: rgba(255,255,255,0.6); line-height: 1.7; margin-bottom: 32px; word-break: keep-all; }
.lp-cta-actions { display: flex; gap: 12px; justify-content: center; }

/* ── FOOTER ── */
.lp-footer {
  background: #0e0e2c; padding: 36px 48px;
  display: flex; align-items: center; justify-content: space-between;
}
.lp-footer-logo { font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.7); }
.lp-footer-copy { font-size: 11px; color: rgba(255,255,255,0.3); font-family: 'JetBrains Mono'; margin-top: 4px; }
.lp-footer-links { display: flex; gap: 24px; }
.lp-footer-links a,
.lp-footer-links button {
  font-size: 12px; color: rgba(255,255,255,0.4); text-decoration: none;
  background: none; border: none; cursor: pointer; font-family: 'Pretendard', sans-serif;
  transition: color .15s;
}
.lp-footer-links a:hover,
.lp-footer-links button:hover { color: rgba(255,255,255,0.8); }

/* ── Scroll reveal ── */
.reveal { opacity: 0; transform: translateY(24px); transition: opacity .7s ease, transform .7s ease; }
.reveal.visible { opacity: 1; transform: translateY(0); }
</style>