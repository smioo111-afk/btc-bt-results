# 시뮬레이터 _auto_reinvest 포팅 로그

**작성일**: 2026-04-18
**대상**: `backtest/core/simulator.py` (공통 시뮬레이터)
**원본**: `btc_bot_v203.py` L1934~2050 `_auto_reinvest` 메서드

---

## 1. 포팅 범위

### 추가된 로직 (v19.1)

프로덕션의 자동 잔액 추가 투입(Reinvest)을 공통 시뮬레이터에 복제.

**발동 조건 (AND)**:
1. 보유 중 (`position > 0`)
2. `active_strategy == "P2"` (pyramid, 프로덕션의 `entry_type=="pyramid"`)
3. `pyramid_level >= 1` (TP1 이후)
4. `rid == 1` (Trend_Up, 프로덕션의 `market_state=="Trend_Up"`)
5. `ema_ok` (EMA 정배열)
6. `price >= avg_entry_price × 1.02` (수익 +2% 이상)
7. AI Gate 통과 (`xp >= rth or xp >= dth`, 진입 블록과 동일 로직)
8. Daily Loss OK (peak_daily 대비 하락이 DAILY_LOSS_LIMIT 이내)

**H-2 동일 캔들 차단**:
- 상태 변수 `last_pyr_add_ai` 추가
- 피라미딩 추가매수 체결 시 `last_pyr_add_ai = ai` 기록 (infinite/legacy 양쪽)
- Reinvest 진입 전 `last_pyr_add_ai == ai`이면 스킵 → `stats["reinvest_skip_h2"] += 1`

**금액 계산**:
- `total_assets = equity + position × price`
- `add_krw = min(equity × 0.95, total_assets × REINVEST_MAX_RATIO)` (REINVEST_MAX_RATIO=0.20)
- 최소: `MIN_ORDER_KRW` (6000)

**체결 효과**:
- `aq_r = add_krw / price`
- `total_cost += add_krw × (1 + COST_RATE)`
- `equity -= add_krw × (1 + COST_RATE)`
- `position += aq_r`
- `avg_entry_price = total_cost / position`
- `pending["reinvest_count"] += 1` (trade record 태깅)

### 코드 삽입 위치

`core/simulator.py` 내 홀딩 페이즈 P2 블록 직후, exit trigger (L379 `if reason:`) 직전.

### 신규 state / stats

- `last_pyr_add_ai`: int, -1 초기화, `_reset()`에서 -1로 복귀
- `REINVEST_MAX_RATIO`, `REINVEST_PROFIT_TH` 상수
- `stats["reinvest_adds"]`: 발동 성공 횟수
- `stats["reinvest_amount_sum"]`: 총 투입 금액 합계
- `stats["reinvest_skip_h2"]`: 동일 캔들 스킵
- `stats["reinvest_skip_gate"]`: AI Gate/Daily Loss 스킵
- `stats["reinvest_skip_amt"]`: 금액 부족 스킵
- `pending["reinvest_count"]`: 거래당 Reinvest 누적 횟수 (trades 레코드로 자동 전파)

---

## 2. 단위 검증

### 세그먼트별 Reinvest 통계 (공통 시뮬, v20.0 설정)

| 구간 | 거래수 | Reinvest 발동 | 투입액 합계 (KRW) | H-2 스킵 | Gate/DL 스킵 | 금액부족 스킵 |
|---|---:|---:|---:|---:|---:|---:|
| IS | 18 | 2 | 607,563 | 0 | 7 | 7 |
| BULL | 22 | 4 | 943,222 | 0 | 3 | 54 |
| BEAR | 22 | 2 | 451,795 | 0 | 7 | 14 |
| **합계** | **62** | **8** | **2,002,580** | **0** | **17** | **75** |

### 주요 관찰

1. **발동 빈도 매우 낮음** (8건/62거래)
   - 금액부족 스킵 75건이 가장 큰 요인 — 초기 80% + 피라미딩 15% = 95% 투입된 상태에서 잔여 equity가 MIN_ORDER_KRW까지 내려갈 가능성
2. **H-2 차단 0건** — 시뮬에서는 동일 캔들 피라미딩과 Reinvest 경쟁이 사실상 발생하지 않음
3. **실전 빈도와 비슷한 수준** — 프로덕션 btc_trade.csv에도 BUY_REINVEST 4건 (04-07~04-18) 기록, 시뮬 BULL 4건과 동일 수준

### 집중 구간 분석 (2024-11-06 ~ 2024-12-22, BULL 280봉 +41.4%)

이 구간 entry 거래 2건:

| entry | exit | pnl | reinvest_count | reason |
|---|---|---:|---:|---|
| 2024-11-15 17:00 | 2024-11-24 17:00 | +3.25% | 2 | 계단손절 |
| 2024-11-28 13:00 | 2024-12-20 01:00 | +10.77% | 0 | 트레일링 |

