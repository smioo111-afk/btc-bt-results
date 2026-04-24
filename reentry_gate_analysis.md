# #56: 재진입 Gate 병목 분석

**작성**: 2026-04-24 16:29

**대상**: 2023 회복기 (2023-01-01 ~ 2024-01-01)

**케이스**: E2b+6mo, M2/AY, E2a

**총 gap 봉 분석**: 2110 봉

## TL;DR

- **Gate는 고도로 중첩됨** — EMA 실패 87% / AI Gate 실패 67% / SCORE 실패 63% / REGIME_DOWN 38% / E2_BLOCK 25% (각 독립 빈도, 합계 > 100%)
- **Primary cascading gate 분포**: AI_GATE 28%, REGIME_DOWN 27%, E2_BLOCK 25%
- **‘단일 gate 해제’ 시뮬 결과**: 어느 gate 하나만 완전 무효화해도 신규 PASS 봉 +5~+14 (baseline 5 → 최대 19/685 = 3%) → **단일 gate 완화 효과 미미**
- **병목 본질**: 대부분 gap 봉이 여러 gate에 동시 실패 → 단일 완화로는 해결 안 됨
- **주요 missed run (03-09→03-15, +13.37%) = E2_BLOCK 18봉 중심** — 3월 초 하락 후 반등인데 O3 예외 미발동. O3 threshold 조정 별도 연구 후보
- **결론**: E2_BLOCK/REGIME_DOWN은 의도된 안전, AI/EMA/Score는 상호 중첩 → **단일 gate 완화 백테스트 NO-GO**. #55 **청산 완화** + O3 threshold 세부화가 더 유망

## A) Gate 분포

### A-1. Primary gate (cascading 우선순위: COOLDOWN → E2_BLOCK → REGIME_DOWN → AI_GATE → EMA → SCORE → MISC)

| case | AI_GATE | COOLDOWN | E2_BLOCK | EMA | MISC_BB | MISC_RSI | PASS | REGIME_DOWN | SCORE | 합계 |
|---|---|---|---|---|---|---|---|---|---|---|
| E2a | 183 | 12 | 172 | 94 | 1 | 10 | 5 | 189 | 6 | 672 |
| E2b+6mo | 190 | 12 | 172 | 95 | 1 | 10 | 5 | 194 | 6 | 685 |
| M2/AY | 225 | 12 | 190 | 108 | 1 | 10 | 5 | 194 | 8 | 753 |

### A-2. 독립 Gate 실패 빈도 (우선순위 무관, 개별 gate 단독 차단 판정)

_한 봉이 여러 gate에 동시 실패 가능 → 합계가 100% 초과._

| gate | n | % of gap bars | 해석 |
|---|---|---|---|
| EMA | 595 | 86.9 | 4H EMA21 < EMA55 (정배열 실패) |
| AI_GATE | 456 | 66.6 | XGB < regime threshold + dynamic |
| SCORE | 432 | 63.1 | Rule score < regime threshold (Range 5.0 / TU 2.8) |
| REGIME_DOWN | 264 | 38.5 | Trend_Down regime (의도된 안전) |
| E2_BLOCK | 172 | 25.1 | 일봉 < EMA200 (F2 BEAR 차단, 의도된 안전) |
| MISC_BB | 41 | 6.0 | Price > BB upper (과매수 방어) |
| MISC_RSI | 23 | 3.4 | RSI ≥ 72 (과매수 방어) |
| COOLDOWN | 12 | 1.8 | 손절 직후 1봉 대기 (영향 미미) |

### A-3. ‘단일 gate 해제’ 시나리오 — 그 gate 하나만 완전 무효화 시 PASS 봉 수

_각 gate 하나만 해제했을 때 PASS 전환되는 봉 수. 다른 gate 에 여전히 막히면 제외._

**baseline PASS (현행)**: 5 봉 / 685

| gate 해제 | 신규 PASS 봉 | 현행 대비 증가 |
|---|---|---|
| EMA | 14 | +9 |
| REGIME_DOWN | 13 | +8 |
| SCORE | 11 | +6 |
| MISC_RSI | 11 | +6 |
| AI_GATE | 10 | +5 |
| MISC_BB | 6 | +1 |
| COOLDOWN | 5 | +0 |
| E2_BLOCK | 5 | +0 |

## B) 상위 5개 Gap (BTC 가격 상승 놓친 구간 — E2b+6mo 한정)

### 2023-03-09 05:00 (exit: ATR손절 -2.94%) → 2023-03-15 01:00 (34봉, BTC +13.37%)

Gate 분포: `E2_BLOCK:18|REGIME_DOWN:9|MISC_RSI:3|AI_GATE:2|COOLDOWN:1|EMA:1`

