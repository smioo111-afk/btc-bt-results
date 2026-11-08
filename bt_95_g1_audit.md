# bt #95 G1 — 시뮬 P3 ↔ production v20.9.24 감사표 (2026-11-08)

시뮬 P3 = `core/simulator.py` `step_atr_source="entry"` + `trail_atr_source="entry"` (v20.9.24 부터 기본값, B0 33,070,501).
production = `btc_bot_v290.py` v20.9.24.

## ✅ P3 범위 항목 — 전부 일치 (8/8)

| # | 항목 | 시뮬 P3 | production v20.9.24 | 판정 |
|---|---|---|---|---|
| 1 | 진입 ATR 정의 | `ca = max(atr_val, price×0.01)` → `entry_atr = ca` (sim L1993/2209, L2301/2309) — atr_val = 진입 확정봉 ATR | `calc_entry_atr(df4h, actual_price)` = `max(get_confirmed_atr(df4h)=atr.iloc[-2], 진입가×0.01)` (L480/491, 진입 L3725, MR L3896) — 진행 중 캔들 ATR 미사용 | ✅ (진입가: 시뮬 봉 종가 / prod 체결가) |
| 2 | 청산용 포지션 ATR | `ca = max(entry_atr, price×0.01)` 매 봉 (L879) | `_get_pos_atr(price)` = `max(entry_atr, 현재가×0.01)` 매 루프 (L1863, 호출 L3432) | ✅ (가격: 시뮬 봉 종가 / prod 30초 현재가) |
| 3 | 계단TP 간격 | `interval = ca × 1.5` (L1074, step entry 모드) | `interval = pos_atr × STEP_TP_INTERVAL_ATR(1.5)` (L2133) | ✅ |
| 4 | B2 손절선 | `tp_at_lv = fe + lv×interval` → `×(1−0.03)`, `max(·, fe×0.95)`, `stop = max(stop, ·)` (L1158/1180) | 동일 (L2224/2231/2232) | ✅ |
| 5 | 트레일링 거리 | `max(H − ca×tm, H×0.95, fe×0.95)` (L951/988/1013/1350, trail entry 모드 ca_tr=ca) tm: TU 4.5 / 기본 3.5 | `calc_trailing_stop(H, pos_atr, entry, trail_m)` = `max(H − pos_atr×tm, H×0.95, entry×0.95)` (L1902) tm: pos_trail_m 4.5(TU) / 3.5 | ✅ |
| 6 | 트레일링 래칫 | entry 모드 비래칫 — 단 ca 의 1% 하한 변동 시에도 청산 판정 동치 (아래 주) | `stop_loss = max(stop_loss, new)` | ✅ (판정 동치) |
| 7 | TP1/TP2 | `fe + ca × 1.8 / 2.8` (L996/1017) | `first_entry + pos_atr × 1.8 / 2.8` (L2029) | ✅ |
| 8 | 피라미딩·잔액투입 | entry_atr 진입 시에만 설정 (추매 갱신 없음), first_entry 고정 | `entry_atr` 진입 시에만 기록 — `_check_partial_tp` 추매 / `_auto_reinvest` 미갱신, first_entry 고정 | ✅ |

**주 (#6 래칫 동치)**: 시뮬 `ts(p) = H − tm·max(ea, 0.01p)`. 가격 p 하락 시 ts 는 비감소(ca↓), H 는 단조 증가 → 과거 ts_t 가 현재 가격을 상회했다면 현재 ts 도 상회. 따라서 "p ≤ max_t ts_t ⇔ p ≤ ts_now" — production 래칫과 청산 결정 동일.

## 운영 항목 (시뮬 해당 없음)
| 항목 | production v20.9.24 |
|---|---|
| 재시작 복원 | `entry_atr` status 영속 → 재시작 시 자동 복원 (`_load_status` default 키 추가) |
| 값 누락 폴백 | 보유 중 `entry_atr ≤ 0` (구버전 포지션·수동매수) → `logger.warning` + `tg_warn` + 현 시점 확정 4H ATR(first_entry 1% 하한) 로 대체·저장 |
| 포지션 리셋 | 청산/팬텀/수동매도 등 4개 리셋 지점 `entry_atr: 0.0` |
| 표시 | 텔레그램 리포트 `진입ATR:X (적용 Y · 1%하한)` 줄 + TP 표시 pos_atr 기준 / 대시보드 `진입ATR` 행 + TP 표시 pos_atr 기준 |

## ⚠️ P3 범위 외 — 기존 차이 (변경 없음, #95 이전부터 모든 시뮬 세계 공통)
| 항목 | 시뮬 | production | 비고 |
|---|---|---|---|
| 초기 ATR 손절 | `price − ca×pos_stop_m` | `min(entry − cur_atr×2.5, entry×0.95)` | 진입 사이징·초기 손절은 #95 범위 아님 |
| 포지션 사이징 | `calc_pos_krw(.., ca, ..)` | `calc_position_size(.., cur_atr, ..)` | 동일 |
| 손절유예(grace) | grace 중 청산 판정 없음 | grace 중 `entry − pos_atr×1.5` 하향 전용 + 인트라캔들 하드스톱 | 4H 시뮬 구조 한계 (기존) |

→ 위 3건은 v20.9.23 이전부터의 구조적 차이로, 이번 변경이 새로 만든 불일치 아님. 후속 정합 대상으로 improvement_todo 등재.
