# PF 프로덕션 로그 감사 보고서

**작성일**: 2026-04-24
**목적**: Phase 2 P2 채택 전 시뮬 결론의 프로덕션 실측 검증
**방법**: 읽기 전용 로그/CSV/코드 분석

---

## 1. 조사 범위

| 항목 | 값 |
|---|---|
| 주요 로그 파일 (활성) | `btc_bot.log` (236KB, 2026-04-19 ~ 04-24) |
| 주요 로그 파일 (아카이브) | `archive_2026-04-21/old_logs/btc_bot.log.1` (10MB, 2026-03-23 ~ 04-19) |
| **통합 커버리지** | **2026-03-23 ~ 2026-04-24 (약 32일)** |
| `btc_trade.csv` | 19 행 (BUY 13 + SELL 5 + SELL_PARTIAL 2) |
| `btc_retrain_history.csv` | 1 행 (2026-04-24, AR3 거부 이벤트 단독) |
| 구 버전 로그 (참고 제외) | `logs_archive/btc_ai_bot.log` (v5.3, 2026-02-23) |

**주요 이벤트 수**:
- `포지션:` (사이징 로그): **721 건**
- `AI Gate: 통과/차단`: 통과 많음 (활성 로그만 2019/99)
- `AI 복원` (재시작): 141 건 (33일간, 하루 평균 ~4회)
- `학습 완료`: 7 건 (4/10 ~ 4/20)
- `SELL` (전량 청산, 실질 pnl 추출 가능): **5 건**

---

## 2. 사이징 거동 분석

### 2.1 `risk_pct` 분포 (721 이벤트)

| 구간 | 건수 | 비율 |
|---|---|---|
| **0.50% (clip low)** | **285** | **39.5%** |
| 0.50 ~ 0.75% | 81 | 11.2% |
| 0.75 ~ 1.00% | 37 | 5.1% |
| 1.00 ~ 1.25% | 46 | 6.4% |
| 1.25 ~ 1.50% | 168 | 23.3% |
| 1.50 ~ 1.75% | 89 | 12.3% |
| 1.75 ~ 2.00% | 5 | 0.7% |
| > 2.00% | 10 | 1.4% |

- **Mean**: 0.952% / **Median**: 0.600% / **Stdev**: 0.482%
- **Min**: 0.500% (→ MIN clip) / **Max**: 2.500% (→ MAX_RISK_PCT clip)
- 전체 69.5% 이벤트가 **1.25% 이하** (절대 다수가 Volatile/Range regime + AI 낮은 상태)

### 2.2 일자별 평균 `risk_pct` (변곡점 있는 날)

| 날짜 | n | mean | min | max | 패턴 |
|---|---|---|---|---|---|
| 03-27 ~ 03-29 | 186 | 0.54% | 0.50 | 0.60 | 저위험 구간 지속 |
| 03-30 | 54 | 0.93% | 0.50 | 1.40 | regime 상승 전환 |
| 03-31 ~ 04-01 | 96 | 1.56% | 1.40 | 1.60 | Trend_Up 지속 |
| 04-07 | 7 | **2.43%** | 2.38 | **2.50** | AI 고신호 (MAX clip) |
| 04-12 ~ 04-13 | 9 | 0.50% | 0.50 | 0.50 | 저신호 |
| 04-20 | 6 | 0.50% | 0.50 | 0.50 | 저신호 |
| 04-21 ~ 04-24 | 22 | 1.48% | 0.70 | 1.96 | Trend_Up 복귀 |

### 2.3 PERF_LOW_RISK_MULT 발동 이력

**프로덕션 로그 전체 통해 `recent_pf < 1.0` 발동 증거 0건**.

검증 절차:
1. 인접 라인간 `risk_pct` 절반 이하 급락 + AI 동일 이벤트 검색 → **1건 매치**
2. 매치 라인(2026-04-22 12:00 → 16:00, 1.40% → 0.70%) 컨텍스트 확인:
   - 12:00 market_state = **Range** (base 1.5%)
   - 16:00 market_state = **Volatile** (base 1.0%, 14:25 Regime 전환)
   - 추가로 Score 5.1 → 4.9 (+0.002 보너스 소실)
   - **결론**: Regime 전환 + Score 변화로 완전히 설명됨. PERF_LOW 아님.
3. `grep -i "PERF_LOW\|risk.*0.5\|risk.*감점"` → **0 건**
4. `recent_pf` 역산: 4/19 마지막 SELL 이후 SELL 추가 없음. `pnls = [+0.33, +0.40, +0.03, +2.08, -0.30]` → **pf = 9.47** 유지. 발동 조건(pf<1.0) 단 하루도 충족 안 됨.