| ts | price | gate | xgb | rth | score | sc_th | EMA | ADX | rgm |
|---|---|---|---|---|---|---|---|---|---|
| 03-09 09:00 | 29,100,000 | COOLDOWN | 0.37 | 0.60 | 4.6 | 2.8 | F | 31 | Tren |
| 03-09 13:00 | 28,937,000 | REGIME_DOWN | 0.50 | 0.60 | 4.1 | 2.8 | F | 32 | Tren |
| 03-09 17:00 | 28,952,000 | REGIME_DOWN | 0.58 | 0.60 | 4.6 | 2.8 | F | 34 | Tren |
| 03-09 21:00 | 28,961,000 | REGIME_DOWN | 0.43 | 0.60 | 4.6 | 2.8 | F | 35 | Tren |
| 03-10 01:00 | 28,062,000 | REGIME_DOWN | 0.51 | 0.60 | 2.5 | 2.8 | F | 37 | Tren |
| 03-10 05:00 | 27,604,000 | REGIME_DOWN | 0.43 | 0.60 | 3.3 | 2.8 | F | 39 | Tren |
| 03-10 09:00 | 27,102,000 | REGIME_DOWN | 0.39 | 0.60 | 3.3 | 2.8 | F | 42 | Tren |
| 03-10 13:00 | 26,996,000 | REGIME_DOWN | 0.39 | 0.60 | 3.3 | 2.8 | F | 45 | Tren |
| 03-10 17:00 | 26,860,000 | REGIME_DOWN | 0.57 | 0.60 | 3.3 | 2.8 | F | 47 | Tren |
| 03-10 21:00 | 27,091,000 | REGIME_DOWN | 0.59 | 0.60 | 3.3 | 2.8 | F | 48 | Tren |
| 03-11 01:00 | 27,052,000 | E2_BLOCK | 0.59 | 0.60 | 3.3 | 2.8 | F | 48 | Tren |
| 03-11 05:00 | 27,343,000 | E2_BLOCK | 0.58 | 0.60 | 2.5 | 2.8 | F | 49 | Tren |
| 03-11 09:00 | 27,682,000 | E2_BLOCK | 0.71 | 0.65 | 2.3 | 2.8 | F | 47 | Vola |
| 03-11 13:00 | 26,974,000 | E2_BLOCK | 0.74 | 0.65 | 2.3 | 2.8 | F | 46 | Vola |
| 03-11 17:00 | 27,322,000 | E2_BLOCK | 0.78 | 0.65 | 2.3 | 2.8 | F | 45 | Vola |
| 03-11 21:00 | 27,343,000 | E2_BLOCK | 0.84 | 0.65 | 2.3 | 2.8 | F | 45 | Vola |
| 03-12 01:00 | 27,453,000 | E2_BLOCK | 0.63 | 0.65 | 2.3 | 2.8 | F | 43 | Vola |
| 03-12 05:00 | 27,737,000 | E2_BLOCK | 0.34 | 0.60 | 3.8 | 2.8 | F | 42 | Tren |
| 03-12 09:00 | 27,492,000 | E2_BLOCK | 0.12 | 0.60 | 3.3 | 2.8 | F | 40 | Tren |
| 03-12 13:00 | 27,442,000 | E2_BLOCK | 0.07 | 0.60 | 3.3 | 2.8 | F | 39 | Tren |
| 03-12 17:00 | 27,518,000 | E2_BLOCK | 0.06 | 0.60 | 3.3 | 2.8 | F | 37 | Tren |
| 03-12 21:00 | 27,317,000 | E2_BLOCK | 0.06 | 0.60 | 3.3 | 2.8 | F | 37 | Tren |
| 03-13 01:00 | 27,780,000 | E2_BLOCK | 0.13 | 0.65 | 2.8 | 2.8 | F | 35 | Vola |
| 03-13 05:00 | 29,199,000 | E2_BLOCK | 0.14 | 0.65 | 2.8 | 2.8 | F | 34 | Vola |
| 03-13 09:00 | 29,334,000 | E2_BLOCK | 0.33 | 0.65 | 3.6 | 2.8 | F | 35 | Vola |
| 03-13 13:00 | 29,696,000 | E2_BLOCK | 0.39 | 0.65 | 3.6 | 2.8 | F | 35 | Vola |
| 03-13 17:00 | 29,313,000 | E2_BLOCK | 0.75 | 0.65 | 2.8 | 2.8 | F | 34 | Vola |
| 03-13 21:00 | 31,502,000 | E2_BLOCK | 0.41 | 0.65 | 3.6 | 2.8 | F | 35 | Vola |
| 03-14 01:00 | 31,891,000 | EMA | 0.72 | 0.65 | 3.6 | 2.8 | F | 36 | Vola |
| 03-14 05:00 | 31,676,000 | MISC_RSI | 0.70 | 0.65 | 4.8 | 2.8 | T | 38 | Vola |
| 03-14 09:00 | 32,131,000 | MISC_RSI | 0.66 | 0.65 | 4.0 | 2.8 | T | 39 | Vola |
| 03-14 13:00 | 31,863,000 | MISC_RSI | 0.61 | 0.65 | 4.8 | 2.8 | T | 40 | Vola |
| 03-14 17:00 | 32,609,000 | AI_GATE | 0.52 | 0.65 | 4.8 | 2.8 | T | 41 | Vola |
| 03-14 21:00 | 33,909,000 | AI_GATE | 0.46 | 0.65 | 4.8 | 2.8 | T | 43 | Vola |

