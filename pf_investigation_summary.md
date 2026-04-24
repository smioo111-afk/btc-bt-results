# PF 시스템 점검 — 종합 판정

**작성일**: 2026-04-24
**관련 문서**:
- Phase 1: `results/pf_investigation_phase1.md`
- Phase 2: `results/bt_real_pf_penalty_impact.md` + `.csv`
- Phase 3: `results/bt_rolling_ai_pf.md` + `.csv`

---

## Phase 1: 현황 요약

| 항목 | 값 |
|---|---|
| `ai_profit_factor` (status.json) | **0.38** (2026-04-20 학습, 4일 고정) |
| `ai_accuracy / precision / recall` | 0.51 / 0.44 / 0.47 (coin-flip 수준) |
| `dynamic_threshold` | 0.55 (미보정) |
| `trade_count` (SELL only) | **5** |
| `recent_pf` (calc_recent_stats) | **9.47** |
| `win_streak` | 0 (마지막 -0.30%) |
| PERF_LOW_RISK_MULT 적용 여부 | **NO** (현재 pf=9.47 > 1.0) |
| `get_ai_gate_threshold` pf 인자 | **dead arg** — 본문 미사용 |

### 구조적 리스크

- n=5 샘플에 PERF_LOW 레버 의존. 1~3건의 손실로 pf가 1.0 아래 급락 가능.
- THRESHOLD_ADJUST_TRADES=30 하한 존재하나 사이징 감점엔 적용 안 됨.

---

## Phase 2: 실거래 PF 감점 영향 (4 케이스)

### 전체 성과 요약

| 케이스 | pf_penalty_mode | final_eq | CAGR | MDD | 2022 | 2023 | 2024 | 2025 | penalty_n/pk_n | GO? |
|---|---|---|---|---|---|---|---|---|---|---|
| **B0** | `current` | 23.63M | +22.17% | 20.49% | -7.8% | +7.8% | +99.5% | +19.3% | 6/62 (9.7%) | — |
| **P1** | `off` | **24.12M** | +22.75% | **18.85%** | -10.8% | **+13.7%** | +99.5% | +19.3% | 0/62 | 부분 GO¹ |
| **P2** | `guard_30` | **24.12M** | +22.75% | **18.85%** | -10.8% | **+13.7%** | +99.5% | +19.3% | 0/62 (skip 6) | 부분 GO¹ |
| P3 | `shadow_rolling` | 23.14M | +21.57% | 19.45% | -7.2% | +6.4% | +98.7% | +18.0% | 26/62 (41.9%) | NO-GO |

¹ GO 기준 (CAGR≥B0 AND MDD≤21% AND 2022 악화 없음 AND n ±20%) 중 **"2022 악화 없음"만 미충족**.
  - CAGR +0.58%p, MDD -1.64%p, n 동일 → 종합 성과는 명백 우위
  - 2022 BEAR 한정 -3%p 악화 (-7.8% → -10.8%) — 감점이 BEAR 방어에 소량 기여했으나 회복기에서 5.9%p 손해

### 핵심 발견

1. **P1/P2가 동일 결과**: B0가 발동시킨 감점 6건이 **모두 trade_count<30 구간**에서 발생 → `guard_30`으로 완벽 회피. Phase 1 구조 리스크가 52개월 시뮬에서도 그대로 재현됨.
2. **감점이 실제로 CAGR을 +0.58%p / MDD -1.64%p 훔치고 있음**: "방어" 라는 명목의 로직이 52개월 기준으로 net-negative.
3. **2022 BEAR -3%p 악화 vs 2023 회복기 +5.9%p 개선** — 구간 기대값 net positive. 연간 CAGR 기준 우위.
4. **P3 (shadow rolling)** 은 감점 41.9% 초과 발동 → 오히려 CAGR -0.60%p 악화. rolling PF는 감점 신호원으로 부적합.

### Phase 2 권고

**P2 (guard_30) 채택**:
- 프로덕션 `calc_position_size` L858 에 `if trade_count >= 30:` 가드 추가
- 현행 로직 유지하면서 **n<30 구간에서 감점 전면 회피**
- 리스크: 실거래 30건 누적 전까지는 하방 방어 레버 없음 (단, KS auto_recover 20%가 최후 방어막으로 기능)
- 기대 효과: 52개월 시뮬 기준 CAGR +0.58%p, MDD -1.64%p

대안 (적극적): **P1 (감점 OFF)** — P2와 시뮬 결과 동일. n≥30이어도 감점이 구조적으로 net-negative일 가능성. 30건 누적 후 재평가 필요.

---

## Phase 3: rolling AI PF 효과 (4 케이스)

### 전체 성과

| 케이스 | window | final_eq | CAGR | MDD | pf_mean | pf_std | unreliable_bars | avg_thresh |
|---|---|---|---|---|---|---|---|---|
| B0 | static (0.38) | 24.12M | +22.75% | 18.85% | 0.38 | 0.00 | 0 | 0.634 |
| R1 | 200봉 | 24.12M | +22.75% | 18.85% | 2.58 | **4.92** | 168 | 0.656 |
| R2 | 500봉 | 24.12M | +22.75% | 18.85% | 1.60 | 1.41 | 99 | 0.647 |
| R3 | 1000봉 | 24.12M | +22.75% | 18.85% | 1.43 | **0.83** | 52 | 0.641 |