**→ Phase 1 판정 (감점 미적용) 실측 확증**.

### 2.4 기타 사이징 이벤트

| 로직 | 상수 | 발동 건수 | 비고 |
|---|---|---|---|
| PERF_LOW_RISK_MULT | × 0.5 | **0** | recent_pf=9.47 상시 |
| LOSS_MODE_POS_MULT | × 0.3 | **0** | cons_loss 3+ 기록 없음 |
| WIN_STREAK 보너스 | +0.002 | **0** | win_streak 3+ 기록 없음 |
| Kimchi 김프 사이징 | × 0.5 | **불명** (로그에 표시 없음) | — |

---

## 3. AI PF 시계열 (`ai_engine.profit_factor`)

### 3.1 학습 이벤트 (7건)

| 시점 | 트리거 | pre_prec / post_prec | pre_pf → **post_pf** | accepted |
|---|---|---|---|---|
| 2026-04-10 21:00 | 30캔들 / regime | 42.2% → 41.8% | 1.17 → **1.30** | T |
| 2026-04-10 22:33 | 재수행 | 42.2% → 41.8% | 1.17 → **1.20** | T |
| 2026-04-13 08:13 | 30캔들 | 41.8% → 42.6% | 1.20 → **0.79** | T ← **1.0 아래 최초 진입** |
| 2026-04-15 07:12 | 30캔들 | 42.6% → 43.5% | 0.79 → **0.54** | T |
| 2026-04-18 05:01 | 30캔들 | 43.5% → 44.1% | 0.54 → **0.42** | T |
| 2026-04-20 05:45 | 30캔들 | 44.1% → 44.3% | 0.42 → **0.38** | T (현재 status) |
| **2026-04-24 02:40** | Regime (R→V) | 44.3% → 46.7% | 0.38 → 0.10 | **F (AR3 거부)** |

### 3.2 PF 분포 (학습 시점 7샘플)

| 지표 | 값 |
|---|---|
| 평균 | 0.756 |
| 중앙값 | 0.79 |
| 최저 | 0.38 (현재) |
| 최고 | 1.30 |
| **1.0 미만 비율** | **4/7 = 57.1%** |
| **1.0 미만 상태로 경과일** | **2026-04-13 ~ 현재 (11일)** |

### 3.3 Unreliable 모드 상태

- `is_reliable() = (precision >= 0.42 AND profit_factor >= 1.0)` (v290 L1543-1545)
- **2026-04-13 PF=0.79 이후 11일간 `is_reliable()=False`**
- `AI_UNRELIABLE_GATE = 0.62` (reliable 기본 0.55 대비 +0.07 엄격)

---

## 4. Threshold 조정 이력

### 4.1 자동 보정 `_calibrate_threshold`

- 호출 조건: `total_trades < THRESHOLD_ADJUST_TRADES (30)` 미달 시 즉시 return
- 현재 SELL total = 5 → **단 한 번도 조건 충족 안 됨**
- 로그 grep: `"Threshold.*보정\|_calibrate_threshold"` → **0 건**
- `status.threshold_calibrated_at = 0` (한 번도 갱신 안 됨)

### 4.2 실제 AI Gate threshold (로그 distinct 값)

- **Trend_Up: `regime≥0.58` 고정** (923 + 475 + 470 등 전부 0.58)
- `dynamic_th` 만 변동 (0.322 ~ 0.766, XGB 분포에 따라)

---

## 5. 🔴 Critical Defect 발견: `check_ai_gate` threshold arg 미사용

### 증거

`btc_bot_v290.py` L719-729:
```python
def check_ai_gate(xgb_prob, threshold, last_xgb_probs=None, market_state="Trend_Up"):
    regime_th = REGIME_CONFIG.get(market_state, {}).get("xgb_th", XGB_ABS_THRESHOLD)
    if last_xgb_probs and len(last_xgb_probs) >= XGB_DYNAMIC_MIN_SAMPLES:
        dynamic_th = float(np.percentile(last_xgb_probs, XGB_DYNAMIC_PERCENTILE))
    else:
        dynamic_th = regime_th
    ok = (xgb_prob >= regime_th) or (xgb_prob >= dynamic_th)
    logger.info(f"AI Gate: ... (regime≥{regime_th:.2f}|dyn≥{dynamic_th:.3f}) ...")
    return ok
```