### 2023-02-10 01:00 (exit: ATR손절 -3.96%) → 2023-02-17 05:00 (42봉, BTC +6.71%)

Gate 분포: `REGIME_DOWN:25|EMA:7|AI_GATE:6|MISC_RSI:3|COOLDOWN:1`

| ts | price | gate | xgb | rth | score | sc_th | EMA | ADX | rgm |
|---|---|---|---|---|---|---|---|---|---|
| 02-10 05:00 | 28,193,000 | COOLDOWN | 0.64 | 0.60 | 3.3 | 5.0 | F | 22 | Rang |
| 02-10 09:00 | 28,014,000 | EMA | 0.61 | 0.60 | 3.3 | 5.0 | F | 24 | Rang |
| 02-10 13:00 | 28,238,000 | EMA | 0.70 | 0.60 | 3.3 | 5.0 | F | 26 | Rang |
| 02-10 17:00 | 28,008,000 | REGIME_DOWN | 0.76 | 0.60 | 3.3 | 2.8 | F | 28 | Tren |
| 02-10 21:00 | 28,038,000 | REGIME_DOWN | 0.68 | 0.60 | 3.3 | 2.8 | F | 30 | Tren |
| 02-11 01:00 | 28,124,000 | REGIME_DOWN | 0.69 | 0.60 | 3.3 | 2.8 | F | 32 | Tren |
| 02-11 05:00 | 28,120,000 | REGIME_DOWN | 0.74 | 0.60 | 3.3 | 2.8 | F | 34 | Tren |
| 02-11 09:00 | 28,206,000 | REGIME_DOWN | 0.75 | 0.60 | 3.3 | 2.8 | F | 34 | Tren |
| 02-11 13:00 | 28,183,000 | REGIME_DOWN | 0.42 | 0.60 | 4.1 | 2.8 | F | 35 | Tren |
| 02-11 17:00 | 28,174,000 | REGIME_DOWN | 0.51 | 0.60 | 3.3 | 2.8 | F | 35 | Tren |
| 02-11 21:00 | 28,210,000 | REGIME_DOWN | 0.36 | 0.60 | 3.3 | 2.8 | F | 35 | Tren |
| 02-12 01:00 | 28,182,000 | REGIME_DOWN | 0.33 | 0.60 | 2.3 | 2.8 | F | 36 | Tren |
| 02-12 05:00 | 28,377,000 | REGIME_DOWN | 0.28 | 0.60 | 2.3 | 2.8 | F | 35 | Tren |
| 02-12 09:00 | 28,297,000 | REGIME_DOWN | 0.30 | 0.60 | 2.3 | 2.8 | F | 34 | Tren |
| 02-12 13:00 | 28,220,000 | REGIME_DOWN | 0.23 | 0.60 | 2.3 | 2.8 | F | 33 | Tren |
| 02-12 17:00 | 28,326,000 | REGIME_DOWN | 0.25 | 0.60 | 2.3 | 2.8 | F | 31 | Tren |
| 02-12 21:00 | 28,338,000 | REGIME_DOWN | 0.16 | 0.60 | 2.3 | 2.8 | F | 31 | Tren |
| 02-13 01:00 | 28,391,000 | REGIME_DOWN | 0.23 | 0.60 | 2.3 | 2.8 | F | 29 | Tren |
| 02-13 05:00 | 28,263,000 | REGIME_DOWN | 0.12 | 0.60 | 2.3 | 2.8 | F | 28 | Tren |
| 02-13 09:00 | 28,333,000 | REGIME_DOWN | 0.29 | 0.60 | 2.8 | 2.8 | F | 28 | Tren |
| 02-13 13:00 | 28,260,000 | REGIME_DOWN | 0.28 | 0.60 | 3.1 | 2.8 | F | 28 | Tren |
| 02-13 17:00 | 28,070,000 | REGIME_DOWN | 0.35 | 0.60 | 4.1 | 2.8 | F | 29 | Tren |
| 02-13 21:00 | 28,056,000 | REGIME_DOWN | 0.63 | 0.60 | 3.1 | 2.8 | F | 29 | Tren |
| 02-14 01:00 | 28,068,000 | REGIME_DOWN | 0.60 | 0.60 | 3.3 | 2.8 | F | 31 | Tren |
| 02-14 05:00 | 28,309,000 | REGIME_DOWN | 0.62 | 0.60 | 3.3 | 2.8 | F | 31 | Tren |
| 02-14 09:00 | 28,100,000 | REGIME_DOWN | 0.42 | 0.60 | 3.3 | 2.8 | F | 30 | Tren |
| 02-14 13:00 | 28,186,000 | REGIME_DOWN | 0.65 | 0.60 | 4.1 | 2.8 | F | 30 | Tren |
| 02-14 17:00 | 28,214,000 | REGIME_DOWN | 0.53 | 0.60 | 4.6 | 2.8 | F | 30 | Tren |
| 02-14 21:00 | 28,485,000 | EMA | 0.49 | 0.58 | 4.6 | 2.8 | F | 29 | Tren |
| 02-15 01:00 | 28,739,000 | AI_GATE | 0.39 | 0.58 | 4.6 | 2.8 | F | 28 | Tren |
| 02-15 05:00 | 28,798,000 | EMA | 0.73 | 0.58 | 3.8 | 2.8 | F | 28 | Tren |
| 02-15 09:00 | 28,747,000 | EMA | 0.60 | 0.58 | 3.8 | 2.8 | F | 27 | Tren |
| 02-15 13:00 | 28,710,000 | EMA | 0.48 | 0.58 | 4.6 | 2.8 | F | 26 | Tren |
| 02-15 17:00 | 29,058,000 | AI_GATE | 0.39 | 0.58 | 4.6 | 2.8 | F | 27 | Tren |
| 02-15 21:00 | 29,543,000 | EMA | 0.50 | 0.58 | 4.6 | 2.8 | F | 29 | Tren |
| 02-16 01:00 | 30,011,000 | MISC_RSI | 0.60 | 0.58 | 5.8 | 2.8 | T | 31 | Tren |
| 02-16 05:00 | 31,186,000 | MISC_RSI | 0.68 | 0.65 | 4.0 | 2.8 | T | 34 | Vola |
| 02-16 09:00 | 31,800,000 | AI_GATE | 0.38 | 0.65 | 4.8 | 2.8 | T | 37 | Vola |
| 02-16 13:00 | 31,484,000 | AI_GATE | 0.45 | 0.65 | 4.8 | 2.8 | T | 40 | Vola |
| 02-16 17:00 | 31,559,000 | AI_GATE | 0.24 | 0.65 | 4.0 | 2.8 | T | 43 | Vola |
| 02-16 21:00 | 32,199,000 | AI_GATE | 0.34 | 0.65 | 4.8 | 2.8 | T | 46 | Vola |
| 02-17 01:00 | 32,088,000 | MISC_RSI | 0.55 | 0.65 | 4.8 | 2.8 | T | 49 | Vola |

