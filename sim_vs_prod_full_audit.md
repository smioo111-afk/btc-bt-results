# 시뮬레이터 vs 프로덕션 전체 정합성 점검

**작성일**: 2026-04-19
**프로덕션**: `btc_bot_v207.py` (v20.7, 3777 lines)
**시뮬레이터**: `backtest/core/simulator.py` + 지원 모듈 (`backtest_pyramiding.py`, `backtest_v185_optimize.py`)
**점검 방법**: 2x Explore 에이전트 병렬 + 수동 검증 (에이전트 오류 정정 포함)

---

## 📊 점검 요약

| 영역 | 상태 | 중요도 |
|---|---|---|
| 1. EMA 정배열 | ✅ 일치 | - |
| 2. Score 계산 + 임계 | ✅ 일치 | - |
| 3. Regime 분류 + 히스테리시스 | ✅ 일치 (sim에 구현됨) | - |
| 4. Leading Signal (O3) | ✅ 일치 | - |
| 5. AI Gate | 🟡 부분 일치 | 낮음 (AI Gate OFF 테스트) |
| 6. VWAP 필터 | ✅ 일치 | - |
| 7. 김치 프리미엄 | ✅ 일치 | - |
| 8. 쿨다운 정책 | 🟡 다름 | 중간 |
| 9. 하드스톱 (인트라캔들) | 🟡 구조적 한계 | 중간 |
| 10. 트레일링 stop | ✅ 일치 | - |
| 11. 계단손절 | ✅ 일치 | - |
| 12. Range New 청산 | ✅ 일치 | - |
| **13. Kill Switch** | **🔴 치명적 누락** | **최우선** |
| 14. 일손실 한도 | ✅ 일치 | - |
| 15. MDD 추적 | ✅ 일치 (sim passive) | - |
| 16. Reinvest 정책 | ✅ 일치 (7/7 non-KS 조건) | - |
| 17. 사이징 v20.7 | ✅ 일치 | - |
| 18. 피라미딩 max_lv | ✅ 일치 (infinite 20) | - |

**종합**: 🔴 1건 / 🟡 3건 / ✅ 14건. **Kill Switch 누락이 단일 최대 이슈**.

---

## 🔴 CRITICAL: Area 13 — Kill Switch

### 프로덕션 (btc_bot_v207.py)

**두 가지 트리거**:
- **MDD-based** (L1582 `_update_mdd`): equity가 peak 대비 -20% 이상 시 `status["kill_switch"]=True`
- **PF-based** (L1595 `_check_kill_switch`): 최근 20거래 PF < 0.7 시 동일

**발동 시 동작**:
- 텔레그램 tg_error 경고
- 신규 진입 차단 (L3291 `ks_active` 가드)
- 피라미딩 차단 (L2032)
- Reinvest 차단 (L2190)

**복구**: **자동 복구 없음**. `/killswitch off` 수동 텔레그램 명령어만 해제 (L2544-2552).

### 시뮬레이터

- `peak_eq` / `mdd` 는 passive 추적만 (L169, L276-278)
- **kill_switch boolean 상태 변수 없음**
- **MDD 초과 시 거래 중단 로직 없음**
- **PF-based 체크 없음**

### 영향

**C6 백테스트 28개월에서 발동 분석 (앞선 확인)**:
- MDD 20% 이상 bar: 25개 (4일)
- 발동 구간: 1회 (2024-10-10 05:00)
- 발동 시 equity 12.66M → 실전에선 이 시점에 trading halt
- 발동 후 sim이 계속 진행해 얻은 수익 +66.88% (15건 거래)
- **실전 v20.7 결과는 백테스트 C6 23.97M보다 훨씬 낮게 나올 가능성**

### 우선 조치

1. 시뮬레이터에 Kill Switch 로직 추가 (MDD-based만 우선)
2. 추가 옵션: 자동 해제 로직 (MDD < 10% 회복 시)
3. 재백테스트로 C6 "실전 재현" 값 확인

---

## 🟡 Area 5 — AI Gate

### 프로덕션
- `get_ai_gate_threshold(ai_reliable, market_state, cons_loss, ...)` (L631-643)
- 동적 threshold: regime별 (Volatile/Range/Loss 모드) boost 적용
- MIN_THRESH / MAX_THRESH clipping