- 파라미터 `threshold` 는 **함수 본문 어디에서도 사용되지 않음**.
- `regime_th` (REGIME_CONFIG 하드코드) 와 `dynamic_th` (분위수) 만 사용.

### 영향 범위

**`get_ai_gate_threshold` 출력이 전부 dead code**:
- `AI_UNRELIABLE_GATE (0.62)` — is_reliable=False 시 적용되어야 하나 **무시됨**
- `dynamic_threshold` — status.json의 보정값 **무시됨**
- `LOSS_MODE_GATE (0.65)` — cons_loss≥3 시 적용되어야 하나 **무시됨**
- `MARKET_VOLATILE_GATE (0.65) / MARKET_RANGE_GATE (0.60)` — `get_ai_gate_threshold` 경로 통한 적용 **무시됨** (REGIME_CONFIG 경로로는 작동)
- `pf` 인자 (Phase 1에서 발견) — get_ai_gate_threshold 내부에서도 미사용 → 이중 dead

### 결과적으로

- **ai_engine.profit_factor < 1.0 11일간 is_reliable=False 상태이나 실제 gate 결정에 영향 0**
- 이 구간 프로덕션은 "명목상 unreliable" 이지만 "실질적 gate 동작은 reliable 과 동일"
- 사실상 **Phase 3 백테스트 R1/R2/R3 = B0 동일 결과**가 프로덕션에서도 자동 성립 (threshold 경로 자체가 작동 안 해서)

### Phase 2 결론 영향

- PERF_LOW_RISK_MULT (`calc_position_size` L858) 는 **정상 작동** 경로. check_ai_gate 와 무관.
- Phase 2 P2 (guard_30) 채택 결론 **유효**.

---

## 6. Trade Log 분석 (32일간 실제 거래)

### 6.1 SELL 전수 (5건, 실질 pnl 추출 가능)

| 시점 | price | 사유 | 실질 pnl | Running PF (cumulative) |
|---|---|---|---|---|
| 2026-04-07 02:04 | 104,653,000 | 수동매도(전량) | +0.33% | n=1, pf=inf |
| 2026-04-08 13:01 | 105,706,000 | 수동매도(전량) | +0.40% | n=2, pf=inf |
| 2026-04-12 11:05 | 106,462,000 | 수동매도(전량) | +0.03% | n=3, pf=inf |
| 2026-04-14 23:39 | 111,244,000 | 수동매도(전량) | +2.08% | n=4, pf=inf |
| 2026-04-19 18:52 | 111,354,000 | 인트라캔들하드스톱 | **-0.30%** | n=5, pf=**9.47** |

- `calc_recent_stats` 가드 `len(sells) >= 5` — **5번째 (4/19) 거래 후 처음으로 pf 계산 활성화**
- 4/07 ~ 4/18 기간: 감점 로직은 "pf=0.0 → 발동 안 됨" 경로로 침묵
- 4/19 이후 현재까지: pf=9.47 → 발동 안 됨
- **n=5 ~ n<30 구간에서 PERF_LOW 감점이 실제로 발동한 사례 0건**

### 6.2 손실 거래 1건 특성

- 2026-04-19 18:52: ATR 트레일링 익절 유형이지만 intra-bar 하드스톱 발동 → 표면 +0.00% / 실질 -0.30% (수수료 0.3%p)
- 단일 손실로 pf 2.84/0.30 = **9.47** 에 착지. 추가 손실 2~3건 발생 시:
  - +1 loss (-1.0%): gains 2.84 / losses 1.30 → pf 2.18 (아직 >1.0)
  - +2 loss (-1.0%): losses 2.30 → pf 1.23 (경계)
  - +3 loss (-1.0%): losses 3.30 → pf **0.86 (발동)**
- **트리거링이 실전에서 여전히 가능**하나 P2 guard_30 이면 n<30 구간 완벽 회피.

---

## 7. 이상 거동 / 추가 발견

### 7.1 재시작 141회 (33일간)

- 평균 약 4.3 회/일
- `AI 복원 Prec=X% PF=X` 로그로 카운트
- 1회 종료 → 1회 재시작 페어. 즉 실제 종료/기동 사이클 ~70회
- 원인: systemd 30분 재시작 정책? 지정된 재시작 주기 확인 필요 (부록)
- **운영 영향**: 로그 상 동일 `AI 복원 PF=X`만 찍히고 매매 연속성은 status.json 으로 보존 → 영향 미미