> B0 가 Phase 2 B0 (23.63M) 가 아니라 24.12M인 이유: Phase 3 는 `pf_penalty_mode` 파라미터를 넣지 않아 시뮬 내부 감점 블록이 작동하지 않음 (None 기본). Phase 2 P1/P2 와 동등 상태.

### 핵심 발견

1. **4 케이스 전부 동일 성과**: rolling PF 가 바뀌어도 **진입 행동 동일** (62건, 정확히 같은 거래).
   - 원인: `rth += 0.05` bump 가 발동해도 XGB proba(xp) 가 대체로 충분히 높아 ai_pass 변화 없음.
   - unreliable_bars (R1: 168, R2: 99, R3: 52) 는 존재하나 그 중 실제 진입 시도가 거의 없음.
2. **PF 시계열 변동성은 window 반비례**:
   - R1 (200봉): std 4.92 — 너무 잦은 스윙
   - R2 (500봉): std 1.41 — 적절
   - R3 (1000봉): std 0.83 — 가장 안정
3. **현 static 0.38은 Phase 3 rolling 평균(1.43~2.58) 대비 저평가** — test set 한 번의 불운한 스냅샷이 4일간 유지됨.

### Phase 3 권고

- **직접 성과 개선 효과 없음** (entries identical).
- 그러나 **PERF_DEGRAD 트리거가 켜지면 얘기 달라짐**: 현재 OFF (v20.8.1 AR1) 이라 숨어있지만, 재발 시 static 0.38 은 영구 트리거 상태. rolling PF 로 교체해야 정상 작동.
- **R3 (1000봉) 채택 추천**: std 가장 낮음, 노이즈 최소. 다만 PERF_DEGRAD OFF 중에는 효과 체감 불가 → 향후 PERF_DEGRAD 재활성 검토 시 선행 필수.
- **교체 우선순위 낮음** (현재는 dead param). 단, Phase 2 P2 채택과 함께 진행 가능.

---

## 종합 권고

### 즉시 채택: **Phase 2 P2 (guard_30)**

**프로덕션 변경**:
```python
# btc_bot_v290.py L858
- if 0 < recent_pf < PERF_LOW_PF_THRESHOLD:
+ # trade_count 통계적 유효성 가드 (n<30 이면 감점 스킵)
+ _stats = calc_recent_stats()  # caller 가 이미 호출하면 재사용
+ if _stats["trade_count"] >= THRESHOLD_ADJUST_TRADES and 0 < recent_pf < PERF_LOW_PF_THRESHOLD:
      risk_pct *= PERF_LOW_RISK_MULT
```

또는 간단히 상수 비교:
```python
# 호출부에서 trade_count 를 calc_position_size 인자로 넘기거나,
# calc_position_size 에서 calc_recent_stats 재호출 (비용 미미)
```

- 52개월 시뮬 CAGR +0.58%p, MDD -1.64%p
- 단독 트레이드오프: 2022 BEAR 방어 -3%p (다른 구간 +5.9%p 로 상쇄)

### 보류: **Phase 3 R3 (rolling 1000봉)**

- 현재는 효과 중립 (entries 동일).
- PERF_DEGRAD 재활성 논의가 나올 때 선행 필수 과제로 재평가.
- 당장 적용 시 장점 없음, 리스크도 없음 → **PERF_DEGRAD 관련 다음 개선과 묶음 처리**.

### 추가 검증 필요 항목

1. **`get_ai_gate_threshold` pf 인자 제거 (cosmetic)**: L706 시그니처에서 `pf` dead arg. 호출부 3곳 수정 필요 (L1819, 1910, 1947 추정). 영향 없으나 코드 위생.
2. **WIN_STREAK 보너스 조건도 통계 유효성 검토**: `recent_pf ≥ 1.2` 조건이 n=5에서도 쉽게 만족. 동일한 guard 적용 여부 논의.
3. **Kill Switch min_trades=20 vs THRESHOLD_ADJUST_TRADES=30 불일치**: KS는 20건이면 PF 기반 발동, 사이징 감점은 (guard 채택 후) 30건부터 — 임계가 다름. 의도된 것인지 확인.

### 리스크

- **Phase 2 P2 채택 시 BEAR 초반 방어 일시 약화**: 30건 누적 전엔 완화 레버 없음. 단, KS auto_recover 20% MDD 가드는 남아있음.
- **통계적 유효성은 52개월 시뮬 (실거래 아님)**: 시뮬 n=62 건의 분포가 실제 라이브 거래와 다를 가능성.

---

## 파일 체크리스트

- [x] `backtest/results/pf_investigation_phase1.md`
- [x] `backtest/results/bt_real_pf_penalty_impact.md`
- [x] `backtest/results/bt_real_pf_penalty_impact.csv`
- [x] `backtest/results/bt_rolling_ai_pf.md`
- [x] `backtest/results/bt_rolling_ai_pf.csv`
- [x] `backtest/results/pf_investigation_summary.md` (본 문서)
- [x] `backtest/scripts/bt_real_pf_penalty_impact.py`
- [x] `backtest/scripts/bt_rolling_ai_pf.py`
- [x] simulator.py: `pf_penalty_mode` / `ai_pf_mode` cfg 추가 (기본 None, 후방호환)