### 시뮬레이터
- `bp.get_xgb_th(regime_id, consecutive_losses)` — 단순 regime + loss 조합
- market_state boost 없음, dynamic threshold 없음

### 영향
- **현재 영향 없음**: 모든 v20.x 백테스트는 `patch_ai_gate_off` 적용 (get_xgb_th → 0) 상태
- AI Gate 활성 환경으로 복귀 시 격차 발생

### 조치
- 현재 AI Gate OFF 운용 → 🟢 무시 가능
- 향후 AI Gate 활성화 시 재정합

---

## 🟡 Area 8 — 쿨다운

### 프로덕션 (L327-330)
- `COOLDOWN_ENTRY = 1800s` (30분, 모든 진입 후)
- `COOLDOWN_STOPLOSS = 14400s` (4시간, 손절 후)
- `COOLDOWN_TRAILING = 3600s` (1시간, 트레일링 익절 후)
- `COOLDOWN_SIGNAL = 3600s` (1시간, 수동/신호 매도 후)
- 5개 시간 기반 쿨다운

### 시뮬레이터
- `bp.COOLDOWN_STOPLOSS_BARS = 1` (L81) — 1봉(4h) 손절 쿨다운만
- `cd_bars` 카운터로 관리
- **TRAILING/ENTRY/SIGNAL 쿨다운 없음**

### 영향
- 손절 후: 프로덕션 4h (1봉) 쿨다운, 사실상 거의 같음
- 트레일링 익절 후: 프로덕션 1h, 사실상 한 봉(4h) 내 재진입 없음 → 유사
- 순수 진입 후 1800s ENTRY 쿨다운: 4h봉 기준으로 사실상 무효 (봉 간격 > 쿨다운)

### 실제 영향도
- 4H 봉 기준이라 대부분 쿨다운이 실전과 큰 차이 없음
- **유일한 큰 격차**: 일손실/트레일링 후 재진입 차단 여부 → 미미
- 조치 불요 (sim 단순화 허용)

---

## 🟡 Area 9 — 하드스톱 (인트라캔들)

### 프로덕션 (L1795-1824)
- `_check_hard_stop` 30초 주기 폴링
- `price <= stop_loss` 감지 시 즉시 시장가 매도 (4H 봉 마감 대기 없음)

### 시뮬레이터
- 봉 단위 처리만 (close 기준)
- 인트라 캔들 고점/저점은 MFE 계산용으로만 사용
- 하드스톱 즉시 발동 로직 없음

### 영향
- 인트라 캔들 급락 시 프로덕션은 빠른 손절, 시뮬은 캔들 close까지 대기
- 실제 차이: 봉 low가 stop_loss 찍었다가 close로 회복한 경우 시뮬은 '손절 미발동', 프로덕션은 '손절 체결'
- BEAR 급락장에서 프로덕션이 더 빨리 털고 나옴 → 실전 MDD가 시뮬보다 약간 작을 수 있음

### 조치
- 구조적 한계 (시뮬은 tick 데이터 접근 없음)
- 개선 방법: 봉 low ≤ stop_loss 시 hit 판정 (pessimistic) 추가 가능
- 현 상태: 시뮬이 optimistic → 백테스트는 약간 더 좋게 나옴

---

## ✅ Area 1 — EMA 정배열
- Prod L665: `ema_ok = ema_s > ema_l`
- Sim L288: `ema_ok = bool(entry_ok_a[ai])` (precomputed ema21 > ema55)
- **동일** — sim은 precompute 단계에서 계산

## ✅ Area 2 — Score 계산 + 임계
- 가중치 `SCORE_EMA_4H=1.2 / SCORE_ATR=1.0 / SCORE_VOLUME=0.8 / SCORE_BREAKOUT=0.8 / SCORE_1D_TREND=0.7 / SCORE_RR_*(1.3/0.7) / SCORE_OBV=0.5` (양쪽 동일, `backtest_pyramiding.py` 상수 공유)
- 임계: `ADX_LOW=2.5 / ADX_HIGH=2.8 / RANGE_NEW=5.0` 양쪽 동일
- Sim L699-710 에서 동일 로직 재현