### 7.2 Phase4 / WIN_STREAK / cons_loss 이벤트

- 전부 **0건** (32일 전 기간).
- WIN_STREAK 3+ 기록 자체가 존재 안 함 (최근 4연승 후 4/19 손실로 단절).

### 7.3 표시값 불일치 여부

- 텔레그램/로그에서 `PF:0.38` 표시 = `ai_engine.profit_factor` = `status.ai_profit_factor`. **일치 확인**.
- `calc_recent_stats().pf` 9.47 은 별도 변수로 사용자 노출 로그 없음 (내부 사이징용). 혼동 여지 존재 — 대시보드/리포트에서 구분 명시 필요.

---

## 8. 시뮬 결과와 실측 대조

| 지표 | 시뮬 (Phase 2 B0) | 프로덕션 실측 | 일치? |
|---|---|---|---|
| PERF_LOW 발동 조건 | n<30 구간에 집중 (6/62 = 9.7%) | 32일간 0건 (거래 n=5) | ✅ 방향 일치 (샘플 규모 차이) |
| PERF_LOW 발동 시점 `recent_pf` | < 1.0 (발동 정의) | 현재 9.47 (미발동) | ✅ |
| 평균 `risk_pct` | 시뮬 미기록 | 0.95% (mean), 0.60% (median) | — (시뮬 메트릭 미산출) |
| AI PF 학습 시 평균 | 시뮬 N/A (학습 1회) | 0.756 (7샘플) | — |
| LOSS_MODE 발동 | 시뮬 없음 (cons_loss 모델 미적용) | 0건 | ✅ |
| Threshold 자동 보정 | 시뮬 없음 | 0건 (n<30) | ✅ |
| `ai_reliable=False` 영향 | 시뮬 없음 | **0 (dead code로 무효화)** | ⚠️ 시뮬이 맞출 필요 없음 |

**결론**: 시뮬의 B0 가정 (PERF_LOW 는 n<30 에서도 발동될 수 있음) 은 **프로덕션에서 아직 실증되지 않았으나**, 트리거링 수학적 가능성은 그대로 (+3 loss 이상 누적 시).

---

## 9. P2 적용 시 예상 영향

### 9.1 즉시 영향

- 현재 `recent_pf=9.47` → P2 적용 여부와 무관하게 **감점 발동 안 됨**
- 즉시 배포해도 **현 시점 거동 변화 0**

### 9.2 과거 12개월 역시뮬 — 해당 기간 P2 조건이 달랐을 시점?

- **없음**: SELL 5건 전체가 4/07 ~ 4/19 구간. 4/07 이전 v290 배포 전까지 간격 있음 (v203 등 구 버전).
- v290 배포 이후 SELL <30 지속 → P2 가드가 B0 대비 차이를 낳는 케이스 미발생.

### 9.3 발생 가능 시나리오

향후 경로 3가지 예측:

| 시나리오 | 누적 SELL | recent_pf | B0 행동 | P2 행동 | 차이 |
|---|---|---|---|---|---|
| A: 손실 몰림 | 6~10 | 0.86 예상 | 감점 0.5× | **감점 스킵** | **다름** |
| B: 수익 지속 | 6~10 | >1.0 | 미발동 | 미발동 | 동일 |
| C: 30 도달 후 손실 | ≥30 | <1.0 | 감점 | 감점 (guard 통과) | 동일 |

**핵심**: A 시나리오에서만 P2 와 B0 가 갈림. 시뮬 Phase 2 에서 이 차이가 6/62 = 9.7% 비율로 관찰됨.

### 9.4 BEAR 방어 vs 회복기 캡처 trade-off 실증

- 시뮬: 2022 BEAR -3%p 악화 vs 2023 회복기 +5.9%p 개선
- 프로덕션: 현재 SELL 5건, 32일간 — BEAR 또는 회복기 구간 판정 어려움 (표본 절대 부족)
- **실증 대기**: 30건 누적 (약 6개월 예상) 후 재평가 필요

---

## 10. 권고

### 10.1 즉시 적용 가능 ✅

**Phase 2 P2 (guard_30) 채택 가능** — 실측 기준:
- 현 시점 거동 변화 0 (recent_pf=9.47 >> 1.0)
- 프로덕션 로그에서 **B0 감점 발동 0건** 확인 (32일간) → 즉시 적용이 리스크 없음
- 향후 손실 누적 시 `n<30` 구간에서의 통계적 불안정성 선제 회피