### 2023-11-15 09:00 (exit: 계단손절 +25.80%) → 2023-11-16 01:00 (3봉, BTC +6.05%)

Gate 분포: `REGIME_DOWN:3`

| ts | price | gate | xgb | rth | score | sc_th | EMA | ADX | rgm |
|---|---|---|---|---|---|---|---|---|---|
| 11-15 13:00 | 47,652,000 | REGIME_DOWN | 0.58 | 0.60 | 5.3 | 2.8 | T | 30 | Tren |
| 11-15 17:00 | 48,319,000 | REGIME_DOWN | 0.78 | 0.60 | 5.3 | 2.8 | T | 30 | Tren |
| 11-15 21:00 | 48,744,000 | REGIME_DOWN | 0.73 | 0.60 | 5.8 | 2.8 | T | 29 | Tren |

### 2023-05-25 09:00 (exit: ATR손절 -3.19%) → 2023-05-29 21:00 (26봉, BTC +5.08%)

Gate 분포: `AI_GATE:9|REGIME_DOWN:7|EMA:5|MISC_RSI:4|COOLDOWN:1`

| ts | price | gate | xgb | rth | score | sc_th | EMA | ADX | rgm |
|---|---|---|---|---|---|---|---|---|---|
| 05-25 13:00 | 35,069,000 | COOLDOWN | 0.60 | 0.60 | 4.1 | 5.0 | F | 26 | Rang |
| 05-25 17:00 | 35,209,000 | REGIME_DOWN | 0.52 | 0.60 | 4.1 | 2.8 | F | 28 | Tren |
| 05-25 21:00 | 35,281,000 | REGIME_DOWN | 0.67 | 0.60 | 3.3 | 2.8 | F | 28 | Tren |
| 05-26 01:00 | 35,519,000 | REGIME_DOWN | 0.57 | 0.60 | 4.1 | 2.8 | F | 28 | Tren |
| 05-26 05:00 | 35,547,000 | REGIME_DOWN | 0.35 | 0.60 | 3.3 | 2.8 | F | 27 | Tren |
| 05-26 09:00 | 35,413,000 | REGIME_DOWN | 0.21 | 0.60 | 3.3 | 2.8 | F | 27 | Tren |
| 05-26 13:00 | 35,501,000 | REGIME_DOWN | 0.30 | 0.60 | 4.1 | 2.8 | F | 27 | Tren |
| 05-26 17:00 | 35,468,000 | REGIME_DOWN | 0.24 | 0.60 | 3.3 | 2.8 | F | 27 | Tren |
| 05-26 21:00 | 35,875,000 | AI_GATE | 0.25 | 0.58 | 3.3 | 2.8 | F | 26 | Tren |
| 05-27 01:00 | 35,908,000 | EMA | 0.48 | 0.58 | 4.6 | 2.8 | F | 24 | Tren |
| 05-27 05:00 | 35,771,000 | EMA | 0.43 | 0.58 | 3.3 | 2.8 | F | 23 | Tren |
| 05-27 09:00 | 35,798,000 | EMA | 0.50 | 0.60 | 3.8 | 5.0 | F | 22 | Rang |
| 05-27 13:00 | 35,798,000 | EMA | 0.43 | 0.60 | 3.8 | 5.0 | F | 21 | Rang |
| 05-27 17:00 | 35,750,000 | AI_GATE | 0.40 | 0.60 | 3.3 | 5.0 | F | 20 | Rang |
| 05-27 21:00 | 35,630,000 | AI_GATE | 0.19 | 0.60 | 3.3 | 5.0 | F | 19 | Rang |
| 05-28 01:00 | 35,716,000 | AI_GATE | 0.21 | 0.60 | 3.3 | 5.0 | F | 17 | Rang |
| 05-28 05:00 | 35,824,000 | AI_GATE | 0.10 | 0.60 | 3.3 | 5.0 | F | 16 | Rang |
| 05-28 09:00 | 36,270,000 | AI_GATE | 0.18 | 0.60 | 3.8 | 5.0 | F | 17 | Rang |
| 05-28 13:00 | 36,355,000 | AI_GATE | 0.41 | 0.60 | 4.6 | 5.0 | F | 18 | Rang |
| 05-28 17:00 | 36,260,000 | AI_GATE | 0.30 | 0.60 | 4.6 | 5.0 | F | 19 | Rang |
| 05-28 21:00 | 36,429,000 | EMA | 0.41 | 0.60 | 4.6 | 5.0 | F | 20 | Rang |
| 05-29 01:00 | 36,793,000 | AI_GATE | 0.35 | 0.60 | 3.8 | 5.0 | F | 22 | Rang |
| 05-29 05:00 | 37,350,000 | MISC_RSI | 0.61 | 0.60 | 5.8 | 5.0 | T | 25 | Rang |
| 05-29 09:00 | 37,252,000 | MISC_RSI | 0.81 | 0.58 | 5.8 | 2.8 | T | 28 | Tren |
| 05-29 13:00 | 37,292,000 | MISC_RSI | 0.53 | 0.58 | 5.8 | 2.8 | T | 30 | Tren |
| 05-29 17:00 | 37,292,000 | MISC_RSI | 0.69 | 0.58 | 5.8 | 2.8 | T | 32 | Tren |