## ✅ Area 3 — Regime 분류 + 히스테리시스
- 프로덕션 `classify_market` (L599-622): 27/23 ADX 회색지대 직전 regime 유지
- 시뮬 `backtest_v185_optimize.py:precompute_v185` L87-108: **같은 로직** (REGIME_HYS_ENTER=27, REGIME_HYS_EXIT=23, 회색지대 prev 유지, DI 방향 반전 시 즉시 전환)
- **완전 동일** (Explore 에이전트 #1의 "sim 히스테리시스 없음" 주장은 오류)

## ✅ Area 4 — Leading Signal (O3)
- 프로덕션 `check_liquidity_sweep` (L852-871): 20봉 저점 undercut 0.2% + 회복 0.5%
- 시뮬 `backtest_o3_ved.precompute_o3` 함수 (동일 로직) → `o3_leading = {"O3": o3}` dict으로 simulate()에 전달
- 시뮬 L666-671에서 `leading_signals` 순회하며 O3 signal 체크
- **일치** (Explore 에이전트 #1의 "sim O3 없음" 주장은 오류. O3a/O3b는 시뮬만의 EMA-bypass 확장 기능, 별도)

## ✅ Area 6 — VWAP 필터
- Prod L3370-3371: `if price <= vwap_val: continue` (Range 제외)
- Sim L716-718: `if not np.isnan(vw) and price <= vw: vp = False` (rid != 0, Range 제외)
- **동일 조건**

## ✅ Area 7 — 김치 프리미엄
- Prod L322-323: KP > 3% 시 사이징 × 0.5
- Sim L145: `kp_sizing = mod["kp_sizing"]` (외부 precompute), L795 `pk *= float(kp_sizing[ai])`
- **동일 효과** (표현만 다름)

## ✅ Area 10 — 트레일링 stop
- 양쪽 동일 공식: `max(high - ATR×trail_m, high × (1 - TRAIL_PCT), entry × (1 - MIN_STOP_PCT))`
- 프로덕션 L802-809 `calc_trailing_stop`, 시뮬 L516-517 (P2 infinite 블록)
- per-position trail_m 각각 status/cfg에서 읽음 — **일치**

## ✅ Area 11 — 계단손절
- 공식: `new_stop = first_entry + (new_lv - step_lookback) × interval`
- Prod L2109-2111, Sim L494 — 동일
- TU/Range 분기도 동일 (pos_step_lookback 우선 → 전역 fallback)

## ✅ Area 12 — Range New 청산
- Prod L1767-1771: `if range_new_mode: return [trailing skip]`
- Prod L2253-2254: `if range_new_mode: return [regime switch skip]`
- Sim L584-585: `and not (RANGE_NEW_ENABLED and entry_regime == "Range")` — 트레일링 skip
- Sim infinite P2 L532-535: 동일 skip
- **일치** — legacy/infinite 양쪽 모두 구현

## ✅ Area 14 — 일손실 한도
- 양쪽 `DAILY_LOSS_LIMIT = 0.05` 동일
- Prod `_check_daily_loss` 실현 손익 파싱 / Sim `peak_daily` vs 현재 — 방법 다르나 threshold 동일, 효과 동일

## ✅ Area 15 — MDD 추적
- 양쪽 `peak = max(peak, equity); mdd = (peak - equity) / peak`
- Prod status 영속화 / Sim in-memory — 계산 로직 **완전 동일**

## ✅ Area 16 — Reinvest 정책 (⚠️ 에이전트 #2 오류 정정)

**실제 구현 상태** (sim L591-629 검증):

| 조건 | Prod | Sim |
|---|---|---|
| 1. P2 pyramid | ✅ | ✅ (`active_strategy == "P2"`) |
| 2. pyramid_level ≥ 1 | ✅ | ✅ (`pyramid_level >= 1`) |
| 3. Trend_Up | ✅ | ✅ (`rid == 1`) |
| 4. EMA 정배열 | ✅ | ✅ (`ema_ok`) |
| 5. price ≥ avg × 1.02 | ✅ | ✅ (`price >= avg_entry_price * REINVEST_PROFIT_TH`) |
| 6. Kill Switch 가드 | ✅ | ❌ (sim에 KS 없음 → Area 13 문제 종속) |
| 7. Daily Loss OK | ✅ | ✅ (`dl_ok_r`) |
| 8. H-2 동일 캔들 가드 | ✅ | ✅ (`last_pyr_add_ai == ai`) |

**결론**: 7/8 조건 일치. Kill Switch 조건만 Area 13 문제와 동일 (종속).
에이전트 #2의 "4/8 조건 누락" 주장은 오류 (실제 코드 L596-619 확인).

## ✅ Area 17 — 사이징 v20.7
- Prod L3408: Range 진입 시 `buy_amount = equity * RANGE_INITIAL_RATIO` (0.70)
- Prod L3403: TU 진입 시 `buy_amount = equity * PYRAMID_INITIAL_RATIO` (0.80)
- Sim L777: `_rg_init = RANGE_INITIAL_RATIO if not None else TRUP_INIT` 분기
- **일치**

## ✅ Area 18 — 피라미딩 max_lv
- Prod infinite mode: L2037 `range(step_lv, 20)` — 하드코딩 20
- Sim L750: `max_pyramid_level = 20 if STEP_MODE == "infinite" else TRUP_MAXLV`
- 양쪽 infinite 시 **20 동일**

---

## 진행 권고

### 즉시 조치 (v20.7 현상 유지 + 시뮬 보강)

**Kill Switch 시뮬 추가 (필수)**:

```python
# simulator.py에 추가할 로직
MDD_STOP_PCT_SIM = c.get("mdd_stop_pct", 0.20)  # prod MDD_STOP_PCT와 동일
KILL_SWITCH_ENABLED = c.get("kill_switch_enabled", True)

# 메인 루프에서 각 bar마다:
if KILL_SWITCH_ENABLED and mdd >= MDD_STOP_PCT_SIM:
    stats["kill_switch_triggered"] = True
    stats["kill_switch_at_bar"] = ai
    # 신규 진입 차단만 (기존 보유 포지션은 일반 청산 로직 따라감)
    # 해제: MDD < 10% 회복 시 자동 (옵션)
    continue  # 새 진입 skip
```

**Kill Switch PF-based (선택)**:
- 사후 stats로 PF 추적, 20거래 후 체크

### 재백테스트 계획

Kill Switch 추가 후 C6 재실행 → 실전 예상치 산출:

| 시나리오 | 예상 최종자산 | 비고 |
|---|---|---|
| v20.6 B0 (Kill Switch 없음 sim) | 19.55M | 현재 |
| **v20.6 B0 (Kill Switch 포함 sim)** | ? | 측정 필요 |
| v20.7 C6 (Kill Switch 없음 sim) | 23.97M | 낙관적 |
| **v20.7 C6 (Kill Switch 포함 sim)** | ? | 실전 기대 |
| + Kill Switch 자동해제 옵션 | ? | |

### v20.7 운영 조치 (병행)

1. Kill Switch 자동 해제 로직 추가 (MDD < 10% 회복 시) — 프로덕션 v20.7.1 미니업데이트
2. MDD 한도 20% → 25% 여유 확대 (C6 최대 20.92% + 4%p 버퍼)

### 기타 정정 기록

Explore 에이전트가 오류 보고한 항목 (본 md에서 정정):
- Area 3 Regime 히스테리시스: 시뮬에 구현되어 있음 (`precompute_v185` L89-108)
- Area 4 O3: 시뮬이 leading_signals 메커니즘으로 지원
- Area 16 Reinvest: 8조건 중 7개 구현, Kill Switch만 누락 (Area 13 종속)

---

## 점검 완료 이후 진행

1. **시뮬 Kill Switch 추가 패치** (backtest/core/simulator.py)
2. **전체 재백테스트** (v20.7 그리드 중 주요 후보: C6, C3, E2, E5)
3. **실전 예상치 재평가** — 백테스트와 실전 괴리 좁히기
4. 필요 시 v20.7.1 미니업데이트 (Kill Switch 자동 해제)

**현재 v20.7 배포 상태는 유지**. 추가 변경은 재백테스트 결과 확인 후.