첫 거래에 Reinvest 2회 발동. 같은 구간 B&H +41.4% 대비 시스템 합산 ~+14% (캡처율 ~34%) — Reinvest 효과에도 불구하고 여전히 큰 격차.

---

## 3. 회귀 테스트 (포팅 전 vs 포팅 후)

### 공통 시뮬 기반 백테스트 #21

| 구간 | 포팅 전 | 포팅 후 | Δ |
|---|---:|---:|---:|
| IS | +12.98% | +12.85% | -0.13%p |
| BULL | +23.81% | **+24.08%** | **+0.27%p** |
| BEAR | +6.00% | +5.93% | -0.07%p |

**회귀 판정**: 모두 1%p 이하 미세 변동. 규정 차이(10%p 이하) 범위 내 → **통과**.

### 공통 시뮬 기반 bt_regime_gate

| Case | BULL 포팅 전 | BULL 포팅 후 | Δ |
|---|---:|---:|---:|
| B0 | +23.81% | +24.08% | +0.27%p |
| A1 | +13.65% | +13.97% | +0.32%p |
| A2 | +10.79% | +10.58% | -0.21%p |
| A3 | +8.59% | +8.89% | +0.30%p |

판정 불변: **A1/A2/A3 모두 기각** (A1만 1/5→2/5로 소폭 개선되었으나 여전히 기각).

---

## 4. 영향 범위 분석

### 공통 시뮬 사용 스크립트 (포팅 영향 받음)

| 스크립트 | 백테스트 번호 | 재실행 필요 |
|---|---|---|
| `backtest_v20_validation.py` | #21 | ✅ 완료 |
| `backtest_regime_gate.py` | (신규) | ✅ 완료 |
| `backtest_exit_pyramid_B.py` | #17-B | (향후 필요 시) |
| `backtest_22_pyramid_o3.py` | #22 | (향후 필요 시) |
| `backtest_23_step_stop.py` | #23 | (향후 필요 시) |
| `backtest_external_data.py` | #18 | (향후 필요 시) |

### 독자 시뮬레이터 사용 (포팅 영향 **없음**)

| 스크립트 | 백테스트 번호 |
|---|---|
| `backtest_exit_pyramid.py` | #17 (원본) |
| `backtest_v20_combined.py` | #20 |

→ 이 두 스크립트는 자체 `simulate_v2()`/`simulate_v20()` 함수를 보유. 동일 포팅을 적용하려면 추가 작업 필요. 본 작업 범위 밖.

---

## 5. 판정 (요구사항 5단계 기준)

**B&H 격차 감소 폭**: **소폭** (캡처율 BULL 31.6% → 31.9%, 거의 변화 없음)

→ 요구사항 5단계의 세 가지 시나리오 중 **"Reinvest 영향 미미, 구조적 문제 다른 곳"**에 해당

### 핵심 결론

1. **시뮬레이터 vs 프로덕션 정합성**: ✅ Reinvest 로직 포팅으로 구조적 불일치 해소
2. **BULL 언더퍼폼 원인이 Reinvest인가**: ❌ 아님 — 발동 빈도·금액 모두 제한적으로 격차 설명 불가
3. **공통 시뮬 결과 신뢰도**: 소폭 상향 (포팅 전 결과도 실제로는 실전 근접했음)

### 후속 조사 방향

Reinvest가 BULL 격차의 주 요인이 아니라면:
- **사이징 정책**: 초기 80% + 피라미딩 15% = 95% 투입. 프로덕션이 더 보수적으로 진입하는지 실전 BUY 로그 비교 필요
- **AI Gate 동적 임계**: 시뮬의 `get_xgb_th + DYN_PCT`와 프로덕션의 `get_ai_gate_threshold`가 다를 가능성
- **MR (평균회귀) 조건 차이**: MR 진입 빈도와 평균 PnL이 격차 기여도 점검 필요
- **실전 손익률 vs 시뮬 손익률 per-trade 대조**: 실전 CONFIRMED 17건 vs 시뮬 62건 분포 비교

---

## 6. 주의 — 백테스트 결론 재평가 필요 여부

Reinvest 영향이 ≤1%p 수준이므로 **과거 백테스트 결과의 전략 채택 판단은 유지**:
- #17-B의 C2 채택 권고 유효
- #20 K2 김프 채택 유효
- bt_regime_gate A1/A2/A3 전부 기각 유효

단, 새 백테스트 작성 시 공통 시뮬은 Reinvest 포함된 버전으로 돌아감을 전제해야 함.

---

## 7. 산출물

- `backtest/core/simulator.py` (Reinvest 로직 추가, +60L)
- `backtest/unit_verify_reinvest.py` (단위 검증 스크립트)
- `backtest/results/backtest_v20_validation.md` (재실행 갱신)
- `backtest/results/bt_regime_gate_result.md` (재실행 + 해석 섹션 갱신)
- `backtest/results/sim_reinvest_porting_log.md` (본 문서)
- improvement_todo.md: "시뮬레이터 vs 프로덕션 구조적 불일치 조사" 항목 진행 상태 갱신 대상