### 2023-03-23 01:00 (exit: 트레일링 +8.15%) → 2023-03-23 21:00 (4봉, BTC +4.64%)

Gate 분포: `REGIME_DOWN:4`

| ts | price | gate | xgb | rth | score | sc_th | EMA | ADX | rgm |
|---|---|---|---|---|---|---|---|---|---|
| 03-23 05:00 | 36,372,000 | REGIME_DOWN | 0.11 | 0.60 | 5.8 | 2.8 | T | 32 | Tren |
| 03-23 09:00 | 36,097,000 | REGIME_DOWN | 0.33 | 0.60 | 4.5 | 2.8 | T | 30 | Tren |
| 03-23 13:00 | 36,442,000 | REGIME_DOWN | 0.44 | 0.60 | 5.0 | 2.8 | T | 30 | Tren |
| 03-23 17:00 | 36,301,000 | REGIME_DOWN | 0.35 | 0.60 | 4.5 | 2.8 | T | 29 | Tren |

## C) 병목 Gate 순위 (E2b+6mo 한정)

| gate | n | % |
|---|---|---|
| REGIME_DOWN | 194 | 28.3 |
| AI_GATE | 190 | 27.7 |
| E2_BLOCK | 172 | 25.1 |
| EMA | 95 | 13.9 |
| COOLDOWN | 12 | 1.8 |
| MISC_RSI | 10 | 1.5 |
| SCORE | 6 | 0.9 |
| PASS | 5 | 0.7 |
| MISC_BB | 1 | 0.1 |

