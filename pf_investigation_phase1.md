# Phase 1: PF 시스템 선행 확인

**작성일**: 2026-04-24
**대상 파일**: `btc_bot_v290.py` (v20.9.4)
**trade log 실제 경로**: `btc_trade.csv` (`btc_trade_log.csv` 아님 — 지시서 오타)

---

## 1. status.json 필드 덤프

| 필드 | 값 | 해석 |
|---|---|---|
| `ai_profit_factor` | **0.38** | 학습 시점 test set 가상 PF. Precision/Recall 수준과 일관 (모델 품질 낮음) |
| `ai_precision` | 0.44 | coin-flip 수준 |
| `ai_recall` | 0.47 | |
| `ai_accuracy` | 0.51 | |
| `ai_last_train_dt` | 2026-04-20T05:45:20+09:00 | 4일 전 학습. 매 30캔들 재학습 정책 (+ regime change) |
| `dynamic_threshold` | 0.55 | 기본값 유지 (보정 안 됨) |
| `threshold_calibrated_at` | 0 | Threshold 자동 보정 1회도 발동 안 됨 (30거래 미달) |
| `consecutive_train_rejects` | 0 | AR3 롤백 가드 발동 없음 |
| `last_retrain_accepted` | True | 최근 재학습 채택됨 |

**해석**: 학습 시점 PF 0.38은 XGB가 거의 coin-flip 수준임을 의미. 단, 이 PF는 **ai_engine 내부 학습 메트릭**일 뿐, 사이징 감점에 쓰이는 `recent_pf` 와는 다른 변수.

---

## 2. trade_log.csv 실거래 카운트

```
파일: /root/tradingbot/btc_trade.csv
총 라인: 19 (헤더 포함 → 실제 18 이벤트)
SELL+SELL_PARTIAL 총합: 7 (grep -c SELL)
SELL (action == "SELL") 만: 5
```

### 최근 SELL 5건 (calc_recent_stats가 실제 집계)

| 날짜 | reason | 실질 PnL |
|---|---|---|
| 2026-04-07 02:04 | 수동매도(전량) | **+0.33%** |
| 2026-04-08 13:01 | 수동매도(전량) | +0.40% |
| 2026-04-12 11:05 | 수동매도(전량) | +0.03% |
| 2026-04-14 23:39 | 수동매도(전량) | +2.08% |
| 2026-04-19 18:52 | 인트라캔들하드스톱 | **-0.30%** |

- 5건 중 4건 수동매도 (자동화 외 개입), 1건 자동. 통계적 유의성 없음.
- 마지막 거래가 -0.30% 손실 → **win_streak = 0**

---

## 3. calc_recent_stats 수동 실행 결과

로직을 네트워크 import 없이 복제 실행 (btc_bot_v290.py L796-819 동일):

```
n=5:  {'winrate': 0.80, 'win_streak': 0, 'pf': 9.467, 'trade_count': 5}
n=10: {'winrate': 0.80, 'win_streak': 0, 'pf': 9.467, 'trade_count': 5}
n=30: {'winrate': 0.80, 'win_streak': 0, 'pf': 9.467, 'trade_count': 5}
```

(n이 다르더라도 SELL 총 5건뿐이므로 동일.)

**PF 계산 검증**:
- gains = 0.33 + 0.40 + 0.03 + 2.08 = 2.84
- losses = 0.30
- pf = 2.84 / 0.30 = **9.47**

---

## 4. 최근 사이징 로그 분석 (PERF_LOW_RISK_MULT 적용 흔적)

`/root/tradingbot/btc_bot.log` 중 2026-04-20 이후 `포지션:` 로그 28건 분석.

### 주요 구간

| 구간 | risk_pct 범위 | 비고 |
|---|---|---|
| 2026-04-20 (08:00~20:00) | **0.50%** (4회) | AI 0.23~0.53, Score 5.1~5.9. **하한 clip (0.005=0.5%) 에 걸림** — AI 낮음(-0.003) + regime Volatile/Range base(1.0~1.5%) 조합 |
| 2026-04-21~24 (신규 포지션) | **1.40~1.96%** (24회) | AI 0.44~0.69, Trend_Up regime base 2.0%. 보너스/페널티 조정 후 값 |

### PERF_LOW_RISK_MULT 적용 여부 역산