**변경안**:
```python
# btc_bot_v290.py L858
- if 0 < recent_pf < PERF_LOW_PF_THRESHOLD:
+ # v20.9.5: n<30 통계 유효성 가드 (pf_investigation #47)
+ _sell_n = calc_recent_stats(n=1)["trade_count"]  # 총 SELL 수
+ if _sell_n >= THRESHOLD_ADJUST_TRADES and 0 < recent_pf < PERF_LOW_PF_THRESHOLD:
      risk_pct *= PERF_LOW_RISK_MULT
```

또는 caller 에서 trade_count 를 인자로 전달 (설계 더 깨끗).

### 10.2 🔴 별건 긴급: `check_ai_gate` dead arg 수정

**발견 사실**:
- `threshold` 파라미터가 본문 미사용 → `get_ai_gate_threshold` 출력 전체 사용 안 됨
- 결과: 11일간 `is_reliable=False` 상태가 실제 gate 에 영향 0, `dynamic_threshold / LOSS_MODE_GATE / AI_UNRELIABLE_GATE` 모두 dead

**두 가지 선택지**:
1. **기능 복원**: `check_ai_gate` 에서 `threshold` 를 실제 사용하도록 수정 (단, 현재 경로가 대체로 잘 동작 중이라 행동 변화 클 수 있음 — 추가 백테스트 필수)
2. **dead 코드 제거**: `get_ai_gate_threshold` 함수 및 호출 전부 제거 → 실제 동작과 의도 정합

**즉시 권고**: 현재 프로덕션 성과는 "dead code 상태로 운영된 결과" 이므로 섣부른 복원 위험. **백테스트로 threshold 경로 복원 시 영향 측정** (새로운 #49 제안) 후 선택.

### 10.3 추가 모니터링 필요

- [ ] **SELL 카운트 30건 도달 예상 시점** (현재 5, 월 ~5건 추정 → 6~12개월)
- [ ] **Regime 전환 기반 재학습 거부 (AR3) 빈도** — 4/24 1회 발생, PF 0.38→0.10 거부. 주기 관찰
- [ ] **재시작 평균 4.3회/일 원인** — systemd 재시작 정책 또는 OOM/network 원인 확인 (오남용 아닌지)
- [ ] **`ai_profit_factor` 1.0 복귀 조건** — 현재 0.38로 11일 경과, 시장 추세 반전 시 학습 거쳐 회복 대기

### 10.4 발견된 이상 거동

| 항목 | 상태 | 우선순위 |
|---|---|---|
| `check_ai_gate` threshold arg dead | 🔴 Critical | High — 백테스트 후 결정 |
| `get_ai_gate_threshold` pf arg dead | 🟡 Minor | Low — 함수 제거 시 자동 해소 |
| 재시작 141회/32일 | 🟡 확인 필요 | Medium — 원인 진단 |
| `threshold_calibrated_at = 0` (0건) | ⚪ 정상 | Low — n<30 이므로 당연 |
| AI PF <1.0 11일 지속 | 🟡 관찰 | Medium — is_reliable 효과 없음 확인 후 낮은 우선순위 |

---

## 11. 결론 요약

- **Phase 1 판정 유효**: PERF_LOW_RISK_MULT 현재 미적용, 과거 32일간도 0회 발동.
- **Phase 2 P2 채택 안전**: 즉시 배포 가능, 현 시점 거동 변화 0, 향후 손실 누적 시 통계 안정성 확보.
- **🔴 예상치 못한 추가 발견**: `check_ai_gate` threshold 파라미터 dead — 전체 AI 신뢰도/동적 임계/연패 gate 시스템이 **실제로 작동하지 않음**. Phase 3 결과 (entries identical) 가 프로덕션에서 동일 원인으로 발생.
- **긴급성 재평가**: Phase 2 P2 는 즉시 가능, 별건 `check_ai_gate` 결함은 신규 조사 과제로 분리 필요.

---

## 부록 A. 조사 명령 재실행 (참고)

```bash
# 로그 전량 파싱
cat /root/tradingbot/archive_2026-04-21/old_logs/btc_bot.log.1 /root/tradingbot/btc_bot.log | \
    grep "포지션:" > /tmp/sizing_all.log

# 학습 이벤트
grep -E "학습 완료" /root/tradingbot/btc_bot.log \
    /root/tradingbot/archive_2026-04-21/old_logs/btc_bot.log.1

# 재학습 이력 CSV
cat /root/tradingbot/btc_retrain_history.csv

# Trade log
cat /root/tradingbot/btc_trade.csv
```
