# bt #85-RR — key numbers

기간: 2022-01-01 ~ 2026-05-31 (53.7개월), 9671봉 · E2 OFF (production v20.9.19 정합) / AI OFF / B2 손절선

## 전제 감사 (sim ↔ production)

| 항목 | production v20.9.19 | sim BASE85 (E2 OFF) | 일치 | 비고 |
|---|---|---|:---:|---|
| E2 진입 차단 | OFF (E2_ENABLED=False) | OFF (bear_arr=0) | ✅ | production·sim 모두 E2 미차단 |
| E2 O3 예외 | True (E2 off라 무효) | False (무효) | ✅ | E2 OFF 상태에서 둘 다 미발동 |
| E2 gap_score 예외 | True (E2 off라 무효) | False (무효) | ✅ | E2 OFF 상태에서 둘 다 미발동 |
| AI Gate | 제거됨 (잔존 0) | patch_ai_gate_off | ✅ | v20.9.17 코드 삭제 / sim 무력화 |
| dynamic gate tiers | 제거됨 | None | ✅ | AI 동적 임계 제거 |
| range_new_enabled | True | True | ✅ |  |
| range_score_th | 5.0 | 5.0 | ✅ |  |
| range_step_lookback | 3.0 | 3.0 | ✅ |  |
| range_initial_ratio | 0.70 | 0.70 | ✅ |  |
| tu_trail_mult | 4.5 | 4.5 | ✅ |  |
| tu_step_lookback | 2.5 | 2.5 | ✅ |  |
| pyramid_initial | 0.80 | 0.80 | ✅ |  |
| step_mode | infinite(무한계단) | infinite | ✅ |  |
| step_interval_atr | 1.5 | 1.5 | ✅ |  |
| step_lookback(전역) | 1.5 | 1.5 | ✅ |  |
| atr_stop_mult | 2.5 | 2.5 | ✅ |  |
| min_stop/floor | 0.05 | 0.05 | ✅ |  |
| trailing_enabled | True | True | ✅ |  |
| tp1/tp2 atr | 1.8 / 2.8 | 1.8 / 2.8 | ✅ |  |
| step_stop_variant | B2 | B2 | ✅ |  |
| step_stop_offset | 0.03 (TP×0.97) | 0.03 | ✅ |  |
| kill_switch | ON (PF<0.7,n≥20) | disabled | ⚠️ | ⚠️ sim 단순화 — B0/B1 공통이라 Δ 무편향 |

## B0/B1 회귀 (#85 원판 대조)

| 지표 | 측정 | #85 기준 | 판정 |
|---|---:|---:|:---:|
| CAGR B0 | +20.25 | +20.25 | ✅ 일치 |
| MDD B0 | 34.51 | 34.51 | ✅ 일치 |
| N B0 | 95 | 95 | ✅ 일치 |
| CAGR B1 | +24.28 | +24.28 | ✅ 일치 |
| MDD B1 | 24.99 | 24.99 | ✅ 일치 |

## 핵심 6지표

| 지표 | B0 (현행) | B1 (눌림목) | Δ |
|---|---:|---:|---:|
| CAGR | +20.25% | +24.28% | +4.03%p |
| MDD | 34.51% | 24.99% | -9.52%p |
| 누적자산 | 22,562,470 | 26,096,924 | +3,534,454 |
| 승률 | 36.8% | 36.0% | -0.8%p |
| PF | 1.39 | 1.56 | +0.18 |
| 거래수 | 95 | 86 | -9 |
| Sharpe | 1.09 | 1.28 | +0.19 |

## 4구간 수익률 (+ MDD)

| 구간 | B0 | B0 MDD | B1 | B1 MDD | Δret |
|---|---:|---:|---:|---:|---:|
| BEAR'22 | -32.11% | -33.7% | -23.17% | -24.0% | +8.94%p |
| RECOVERY'23 | +50.57% | -14.7% | +38.19% | -21.7% | -12.38%p |
| BULL'24 | +127.69% | -22.6% | +151.96% | -17.9% | +24.27%p |
| RANGE'25~ | -3.74% | -11.4% | -3.12% | -8.8% | +0.62%p |

## 판정

**채택 (B1) — CAGR↑ & MDD↓ 동시 우위. 승률 -0.8%p 는 절대수익 원칙상 기각 사유 아님**