2026-04-21 새벽 예시: `risk_pct:1.96%` @ AI 0.69, Score 5.1
- Trend_Up base = 2.0%
- AI 0.69 ≥ CONF_HIGH_THRESH(0.70)? 아니오 → interpolation: r = (0.69-0.58)/(0.70-0.58) = 0.917 → risk += -0.003 + 0.917*0.006 = **+0.0025**
- Score 5.1 ≥ 5.0 → +0.002
- 소계: 2.0% + 0.25% + 0.2% = **2.45%**
- clip(0.025=2.5%) 내 → 2.45%
- **PERF_LOW_MULT 미적용**: 2.45%이나 실제 로그 1.96%. 차이는 MAX_POSITION_RATIO(0.60) 제약으로 역산 시 risk_pct가 표시값까지 내려갔을 수 있음.

핵심: **PERF_LOW_MULT 적용 시 기대 risk_pct는 절반 (예: 1.0~1.2%)** 이어야 하나, 실제 로그는 1.40~1.96% → 미적용 확증.

---

## 5. get_ai_gate_threshold (L705-717) 분석

```python
def get_ai_gate_threshold(ai_reliable, market_state, cons_loss,
                           win_streak, winrate, pf, dynamic_thresh=None):
    base = AI_GATE_THRESHOLD if ai_reliable else AI_UNRELIABLE_GATE
    if dynamic_thresh is not None and dynamic_thresh != AI_GATE_THRESHOLD:
        base = dynamic_thresh if ai_reliable else max(dynamic_thresh, AI_UNRELIABLE_GATE)
    if market_state == "Volatile":
        base = max(base, MARKET_VOLATILE_GATE)
    elif market_state == "Range":
        base = max(base, MARKET_RANGE_GATE)
    if cons_loss >= MAX_CONSECUTIVE_LOSS:
        base = max(base, LOSS_MODE_GATE)
    return float(np.clip(base, MIN_THRESH, MAX_THRESH))
```

**PF 인자는 시그니처에 있으나 함수 본문에서 사용되지 않음 (dead arg)**.

PF가 실제 행동에 영향을 주는 곳:
1. `calc_position_size` L858: `0 < recent_pf < 1.0` → `risk_pct *= 0.5`  (현 이슈)
2. `calc_position_size` L853-856: win_streak 보너스 조건에 `recent_pf >= WIN_STREAK_MIN_PF(1.2)` 포함
3. Kill Switch: `calc_recent_stats(n=KILL_SWITCH_MIN_TRADES=20)` 의 pf를 `pf < KILL_SWITCH_PF(0.7)` 로 체크 (n<20이면 발동 안 됨)

**결론**: `get_ai_gate_threshold` 의 pf 인자는 호출부에서 전달하지만 실제 threshold 조정엔 무관. 지시서의 "pf 인자가 threshold 계산에 어떻게 쓰이는지" → **쓰이지 않음** (dead code).

---

## 사이징 감점 현재 적용 여부 판정

### **NO (확인됨)**

| 근거 | 값 |
|---|---|
| `recent_pf` (현재) | **9.47** |
| `PERF_LOW_PF_THRESHOLD` | 1.0 |
| 발동 조건 `0 < pf < 1.0` | **False** |
| 최근 로그 risk_pct | 1.40~1.96% (Trend_Up base 2.0% 근처, 감점 없음) |

### 그러나 구조적 리스크

- **n=5 전적**: 마지막 거래가 이미 손실 (-0.30%). win_streak = 0.
- 추가 손실 1~2건 시 pf가 1.0 아래로 급락 가능:
  - 현재 gains=2.84, losses=0.30
  - 만약 다음 2건이 각각 -1.0%면: gains=2.84, losses=2.30 → pf=1.23 (감점 직전)
  - 3건 연속 -1.0% 시: losses=3.30 → pf=0.86 → **감점 발동**
- 통계적 유의성 전혀 없음 (n=5). 한 건의 손실이 레버를 뒤집음.

### WIN_STREAK 보너스도 실질 dead

- 조건: win_streak ≥ 3 AND winrate ≥ 0.55 AND pf ≥ 1.2
- 현재 win_streak = 0 (최근이 손실). **미발동**.
- 최근 5건 중 연승 최대 4건 (마지막 손실 직전까지 +0.33/+0.40/+0.03/+2.08) 이었으나 현재는 단절.

---

## Phase 2/3 진입 정당성

Phase 1 결과 요약:
- **현재는 감점 미적용** 상태이나 (pf=9.47) → Phase 2 B0 시뮬 결과가 프로덕션 현황과 일치하는지 교차검증 가능.
- **감점 로직 자체가 통계적으로 불안정**: n<30 가드 없이 n=5 샘플로 레버를 흔듦 → Phase 2 P2 (n<30 가드) 가치 있음.
- **ai_engine.profit_factor=0.38** 은 학습 시점 고정값으로 변동 없음 → Phase 3 rolling 변경 시 동적 갱신 효과 측정 가치 있음.

**Phase 2 + Phase 3 전부 진행**.