## D) 시나리오 판정 (독립 solo-pass 기준)

기준: 각 gate 해제 시 _신규 PASS 증가_ 봉 수로 판정 (단독 병목 측정).

| 시나리오 | gate | 신규 PASS | 판정 |
|---|---|---|---|
| A: EMA 정배열 대기 | EMA | +14 | 🟡 부분 (10~29 봉) |
| B: 쿨다운 (손절 후 1봉) | COOLDOWN | +5 | 🔴 기여 미미 |
| C: Score 하락 | SCORE | +11 | 🟡 부분 (10~29 봉) |
| D: AI Gate | AI_GATE | +10 | 🟡 부분 (10~29 봉) |
| E: E2 차단 (의도된 안전) | E2_BLOCK | +5 | 🔴 기여 미미 |
| F: Regime Down (의도된 안전) | REGIME_DOWN | +13 | 🟡 부분 (10~29 봉) |
| G: RSI/BB 필터 | MISC_RSI | +11 | 🟡 부분 (10~29 봉) |

## E) v21 후보 백테스트 설계 제안

- 🟡 **시나리오 C (Score)** → 회복기 한정 `RANGE_NEW_SCORE_TH` 5.0→4.5 grid (userMemory ‘EMA AND 금지’ 제약 밖, Score 별 축)
- 🟡 **시나리오 B (쿨다운)** → `COOLDOWN_STOPLOSS_BARS` 1→0 백테스트 GO
- ⚪ **E2_BLOCK / REGIME_DOWN 은 의도된 안전 장치** — 완화 시 2022 BEAR 방어 훼손 (#42 결과). 예외 경로 (O3) 는 이미 작동 중이나 확장 고려 가능
- 🔍 **03-09 → 03-15 +13.37% gap** 은 **E2_BLOCK 18봉** 이 주범 (O3 예외 미발동). O3 signal 조건 (20-bar low + 0.5% recovery) 이 3월 하락·반등 패턴을 놓친 케이스 — O3 threshold 완화 별도 연구 후보

## F) GO/NO-GO 종합

🟡 **소규모 개선 여지** (14 봉) → 제한적 v21 실험 GO

**요약**: 2023 gap 병목의 본질은 (E2_BLOCK + REGIME_DOWN) 52% = 의도된 안전 장치이므로 완화 시 BEAR 방어 훼손. 해결 가능한 gate (AI/EMA/Score/쿨다운)는 부분적 개선만 가능.

## G) 전체 Gap 리스트 (케이스별, 시간순)

### E2b+6mo (18 gaps)

| exit_ts | exit_reason | gap_bars | BTC%p | top_gate | gate 분포 |
|---|---|---|---|---|---|
| 2023-01-31 01:00 | 트레일링 +32.38 | 12 | +3.41 | AI_GATE | AI_GATE:7|REGIME_DOWN:5 |
| 2023-02-10 01:00 | ATR손절 -3.96 | 42 | +6.71 | REGIME_DOWN | REGIME_DOWN:25|EMA:7|AI_GATE:6|MISC_RSI:3|COOLDOWN:1 |
| 2023-03-03 09:00 | 계단손절 -3.61 | 26 | +0.00 | REGIME_DOWN | REGIME_DOWN:17|AI_GATE:5|EMA:3|COOLDOWN:1 |
| 2023-03-09 05:00 | ATR손절 -2.94 | 34 | +13.37 | E2_BLOCK | E2_BLOCK:18|REGIME_DOWN:9|MISC_RSI:3|AI_GATE:2|COOLDOWN:1|EMA:1 |
| 2023-03-23 01:00 | 트레일링 +8.15 | 4 | +4.64 | REGIME_DOWN | REGIME_DOWN:4 |
| 2023-04-20 17:00 | 트레일링 -0.11 | 41 | +2.49 | REGIME_DOWN | REGIME_DOWN:21|EMA:12|AI_GATE:7|COOLDOWN:1 |
| 2023-05-08 17:00 | 트레일링 -3.77 | 2 | -0.54 | COOLDOWN | COOLDOWN:1|EMA:1 |
| 2023-05-12 09:00 | ATR손절 -3.80 | 39 | +0.62 | AI_GATE | AI_GATE:21|REGIME_DOWN:13|EMA:4|COOLDOWN:1 |
| 2023-05-25 09:00 | ATR손절 -3.19 | 26 | +5.08 | AI_GATE | AI_GATE:9|REGIME_DOWN:7|EMA:5|MISC_RSI:4|COOLDOWN:1 |
| 2023-06-01 09:00 | ATR손절 -3.07 | 85 | -8.74 | REGIME_DOWN | REGIME_DOWN:42|AI_GATE:25|EMA:16|COOLDOWN:1|SCORE:1 |
| 2023-07-10 13:00 | 트레일링 +21.17 | 140 | -3.41 | AI_GATE | AI_GATE:81|EMA:39|REGIME_DOWN:18|SCORE:2 |
| 2023-08-17 21:00 | 트레일링 -1.28 | 75 | -2.15 | E2_BLOCK | E2_BLOCK:58|REGIME_DOWN:7|AI_GATE:5|EMA:4|COOLDOWN:1 |
| 2023-09-01 01:00 | ATR손절 -3.78 | 83 | +0.42 | E2_BLOCK | E2_BLOCK:78|REGIME_DOWN:4|COOLDOWN:1 |
| 2023-09-21 21:00 | 계단손절 -1.00 | 43 | +1.48 | E2_BLOCK | E2_BLOCK:18|AI_GATE:13|REGIME_DOWN:5|SCORE:3|EMA:2|COOLDOWN:1|MISC_BB:1 |
| 2023-11-15 09:00 | 계단손절 +25.80 | 3 | +6.05 | REGIME_DOWN | REGIME_DOWN:3 |
| 2023-12-11 09:00 | 트레일링 +16.62 | 15 | +1.18 | REGIME_DOWN | REGIME_DOWN:7|PASS:5|AI_GATE:3 |
| 2023-12-18 09:00 | ATR손절 -5.31 | 1 | +0.09 | COOLDOWN | COOLDOWN:1 |
| 2023-12-26 21:00 | 트레일링 +0.98 | 14 | +0.20 | REGIME_DOWN | REGIME_DOWN:7|AI_GATE:6|EMA:1 |

### M2/AY (18 gaps)

| exit_ts | exit_reason | gap_bars | BTC%p | top_gate | gate 분포 |
|---|---|---|---|---|---|
| 2023-01-31 01:00 | 트레일링 +32.38 | 12 | +3.41 | AI_GATE | AI_GATE:7|REGIME_DOWN:5 |
| 2023-02-10 01:00 | ATR손절 -3.96 | 44 | +7.59 | REGIME_DOWN | REGIME_DOWN:25|AI_GATE:8|EMA:7|MISC_RSI:3|COOLDOWN:1 |
| 2023-03-03 09:00 | 계단손절 -3.61 | 26 | +0.00 | REGIME_DOWN | REGIME_DOWN:17|AI_GATE:5|EMA:3|COOLDOWN:1 |
| 2023-03-09 05:00 | ATR손절 -2.94 | 34 | +13.37 | E2_BLOCK | E2_BLOCK:18|REGIME_DOWN:9|MISC_RSI:3|AI_GATE:2|COOLDOWN:1|EMA:1 |
| 2023-03-23 01:00 | 트레일링 +8.15 | 5 | +4.32 | REGIME_DOWN | REGIME_DOWN:4|AI_GATE:1 |
| 2023-04-20 17:00 | 트레일링 -2.48 | 41 | +2.49 | REGIME_DOWN | REGIME_DOWN:21|EMA:12|AI_GATE:7|COOLDOWN:1 |
| 2023-05-08 17:00 | 트레일링 -3.77 | 2 | -0.54 | COOLDOWN | COOLDOWN:1|EMA:1 |
| 2023-05-12 09:00 | ATR손절 -3.80 | 104 | +2.68 | AI_GATE | AI_GATE:57|EMA:22|REGIME_DOWN:20|MISC_RSI:4|COOLDOWN:1 |
| 2023-06-01 09:00 | ATR손절 -3.07 | 85 | -8.74 | REGIME_DOWN | REGIME_DOWN:42|AI_GATE:25|EMA:16|COOLDOWN:1|SCORE:1 |
| 2023-07-10 13:00 | 트레일링 +21.17 | 140 | -3.41 | AI_GATE | AI_GATE:81|EMA:39|REGIME_DOWN:18|SCORE:2 |
| 2023-08-17 21:00 | 트레일링 -1.28 | 75 | -2.15 | E2_BLOCK | E2_BLOCK:58|REGIME_DOWN:7|AI_GATE:5|EMA:4|COOLDOWN:1 |
| 2023-09-01 01:00 | ATR손절 -3.78 | 107 | +0.40 | E2_BLOCK | E2_BLOCK:96|REGIME_DOWN:4|AI_GATE:4|SCORE:2|COOLDOWN:1 |
| 2023-09-21 21:00 | 계단손절 -0.95 | 43 | +1.48 | E2_BLOCK | E2_BLOCK:18|AI_GATE:13|REGIME_DOWN:5|SCORE:3|EMA:2|COOLDOWN:1|MISC_BB:1 |
| 2023-10-11 09:00 | 계단손절 -0.77 | 1 | +0.72 | COOLDOWN | COOLDOWN:1 |
| 2023-11-15 09:00 | 계단손절 +25.24 | 3 | +6.05 | REGIME_DOWN | REGIME_DOWN:3 |
| 2023-12-11 09:00 | 트레일링 +16.62 | 16 | +1.20 | REGIME_DOWN | REGIME_DOWN:7|PASS:5|AI_GATE:4 |
| 2023-12-18 09:00 | ATR손절 -5.32 | 1 | +0.09 | COOLDOWN | COOLDOWN:1 |
| 2023-12-26 21:00 | 트레일링 +0.98 | 14 | +0.20 | REGIME_DOWN | REGIME_DOWN:7|AI_GATE:6|EMA:1 |

### E2a (17 gaps)

| exit_ts | exit_reason | gap_bars | BTC%p | top_gate | gate 분포 |
|---|---|---|---|---|---|
| 2023-02-10 05:00 | 트레일링 -0.79 | 41 | +8.01 | REGIME_DOWN | REGIME_DOWN:25|EMA:6|AI_GATE:6|MISC_RSI:3|COOLDOWN:1 |
| 2023-03-03 09:00 | 계단손절 -3.61 | 26 | +0.00 | REGIME_DOWN | REGIME_DOWN:17|AI_GATE:5|EMA:3|COOLDOWN:1 |
| 2023-03-09 05:00 | ATR손절 -2.94 | 34 | +13.37 | E2_BLOCK | E2_BLOCK:18|REGIME_DOWN:9|MISC_RSI:3|AI_GATE:2|COOLDOWN:1|EMA:1 |
| 2023-03-23 01:00 | 트레일링 +8.15 | 4 | +4.64 | REGIME_DOWN | REGIME_DOWN:4 |
| 2023-04-20 17:00 | 트레일링 -0.11 | 41 | +2.49 | REGIME_DOWN | REGIME_DOWN:21|EMA:12|AI_GATE:7|COOLDOWN:1 |
| 2023-05-08 17:00 | 트레일링 -3.77 | 2 | -0.54 | COOLDOWN | COOLDOWN:1|EMA:1 |
| 2023-05-12 09:00 | ATR손절 -3.80 | 39 | +0.62 | AI_GATE | AI_GATE:21|REGIME_DOWN:13|EMA:4|COOLDOWN:1 |
| 2023-05-25 09:00 | ATR손절 -3.19 | 26 | +5.08 | AI_GATE | AI_GATE:9|REGIME_DOWN:7|EMA:5|MISC_RSI:4|COOLDOWN:1 |
| 2023-06-01 09:00 | ATR손절 -3.07 | 85 | -8.74 | REGIME_DOWN | REGIME_DOWN:42|AI_GATE:25|EMA:16|COOLDOWN:1|SCORE:1 |
| 2023-07-10 13:00 | 트레일링 +21.17 | 140 | -3.41 | AI_GATE | AI_GATE:81|EMA:39|REGIME_DOWN:18|SCORE:2 |
| 2023-08-17 21:00 | 트레일링 -1.28 | 75 | -2.15 | E2_BLOCK | E2_BLOCK:58|REGIME_DOWN:7|AI_GATE:5|EMA:4|COOLDOWN:1 |
| 2023-09-01 01:00 | ATR손절 -3.78 | 83 | +0.42 | E2_BLOCK | E2_BLOCK:78|REGIME_DOWN:4|COOLDOWN:1 |
| 2023-09-21 21:00 | 계단손절 -1.00 | 43 | +1.48 | E2_BLOCK | E2_BLOCK:18|AI_GATE:13|REGIME_DOWN:5|SCORE:3|EMA:2|COOLDOWN:1|MISC_BB:1 |
| 2023-11-15 09:00 | 계단손절 +25.80 | 3 | +6.05 | REGIME_DOWN | REGIME_DOWN:3 |
| 2023-12-11 09:00 | 트레일링 +16.62 | 15 | +1.18 | REGIME_DOWN | REGIME_DOWN:7|PASS:5|AI_GATE:3 |
| 2023-12-18 09:00 | ATR손절 -5.31 | 1 | +0.09 | COOLDOWN | COOLDOWN:1 |
| 2023-12-26 21:00 | 트레일링 +0.98 | 14 | +0.20 | REGIME_DOWN | REGIME_DOWN:7|AI_GATE:6|EMA:1 |
