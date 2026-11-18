# 백테스트 로그 (v2)

> v20.0 시뮬레이터 도입 이후 (#20 ~) + v20.6/v20.7 채택 근거 + E2 연구 (#38 ~ #44).
> 초기 탐색 (#1 ~ #19) 및 Phase 테스트는 `backtest_log_v1.md` 참조.

> ## ⚠️ 시뮬 베이스라인 교체 공지 (2026-11-08, #95 P3 → production v20.9.24, 현행)
> - **P3세계(현행)**: 계단·트레일링·TP1/TP2 청산 ATR = 진입 고정 entry_atr (`step_atr_source="entry"`, `trail_atr_source="entry"` 기본) = **production v20.9.24**. **B0 = 33,070,501 / CAGR +31.13% / MDD 25.80% / PF 1.63 / N80**.
> - 실효 개선 기준 = K0 Δ +4.69M (vs v20.9.23 정합 ST/P0). 아래 `═══ P3세계 전환 경계선 (#95) ═══` 위 = P3세계.
>
> ## ⚠️ 시뮬 베이스라인 교체 공지 (2026-11-08, #93-F → ST세계)
> - **ST세계(현행)**: S세계 + 트레일링·TP1·TP2 live ATR + 래칫 (`trail_atr_source="forming"` 기본). **B0 = 21,684,035 / CAGR +19.17% / MDD 29.57% / PF 1.46 / N83** (B1+K4+B2). production 일치율 트레일 99% / 계단 86% (≤0.5%).
> - 아래 `═══ ST세계 전환 경계선 (#93-F) ═══` 위 = ST세계. 회귀: `bt_93f_switch_regression.py` 5/5.
>
> ## ⚠️ 시뮬 베이스라인 교체 공지 (2026-11-08, #93-E → S세계)
> - **S세계(현행)**: F세계 + 계단TP interval live ATR (`step_atr_source="forming"` 기본). **B0 = 24,160,396 / CAGR +22.13% / MDD 27.44% / PF 1.47 / N73** (B1+K4+B2).
> - #93-F(트레일링·TP1·TP2 live ATR, ST세계 21,684,035)는 #92 V1/V2 뒤집힘으로 **전환 보류** (`trail_atr_source="entry"` 기본).
> - **⚠️ S/ST세계에서 #87 K4 vs K0 부호 뒤집힘** → #87-R 재검증 대기. 회귀: `bt_93f_switch_regression.py`.
> - 아래 `═══ S세계 전환 경계선 (#93-E) ═══` 위 = S세계, 그 아래 = F세계(B0 33,070,501), `═══ F세계 전환 경계선 ═══` 아래 = C세계(B0 29,952,352).
>
> ## ⚠️ 시뮬 베이스라인 교체 공지 (2026-09-23, #93-B)
> - **F세계(현행)**: `precompute_v185(atr_source="forming")` 기본 — production 정합(미완성캔들 ATR, live 99.8% 일치). **B0 = 33,070,501 / CAGR +31.13% / MDD 25.80% / PF 1.63 / N80** (B1+K4+B2).
> - **C세계(구 베이스라인)**: 확정캔들 ATR. #92 이전 모든 항목의 수치는 C세계 (**B0 = 29,952,352**). 재현: `BT_ATR_SOURCE=confirmed` 또는 `atr_source="confirmed"`.
> - 과거 채택(#85 B1 / #87 K4 / #92 V0)은 F세계에서 Δ 부호·순위 보존 확인 (#93-B) → 유효. 단 **수치 직접 비교 금지** — 세계 간 차이 비상수(+0.46M~+14.0M).
> - **⚠️ Kill Switch/사이징 연동 실험은 F세계 필수** (#87 K2: Δ -12.46M(C) → -1.16M(F), ×0.09 — 세계 민감도 극심).
> - 아래 `═══ F세계 전환 경계선 ═══` 위 = F세계, 아래 = C세계.

---

## 운영 규칙 (2026-04-19 추가)

매 백테스트 완료 시:
1. 이 파일에 표준 형식으로 항목 추가 (기존 형식 유지)
2. 산출물 경로 + commit hash 명시
3. 판정: ✅ 채택 / ❌ 기각 / 📊 분석
4. 후속 액션 기재

매 버전업 시:
- 이전 항목 검토, 패턴 식별, 다음 방향 도출

---

## 2026-11-08 #95 P3 채택 → production v20.9.24 배포 — ✅ G1~G4 통과, 무포지션 배포

- **production**: 진입 시 `entry_atr = max(직전 확정 4H ATR, 진입가×1%)` 저장 → 청산 ATR `max(entry_atr, 현재가×1%)` 로 계단TP·B2·트레일링·TP1/TP2 계산 (`btc_bot_v290.py` v20.9.24).
- **G1** 감사 8/8 일치 (`bt_95_g1_audit.md`) — 범위 외 기존 차이 3건(초기 손절·사이징·grace) 별도 등재.
- **G2** production 메서드 실행 vs 시뮬 P3 (`bt_95_g2_prod_verify.py` → `bt_95_g2_prod_verify.md`): 계단 25건 손절 평균 0.023% / 최대 0.140%, 트레일 86건 평균 0.003% / 최대 0.062% — 전부 ≤0.5%. 2026-08-25 Lv8 신규칙 손절 100,990,773 vs 시뮬 100,994,498 (-0.004%) (live 구규칙 104,986,408).
- **G3** py_compile/AST/pyflakes 신규 경고 0 · **G4** in_position=False, BTC 0.0.
- **시뮬**: 기본 step/trail = entry → B0 33,070,501. 회귀 `bt_93f_switch_regression.py` 5/5, `bt_93e_*`(default 33,070,501로 갱신)·`bt_93b_*` ✅.
- **#92 재확인**: P3 = E세계 → #93-B 결과(V0 최우위) 유효, 해소.

---

## 2026-11-09 #98: MR(Range 평균회귀) 재검증 — 🔴 기각, MR 명시 비활성 (v20.9.25)

- **세계**: P3세계 (production v20.9.24), M0_K4 = B0 33,070,501 정확 일치. 기간 2022-01 ~ 2026-05. 스크립트 `backtest/bt_98_mr_revalidate.py`.
- **배경**: production MR 경로는 v20.9.16 이전부터 `stats`/`cons_loss` NameError 로 실행 불가(debug 로그로 은폐). 시뮬은 Range New 활성 시 MR 비활성. NameError 수정 시 미검증 MR 이 켜지므로 먼저 검증.
- **재현**: `mr_with_range_new` + `mr_prod_mode` (production 사이징 risk 1.1%·5~60% clip, 유예 없는 손절, 진입 스톱 -5% 상한). 기본값은 기존 동작.

| 케이스 | 정의 | 최종자산 | CAGR | MDD | PF | N | MR건수 | MR승률 | MR평균 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| M0_K4 | MR OFF (B0) | 33,070,501 | +31.13% | 25.80% | 1.63 | 80 | 0 | - | - |
| M1_K4 | 운영 코드 (RSI<=35, BB<=0.15) | 22,327,911 | +19.96% | 23.06% | 1.33 | 129 | 60 | 46.7% | -0.16% |
| M2_K4 | 엄격 (RSI<=30, BB<=0.10) | 28,977,225 | +27.26% | 22.91% | 1.50 | 111 | 35 | 51.4% | -0.33% |
| M0_K0 | MR OFF, KS 없음 | 28,789,694 | +27.08% | 25.80% | 1.59 | 83 | 0 | - | - |
| M1_K0 | 운영 코드, KS 없음 | 27,708,802 | +25.98% | 27.23% | 1.36 | 148 | 72 | 37.5% | -0.33% |
| M2_K0 | 엄격, KS 없음 | 29,356,730 | +27.64% | 24.56% | 1.46 | 117 | 39 | 48.7% | -0.43% |

- **판정**: 실효 기준 K0 에서 M1 Δ -1.08M / MDD +1.43%p. K4 에서 M1 Δ -10.74M. MR 자체 평균수익 M1 -0.33%(K0), 청산 67%가 6봉 시간초과.
- M2_K0 +0.57M 은 MR 평균 -0.43% 인데 총합만 개선된 경로 효과이며 K4 에서 -4.09M 로 뒤집혀 채택 근거 없음.
- **조치**: production MR 진입에 `not RANGE_NEW_ENABLED` 게이트 (시뮬 동일). 한계: 봉 종가 기준 손절(production 은 30초 감시), DI약세 사이징은 1.1% 고정 근사.

---

═══ P3세계 전환 경계선 (#95, v20.9.24, 2026-11-08) — 위 = P3세계 (B0 33,070,501 = production), 아래 = ST세계 (B0 21,684,035) ═══

---

## 2026-11-08 #87-R: K4 vs K0 MDD 트리거 민감도 (ST세계 + #95 후보 세계) — 📊 MDD 트리거는 live-ATR 트레일 세계에서만 발동·손해, K4 이득원 = PF 트리거

| 세계 | K0 | K4 20%(현행) | 22% | 25% | 30% |
|---|---|---|---|---|---|
| P0 (ST 현행) | 24.10M | **-2.42M** | -3.72M | ±0 | ±0 |
| P1 계단 entry | 26.02M | +4.27M | +4.27M | +4.27M | +4.27M |
| P2 트레일 entry | 26.37M | -2.21M | -3.50M | +0.49M | +0.49M |
| P3 둘 다 entry | 28.79M | +4.28M | +4.28M | +4.28M | +4.28M |

- P1/P3: 임계 무관 동일 → MDD 트리거 미발동, K4 이득은 PF<0.7 트리거 (2023 PF 깜빡임 구간 진입 차단). P0/P2: MDD 20~22% 발동(2025-02 등) → 장기 정지 손해, ≥25% 미발동.
- 시사: 계단 ATR 출처가 K4 부호를 결정. #95 P1/P3 채택 시 K4(20%) 유지 타당, P0 유지 시 MDD 임계 25% 상향 또는 K0 검토 필요.
- 정합: P0/20% 21,684,035 ✅, P3/20% 33,070,501 ✅. 산출물 `bt_87R_verdict.md` / `_key_numbers.md` / `_full.md`. 스크립트 `bt_87R_ks_mdd_sensitivity.py`.

---

## 2026-11-08 #95: 계단·트레일링 ATR 출처 변형 (ST세계, production 변경 후보) — ✅ 후보 P1/P2/P3 (K0·K4 모두 통과), 최우위 P3

| 안 | 정의 | K0 누적 (Δ) | K4 누적 (Δ) | K4 MDD | 비악화 |
|---|---|---|---|---|---|
| P0 | 현행 (계단·트레일 live ATR) | 24.10M | 21.68M | 29.57% | 기준 |
| P1 | 계단만 진입 ATR | 26.02M (+1.91M) | 30.29M (+8.60M) | 24.80% | 3/4 |
| P2 | 트레일·TP만 진입 ATR | 26.37M (+2.27M) | 24.16M (+2.48M) | 27.44% | 3/4 |
| **P3** | **계단+트레일 진입 ATR** | **28.79M (+4.69M)** | **33.07M (+11.39M)** | **25.80%** | 3/4 |
| P4 | 트레일·TP 확정 캔들 ATR | 26.10M (+1.99M) | 23.48M (+1.79M) | 28.21% | 2/4 ❌ |

- 4구간: 전 후보 BEAR'22 악화 (P1 -6.12 / P2 -1.12 / P3 -7.16%p), RECOV/BULL/RANGE 개선. P4 는 RANGE -0.01%p 로 2/4.
- 거래 품질: 트레일 조기청산(Lv≤1) P0 18 → P2 15 / P3 19 / P1 26. P0 상위10% 유지 P3 7/9(K0)·6/9(K4). 2023-11-16: P0·P1 트레일 Lv1 ≈-2% / P2·P4 계단 Lv12 +14.7% / P3 Lv10 +12.2%.
- 해석: K0(경로 무관) Δ 는 +1.9~4.7M, K4 Δ 는 KS 경로(#87-R) 증폭. 계단 entry(P1/P3) 는 MDD 트리거 회피가 K4 이득의 큰 부분.
- 주의: 시뮬 진입 ATR = max(진입 확정봉 atr, 진입가 1%) — production 반영 시 진입 시점 cur_atr 저장 정의 정합 필요 (차기 설계).
- 정합: P0-K4 21,684,035 / P2-K4 24,160,396 / P3-K4 33,070,501 ✅. 산출물 `bt_95_verdict.md` / `_key_numbers.md` / `_full.md`. 스크립트 `bt_95_step_entry_atr.py`.
- 후속: 사용자 채택안 결정 → #87-R 결과 해당 세계 확인(완료) → #92 재확인 → production 설계(무포지션 배포).

---

## 2026-11-08 #93-F 전환 (사용자 승인): 시뮬 기본 `trail_atr_source="forming"` → ST세계 B0 21,684,035

- `core/simulator.py` `TRAIL_ATR_SOURCE_DEFAULT="forming"`, `"confirmed"` 옵션 추가(#95 P4). 백업 `core/simulator.py.bak.pre_95`.
- 회귀: `bt_93f_switch_regression.py` 5/5 ✅ (default 21,684,035 / E 33,070,501 / S 24,160,396 / ST 21,684,035 / C 29,952,352). `bt_93e_switch_regression.py` 는 trail=entry 고정으로 갱신 ✅, `bt_93b_switch_regression.py` ✅.
- 근거: production 일치율 트레일 99% / 계단 86% (≤0.5%). #92 V1/V2 재확인은 #95 확정 후.

---

═══ ST세계 전환 경계선 (#93-F, 2026-11-08) — 위 = ST세계 (B0 21,684,035), 아래 = S세계 (B0 24,160,396) ═══

---

## 2026-11-08 #93-F: 트레일링·TP1·TP2 ATR 출처 정합 + #93-E 전환 — 🔴 #93-F 1차 보류 (#92 V1/V2 뒤집힘) → ✅ 사용자 승인 후 전환 (위 항목) / ✅ #93-E 전환 완료

- **#93-E 전환 (사용자 승인)**: `core/simulator.py` `STEP_ATR_SOURCE_DEFAULT="forming"` → **B0 = 24,160,396** (S세계).
- **#93-F 구현 (opt-in)**: `trail_atr_source` / env `BT_TRAIL_ATR_SOURCE` — forming 시 트레일링 ATR 항(MR/P0/P1/infinite) + TP1/TP2 = `ind["atr_forming"][ai]` (하한 없음), 트레일링 레벨 래칫(`trail_peak`, production `stop_loss=max(stop,trail)` 정합). 기본 `entry`. 백업 `core/simulator.py.bak.pre_93f`.
- **production 대조** (`bt_93f_trail_atr_verify.py`, `트레일링: X KRW` 86건/binding 84건): EXACT 0.054% (수식 검증) / **ENTRY 0.690%** / **forming 0.142% (≤0.5% 99%)**. 봉 경계 52건 forming 0.076% vs ENTRY 0.830%. TP1/TP2 = 1쌍, 판별력 없음.
- **B0**: E 33,070,501 → S 24,160,396 → **ST 21,684,035** / CAGR +19.17% / MDD 29.57% / PF 1.46 / N83. ST_conf 23,417,733.
- **상대비교** (`bt_93f_relative_audit.py`, E 대비): #85 B1 ✅ (+7.02M) / #87 K1·K2 ✅ / #87 K3·K4 ❌ (기보고, ST K4 -2.42M) / **#92 V1 -0.65M→+3.46M ❌, V2 -8.05M→+2.55M ❌ (ST 1위 V1)** — 단 ST_conf 에서는 V1 -0.15M / V2 -2.11M 로 보존 → 비강건 / #92 V3 ✅.
- 진단 (S→ST): 계단손절 ΣPnL +96.4%→+60.3%, 트레일링 +83.8%→+120.3% (건수 15→22) — live ATR 축소 시 트레일 조여져 계단 진행 전 조기 청산 (예: 2023-11-16 Lv12 +14.7% → Lv1 트레일 -1.7%).
- **조치**: 신규 뒤집힘 → trail 전환 보류. 회귀 `bt_93f_switch_regression.py` 5/5 ✅ (default 24,160,396 / E 33,070,501 / S 24,160,396 / ST 21,684,035 / C 29,952,352). `bt_93b_switch_regression.py` 는 step·trail entry 고정으로 갱신(✅). production 무변경.
- **준비(미실행)**: `bt_87R_ks_mdd_sensitivity.py` (K0 vs K4 × MDD 20/22/25/30%), `bt_95_step_entry_atr.py` (계단 ATR forming vs entry × K0/K4).
- 산출물: `bt_93f_verdict.md` / `bt_93f_key_numbers.md` / `bt_93f_full.md` / `bt_93f_trail_atr_verify.md`

---

═══ S세계 전환 경계선 (#93-E, 2026-11-08) — 위 = S세계 (B0 24,160,396), 아래 = F세계 (B0 33,070,501) ═══

---

## 2026-11-08 #93-E: 계단TP interval ATR 출처 정합 (entry_atr → live cur_atr) — 🔴 1차 보류 (#87 K4 vs K0 부호 뒤집힘) → ✅ 사용자 승인 후 전환 (위 #93-F 항목)

- **구현 (시뮬 전용, opt-in)**: `core/simulator.py` `step_atr_source` cfg / env `BT_STEP_ATR_SOURCE` — `"entry"`(**현 기본**, 진입 ATR 고정) / `"forming"`(production 정합: interval = `ind["atr_forming"][ai]` × 1.5, 봉마다 재계산, B2 손절선 동일 interval). `backtest_pyramiding.precompute` 에 `ind["atr_forming"] = (13·atr[i]+|open[i+1]-close[i]|)/14` 추가. 백업 `*.bak.pre_93e`.
- **production 대조** (`bt_93e_step_atr_verify.py`, live 로그 B2 시대 25건/binding 21건, Upbit 1분봉 재구성): EXACT 평균 0.028% (수식 검증), **ENTRY(구) 1.29% / 최대 5.76%**, **forming 0.19% / ≤0.5% 86%**. 2026-08-25 Lv8 손절 104,986,408: forming +0.03% / ENTRY -5.75%.
- **B0 (B1+K4+B2)**: entry **33,070,501** (회귀 ✅ 정확) → forming **24,160,396** / CAGR +22.13% / MDD 27.44% / PF 1.47 / N73 (**Δ -8.91M, CAGR -9.00%p**). S_conf(확정 atr) 23,850,101.
- **상대비교** (`bt_93e_relative_audit.py`): #85 B1 vs B0 +4.06M→+6.94M ✅ / #92 V1~V3 vs V0 전부 음수 유지 ✅ / #87 K1·K2 ✅ / **#87 K3 +3.71M→-3.70M ❌, K4 +4.28M→-2.21M ❌** (S_conf 도 동일 뒤집힘 → ATR 근사 선택과 무관). S 세계 #87 1위 = K0.
- **메커니즘**: S 경로에서 K4 가 2025-02-25 롤링 MDD 20.1% 발동 → 2025-05-22 복구(≈86일 정지, 차단 진입 352→993). E 경로는 PF 깜빡임만. K4 이득이 임계 경계의 경로 의존적.
- **조치**: 지시대로 중단 — 시뮬 기본 entry 유지(B0 불변), CLAUDE.md 베이스라인 미갱신. 회귀 `bt_93e_switch_regression.py` (default/entry 33,070,501 / forming 24,160,396) ✅, `bt_93b_switch_regression.py` ✅. production 무변경.
- 산출물: `bt_93e_verdict.md` / `bt_93e_key_numbers.md` / `bt_93e_full.md` / `bt_93e_step_atr_verify.md`
- **후속 (사용자 결정)**: S 세계 전환 여부 + #87 K4 재검증(K0 vs K4, KS 임계 민감도). 범위 외 동일 계열 불일치 → #93-F(트레일링/TP1·TP2 도 `ca`=entry_atr, production `cur_atr`).

---

## 2026-09-23 #93-B 전환: 시뮬 B0 → F세계 (forming ATR) — ✅ 전환 완료 (회귀 2/2 정확 일치)

- `backtest/backtest_v185_optimize.py` `precompute_v185(df_all, df_daily, atr_source=None)` — 기본 `"forming"` (env `BT_ATR_SOURCE` override), `"confirmed"` 보존. forming 시 Volatile 마스크 + `atr_ok`(Rule Score) 모두 재구성. 백업 `backtest_v185_optimize.py.bak.pre_93b`.
- **회귀 (`bt_93b_switch_regression.py`)**: 기본/forming = **33,070,501** ✅ 정확 / confirmed = **29,952,352** ✅ 정확 / env override(confirmed) = 29,952,352 ✅.
- bt_93 / bt_93b 스크립트는 `atr_source="confirmed"` 로 고정 (C 기준에서 세계 파생 — 재실행 시 동일 수치 확인).
- 레거시 bt_85~bt_92 스크립트를 그대로 재실행하면 이제 F세계 수치가 나옴 (내장 REF 회귀는 ⚠️ 편차 표시가 정상). C세계 재현은 `BT_ATR_SOURCE=confirmed`.
- **분리 등재 #93-E**: 계단TP interval ATR 출처 불일치 (production live `cur_atr` vs 시뮬 `entry_atr`) — F 전환과 무관, 다음 작업.
- production 코드 무변경 (`btc_bot_v290.py` md5 전후 동일).

---

## 2026-09-23 #93-B: 시뮬 베이스라인 무결성 (확정 vs 미완성캔들 ATR) — ✅ 상대비교 전부 보존 + 결정론 재현 가능 → 시뮬 F 전환 (승인·완료, 위 항목)

**(1) 결정론**: 진입 판정 시점 production ATR = `(13·atr[i]+|open[i+1]-close[i]|)/14` — 확정 데이터만으로 결정. live log `[새 캔들]` 942건 대조: 과열장 판정 일치 **F 99.8%** (C=시뮬기존 95.6%), ATR 오차 중앙 0.20%. 잔여 2건 = 경계(94 vs 95). 봉 내부(보유 중 `_check_regime_switch`, 계단TP `cur_atr` vs 시뮬 `entry_atr`)는 구조적 한계 — 범위 외.

**(2) Δ 보존** (4세계 C / F / F_tr0 / F_hi, C 세계 11건 과거 수치 ±0.02% 회귀):

| 결정 | Δ C | Δ F | 배율 | 부호 |
|---|---|---|---|---|
| #85 B1 vs B0 | +3.53M | +4.06M | ×1.15 | ✅ |
| #87 K1 vs K0 | -18.11M | -20.34M | ×1.12 | ✅ |
| #87 K2 vs K0 | -12.46M | -1.16M | ×0.09 | ✅ |
| #87 K3 vs K0 | +2.92M | +3.71M | ×1.27 | ✅ |
| #87 K4 vs K0 | +3.86M | +4.28M | ×1.11 | ✅ |
| #92 V1 vs V0 | -0.93M | -0.65M | ×0.71 | ✅ |
| #92 V2 vs V0 | -7.91M | -8.05M | ×1.02 | ✅ |
| #92 V3 vs V0 | -12.79M | -11.80M | ×0.92 | ✅ |

채택안(B1/K4/V0) 4세계 전부 1위 유지. 세계 간 차이 비상수(K1 +0.46M ~ K2 +14.0M) → "상수 오프셋" 문서화안 불성립.
**판정**: 과거 채택 안전. 시뮬 F(production 정합) 전환 권고 — 신규 B0 = **33.07M / +31.13% / MDD 25.80% / N80**. 전환 작업은 사용자 승인 대기.
**주의**: K2 처럼 KS/사이징 연동 안은 세계 민감(크기 ×0.09) → 향후 F 세계 필수.
**산출**: `backtest/bt_93b_live_atr_verify.py`, `backtest/bt_93b_relative_audit.py`, `results/bt_93b_{verdict,key_numbers,full}.md`, `results/bt_93b_live_atr_verify.csv`

---

## 2026-09-23 #93 [C/F 병기 — R0=F, R1=C]: ATR regime 확정캔들/히스테리시스 검증 (4년, B1+K4+B2) — ❌ R1~R3 전량 기각 (R0 현행 유지) / ⚠️ 시뮬 B0≠production

**배경**: 실거래 09-21~09-23 Volatile↔Trend_Up 5회 왕복 — 매 캔들 시작(xx:00) TU 복귀, 수분~수시간 뒤 Volatile. production `get_atr_regime` 가 미완성 캔들 포함 ATR 사용 → 시작 직후 ATR ≈ 확정×0.93 (Wilder 재귀).

**선행 감사**: 시뮬(`bv.precompute_v185`) = 확정 캔들 → **R1 = 시뮬 기존 베이스** (regime/atr_ok 배열 완전 동일). production 현행(R0) 은 시뮬 미반영이었음 → forming ATR `(13·atr[i]+|open[i+1]-close[i]|)/14` 로 신규 모델링 (pandas_ta 재귀 일치 검증). rejected 이력 없음.

**R1 회귀**: 29,952,352 / +28.22% / 25.04% / N83 = bt_87 K4 ✅ 정확 일치.

| 안 | 설명 | CAGR | MDD | 누적 | Δ vs R0 | PF | 승률 | N | 전환(4H) | 1H진동 | Volatile봉% | 추매 | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **R0** | 현행 (미완성캔들, ≥95) | **+31.13%** | 25.80% | **33,070,501** | — | 1.63 | 38.8% | 80 | 596 | 725 | 4.37% | 50 | 기준 |
| R1 | 확정캔들 iloc[:-1] | +28.22% | 25.04% | 29,952,352 | -3,118,149 | 1.61 | 37.3% | 83 | 692 | 376 | 9.87% | 44 | ❌ 누적악화 |
| R2 | 미완성 + 95/92 | +30.48% | 25.80% | 32,354,900 | -715,601 | 1.63 | 38.8% | 80 | 581 | 577 | 5.79% | 47 | ❌ 누적악화 |
| R3 | R1+R2 | +28.02% | 25.04% | 29,744,164 | -3,326,337 | 1.60 | 37.3% | 83 | 633 | 337 | 11.36% | 42 | ❌ 누적악화 |

4구간 (BEAR22/RECOV/BULL24/RANGE25): R0 -23.68/+51.79/+186.44/-1.03 · R1 -23.17/+58.60/+151.96/-3.12 → 차이는 BULL24 집중 (Volatile 감축사이징 회피).
1H진동 = 2023-11~2026-04 캔들 내 1h 관측 regime 전환 (production 30초 루프 하한). TU 보유 중 `_check_regime_switch` 발화: R0 123 / R1 62.

**판정**: R1~R3 기각 (절대수익 원칙). 진동 제거는 가능(R1 1H 진동 -48%)하나 -3.12M. 드리프트는 우연한 이득(실효 과열장 임계 ≈ 확정 97~98%ile).
**⚠️ 발견**: 시뮬 B0(29.95M) = R1 세계. production 실동작 모델 = 33.07M. 과거 #85~#92 상대비교는 동일 세계 내라 방향성 유효 추정(미검증). 시뮬 B0 forming-ATR 전환은 사용자 결정 대기.
**미모델**: 보유 중 entry_type 전환(Volatile 구간 pyramid→trend: 계단TP/추매 정지, P0 트레일링). 손절선 하향 없음(step_tp_level+max 경로).
**후속**: #93-B 시뮬 B0 정합 / #93-C 확정캔들+과열장 임계 97·98·99·OFF / #93-D `_check_regime_switch` 봉 단위화(시뮬 entry_type 전환 모델 선행).
**배포**: 채택안 없음 → 지시서 없음, production 무변경.
**산출**: `backtest/bt_93_atr_regime_hys.py`, `results/bt_93_{verdict,key_numbers,full}.md`, `results/bt_93_trades_R*.csv`

---

## ═══ F세계 전환 경계선 (2026-09-23) — 이 아래 항목 수치 = C세계(구 베이스라인, 확정캔들 ATR) ═══

---

## 2026-08-05 #92 [C세계]: B2 저ATR 본전 하한 검증 (4년, B1+K4) — ❌ V1~V3 전량 기각 (V0/현행 B2 유지)

### 배경

실거래 감사(07-06, 07-24): `STEP_STOP_VARIANT=B2`(TP1×0.97)가 저ATR(횡보장 1~2%ile) 구간에서 TP1 도달(피라미딩Lv1) 후에도 손절선이 진입가 아래에 형성됨을 확인. TP1 거리(1.5×ATR)가 작을 때 3% 오프셋을 다시 빼면 진입가 밑으로 내려가는 구조.
- 07-06: TP1가 95,566,630 × 0.97 = 92,824,866 < 진입 94,390,516 (-1.66%)
- 07-24: 손절 94,066,058 < 진입 95,843,661 (-1.85%)

베이스: B1(눌림목) + KS=K4(rolling_peak) + B2(offset=3%) = production v20.9.22 정합.

### 무손실 회귀 ✅

V0 = bt_87 K4 정확 일치: 29,952,352 / CAGR +28.22% / MDD 25.04% / N=83.

### 4변형 결과 (기간 2022-01~2026-05, 53.7개월)

| 안 | 설명 | CAGR | MDD | 누적 | ΔV0 | N | PF | 승률 | 판정 |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| **V0 (기준)** | 현행 B2 (하한 없음) | +28.22% | 25.04% | 29,952,352 | — | 83 | 1.61 | 37.3% | 기준선 |
| V1 | B2 + 본전 하한(×1.001) | +27.31% | 22.90% | 29,027,158 | -925,194 | 88 | 1.56 | 35.2% | ❌ REJECT(BULL24 악화) |
| V2 | B2 + 본전+0.5% 하한(×1.005) | +19.62% | 22.38% | 22,043,735 | -7,908,617 | 89 | 1.42 | 31.5% | ❌ REJECT(BULL24·RANGE25 악화) |
| V3 | 동적 오프셋 min(3%,0.5×ATR%) | +13.02% | 23.48% | 17,162,005 | -12,790,347 | 120 | 1.25 | 43.3% | ❌ REJECT(BULL24·RANGE25 악화) |

### TP1 도달 거래 저ATR 손절 — 개선은 실제로 있었음

| 안 | TP1도달N | 저ATR(≤20%ile) TP1 손절N | 저ATR손절평균% |
|---|---:|---:|---:|
| V0 | 34 | 2 | -2.51% |
| V1 | 37 | 2 | -2.17% |
| V2 | 36 | 3 | -0.91% |
| V3 | 56 | **0** | — |

V3는 저ATR TP1 손절을 완전히 제거(2→0)했지만, 그 대가로 BULL'24 캡처가 **+152.0% → +90.4%**로 붕괴. 원인은 2024-01-29 진입 거래(V0/V1/V2 +56.70% 대비 V3 +1.39%) — 동적 오프셋이 저ATR(10%ile) 구간에서 손절선을 TP1에 바짝 붙여, 이후 몇 주간 이어진 대세 상승 추세를 초기 조정에서 조기 손절시킴. bt_86 C1이 경고한 "타이트 손절 위험"이 그대로 재현.

### 판정: **V0(현행 B2) 유지 — V1/V2/V3 전량 기각**

- 절대수익 원칙: 저ATR 소액 손절(-2%대, 4년간 2~3건) 개선이 BULL'24 캡처 붕괴(-2.8%p~-61.6%p, 누적 최대 -12.79M)에 압도적으로 못 미침.
- V1(가장 약한 개입, 본전+0.1%)조차 BULL -2.8%p로 REJECT — "본전 하한"이라는 최소한의 개입도 무해하지 않음. 저ATR 구간의 좁은 TP1-스톱 간격은 손실 케이스뿐 아니라 대형 트렌드 캡처의 초입 구간이기도 해서, 하한을 걸면 둘 다 동시에 잘려나감.
- **결론**: 07-06/07-24류 손실(-2%대)은 B2 설계상 감내 가능한 비용이며, 이를 본전 보장으로 틀어막으려는 시도는 정확히 AI Gate/#89 손실모드 패턴처럼 "그럴듯하지만 해로운" 개입.

### 코드 변경

`core/simulator.py`: B2 분기에 `step_stop_be_floor_pct`(V1/V2 본전 하한 훅) / `step_stop_dynamic_offset`(V3 동적 오프셋 훅) 신규 추가. 둘 다 cfg 미설정(기본 None/False) 시 기존 B2 동작과 byte-identical (V0 회귀 정확 일치로 검증). **production 코드(`btc_bot_v290.py`) 무변경.**

### 산출

`bt_92_verdict.md` / `bt_92_key_numbers.md` / `bt_92_full.md`

---

## 2026-07-27 #89 [C세계]: 손실모드 사이징 4년 검증 (S0~S3, v20.9.22 정합) — ❌ 전량 기각 (S0 현행 유지) + 시뮬 결함 발견/수정

### 배경

라이브 사이징이 오락가락(7/7 80% / 7/19 60% / 7/21 70%) — 손실모드(연패≥3→×0.3) 오작동 의심.

### 선행 감사 — "오락가락" 의 정체 = regime 경로 분기 (오작동 아님)

| 진입 경로 | 사이즈 | `calc_position_size` 경유 | Loss Mode | PERF_LOW_RISK |
|---|---|:---:|:---:|:---:|
| Trend_Up 피라미딩 초기 | equity×80% | ❌ 우회 | ❌ | ❌ |
| Range 신규 | equity×70% | ❌ 우회 | ❌ | ❌ |
| Leading(O3)/E2예외 | equity×40% | ❌ 우회 | ❌ | ❌ |
| Volatile/Trend_Down (+비활성 Range레거시/MR) | `calc_position_size`(상한60%) | ✅ 경유 | ✅ | ✅ |

**결론**: 연패 중이어도 TU/Range/Leading 이면 그대로 80/70/40%가 나간다. 7/7·19·21 값 차이는 손실모드가 아니라 **어느 regime 경로를 탔는지**의 결과.

**시뮬 결함 발견**: 시뮬레이터의 `calc_position_size` 대응 함수(`backtest_pyramiding.calc_pos_krw`)에는 cons_loss/PF 감점 항이 전혀 없어, 기존 B0/B1/K4 백테스트는 라이브의 부분 적용 경로(Volatile/Trend_Down)조차 재현 못하고 있었다. → `core/simulator.py` 에 `loss_mode_variant` 훅 신규 추가로 수정 (cfg 미설정 시 기존 백테스트 전부 동일 동작, 회귀 없음).

### 무손실 회귀 ✅

**S2(완전제거) = bt_87 K4 정확 일치**: 29,952,352 / CAGR +28.22% / MDD 25.04% / N=83. (S2=제거는 기존 버그 상태와 동치이므로 정확 일치가 정답)

### 4변형 결과 (B1+K4 베이스, 기간 2022-01~2026-05, 53.7개월)

| 안 | 설명 | CAGR | MDD | 누적 | ΔS0 | N | PF | 승률 | 저점자산 | 판정 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| **S0 (라이브 재현)** | TU/Range/Leading 우회 유지, Volatile/Trend_Down만 적용 | **+28.17%** | 24.71% | **29,900,585** | — | 83 | 1.61 | 37.3% | 7,615,442 | 기준 |
| S1 전경로 일관적용 | Loss Mode+PERF_LOW 를 TU/Range/Leading 에도 | +21.88% | 23.50% | 23,945,975 | -5,954,610 | 82 | 1.30 | 31.7% | 7,737,292 | ❌ REJECT(CAGR-6.3%p) |
| S2 완전제거 | Loss Mode+PERF_LOW 삭제 (=기존 버그와 동치) | +28.22% | 25.04% | 29,952,352 | +51,766 | 83 | 1.61 | 37.3% | 7,581,154 | ⚠️ 저점자산 -0.45%(노이즈 수준) |
| S3 강화(계단감점) | 3연패50%/5연패30%, 전경로 | +21.93% | 23.61% | 23,986,477 | -5,914,108 | 82 | 1.32 | 31.7% | 7,726,320 | ❌ REJECT(CAGR-6.3%p) |

### S0 vs 기존 버그(S2) 갭 — Volatile/Trend_Down 적용 효과 실측

Δ-51,767 (-0.17%, 8건 중 6건만 감점 발동) — **사실상 노이즈**. 이 경로 자체의 거래량이 4년간 8건뿐이라 버그 수정의 실질 영향은 미미.

### 최대 연패구간(6연패, 2022-04-01~2022-07-12) 자금곡선 — 핵심

| 안 | 구간낙폭 | 고점 재돌파 |
|---|---:|---:|
| S0 | -16.35% | 194일 |
| S1/S3(uniform) | -13.27%/-13.40% | 194일(1~2봉 단축, 유의차 없음) |

- 연패 중 사이징 축소(S1/S3)는 **해당 구간 낙폭만 -3%p 완화**. 반등 속도엔 실질 차이 없음(회복기 시작점이 얕아 절대 목표까지 거리가 짧았을 뿐).
- 그러나 **BULL'24 캡처가 +150.7%(S0) → +104.2%(S1/S3) 로 붕괴** — 축소된 TU/Range 사이징이 강세장 내내 지속 적용되며 상승분 자체를 갉아먹음. "지는 크기를 줄이는 대가로 이기는 크기도 준다" 가 그대로 확인됨.

### 판정: **S0(현행) 유지 — S1/S3 기각, S2 관찰 보류**

- S1/S3: 연패구간 방어(-3%p)가 BULL 캡처 손실(-46.5%p, CAGR -6.3%p, 누적 -5.9M)에 압도적으로 못 미침 → 절대수익 원칙 위반, 명확 기각.
- S2(완전제거): 누적/CAGR 미세 우위(+51,766/+0.05%p)이나 저점자산 -0.45%(노이즈 수준, 8건 표본) → 채택도 기각도 아닌 **현행(S0) 유지가 안전** (Volatile/Trend_Down 표본이 너무 작아 통계적 의미 없음). Loss Mode/PERF_LOW_RISK 코드 자체는 유지하되, "우회가 오히려 정답이었다"는 것이 이번 검증의 실질 결론.
- **핵심 발견**: 손실모드의 TU/Range 우회는 버그가 아니라 사실상 4년 검증을 통과한 설계였다. 우회를 없애려는 시도(S1/S3)는 정확히 AI Gate 패턴처럼 "그럴듯하지만 해로운" 개입.

### 산출

`bt_89_verdict.md` / `bt_89_key_numbers.md` / `bt_89_full.md`, `bt_89_trades_S0~S3.csv`. 시뮬 변경: `core/simulator.py`(`loss_mode_variant` cfg 훅: bypass/uniform/graduated/removed, 기본 None=기존 동작 무변경), `bt_85_entry_timing.py`(`run_case_85` 반환에 `eq_sr`/거래별 `lm_cons_loss`/`lm_mult`/`entry_pk` 필드 추가, 트레이드 CSV 컬럼 확장). **production 코드(`btc_bot_v290.py`) 무변경.**

---

## 2026-07-19 #90 [C세계]: ADX 조건부 정배열 선행 진입 (5안, 4년, v20.9.22 정합) — ❌ 전량 기각

베이스: B1(눌림목) + KS=K4(rolling_peak) = production v20.9.22 정합. 무손실 회귀: B1 = 29,952,352 / CAGR +28.22% / MDD 25.04% / N=83 (bt_87 K4 정확 일치).

### 설계

EMA 4H 정배열(ema21>ema55) 확인 후 진입 = 고점 추격(#85 진단). ADX 가 높으면 golden cross 완성 전에도 선행 진입(Leading path, 40% 사이징, 피라미딩 금지)을 허용해 진입가를 낮출 수 있는지 검증.

- G1: ADX≥27 & 정배열까지 ≤1% / G2: ADX≥27 & ≤2% / G3: ADX≥27 & ≤3% / G4: ADX≥35 & ≤2%(강한추세만)
- E1(대조군): 횡보장(Range regime) 신규 진입 전면 금지 — "더 사자"(G1~4) vs "덜 사자"(E1) 대조

### 결과 (기간 2022-01~2026-05, 53.7개월)

| 안 | CAGR | MDD | 누적 | ΔB1 | 거래수 | PF | 승률 | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| B1 (기준) | +28.22% | 25.04% | 29.95M | — | 83 | 1.61 | 37.3% | 기준선 |
| G1 | +14.80% | 22.81% | 18.39M | -11.56M | 87 | 1.46 | 34.5% | ❌ BULL24 미개선 |
| G2 | +18.36% | 21.11% | 21.04M | -8.91M | 92 | 1.51 | 35.9% | ❌ BULL24 미개선 |
| G3 | +18.06% | 23.61% | 20.81M | -9.14M | 92 | 1.52 | 34.8% | ❌ BULL24 미개선 |
| G4 | +27.90% | 25.04% | 29.62M | -0.33M | 85 | 1.57 | 36.5% | ❌ BULL24 미개선(중립에 가까움) |
| E1 | +15.79% | 20.61% | 19.10M | -10.86M | 60 | 1.51 | 33.3% | ❌ BULL24 미개선 + RANGE25 악화 |

### 선행진입(G90) 세부 — 메모리 "22% 승률" 경고 재확인 ✅

| 안 | 선행진입N | 승률 | 골든크로스 완성율(10일) | 완성시 승률 | 미완성시 승률 |
|---|---:|---:|---:|---:|---:|
| G1 | 18 | **22.2%** | 77.8% | 28.6% | 0.0% |
| G2 | 25 | **24.0%** | 72.0% | 33.3% | 0.0% |
| G3 | 25 | **24.0%** | 76.0% | 31.6% | 0.0% |
| G4 | 4 | 0.0% | 75.0% | 0.0% | 0.0% |

- 선행진입 승률 22~24% — 메모리 경고(조기 진입 승률 저조) **정확히 재현**. 골든크로스 자체는 72~78% 확률로 실제 완성되나(가짜 골든크로스는 소수), **완성돼도 승률 29~33%에 불과** — path 자체(Leading=P0 단일진입, 40% 캡, 피라미딩 금지)가 손실 구조.

### 핵심 발견 — 가설 반전 (RANGE/BEAR 무관, BULL'24 캐니벌라이제이션이 진범)

- **당초 가설(RANGE'25 손실 증가) 기각**: G1~G3 RANGE'25 는 오히려 B1(-3.1%)보다 소폭 개선(+1.1%/-0.4%/-0.4%). BEAR'22 도 소폭 개선(-19.8%~-22.0% vs B1 -23.2%).
- **실제 원인 = BULL'24 캐니벌라이제이션**: BULL'24 가 B1 +152.0% → G1~G3 +61~70% 로 붕괴(-82~91%p). 선행 진입이 이후 정상 EMA-path 진입(피라미딩 가능, 무제한 사이징)을 대체(path-substitution) 하면서 **더 큰 수익을 냈을 정상 진입 슬롯을 40% 캡 + 무피라미딩 Leading 진입이 선점** → 조기 진입일수록 손실이 아니라 "덜 번" 것이 지배적 손실 원인.
- G4(ADX≥35, N=4로 트리거 희소)만 거의 중립(-0.33M, -0.32%p) — 사실상 B1과 동일.

### 판정

**G1~G4 전량 기각, E1 기각, B1(production 현행) 유지.** 절대수익 원칙: BULL'24 미개선 + (E1은 RANGE25도 악화) → 채택 조건 불충족. 조기 진입 로직은 [[project_recovery_roadmap]] 기각 이력과 일치 (Recovery overlay 조기진입 시도 기각 재확인).

### 산출

`bt_90_verdict.md` / `bt_90_key_numbers.md` / `bt_90_full.md`, `bt_90_trades_{B1,G1~G4,E1}.csv`. 시뮬 변경: `core/simulator.py`(G90 ADX조건부 선행진입 훅 + E1 Range진입금지 훅, 둘 다 cfg 키 미설정 시 기존 동작 불변), `bt_85_entry_timing.py`(`run_case_85` extra_cfg/extra_mod 파라미터 추가, trades 반환 추가). **production 코드(`btc_bot_v290.py`) 무변경.**

---

## 2026-06-13 #87 [C세계]: Kill Switch 복구 설계 비교 (5안, 4년, B1 포함) — 🟢 K4 채택 권고 + 현행 K1 치명결함 발견

선행: **simulator 에 KS 구현** (bt_85RR 감사의 유일 불일치 항목 해소). MDD 20% / PF<0.7(n≥20) 트리거, 발동 시 신규 진입만 차단(보유 청산 유지). 베이스 = B1(눌림목) 포함 production v20.9.20 정합(E2 OFF / AI OFF / B2).

### 무손실 회귀 ✅
- **K0(KS 없음) = bt_85RR B1 정확 일치**: 26,096,924 / CAGR +24.28% / MDD 24.99% / N=86. 시뮬 KS 추가가 baseline 무변경 확인.

### 5안 결과 (기간 2022-01 ~ 2026-05, 53.7개월)
| 안 | CAGR | MDD | 누적 | ΔK0 | KS발동 | 복구 | 정지 |
|---|---:|---:|---:|---:|---:|---:|---:|
| K0 disabled | +24.28% | 24.99% | 26.10M | — | 0 | 0 | 0일 |
| **K1 permanent(현행)** | **-4.96%** | 21.00% | **7.99M** | **-18.11M** | 1 | 0 | **1342일** |
| K2 time(7일,×0.5) | +7.28% | 27.47% | 13.63M | -12.46M | 183 | 182 | 1274일 |
| K3 market(24h+가/EMA) | +27.31% | 24.64% | 29.02M | +2.92M | 103 | 103 | 193일 |
| **K4 rolling_peak(90일)** | **+28.22%** | 25.04% | **29.95M** | **+3.86M** | 132 | 132 | 151일 |

### 헤드라인 — 현행 K1 치명결함
- K1 은 **2022-09-28 단일 발동 → 영구정지(미복구) → 1342일 halt** → RECOVERY'23 +0% / **BULL'24 +0%** (K0 +152.0%, **-152%p 미참여**). K0 대비 누적 **-18.11M(-69%)**.
- 즉 현행 production 설계(MDD20% 영구정지·수동해제)는 **BEAR'22형 하락 1회로 강세장 전체를 잃는 구조**.

### K2 함정 (시간복구)
- 7일 후 재개하나 **전체기간 peak 기준 MDD 가 안 떨어져 매주 재발동(183회)** → 1274일 사실상 정지 + ×0.5 사이징으로 BULL'24 +61.9%만 포착. time-only 복구는 무효.

### K4 채택 근거 (절대수익 원칙)
- **롤링피크(90일)**: 정지 중 피크 자연감쇠 → MDD<10% 도달로 복구. BULL'24 +152% 완전 포착 + RECOVERY'23 **+58.6%**(K0 +38.2% 상회, 휩쏘 회피 재진입).
- 누적 **K0 +3.86M / K1 +21.96M**, MDD +0.05%p(중립). K3(시장복구)도 우수(+2.92M, MDD -0.35%p)하나 2조건 복합 → 단순성·수익 K4 우위.
- 판정: 1순위 누적 최대(손실 최소) + MDD 보호 유지(악화 없음), 동률 시 단순한 안.

### 산출
`bt_87_verdict.md` / `bt_87_key_numbers.md` / `bt_87_full.md`, `bt_87_trades_K0~K4.csv`. 시뮬 변경: `core/simulator.py`(KS K2/K3/K4 복구모드), `bt_85_entry_timing.py`(KS 통계 반환). 후속: K4 production 적용은 별도 설계·검증(현재 미배포, production 무변경).

---

## 2026-06-12 #85-RR [C세계]: B1 눌림목 최종 재검증 (E2 OFF, production-audited) — 🟢 채택 후보 (#85-R 기각 번복)

### 배경

#85-R 은 **E2 ON** 베이스라인으로 B1(눌림목 EMA21 +1.5%)을 기각. 그러나 production(v20.9.19)은 **E2 OFF**(`E2_ENABLED=False`, v20.9.10~). 코드 주석 "v20.9.17 프로덕션 E2 ON 정합"은 **오기**(E2_BLOCK_MODE 상수만 보고 E2_ENABLED 미확인). → production 정합(E2 OFF) 베이스라인으로 B0 vs B1 최종 재측정.

### 파일

- `backtest/bt_85RR.py` (B0/B1 + 전제 감사 + 회귀 + 승률 diff + 절대수익 판정)
- 산출: `results/bt_85RR_{verdict,key_numbers,full}.md` + `bt_85RR_trades_{B0,B1}.csv`

### 전제 감사 (필수 선행)

- sim BASE85(E2 OFF) ↔ production v20.9.19 **항목별 대조 22개 중 21개 일치**. 유일 차이 = kill_switch(sim disabled) — B0/B1 공통이라 Δ 무편향. E2 O3/gap 예외는 production=True이나 **E2 OFF라 미발동** → sim(False)과 동일 결과.
- **B0 회귀 ✅ 정확 재현**: CAGR +20.25% / MDD 34.51% / N=95 = #85 원판값 일치.

### 결과 (6지표)

| | CAGR | MDD | 누적 | 승률 | PF | N | Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | +20.25% | 34.51% | 22.56M | 36.8% | 1.39 | 95 | 1.09 |
| B1 | +24.28% | 24.99% | 26.10M | 36.0% | 1.56 | 86 | 1.28 |
| Δ | **+4.03%p** | **-9.52%p** | +3.53M | -0.8%p | +0.18 | -9 | +0.19 |

### 4구간

- BEAR'22 +8.94%p · RECOVERY'23 -12.38%p · BULL'24 **+24.27%p** · RANGE'25 +0.62%p. 순효과 = BULL'24·BEAR'22 우위가 RECOVERY 손실 압도.

### 승률 Δ -0.8%p 출처

- 진입 치환(눌림목 대기)으로 B0 95건 → B1 86건. 공통 진입봉 50, B1 고유 36(손28/익8), B0 고유(B1 미진입) 45(손33/익12). 고점추격 손실 회피 > 일부 승리 회피. 순효과는 CAGR/MDD가 대변.

### 판정: 🟢 **채택 후보 (B1)** — 절대수익 우선 원칙

- CAGR↑(+4.03%p) **AND** MDD↓(-9.52%p) 동시 우위 → 승률 -0.8%p는 기각 사유 아님(사용자 원칙).
- #85-R(E2 ON) 기각은 **비프로덕션 베이스라인** 기반 → 본 재검증이 production 정합 결론.
- 부수 확인: **bt_86 C0~C2 E2 OFF 재실행 → 청산 결론 유지**(C0 PF 1.39 > C1 1.33 / C2 1.31, `results/bt_86_e2off_result.md`). 진입(B1) 변경과 청산은 독립.
- `bt_ai_value_4year.md` 환경 정정(E2 ON 측정 명시, 결론 불변) 주석 추가.

### 후속 액션

- B1 production 적용은 **별도 사용자 승인 필요**(진입 로직 변경). 적용 시 라이브 점진 도입 + kill_switch 라이브 영향 모니터링 권장. 단독 적용 전 #63 path-substitution(진입 치환) 재점검.

---

## 2026-04-24 #62: Range/Volatile regime 전용 exit 로직 선행 분석 (Phase 1 only) — 🔴 연구 종료

### 배경

회복기(2023) 수익 저조 원인을 "Range/Volatile regime 전용 exit 로직 부재"로 가정하고 Phase 2 본 백테스트 (R1~V3, C1~C2 9 cases) 전 선행 분석 수행. 메모리 `feedback_param_tuning_rejected` (exit 튜닝 #47 기각) + `project_recovery_roadmap` (회복기 구조적 한계 수용) 기조와의 정합도 검증.

### 파일

- 분석 스크립트: `/tmp/phase1_analysis.py`
- 결과: `backtest/results/bt_regime_exit_tuning_phase1.md`
- 입력: `bt_recovery_regime_trades.csv` (B0 only, 68 trades, 52mo 2022~2026-04)

### Phase 1 핵심 발견

1. **Volatile ATR손절 비중 = 1/9 (11%)**. "공통 ATR이 Volatile에 과민"이라는 사전 가설 기각. Volatile은 트레일링 8/9 주력 구조.
2. **Range ATR손절 평균 MFE = 0.42%** — 진입 직후 즉시 역배. 손절 완화(R2)로 건질 여지 없음.
3. **TU/Range/Volatile 손실거래 MFE 분포 동일 패턴** (평균 1.5~1.9%, MFE≥1% 50~56%). "수익→손실 전환"은 regime 특성이 아닌 4H 전략 구조 특성. TU가 전용 로직 있어도 동일 패턴.
4. **Range의 계단손절(평균 +6.52%, 승률 50%)은 이미 "Range 전용 exit 역할" 수행 중**. R1 (트레일링 부분 허용)이 이를 교란할 risk.
5. **Early bars (R3/V3) 표본 무의미**: Range hold≤5 = 2/27 (7%), Volatile hold≤5 = 0/4.
6. **회복기 Range+Volatile 손실 9건 중 개선 여지 있는 거래 2~3건** (MFE 1.83~2.43% 계단손절). 이론 최대 개선폭 **+3~5%p** (GO 기준 +3%p 간신히).

### 6 가설 판정

| 가설 | 판정 | 기각 근거 |
|---|:---:|---|
| R1 Range 트레일링 TP1 이후 | 🟡 | 기대+3~5%p, 계단(+6.52%) 교란 risk |
| R2 Range 초기 손절 × 1.5 | 🔴 | ATR 손절 MFE 0.42%, 즉시 역배 |
| R3 Range early_bars=3 | 🔴 | hold≤5 2/27 통계 무의미 |
| V1 Volatile 전용 trail_m | 🔴 | 회복기 Volatile 손실 2/3 이미 트레일링, 완화시 손실 키움 |
| V2 Volatile 전용 stop_m | 🔴 | Volatile ATR손절 1/9, 발동 희소 |
| V3 Volatile early_bars=3 | 🔴 | Volatile hold≤5 = 0 |

### 판정: 🔴 연구 종료

- 6개 가설 중 5개 Phase 1에서 기각. R1만 미약 여지.
- Phase 2 (40분 투입) 기대 성과 낮음 + 메모리 기조 (`feedback_param_tuning_rejected`, `project_recovery_roadmap`)와 부합.
- 구조적 발견: "손실거래 MFE 패턴"은 regime 전용 로직으로 풀리지 않음.

### 후속 액션

- #62는 `improvement_todo.md`에 "관찰 완료"로 아카이브.
- 회복기 개선은 로드맵대로 Shadow AI 평가 (5월 중순) → AI 교체 순서 유지.
- 대안 축: entry timing (Range ATR손절 MFE=0.42% 시사 "초기 진입점 자체 나쁨" 가설).

---

## 2026-04-24 #59: A (O3 제거) robustness 검증 (T1~T5) — 🟡 조건부 채택 / 과적합 기각 but T5 불일치

### 배경

#58 A (O3 완전 제거) 1순위 도출 후 검토: 2023 회복 +30.45% 중 2023-01-05 gap+score 예외 단일 거래 +32.38%p 비중. 구조적 개선인지 단일 대박 아티팩트인지 확정.

### 파일

- 스크립트: `backtest/scripts/bt_a_robustness.py`
- 결과: `backtest/results/bt_a_robustness.md` / `bt_a_walk_forward.csv` / `bt_a_random_start.csv`
- 시뮬 변경: `backtest/core/simulator.py` — `mod["skip_entry_mask_a"]` hook 추가 (특정 봉 신규 진입 차단, exit/pyramid 무영향)

### 5 테스트 결과

| Test | 결과 | 판정 |
|------|------|:---:|
| **T1** 2023-01-05 거래 skip → A | CAGR Δ+2.77%p (원 Δ+2.78%p, final 30.22M vs 30.23M) | ✅ |
| **T2** 6mo walk-forward × 9 윈도우 | A 우위 5/9 (56%) | 🟡 |
| **T3** 100 random 12mo starts | A 승률 77/100, 평균 Δ +4.80%p, t≈9.24 | ✅ (통계 유의) |
| **T4** 2023 회복기 제외 (stitched) | A +27.47% vs B0 +27.34%, Δ+0.13%p | 🟡 |
| **T5** B0 O3 12건 순기여 | +5.17% (WR 33%, PF 1.20) — win 2건 (+14.42%, +10.77%) 이 지배 | ❌ (net negative 불일치) |

### 핵심 인사이트

1. **T1 의외 결과 — 단일 거래 의존 기각**: A_T1 (2023-01-05 skip) = CAGR +29.37% vs 원 A +29.38%. 거의 불변. **A의 2023 회복 +30.45%는 단일 대박이 아닌 여러 진입 (EMA 경로 + gap+score 3건 포함) 의 합산 효과**. 실제 2023-01-05 gap+score 예외 진입의 equity 기여는 <1만원 규모 (40% 사이징 × 당시 자본 × 32% PnL). 과적합 가설은 기각.

2. **T3 통계 유의성 강함 (t=9.24)**: 100 random 12mo window 에서 A 승률 77%, 평균 Δ CAGR +4.80%p, std 5.20%. one-sample t ≈ 9.24 >> 2 → **A 우위는 무작위 아님**.

3. **T2/T4 — 개선의 회복기 집중**: 
   - T2: 2023 H1 (+27.25%p A 우세) 이 dominant. 2023 H2 는 오히려 B0 +16.12%p 우세 (BULL 전환 O3 기여).
   - T4: 2023 제외 시 A ≈ B0 (Δ+0.13%p). **A의 CAGR edge 대부분은 2023 회복기에서 발생**.
   - 결론: A의 구조적 개선은 실재 but **deep bear→recovery regime 조건부**.

4. **T5 O3 net-negative 주장 기각**: B0의 O3 경로 12건 합산 PnL = +5.17% (PF 1.20, WR 33%). O3 자체는 net-positive. 단 승 2건 (2022-03-14 +14.42%, 2026-04-02 +10.77%) 이 지배 — 제거 시 -20.08%. **O3는 저 WR + 고 variance**. #57 "O3 net-negative" 주장은 부정확 — O3 는 **자본/시점 기회비용** 관점에서 열위 (A가 같은 자본을 더 나은 경로로 활용).

5. **2023 H2 역전 이유 (T2)**: 2023-07 ~ 2024-01 구간에서 B0 +51.46% vs A +35.34% (-16.12%p). BULL 전환 초기 O3 신호 (Range 저점 sweep 후 회복) 가 BULL 캡처 기여. O3 제거 = 이 구간 기회 상실.

### GO 기준 (task 정의)

| 조건 | 값 | 통과 |
|------|-----|:---:|
| T1 Δ CAGR ≥ +1.0%p (대박 제거 후) | +2.77%p | ✅ |
| T3 승률 ≥ 55% | 77% | ✅ |
| T5 O3 순효과 < 0 | +5.17% | ❌ |

→ **🟡 조건부 채택** (2/3 통과, T5 불일치)

### 권고

- 🟡 **조건부 채택 — 즉시 프로덕션 반영 보류**:
  - A의 구조적 개선은 실재 (T1/T3 확증) but 효과는 **deep bear → recovery regime 조건부** (T4). 현재 2026-04 시장 = 2025-10 이후 하락→재회복 초기 국면으로 A 가 유리한 regime 일 수 있으나, 향후 강세장에서 B0 (O3) 기회비용 상쇄.
  - T5 O3 순기여 +5.17% 은 BULL 전환 (2022-03, 2026-04) 에 집중 → 완전 제거 시 그 기회 상실.
- 🟢 **배포 시나리오 (권장)**:
  1. **Shadow 모드 A/B 병행**: 수개월 실거래 A vs B0 비교. Shadow AI 평가 (5월 중순) 와 병행.
  2. **조건부 비활성** (대안): O3 예외 경로를 "특정 regime (강한 하락 후 초기 반등) 외 비활성" 로 조건부 전환 고려 (추가 #60 연구 필요, 단 #45~#48 기각 패턴 고려 시 신중).
  3. **배포 보류**: #57 권고대로 Shadow AI → Phase 3 AI 교체 진행이 우선.
- 🔴 **과적합 가설 기각** — T1/T3 로 A의 구조적 개선 근거 확증. #58 의 A 도출은 단일 거래 아티팩트 아님.
- **MEMORY.md 로드맵 유지**: Shadow AI (5월 중순) → Phase 3 AI 교체 권고 (A 배포는 Shadow 평가 후).

### 시뮬 변경

`backtest/core/simulator.py`: `mod["skip_entry_mask_a"]` (bool array) hook 추가. True 인 ai 에서는 신규 진입 (main + MR) 차단, 기존 포지션 exit/pyramid 무영향. 프로덕션 코드 미반영.

### 산출물

- `backtest/results/bt_a_robustness.md`
- `backtest/results/bt_a_walk_forward.csv` (9 윈도우)
- `backtest/results/bt_a_random_start.csv` (100 시도)

---

## 2026-04-24 #58: O3 제거 + gap+score 변형 + G8 개선 통합 (8 케이스, 52mo) — 🟢 A (O3 OFF) 채택 후보 / G8 전면 기각

### 배경

#57 도출 3가지 가설 검증:
1. O3 예외가 net-negative (G5=rec 1.0% 최고, O3 거의 비활성)
2. O3 완화는 BULL 캡처 희생 (#57 G4/G6/G7)
3. G8 (30봉 저점+상승전환)은 BEAR 오발 악화

### 파일

- 스크립트: `backtest/scripts/bt_o3_removal_grid.py`
- 결과: `backtest/results/bt_o3_removal_grid.md` / `.csv` / `bt_o3_removal_trades.csv`
- 시뮬 변경: `backtest/core/simulator.py` — `e2_g8_trigger_enabled` / `e2_g8_require_bars` cfg 추가 (E2 예외 경로에 G8 통합, 40% 사이징 공유)

### 결과표

| case | 정의 | CAGR% | MDD% | 2022 | 2023 | 2024 | 2025 | 예외 PF | 판정 |
|:---:|------|------:|-----:|-----:|-----:|-----:|-----:|--------:|:---:|
| B0 | O3 on (20/0.5%) gap=180d | +26.60 | 20.81 | -8.96 | +19.31 | +162.03 | -3.18 | 2.06 (16) | base |
| G5 | O3 on (20/1.0%) gap=180d | +29.05 | 19.56 | -6.40 | +30.45 | +164.05 | -7.25 | 2.43 (7) | 🟢 GO |
| **A** | **O3 OFF gap=180d** | **+29.38** | **19.56** | **-5.43** | **+30.45** | **+165.14** | -7.57 | 5.82 (4) | **🟢 GO** |
| C | O3 OFF gap=90d | +27.97 | 19.56 | -11.73 | +30.45 | +165.14 | -5.47 | 1.52 (17) | 🔴 REJ |
| D | O3 OFF gap=120d | +28.09 | 19.56 | -9.46 | +30.45 | +165.14 | -7.47 | 1.88 (11) | 🟢 GO |
| E | O3 OFF gap=180d G8+bars≥90 | +27.20 | 20.39 | -13.72 | +27.97 | +166.91 | -4.59 | 1.66 (31) | 🔴 REJ |
| F | O3 OFF gap=180d G8+bars≥180 | +27.26 | 19.92 | -13.22 | +27.97 | +165.14 | -4.32 | 1.54 (27) | 🔴 REJ |
| G | O3 OFF gap=120d G8+bars≥90 | +26.01 | 23.11 | -17.13 | +27.97 | +166.91 | -4.59 | 1.51 (32) | 🔴 REJ |

(B0 대비 Δ: A Δ2022 +3.54%p, Δ2023 +11.14%p, Δ2024 +3.11%p, ΔCAGR +2.78%p, ΔMDD -1.25%p)

### 핵심 인사이트

1. **A (O3 완전 제거) 전 지표 최고** — 5/6 GO 기준 통과 + 예외 경로 PF 5.82 (gap+score 4건만, 모두 180d 이후). G5 대비 CAGR +0.33%p, 2022 BEAR +0.97%p 개선. O3 경로 3건 (G5) 중 WR 0% → O3 자체가 net-negative 확증.

2. **A ≈ G5 분석** — 회복기 수익 원인: G5의 2023 +30.45%는 O3 기여가 아닌 **EMA 경로 + gap+score 예외 4건 (PF 5.82)** 에서 발생. G5 O3 경로 3건 모두 손실 (#57 대조 재현). A의 CAGR가 G5보다 약간 높은 것은 O3 손실 3건 제거 효과.

3. **gap+score 단축 부작용** — C (90d): 2022 -11.73% (-2.77%p 악화, REJECT). D (120d): -9.46% (-0.50%p, 경계선 GO). 90→120d에서 오발 8→5건, 120→180d에서 5→4건. **180d 이상 유지가 BEAR 방어 필수**.

4. **G8 전면 기각** — E/F/G 모두 BEAR22 -4~-8%p 악화, 회복기 2023 +27.97% (vs A +30.45%, -2.48%p 감소). G8 신호 총 2112건 중 BEAR22 457건 (B0 O3 대비 10배). bars≥90/180 가드로도 BEAR 오발동 차단 불가 — **30봉 저점±3%+상승전환 조건은 회복기와 BEAR 재반등을 구별 못함**.

5. **03-09 커버 실패 (전 case ❌)** — 2023-03-09 SVB 쇼크 반등은 어떤 예외 경로로도 커버 못함 (F2 E2 활성 중 gap+score 조건(gap≤-10% & score≥4) 미충족 + 180/120/90 bars 가드와 무관). 회복기 조기 진입은 이번 grid 로는 해결 불가.

### 권고

- 🟢 **A 채택 후보** — v20.9.9 또는 v21 로 프로덕션 반영 검토:
  - `E2_O3_EXCEPTION_ENABLED = False` (O3 예외 경로 완전 제거)
  - gap+score 180d 유지
  - G8 불채택
- 🟡 **D는 보수 대안** — gap=120d가 CAGR/2022 tradeoff 허용 가능하면 선택지. 단 2022 -0.50%p 마진이 얇아 OOS 리스크.
- 🔴 **#58 종료** — G8/gap 단축/O3 grid 3축 모두 소진. 추가 E2 예외 경로 최적화 기각.
- 🟢 **MEMORY.md 로드맵 유지** — Shadow AI (5월 중순) → Phase 3 AI 교체 진행.

### 시뮬 변경 (프로덕션 미반영)

`backtest/core/simulator.py`:
- cfg: `e2_g8_trigger_enabled` (bool), `e2_g8_require_bars` (int)
- mod: `g8_trigger_a` (bool array)
- 동작: E2 차단 상태에서 G8 신호 + bars_since_e2 ≥ require → gap+score 경로와 동일한 40% 사이징 bypass
- stats: `e2_g8_attempts`, `e2_g8_entries`, trade에 `e2_exception_triggers = [..., "g8"]`
- A/C/D 케이스는 기존 `e2_o3_exception=False` 만으로 구현 가능 (별도 추가 없음)

### 산출물

- `backtest/results/bt_o3_removal_grid.md`
- `backtest/results/bt_o3_removal_grid.csv`
- `backtest/results/bt_o3_removal_trades.csv` (G5 2023 회복기 14건 + 전 case E2 예외 진입)

---

## 2026-04-24 #57: O3 grid search + PASS 봉 검증 — 🟡 G5 (rec=1.0%) 재검토 / O3 자체 비효율 시사

### Branch 1: PASS 봉 검증 (#56 analyzer 보강)

**결론**: 🟢 **논리 버그 아님** — #56 analyzer가 gate=PASS 로 분류한 15개 봉 전원이 실제 시뮬에서 **VWAP 차단** (Volatile regime에서 `price <= vwap20`) 으로 진입 못함. #56 analyzer에 VWAP / OBV block / close-prev gap 3개 gate가 누락되어 있었음.

**산출**: `backtest/scripts/verify_pass_bars.py`, `backtest/results/pass_bars_verification.md`

### Branch 2: O3 Grid Search (9 케이스, 52mo)

**파일**: `backtest/scripts/bt_o3_grid.py` / `backtest/results/bt_o3_grid.md` / `bt_o3_grid.csv`

**Config**: V42_BASE (KS OFF) + F2 block + E2b+6mo 예외 (O3 + gap_score_180d) + AI Gate OFF / 52mo / 원본 precompute_o3 100% 정합 확인

**Grid (lookback × min_recovery)**:

| Case | lookback | rec | 2022_BEAR | 2023_회복 | CAGR | O3 firings | O3-exc n/PF | 판정 |
|---|---|---|---|---|---|---|---|---|
| **B0** | 20 | 0.5% | -8.96 | +19.31 | +26.60 | 172 | 12 / 1.20 | base |
| G1 | 10 | 0.5% | -12.65 | +19.31 | +24.48 | 224 | 14 / 0.78 | 🔴 REJ |
| G2 | 15 | 0.5% | -9.00 | +19.31 | +26.04 | 189 | 13 / 1.09 | 🟡 NO |
| G3 | 30 | 0.5% | -9.87 | +19.31 | +25.09 | 137 | 8 / 0.60 | 🔴 REJ |
| G4 | 20 | 0.3% | -11.91 | +18.04 | +21.72 | 226 | 15 / 0.90 | 🔴 REJ |
| **G5** | 20 | **1.0%** | **-6.40** | **+30.45** | **+29.05** | 82 | 3 / 0.00 | **🟡 REJ (sample 이슈)** |
| G6 | 10 | 0.3% | -16.20 | +18.04 | +19.45 | 308 | 17 / 0.61 | 🔴 REJ |
| G7 | 15 | 0.3% | -11.95 | +18.04 | +21.00 | 255 | 16 / 0.84 | 🔴 REJ |
| G8 | 30±3%+상승전환 | - | -14.46 | +24.39 | +21.65 | 2112 | 42 / 1.50 | 🔴 REJ |

### 핵심 인사이트 (자동 판정 너머)

1. **G5 이상치**: 5/6 GO 기준 통과 (CAGR +2.45%p, 2023 회복 +11.14%p, 2022 BEAR +2.56%p 개선, MDD -1.25%p, BULL +2.02%p). O3-예외 PF=0만 실패하나 **n=3으로 통계적 의미 없음**. 실질적으로 "O3를 거의 꺼놓은" 상태이며, 이때 전략이 오히려 개선된다는 것은 **O3 자체가 net-negative** 임을 시사.

2. **#42 재확인과 교차**: 
   - E2a (예외 없음): 2023 +12.72%
   - E2b (O3 only): 2023 +12.72% ← **O3 alone gives ZERO recovery improvement**
   - E2b+6mo (O3 + gap_score): 2023 +19.31%
   - **회복기 alpha 전체가 gap_score + 180d 경로에서 나옴. O3는 오히려 BEAR에서 low-quality 진입으로 손해**

3. **G8 (O3 재설계)**: 03-09 gap 8봉 커버 성공, O3-예외 PF 1.50 통과. 그러나 O3 총 발동 2112 (B0 × 12), BEAR22 오발 457 (B0 × 10) → **2022 BEAR -14.46%**, BULL -33%p. **조건 재설계는 전면적 오발동 초래**.

### 권고

- 🔴 **O3 파라미터 grid 최적화 기각** — lookback/rec 조정은 결정적 개선 불가
- 🟡 **#58 후보: O3 제거 또는 극도 엄격화 연구** — G5 인사이트 심화. 두 옵션:
  - (a) **O3 완전 비활성** (`e2_o3_exception=False`) + gap_score 단독으로 BEAR 예외 처리
  - (b) **O3 rec ≥ 1.0% 유지** (G5 수준, 실질 비활성화에 근접)
  - 가설: gap_score (180d + gap < -10% + score > 4) 만으로 회복기 진입 커버, O3의 BEAR 오발동 완전 제거
- 🟢 **MEMORY.md 회복 로드맵 재확인**: Shadow AI 평가 (5월 중순) → Phase 3 AI 교체. 외부 신호 후순위.

### 기록

- `pass_bars_verification.md` (Branch 1 검증 MD)
- `bt_o3_grid.md` / `bt_o3_grid.csv` (Branch 2)

### 시뮬 변경

없음 (원본 precompute_o3 보존, grid 전용 헬퍼만 bt_o3_grid.py 내에 정의).

---

## 2026-04-24 #56: 재진입 Gate 병목 분석 — 🔴 단일 gate 완화 NO-GO / O3 threshold 연구 여지

### 배경

#55 trades.csv 에서 청산 → 재진입 gap 수십 %p 기회 손실 확증. 각 gap 봉에서 **어느 gate가 진입을 막았는지** bar-by-bar 식별.

### 방법

신규 시뮬 없음. #42 precompute + XGB 모델 재사용. 2023 3 케이스 (E2b+6mo, M2/AY, E2a) × 각 gap 봉 × 7 gate 평가:
- COOLDOWN / E2_BLOCK / REGIME_DOWN / AI_GATE / EMA / SCORE / MISC(RSI/BB)

### 핵심 발견

**(A) Gate는 고도 중첩** (E2b+6mo 685 gap 봉 기준, 독립 빈도):
- EMA 실패 87% / AI Gate 실패 67% / SCORE 실패 63%
- REGIME_DOWN 38% / E2_BLOCK 25% / COOLDOWN 2%

**(B) Primary cascading 분포**: AI_GATE 28% · REGIME_DOWN 27% · E2_BLOCK 25% · EMA 14%

**(C) 단일 gate 해제 효과 미미**:
| 해제 | 신규 PASS 봉 | 증가 |
|---|---|---|
| EMA | 14 | +9 |
| REGIME_DOWN | 13 | +8 |
| SCORE | 11 | +6 |
| AI_GATE | 10 | +5 |
| COOLDOWN | 5 | +0 |

baseline 5봉 → 어느 gate 하나만 해제해도 최대 19봉 (3%) 회복. **단일 완화 효과 무의미**.

**(D) 주요 missed run (03-09 → 03-15, BTC +13.37%) = E2_BLOCK 18봉 중심**:
- 3월 초 BTC 29M → 26.8M 하락 (F2 BEAR 활성) → 03-11 반등 시작 → 03-13 31.5M 도달
- 이 구간 내내 E2_BLOCK ON + O3 signal 미발동
- O3 signal 조건 (20-bar low break + 0.5% recovery) 이 3월 반등 패턴 누락

### 시나리오 판정

| 시나리오 | gate | 단독 PASS | 판정 |
|---|---|---|---|
| A: EMA 정배열 대기 | EMA | +14 | 🟡 부분 (R1/R2 기각으로 직접 불가) |
| B: 쿨다운 | COOLDOWN | +5 | 🔴 미미 |
| C: Score 하락 | SCORE | +11 | 🟡 부분 |
| D: AI Gate | AI_GATE | +10 | 🟡 부분 |
| E: E2_BLOCK | - | 의도된 안전 | ⚪ 완화 시 BEAR 방어 훼손 |
| F: REGIME_DOWN | - | 의도된 안전 | ⚪ 완화 불가 |

### GO/NO-GO 종합

🔴 **단일 gate 완화 NO-GO** — gate 중첩으로 효과 3% 이내

🟡 **O3 threshold 조정 연구 여지** — 03-09 gap 사례에서 O3 미발동이 주범. O3 조건 완화 (예: 30-bar low + 0.3% recovery) 별도 백테스트 필요

### 권고

- 🔴 **EMA / AI / Score 개별 완화 실험 기각** — 효과 3% 이내
- 🟡 **O3 signal 조건 grid search** (회복기 3월 패턴 캡처) — 별도 연구 (#57 후보)
- 🟢 **#55 청산 완화 + O3 조건 완화 = 회복기 개선 투-트랙**

### 산출

- `backtest/scripts/analyze_reentry_gates.py`
- `backtest/results/reentry_gate_analysis.md`
- `backtest/results/reentry_gate_bars.csv` (2110행 × 케이스 3 × gap 봉 all)

### 시뮬 변경

없음.

---

## 2026-04-24 #55: 2023 회복기 Exit 패턴 분석 (4+1 케이스) — 🟡 청산 완화 v21 연구 GO

### 배경

#42 E2b+6mo 2023 +19.31% vs E2a +12.72% (+6.59%p), #52 AY 2023 +20.14% vs B0 +13.67% (+6.47%p) — 수익 차이 3가지 가설 분리 검증:
1) 17일 빠른 진입 효과
2) 예외 경로 추가 진입 기여
3) 잦은 손절/익절로 인한 기회 손실

### 방법

신규 시뮬 없음 — #42/#52 precompute 재사용, 5 케이스 재실행 후 2023 거래만 추출해 분석.

| case | 설정 | 2023 거래 | 2023 PnL |
|---|---|---|---|
| E2a (#42) | F2 block, 예외 없음, KS OFF | 20 | +41.65%p |
| E2b+6mo (#42) | F2 block + O3 + gap+score, KS OFF | 21 | +70.86%p |
| M1/B0 (#52) | F10 block + 예외, KS auto | 19 | +67.37%p |
| M2/AY (#52) | F2 block + 예외, KS auto | 20 | +70.34%p |
| E2-OFF (#42) | 차단 없음, KS OFF (참고) | 20 | +71.80%p |

### 핵심 발견

**가설 1 (17일 조기 진입) — 🟢 #42 gap의 전부**
- E2b+6mo gap +29.22%p vs 01-05 Trend_Up 예외 진입 단일 거래 +32.38%p → **설명력 111%**
- 01-05 이후 20건은 E2a와 거의 동일 (trade sequence 공유, Feb 이후 모든 거래가 매칭됨)

**가설 2 (예외 경로) — 🟢 17일 효과와 동전의 양면**
- E2b+6mo 예외 거래 1건만 (2023-01-05), 나머지는 예외 아님
- 따라서 예외 ≡ 17일 효과

**가설 3 (청산 완화 여지) — 🟡 gap 설명 아님, 그러나 공통 upside 존재**
- 5 케이스 전체에서 HARD (MFE≥+3% & pnl≤0) 평균 **5건 / -7%p**, SOFT (pnl < 0.5×MFE) 평균 **3~4건 / +11%p**
- 이론상 회수 상한 HARD+SOFT ≈ **+55%p** (회복기 한정)
- 하지만 양쪽 쌍(#42/#52)에서 모두 공통으로 발생 → gap 설명에는 기여 X
- 실제 trigger는 Feb 2~5월 변동성 구간의 ATR/계단 손절 반복 (2023-02-25 -3.61, 03-07 -2.94, 05-09 -3.80, 05-19 -3.19, 05-29 -3.07 등)

**Whipsaw**: 5봉 이내 exit + 즉시 재진입 = **0건** → 빠른 재진입 아닌, **개별 trade의 stop 조기화**가 문제

### GO/NO-GO 판정

| 방향 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 청산 완화 (회복기) | HARD≥20% OR gap≥5%p | HARD 19~25% / gap ~55%p | 🟢 GO |
| 예외 경로 확장 | 예외 PnL ≥ +5%p | 1건 +32.38%p | 🟢 이미 작동, 추가 확장은 별도 |
| 17일이 전부? | ≥70% of gap | **111%** | 🟢 #42는 17일 단일 거래가 전부 |

### 결론

1. **#42 +6.59%p gap의 본질 = 회복기 첫 진입 1건** (2023-01-05 Trend_Up O3 예외). Feb 이후 20건은 trade 공유.
2. **#52 +6.47%p gap** (AY vs B0): 양쪽 모두 01-05 진입, **F5 제거로 M1 손실 5건 회피**가 주 원인 (#52에서 이미 규명).
3. **회복기 청산 완화는 orthogonal upside** — gap 설명엔 기여 안 하나, 모든 케이스에 ~-7%p (HARD) + (SOFT 미회수 peak ~11%p) 공통 기회 존재.

### 권고

**v21 후보**:
- 🟢 **청산 완화 (회복기 한정)**: HARD 패턴 집중 분석 후 ATR_STOP 확대 / 트레일링 lag 증가 실험
- 🟢 **E2b+6mo 유지 확정**: 17일 조기 진입이 핵심 메커니즘이므로 현 규칙 유지
- 🔴 **예외 경로 추가 확장 기각**: 이미 회복기에 1건만 작동, 나머지 확장은 오히려 BEAR 진입 위험
- ⚪ **trade-level 차이 (#52 F5)**: 이미 AY (F2 단독)로 해결됨

### v21 다음 연구 과제

- **청산 완화 실험**: HARD 5건 (ATR 13건, 계단 19건, 트레일링 20건 중 MFE≥3% & pnl≤0) 세부 패턴 분석 → 회복기 탐지 플래그 하 청산 파라미터 상향 grid search
- **Recovery flag**: `bars_since_e2 ∈ [1080, 2160]` 또는 daily_ema200_gap_pct ∈ [-15%, 0%] 구간에서만 완화 적용

### 산출

- `backtest/scripts/analyze_2023_recovery_exits.py`
- `backtest/results/recovery_2023_exit_analysis.md`
- `backtest/results/recovery_2023_trades.csv` (100건)

### 시뮬 변경

없음 (기존 precompute 재사용).

---


## 2026-04-14 #20: 트리플 배리어 + 김프 + 고확신 부스트 + O3 관리
- **파일**: `backtest/backtest_v20_combined.py`
- **결과**: `backtest/results/backtest_v20_combined_result.md`
- **기준**: v19.9 production
- **목적**: AI 품질(트리플 배리어) + 한국 특화(김프) + 자본 배분(고확신) + O3 최적화

### A파트: 트리플 배리어 라벨링 (핵심 발견)
| ID | 상단/하단/시간 | BULL | BEAR | 최종자산 | MDD | 판정 |
|:--:|-------------|----:|----:|--------:|---:|:----:|
| B0 | +1.2%/없음/8봉 | +13.02% | -9.36% | 10,244K | 16.6% | - |
| **TB1** | +1.2%/-2.5%/8봉 | +16.48% | **-1.96%** | **11,432K** | **13.3%** | **⭕** |
| **TB2** | +1.2%/-3.5%/8봉 | +16.62% | **-2.07%** | **11,421K** | **13.2%** | **⭕최적** |
| TB3 | +1.2%/-5.0%/8봉 | +14.22% | -2.07% | 11,185K | 13.2% | ⭕ |
| TB4 | +1.5%/-2.5%/8봉 | +11.01% | -3.52% | 10,710K | 13.1% | △ |
| TB5 | +1.2%/-2.5%/12봉 | +15.02% | -4.00% | 10,742K | 13.1% | △ |

**트리플 배리어 라벨링 효과 (TB1~TB3)**:
- **BEAR: -9.36% → -2.07% (+7.29%pp)** — 라벨링 품질 개선이 BEAR 방어에 직접 기여
- BULL: +13.02% → +16.62% (+3.60%pp) — 동시에 BULL도 개선
- MDD: 16.6% → 13.2% (-3.4%p)
- 샘플 204개 → 1504개 (+637%) — 모호한 샘플 제거 대신 모두 라벨링
- B0 양성 중 -2.5% 터치: 단 3.1% → 현재 라벨링의 noise는 제한적이나, TB가 더 많은 샘플을 생성

### B파트: 김치 프리미엄 Modifier
| ID | 조건 | BULL | BEAR | 최종자산 | 판정 |
|:--:|------|----:|----:|--------:|:----:|
| K1 | 김프>5% 차단 | +12.94% | -9.24% | 10,228K | △ |
| **K2** | **김프>3% ×0.5** | **+13.83%** | **-4.17%** | **10,921K** | **⭕최적** |
| K3 | 김프<-1% ×1.2 | +13.42% | -8.04% | 10,463K | △ |
| K4 | K1+K3 | +13.35% | -7.93% | 10,483K | △ |
| K5 | 김프3일 급등 차단 | +10.50% | -10.22% | 9,958K | ❌ |

**K2 (김프>3% 사이징 축소)**: BEAR -4.17% (B0 -9.36% 대비 +5.19%pp)
- 김프 통계: 평균 1.96%, 5%ile -2.23%, 95%ile 7.20%
- 김프>3% 발생: 2077봉 (30.1%) — 충분한 발동 빈도
- 김프>3% 시 사이징 절반 → 고프리미엄 구간 방어 효과

### C파트: TU 고확신 부스트 — 전체 기각
- H1~H4 모두 BEAR 악화 (HC 거래 평균 PnL -1.13% vs 일반 +0.72%)
- 고확신 조건이 실제로 좋은 거래를 선별하지 못함
- Score≥5.0 + XGB≥0.60이 Trend_Up에서 유효한 필터가 아님

### D파트: O3 별도 관리 — 전체 기각
- O3 거래 단 2건 (통계적 무의미)
- 느슨한 청산(O1/O2)이 오히려 O3 PnL 하락 (+5.18% → +4.44%)
- 현재 표준 파라미터가 O3에도 적절

### E파트: 최적 조합
| ID | 조합 | BULL | BEAR | 최종자산 | MDD |
|:--:|------|----:|----:|--------:|---:|
| B0 | 기준 | +13.02% | -9.36% | 10,244K | 16.6% |
| **X2** | **TB2+K2** | **+18.44%** | **-0.80%** | **11,749K** | **12.1%** |

**X2 (TB2+K2) 결과**:
- 최종자산: 11,749K (B0 대비 **+1,505K / +14.7%**)
- BULL: +18.44% (+5.42%pp) / BEAR: -0.80% (+8.56%pp)
- MDD: 12.1% (B0 16.6% 대비 -4.5%p)
- BULL과 BEAR 동시 대폭 개선 + MDD 크게 감소

### #20 핵심 결론

1. **트리플 배리어가 게임 체인저**: 하단 배리어 -3.5%로 "중간에 큰 드로다운 경험하는 양성 라벨"을 제거 → BULL·BEAR 동시 개선
2. **김프가 한국 시장 특화 알파**: 김프>3% 시 사이징 축소 → 과열 구간 방어 (BEAR +5.19%pp)
3. **두 효과는 독립적**: TB2(AI 품질) + K2(시장 과열 감지) 조합 시 시너지 (+14.7%)
4. 고확신 부스트와 O3 관리는 발동이 적어 효과 확인 불가

**채택 권고**: TB2(트리플 배리어 -3.5%) + K2(김프>3% ×0.5) → v20.0 후보

---

## 2026-04-14 #20 정합 검증: B0 기준선 불일치 해소

- **파일**: `backtest/backtest_v20_b0_verify.py`
- **목적**: #20 B0가 #17-B X1(v19.9)과 크게 다른 원인 해명 + 정합된 기준선 위 K2/TB2 순수 효과 측정

### 원인
- #20: `train_xgb_triple(None)` (라벨링 threshold를 train/test 독립 선택)
- #17: `v2.train_xgb_13()` (train+test 합산 기준 threshold 선택)
- 이 차이로 XGB 모델이 달라짐 → BULL 39% vs 52% 승률, BEAR -9.36% vs -0.28%

### 검증 결과 (B0 모델을 v2.train_xgb_13으로 통일)

| ID | 설명 | BULL | BEAR | 최종자산 | MDD | 판정 |
|:--:|:-----|:----:|:----:|--------:|:---:|:----:|
| B0 | v19.9 기준 (v2.train_xgb_13) | +16.70% | -0.19% | 11,647K | 13.2% | baseline |
| TB2 | 트리플 배리어 +1.2%/-3.5%/8봉 | +16.62% | -2.25% | 11,400K | 13.2% | ❌ BEAR악화 |
| K2 | 김프>3% ×0.5 | +18.48% | +1.72% | 12,052K | 11.9% | ⭕ +405K |
| X2 | TB2+K2 | +18.44% | -0.98% | 11,728K | 12.1% | ❌ BEAR악화 |

- **#17-B X1 대비 B0 Gap**: BULL 0.65%pp, BEAR 0.17%pp → 정합 확인
- BEAR B&H 차이(-27.6% vs -25.1%)는 데이터 길이 차이 (1일분 추가 데이터)

### 결론
1. **TB2 기각**: 정합된 기준선에서 BEAR -2.05%pp 악화. 원본 #20에서 TB2가 좋아보인 이유는 B0 기준선이 잘못된 모델(-9.36%)로 낮았기 때문
2. **K2만 채택**: BULL +1.78%pp, BEAR +1.92%pp, MDD -1.3%p — 순수 개선 확인
3. **교훈**: 백테스트 간 학습 함수 통일 필수 → `backtest/core/` 공통 시뮬레이터 도입

---

## 2026-04-14 #21: v20.0 종합 성능 검증

- **파일**: `backtest/backtest_v20_validation.py`
- **기간**: IS 2024-01~09 / OOS-BULL 2024-10~2025-06 / OOS-BEAR 2025-07~현재
- **목적**: 공통 시뮬레이터(core/)로 v20.0 프로덕션(K2 김프) 전체 성능 B0 측정
- **수정**: 시뮬레이터 TimeExit/ForceExit 삭제 — 프로덕션에 없는 로직이었음 (v20.0에서 Time Exit 전체 삭제됨)

### 수익률

| 항목 | IS | OOS-BULL | OOS-BEAR |
|------|:---:|:---:|:---:|
| 수익률 | +10.78% | +17.80% | +5.84% |
| B&H | +47.0% | +75.4% | -24.7% |
| 캡처율 | 23% | 24% | -24% |

- **연속 최종자산 (BULL→BEAR)**: 12,468K (B&H 13,201K)

### 매매 통계

| 항목 | IS | BULL | BEAR | 전체 |
|------|:---:|:---:|:---:|:---:|
| 거래수 | 21 | 22 | 21 | 64 |
| 승률 | 33% | 45% | 52% | 44% |
| PF | 1.57 | 2.74 | 2.06 | 2.06 |
| MDD | 15.9% | 6.6% | 8.9% | - |
| 평균PnL | +1.33% | +2.72% | +0.81% | +1.64% |

### 청산 사유 분포 (전체)

| 사유 | 건수 | 평균PnL |
|------|:---:|:---:|
| 트레일링 | 27 (42%) | +5.54% |
| ATR손절 | 14 (22%) | -4.10% |
| MR시간초과 | 10 (16%) | -0.22% |
| 계단손절 | 5 (8%) | +0.82% |
| 본전청산 | 4 (6%) | -0.61% |
| MR익절 | 2 (3%) | +2.84% |

### Regime별 (전체)

| Regime | 거래 | 승률 | 평균PnL |
|--------|:---:|:---:|:---:|
| Trend_Up | 11 | 36% | -0.42% |
| Range | 38 | 42% | +2.91% |
| Volatile | 2 | 100% | +3.04% |
| Range_MR | 13 | 46% | -0.39% |

### 진입 경로별

| 경로 | 거래 | 승률 | 평균PnL |
|------|:---:|:---:|:---:|
| EMA | 58 | 45% | +1.68% |
| O3 Lead | 6 | 33% | +1.02% |

### 김프 (K2: 김프>3% → ×0.5)

- 사이징 축소: 12건 / 축소 거래 평균PnL: -3.03%
- 김프 과열 구간에서 축소 → 평균 -3% 손실 제한 (미축소 시 더 큰 손실)

### 리스크

- 최대 MDD: 15.9% (IS) / OOS는 BULL 6.6%, BEAR 8.9%
- 최대 연속손실: 5회 (전 구간 동일)
- Kill Switch: IS/BULL 발동 (단일거래 -5% 이상), BEAR 미발동
- 피라미딩: TP1 45% / TP2 14% / 추가매수 Lv1 6건

### 핵심 결론

1. **BEAR +5.84% (B&H -24.7%)**: 하락장에서 **절대 수익** 달성 — TimeExit 제거로 -2.34%→+5.84% 대폭 개선
2. **연속 최종자산 12,468K**: 수정 전 11,789K 대비 +679K (+5.8%) — TimeExit이 수익 거래를 조기 청산하고 있었음
3. **OOS MDD 대폭 감소**: BULL 10.8%→6.6%, BEAR 15.1%→8.9% — 포지션이 트레일링으로 자연 종료되며 드로다운 축소
4. **거래수 90→64건**: TimeExit/ForceExit 30건 소멸 → 포지션 유지 시간 증가 (25.8→39.8봉)
5. **Range 핵심 엔진 유지**: 38건/42%/+2.91%
6. **시뮬레이터-프로덕션 동기화 완료**: 청산 경로가 ATR손절/트레일링/계단손절/본전청산/MR만 남아 프로덕션과 1:1 대응

상세 결과: `backtest/results/backtest_v20_validation.md`

---

## 2026-04-14 #22: 피라미딩 사이징 재테스트 + O3→EMA 전이 분석

- **파일**: `backtest/backtest_22_pyramid_o3.py`
- **기간**: IS 2024-01~09 / OOS-BULL 2024-10~2025-06 / OOS-BEAR 2025-07~현재
- **목적**: (A) 피라미딩 초기 사이징 최적화, (B) O3 선행 신호의 Scout 구조 가능성 분석

### 파트 A: 피라미딩 사이징

| ID | 초기 | BULL | BEAR | 최종자산 | MDD | PF |
|:--:|:---:|----:|----:|--------:|---:|---:|
| **B0** | **80%** | **+17.80%** | **+5.83%** | **12,468K** | **8.9%** | **2.52** |
| P70 | 70% | +17.05% | +5.93% | 12,399K | 8.7% | 2.50 |
| P60 | 60% | +16.27% | +6.03% | 12,328K | 8.5% | 2.48 |
| P50 | 50% | +15.49% | +6.13% | 12,256K | 8.4% | 2.46 |

**결론**: B0(80%)이 최적. 사이징 축소 시 MDD 미미하게 개선(-0.5%p)되나 최종자산 -212K 감소. BEAR는 소폭 개선되지만 BULL 손실이 더 큼. **2단계 스킵.**

### 파트 B: O3→EMA 전이 분석

| 항목 | 값 |
|------|:---:|
| 총 O3 발동 | 79건 |
| EMA 정배열 시 발동 | 20건 (25%) — 이미 EMA 경로 가능 |
| EMA 역배열 시 발동 | 59건 (75%) |
| 역배열 → 정배열 전환률 (50봉) | **46% (27/59)** |
| 전환까지 평균 봉수 | **29.4봉 (중앙 30봉)** |
| 전환까지 평균 가격변화 | +4.92% |
| 전환까지 평균 중간MDD | -2.94% |
| 미전환 32건 평균MDD | **-10.09%** |

### Scout 판단

- 전환률 46% < 60% → **❌ Scout 불가**
- 평균 봉수 29.4 > 10 → **❌ 의미 없음** (EMA 전환까지 5일 이상 대기)
- 평균 MDD -2.94% → △ 보통
- 가격변화 +4.92% → ⭕ 이상적 선진입 이점

### 핵심 결론

1. **피라미딩 80% 유지**: 축소 시 BULL 캡처 감소가 BEAR 방어 이득보다 큼
2. **O3 Scout 구조 기각**: 전환률 46%는 반타작 수준, 미전환 시 MDD -10% 위험. 평균 29봉(4.8일) 대기는 자본 묶임 비용 과다
3. **O3 역할 재정의**: 현재 Leading 진입으로 사용 중이나, 75%가 역배열 시 발동 → EMA와 무관하게 진입하는 독립 신호로서의 가치가 더 큼
4. **O3 정배열 25%**: 이미 EMA 경로로 진입 가능한 구간 → O3의 추가 가치는 75%의 역배열 발동에 집중

상세 결과: `backtest/results/backtest_22_pyramid_o3.md`

---

## 2026-04-15 #23: TP 무한 계단손절 구조 재설계
- **파일**: `backtest/backtest_23_step_stop.py`
- **기간**: IS 2024-01~09 / OOS-BULL 2024-10~2025-06 / OOS-BEAR 2025-07~현재
- **목적**: v20.0 Lv2 추가매수 스킵 시 손절만 갱신 → 즉시 하드스톱 문제 해결. TP를 무한 확장하여 계단손절 지속 갱신.

| ID | 설명 | 최종자산 | BULL | BEAR | MDD | 판정 |
|:--:|------|--------:|----:|----:|---:|:----:|
| B0 | v20.0 현재 (TP1/TP2 legacy) | 13,000,249 | +25.51% | +3.58% | 9.3% | 기준 |
| S1 | 무한계단 2칸 + Trail + 5%하한 | 12,853,887 | +24.10% | +3.58% | 9.3% | 기각 |
| S2 | 무한계단 2칸 + 5%하한만 | 13,544,092 | +31.24% | +3.20% | 13.2% | 기각(MDD) |
| S3 | 무한계단 1.5칸 + Trail + 5%하한 | 13,029,630 | +24.91% | +4.32% | 8.7% | **채택후보** |
| S4 | 무한계단 2칸 + Trail + 3%하한 | 12,853,887 | +24.10% | +3.58% | 9.3% | 기각 |
| S5 | 무한계단 2칸 + Trail + 하한OFF | 12,853,887 | +24.10% | +3.58% | 9.3% | 기각 |

**핵심 발견**:
1. **스킵 즉시청산 0건**: 모든 S1~S5에서 "추가매수 스킵 후 즉시 청산" 0건 (구조적 해결 확인)
2. **TP 도달 최대 11단계**: B0은 TP2까지만 존재하지만, 무한 계단 구조에서 TP11까지 도달
3. **계단손절 PnL 대폭 개선**: B0 계단손절 평균 -0.05% → S3 계단손절 평균 +6.05%
4. **S3 MDD 개선**: 8.7% (B0 9.3% 대비 -0.6%p)
5. **BEAR 구간 S3 +0.74%pp 개선**: 3.58% → 4.32%

**결론**: S3(무한계단 1.5칸 + Trail + 5%하한) 유일한 채택 후보. 자산 소폭 개선(+29K), MDD 개선(-0.6%p), BEAR 개선(+0.74%pp). 스킵즉시청산 0건으로 구조적 문제 해결 확인.

상세 결과: `backtest/results/backtest_23_step_stop.md`

---

## 2026-04-19 세션 요약

14건 백테스트 + 3건 프로덕션 패치 (v20.6 / v20.7 / v20.8).
채택 v20.5(R3 기존) → v20.6(BD+E2+버그) → v20.7(C6) → v20.8(KS 자동복구).

---

## 2026-04-19 #24: TU Range New 확장 (T1/T2) — ❌ 기각
- **파일**: `backtest/backtest_tu_range_new.py`
- **모드**: legacy / AI Gate OFF
- **목적**: v20.5 R3 배포 후 TU 진입도 Range New 경로로 통일하면 MDD/수익 개선되는지

| 케이스 | 설명 | BULL | BEAR | MDD | 연속자산 |
|---|---|---|---|---|---|
| B0 | R3 현행 | +59.35% | +4.33% | 12.30% | 16,624K |
| T1 | TU 트레일 OFF | +66.30% | +0.74% | **30.31%** | 16,753K |
| T2 | T1 + Score 5.0 | +61.31% | +0.32% | **30.31%** | 16,183K |

**결론**: MDD 30% 치명적 → 전면 기각. TU는 현 P2 트레일링 유지. TU 개선은 다른 축으로.
**후속**: TU 전용 개선 1차 단독 백테스트 (#25)
**산출**: `backtest/results/bt_tu_range_new_result.md` (untracked, 후속 commit에 포함)

---

## 2026-04-19 #25: TU 전용 개선 1차 단독 (A/B/C/D) — B 단독 5/5 PASS
- **파일**: `backtest/backtest_tu_improve_1.py`
- **모드**: legacy / R3 기반 / AI Gate OFF
- **목적**: TU 진입 포지션만 4축 변경 단독 측정 (min_stop/trail/regime전환/step)

| 케이스 | 변경 | BULL | BEAR | MDD | 판정 |
|---|---|---|---|---|---|
| B0 | R3 현행 | +59.35% | +4.35% | 12.30% | 기준 |
| A | min_stop 5%→3% | +59.35% | +4.35% | 12.30% | 4/5 (무효) |
| **B** | **trail 4.5 + 초반4봉 보호** | +60.24% | +6.56% | 13.72% | **✅ 5/5** |
| C | TU→Range 50%/Down 전량 | +47.23% | +10.60% | 10.12% | 3/5 (BULL 악화) |
| D | step_off -1.0 (계단 완화) | +65.35% | +2.74% | 12.89% | 4/5 (BEAR 악화) |

**결론**: B 단독만 모든 기준 통과. C는 BULL false, D는 BEAR 악화.
**후속**: B + D 조합 탐색 + 메커니즘 분석 (#26, #27)
**산출**: `bt_tu_improve_1_result.md` | commit `cac8392`

---

## 2026-04-19 #26: TU 1차 심층 분석 — 📊 메커니즘 파악
- **파일**: `backtest/analyze_tu_improve_1.py`
- **목적**: 각 옵션 작동 메커니즘 추적 + 권장 변경 매핑

**발견**:
- A 무효 이유: BULL/BEAR에서 min_stop이 binding 아님 (trail_high×0.95가 먼저 작동)
- B 핵심 효과: trail_m 4.5 확장 (초반 4봉 보호는 실제 0건 발동)
- C BULL 손해: **Down 전량 6건 전부 false signal** (Trend_Up 중 일시 조정을 Down 오인)
- D BULL 이득: 샘플 1건만. 강추세+고ADX+긴 보유 공통.

**결론**: C는 Down만 분리해도 BULL 악화. BDC 조합은 Down 지속 필터 필요 (2차에서).
**후속**: TU 2차 조합 + Down 지속 필터 (#27)
**산출**: `bt_tu_improve_1_analysis.md` | commit `cac8392`

---

## 2026-04-19 #27: TU 개선 2차 조합 (B-simple/BD/BDC2/BDC3) — BD 채택 (legacy)
- **파일**: `backtest/backtest_tu_improve_2.py`
- **모드**: legacy / R3 기반 / AI Gate OFF
- **목적**: B 단순화 + BD 조합 + Down N봉 지속 필터

| 케이스 | 설명 | BULL | BEAR | MDD | cont vs B0 | 판정 |
|---|---|---|---|---|---|---|
| B0 | R3 현행 | +59.35% | +4.37% | 12.30% | - | 기준 |
| B-simple | trail 4.5만 | +59.35% | +5.61% | 14.03% | +197K | ✅ 5/5 |
| **BD** | trail 4.5 + step -1.0 | +65.35% | +3.97% | 14.03% | **+560K** | **✅ 5/5** |
| BDC2 | BD + Down 2봉 지속 | +55.10% | +3.12% | 14.03% | -638K | ❌ 2/5 |
| BDC3 | BD + Down 3봉 지속 | +63.12% | +2.85% | 14.03% | +145K | ❌ 4/5 |

**결론**: BD legacy 채택 후보. 1차 false 6건 중 BDC2/3에서 4-5건 여전히 발동 → 지속 필터 효과 제한.
**후속**: **BD infinite 재검증 필수** (legacy↔infinite 드리프트 우려) (#28)
**산출**: `bt_tu_improve_2_result.md` | commit `cac8392`

---

## 2026-04-19 #28: BD infinite 재검증 — ❌ 기각
- **파일**: `backtest/backtest_bd_infinite.py`
- **모드**: **infinite** (프로덕션 일치) / R3 / AI Gate OFF
- **목적**: BD (trail 4.5 + step_lookback 2.5)가 infinite 모드에서도 유효한지

| 케이스 | BULL | BEAR | MDD | 판정 |
|---|---|---|---|---|
| B0_inf | +45.35% | +4.83% | 11.64% | 기준 (legacy B0 +59.35% 대비 -14%p) |
| B-simple_inf | +45.35% (무변화) | +4.83% (무변화) | 11.64% | 3/5 |
| BD_inf | +54.85% | +2.00% | **14.03%** | **4/5 기각 (BEAR -2.83%p)** |

**결론**: **legacy→infinite BULL -14%p 드리프트 발견**. BD BULL +9.5%p이나 BEAR -2.83%p로 기각. B-simple은 infinite에서 무효 (계단이 지배적).
**후속**: R3 자체가 infinite에서도 유효한지 긴급 재검증 (#29)
**산출**: `bt_bd_infinite_recheck_result.md` | commit `cac8392`

---

## 2026-04-19 #29: R3 infinite 재검증 — ✅ 5/5 유지
- **파일**: `backtest/backtest_r3_infinite.py`
- **모드**: legacy / infinite 양쪽 / AI Gate OFF
- **목적**: R3(v20.5) 자체가 infinite 모드에서도 유효한지

| 케이스 | BULL | BEAR | MDD | cont_eq |
|---|---|---|---|---|
| BL_legacy | +24.09% | +0.81% | 10.11% | 12,510K |
| BL_inf | +20.87% | +1.57% | 9.37% | 12,276K |
| R3_legacy | +59.35% | +4.40% | 12.30% | 16,636K |
| **R3_inf** | **+45.35%** | **+4.82%** | 11.64% | **15,238K** |

**결론**: R3_inf는 BL_inf 대비 BULL +24.48%p, BEAR +3.25%p, cont +24%. **5/5 PASS → v20.5 유지 확정**. legacy-infinite 드리프트는 모드×R3 교호작용.
**후속**: v20.6 후보 통합 (R3+BD+E2 조합) (#30)
**산출**: `bt_r3_infinite_recheck_result.md` | commit `cac8392`

---

## 2026-04-19 #30: v20.6 후보 통합 (R3+BD+E2) — ✅ 채택
- **파일**: `backtest/backtest_v20.6_candidates.py`
- **모드**: infinite / AI Gate OFF
- **목적**: E2(일봉 EMA200 BEAR 모드)가 BD의 BEAR 약점 보완 여부 6 케이스

| 케이스 | BULL | BEAR | MDD | cont_eq | 판정 |
|---|---|---|---|---|---|
| BL | +20.87% | +1.58% | 9.44% | 12,277K | 기준 |
| R3 | +45.35% | +4.84% | 11.64% | 15,238K | R3 단독 |
| R3+BD | +54.85% | +2.01% | 14.03% | 15,795K | BD BEAR 약화 |
| R3+E2 | +44.96% | +6.51% | 11.32% | 15,440K | E2만 |
| **R3+BD+E2** | **+54.44%** | **+3.64%** | **11.32%** | **16,005K** | **✅ 전체 PASS** |
| BD+E2 | +30.21% | +0.79% | 7.86% | 13,124K | R3 없이 |

**결론**: E2가 BD BEAR 약점 정확히 보완 (+1.63%p BEAR, -2.71%p MDD). **v20.6 채택.**
**후속**: v20.6 배포 (commit `cac8392`) + 28개월 연속 평가 (#31)
**산출**: `bt_v20.6_candidates_result.md` | commit `cac8392`

---

## 2026-04-19 #31: 28개월 연속 v20.6 vs B&H — 📊 캡처 98.8% 발견
- **파일**: `backtest/backtest_full_period_v20.6.py`
- **모드**: infinite / 2024-01-01 ~ 2026-04-19 (5040봉 연속)
- **목적**: 분할(IS/BULL/BEAR)이 아닌 연속 28개월 운용 시 v20.6 성과

| case | 최종자산 | 총수익 | CAGR | MDD(bar) | Sharpe | B&H캡처 |
|---|---|---|---|---|---|---|
| BL (R3 이전) | 16.67M | +66.68% | 24.89% | 16.58% | 0.71 | 69.03% |
| R3 (v20.5) | 19.27M | +92.75% | 33.04% | 23.49% | 0.66 | 96.03% |
| **v20.6** | **19.55M** | **+95.46%** | 33.85% | 26.10% | 0.66 | **98.83%** |
| B&H | 19.66M | +96.59% | 34.19% | **48.08%** | 0.77 | 100% |

**결론**: 연속 복리 운용 시 v20.6는 B&H 수익 98.8% 캡처, MDD는 절반. 분할 합산보다 22% 높음 (복리 효과).
**후속**: 이 "캡처 98.8%"가 진짜인지 검증 필요 (#32)
**산출**: `bt_full_period_v20.6_vs_bnh_result.md` | commit `a120546`

---

## 2026-04-19 #32: v20.6 vs B&H 격차 분석 — 📊 BULL 실제 캡처 68% 진실
- **파일**: `backtest/analyze_v20.6_bh_gap.py`
- **목적**: 98.8% 캡처 검증 — 피크 기준 + 월별 격차 추적

**핵심 반전**:
| 지표 | B&H | v20.6 | 캡처 |
|---|---|---|---|
| 최종자산 (2026-04-19) | 19.68M | 19.55M | **99.33%** ✓ |
| **최고점 (2025-10-09)** | **31.26M** | **21.34M** | **68.26%** ⚠️ |
| 피크→종료 낙폭 | -37.06% | -8.40% | — |

**결론**: 실제 BULL 캡처 68% (32% 놓침). "99% 캡처"는 B&H가 -37% 폭락해 따라잡힌 것일 뿐. 2024-11 (+14%p), 2025-01 (+11%p), 2024-03 (+13%p) 등 BULL 월에서 반복 under-capture.
**후속**: 12개월 under-capture 원인 정밀 분석 (#33)
**산출**: `bt_v20.6_bh_gap_analysis.md` | commit `4b0e7bd`

---

## 2026-04-19 #33: 12개월 미달 30건 정밀 분석 — 📊 TP_A/R2a 공동 1순위
- **파일**: `backtest/analyze_v20.6_undercap_12months.py`
- **목적**: 12 under-capture 월 × 30 거래별 청산 맥락 + post-exit 가격 추이 + 권장 변경

**권장 변경별 커버리지 (max32 +3%p 이상 23건)**:
| 변경 | 커버 거래 | 합산 놓친 수익 |
|---|---|---|
| TP_A (step_lookback 완화) | 9건 | +56.4%p |
| R2a (trail 4.5→5.5) | 8건 | +50.8%p |
| 하드스톱 완화 | 6건 | +32.7%p |
| E2b (모멘텀 조건) | 2건 | +10.8%p |

**결론**: 계단손절 12건 / 트레일링 8건이 주범. TP_A/R2a 이론상 동등 효과, 조합 시 +100%p 잠재.
**후속**: R2a + TP_A 그리드 (#34)
**산출**: `bt_v20.6_undercap_12months.md` | commit `7eea034`

---

## 2026-04-19 #34: v20.7 R2a + TP_A 그리드 9 케이스 — ❌ 전면 기각
- **파일**: `backtest/backtest_v20.7_grid.py`
- **모드**: infinite / R3+BD+E2 기반 / AI Gate OFF
- **그리드**: trail_m {4.5, 5.0, 5.5} × step_lookback {3.0, 3.5, 4.0}

**결과**: 9 케이스 모두 최종자산 19,413K~19,545K, MDD 26.10% 동일, BULL 피크캡 67.8%~68.3% (B0 대비 거의 무변화).

**핵심 진단**:
- 거래 40건 중 TU 14건, Range 22건
- **계단손절 16건 중 Range 11건 (69%)**, TU 5건 (31%)
- TU_STEP_LOOKBACK / tu_trail_m 은 TU 14건만 영향 → Range 11건 무영향
- MDD 26%는 Range P2 경로 unrealized drawdown이 근본 → TU 튜닝으로 건드릴 수 없음

**결론**: TU-only 튜닝 공간 소진. Range 계단이 진짜 병목. 이전 분석 #33의 "TP_A 9건"은 TU+Range 혼합 가정, 실제 TU는 5건만.
**후속**: Range 전용 파라미터 + EMA 역배열 분석 (#35)
**산출**: `bt_v20.7_grid_result.md` | commit `c2f226e`

---

## 2026-04-19 #35: EMA 역배열 + Range 계단 분석 (A/B) — 📊 B 우선
- **파일**: `backtest/analyze_v20.6_deep_A_B.py`
- **목적**: EMA 역배열 재진입 차단 10건 (A) + Range 계단손절 11건 (B) 정밀 분석

**분석 A (EMA 역배열)**:
- 14건 (원안 10 확장), 이상적 +74.6%p 잠재 / 실제 재진입 가능 시 +30.9%p
- O3 발동 2/14건 (14%) → O3 확장만으론 커버 제한
- EMA 회복 내재 7/14건 (50%)

**분석 B (Range 계단)**:
- 11건 / 평균 hold 66.5봉 / 평균 MFE **10.10%** (꽤 상승 후 stop)
- pyramid_level ≥ 2 도달 9/11건
- 완화 효과: 11/11건 구조적 회피 가능, **+42.7%p 잠재**

**결론**: B(Range 계단)가 A(EMA)보다 우선 — 효과 크고 구현 단순 (`range_step_lookback` 키 추가).
**후속**: Range step + 사이징 그리드 (#36)
**산출**: `bt_v20.6_ema_reverse_10.md` + `bt_v20.6_range_step_11.md` | commit `e8a6b4b`

---

## 2026-04-19 #36: Range step + 사이징 그리드 (C6 채택) — ✅ v20.7
- **파일**: `backtest/backtest_v20.7_range_grid.py` (9) + `backtest_v20.7_size_extreme.py` (6) + `backtest_v20.7_ema_bypass.py` (4)
- **모드**: infinite / R3+BD+E2 / AI Gate OFF
- **그리드**: range_step {2.0, 2.5, 3.0, 3.5} × range_init {40, 50, 60, 70, 80%} + O3 확장

**Range grid (9)** + **extreme (6)** 핵심 결과:
| 케이스 | step | init | 최종자산 | MDD | BULL피크캡 |
|---|---|---|---|---|---|
| B0_v206 | 1.5 | 80% | 19.55M | 26.10% | 68.26% |
| **C6** | **3.0** | **70%** | **23.97M** | **20.92%** | **83.57%** |
| C3 | 3.0 | 80% | 24.08M | 21.66% | 84.10% |
| E2 | 3.0 | 40% | 23.63M | **18.77%** | 81.97% |

**O3 확장 4 케이스**: 모두 -7M 이상 급락 (O3a/b/ab 전면 기각, BEAR 악화).

**결론**: **C6 채택** (step 3.0 + init 70%). 전체 15 Range 케이스 모두 B0 대비 수익 +23~45%p. MDD 15% 절대 달성 불가 → 기준 현실화 (26%→20%대). 사용자 결정: v20.7 + Kill Switch 20%.
**후속**: v20.7 배포 (commit `906ed2f`) + 시뮬-프로덕션 정합성 점검 (#37 포함)
**산출**: `bt_v20.7_range_step_size_grid.md`, `bt_v20.7_size_extreme.md`, `bt_v20.7_ema_reverse.md`, `bt_v20.7_final_comparison.md` | commits `4ff6c0d` + `f24aeb6`

---

## 2026-04-19 #37: v20.7 진실 평가 (Kill Switch + AI Gate) — 📊 자동복구 근거
- **파일**: `backtest/backtest_v20.7_full_truth.py` + `backtest/core/simulator.py` (KS 추가)
- **모드**: infinite / 12 케이스 × (KS OFF/PERM/AUTO × AI OFF/EST)
- **배경**: 시뮬-프로덕션 정합성 18 영역 점검 결과 Kill Switch만 Critical 발견 (`sim_vs_prod_full_audit.md`)
- **AI Gate 실측**: 프로덕션 20,228 logs → Trend_Up 97.78% / Range 70.64% 통과율 (`ai_gate_pass_rate.md`)

**12 케이스 결과**:
| 시나리오 | BL | v20.6 | v20.7 |
|---|---|---|---|
| 낙관 (KS OFF + AI OFF) | 16.68M | 19.55M | **23.97M** |
| 현실 (KS PERM + AI EST) | 13.69M | 12.67M | 14.37M |
| **자동복구 (KS AUTO + AI EST)** | — | — | **18.06M** |

**핵심 발견**:
- Kill Switch 1회 발동(2024-10-10)만으로 3340 진입 차단, BULL 전체 캡처 실패
- v20.7 낙관 23.97M → 현실 12.66M (**-47%**)
- **자동복구 시 +5.39M 회복** (v20.6 현실 대비)
- AI Gate EST는 v20.7에서 +1.7M 역설적 도움 (Range 저품질 진입 차단)

**결론**: v20.7 자체는 현실에서도 v20.6 상회하나, **자동복구 필수**. 프로덕션 v20.8 패치 진행.
**후속**: v20.8 Kill Switch 자동복구 + 24h 재발동 방지 배포 (commit `811622f`)
**산출**: `bt_v20.7_full_truth.md`, `ai_gate_pass_rate.md`, `sim_vs_prod_full_audit.md` | commits `1668209` (audit) + `e6e234a` (truth)

---

## 세션 종합 (2026-04-19)

**채택 흐름**: v20.5 R3 → v20.6 (BD+E2+버그+UX) → v20.7 (C6) → v20.8 (KS 자동복구)

**주요 발견**:
- legacy vs infinite 모드 격차 확인 → 이후 infinite만 사용
- BULL 실제 캡처 68% (피크 기준), 99% 주장은 측정 오류
- Range 계단이 최대 병목 (TU 아님). v20.7 C6로 +44%p 수익 개선
- Kill Switch 미구현이 시뮬 vs 프로덕션 최대 괴리 (현실 -47%)
- AI Gate 실제 영향 미미 (Trend_Up 97.78% 통과)

**기각 항목** (재시도 방지):
- TU Range New 확장, TU 전용 그리드 (Range 병목)
- BD 단독 infinite, BDC2/3 (Down 지속 필터 무효)
- O3 역배열 우회 (O3a/b/ab, BEAR 파괴)

**향후 관찰**: Kill Switch 실전 발동 시 자동복구 효과, BULL 피크 캡처 실측, Range 계단손절 건수 감소

---

## 2026-04-20 #38: E2b O3 예외 허용 검증 (6 케이스) — 🟡 Soft 채택 후보 (E2b)
- **파일**: `backtest/scripts/bt_e2b_o3_exception.py` + `backtest/core/simulator.py` (e2_o3_exception 신규 cfg)
- **모드**: infinite / 5034봉 연속 (2024-01-01 ~ 2026-04-19)
- **KS**: OFF (E2 단독 효과 측정) / **AI Gate**: OFF / **시뮬**: v20.8.1 정합
- **배경**: v19.3 "EMA 역배열 O3 예외 허용" 철학이 v20.6 E2 도입으로 무력화. 2026-04-20 E2 재평가(#37 외)는 "E2 완화" 축만 다룸 → "E2 유지 + O3 예외" 축 미검증
- **근거**: `backtest_log.md #8` O3 선행신호 채택 (4건 중 3승, +309K)

**6 케이스 결과**:
| ID | 최종자산 | ret(%) | BULLcap(%) | BEAR/횡보(%) | MDD(%) | O3예외진입 | N |
|---|---|---|---|---|---|---|---|
| E2a (baseline) | 23,946,077 | +139.46 | 83.5 | -0.94 | 20.92 | 0 | 30 |
| E2-OFF | 23,118,836 | +131.19 | 82.5 | -3.21 | 21.33 | 0 | 39 |
| **E2b (40% P0)** | **24,584,676** | **+145.85** | 81.9 | **+3.76** | 20.92 | **5** | 35 |
| E2c (20% P0) | 24,266,762 | +142.67 | 82.7 | +1.39 | 20.92 | 5 | 35 |
| E2d (XGB≥0.65) | 24,150,577 | +141.51 | 81.9 | +1.93 | 20.92 | 3 | 33 |
| E2e (XGB≥0.65+Score≥5.0) | 23,946,077 | +139.46 | 83.5 | -0.94 | 20.92 | 0 | 30 |

**핵심 발견**:
- **E2b +638K vs E2a** (MDD 불변, BULL-capture -1.6%p, BEAR/횡보 -0.94% → +3.76%)
- O3 예외 진입 5건: 1 BULL (-4.56%), 4 BEAR (평균 +2.99%, 승률 50%)
- E2-OFF는 E2a 대비 -827K → #37 E2 재평가 결과와 정합 (E2 제거 시 BEAR 악화)
- E2e Score≥5.0 너무 엄격 → 모든 O3 예외 진입의 score 3.07~3.77로 14건 전부 차단됨
- MDD 20.92% 공통 (baseline 사건) → O3 예외는 MDD에 기여하지 않음

**채택 판정 (AND 전부 만족)**:
| 조건 | E2b | E2c | E2d | E2e |
|---|---|---|---|---|
| E2a +200K 이상 | ✅ +638K | ✅ +321K | ✅ +205K | ❌ +0 |
| BEAR/횡보 ≥ -0.94% | ✅ +3.76% | ✅ +1.39% | ✅ +1.93% | ✅ -0.94% |
| O3 예외 ≥ 5건 | ✅ 5 | ✅ 5 | ❌ 3 | ❌ 0 |
| MDD ≤ 20% | 🟡 20.92%* | 🟡 20.92%* | 🟡 20.92%* | 🟡 20.92%* |
| **판정** | **🟡 Soft** | **🟡 Soft** | ❌ 미채택 | ❌ 미채택 |

*Soft 해석: MDD는 baseline E2a와 동일 (20.92%) → O3 예외가 악화시키지 않음

**결론**: **Soft 시나리오 A'** (2건 채택 후보 — E2b 1순위). MDD 상한 20%를 엄격 적용 시 KS 재설계 선행 후 E2b 재평가 권장. v19.3 철학("EMA 역배열 O3 예외")은 **일봉 EMA200 역배열에서도 BEAR 기준 평균 +2.99% / 50% WR로 유효성 확인** (4H 기준 75% WR보단 저하).
**후속 방향**: v20.9 후보 — E2 패치(O3 예외) + KS 재설계 병행 검토. 프로덕션 적용 전 BEAR 구간 (2025-11~) 집중 재검증 권장.
**산출**: `bt_e2b_o3_exception.md`, `e2b_lead_entries.csv` (13건)

---

## 2026-04-20 #39: E2 BEAR 구간 가상 거래 탐색 — 📊 v21 규칙 후보 도출
- **파일**: `backtest/scripts/bt_e2_research_log.py` + `backtest/scripts/analyze_e2_research.py`
- **모드**: 관찰 전용 (실제 거래 X) — E2 활성 4H봉마다 1건 가상 진입 + 200봉 추적
- **기간**: 2024-01-01 ~ 2026-04-19 (E2 활성 1,476봉 = 총 29.3%)
- **데이터**: `e2_research_snapshots.csv` + `e2_virtual_trades.csv` (self-contained, 50+ 지표 스냅샷)

**기본 통계 (pnl_at_20bar 기준)**:
- 표본 746건, 승률 46.25%, 평균 PnL -0.21%
- 최종청산 기준: 승률 59.42%, 평균 +0.33%
- exit_reason: tp_5pct 42.6% (평균 +4.70%) / stop_5pct 37.0% (-5.30%) / e2_released 18.6% (+1.54%)
- 평균 MFE +3.56% / MAE -3.16% (변동성 극단 평균)

**상위 조건 조합 (n≥50, 평균 PnL 기준)**:
| 순위 | 규칙 | n | WR | avg | PF |
|---|---|---|---|---|---|
| 1 | `d_ma5>ma10 AND score>4.0 AND gap<-10%` | 66 | 77.3% | +0.89% | 2.69 |
| 2 | `score>4.0 AND gap<-10%` | 80 | 75.0% | +0.88% | 2.44 |
| 3 | `ema_ok=T AND score>4.0 AND gap<-10%` | 80 | 75.0% | +0.88% | 2.44 |
| 4 | `rsi4h>55 AND score>4.0 AND gap<-10%` | 66 | 74.2% | +0.69% | 2.00 |
| 5 | `ema_ok=T AND rsi4h>55 AND gap<-10%` | 74 | 74.3% | +0.68% | 2.08 |

**하위 조건 (피해야 할 패턴)**:
- `bnc30>10% AND adx4h>25`: n=67, WR 16.4%, -1.84% avg, PF 0.09 (과열 반등 + 추세 강함 = 단기 피크 진입 위험)

**Decision Tree 상위 leaf** (max_depth=4, min_leaf=30):
- `days_since_e2_start > 141d AND adx_4h ≤ 40`: n=43, WR 100%, avg +1.91% (BEAR 후반 + 저변동성)

**핵심 발견**:
- **E2 gap<-10% + rule_score>4.0 조합이 BEAR 구간 상승 진입 1순위** (WR 75%+, n 80)
- E2b (O3 예외)는 gap<-10% 조건을 포함하므로 **상위 조합과 자연 교집합 영역** 존재
- 4H ema_ok 혹은 rsi_4h > 55 추가 시 품질 소폭 유지 — 과도한 제약은 샘플 급감
- **BEAR 장기화 (days_since_e2 > 141)** 구간이 승률 100% (n=43) — 저점 확인 후 진입 시그널
- `adx_4h > 25 + 30일저점반등>10%` 조합 최악 — 급반등 peak 진입 = fake rally 위험
- fng_value Q1 (5~14, Extreme Fear) 평균 +0.19% / WR 56% — 공포 극단도 매수 기회 시사
- kimp_pct Q1 (-10% ~ 0) 평균 +0.63% / WR 60% — 김프 음수 = 로컬 부담 축소

**2026-04-18 현재 상황 유사 케이스** (gap -6.37%, 7d +4.03%, rsi4h 60.9):
- 최근 2026-04-14 ~ 17 동일 구간 근접 (거리 1.03~2.02) → 대부분 max_hold / +1~5% tp_5pct
- 최근 데이터 품질: 양호하나 표본 제약

**결론**: **E2 완전 차단 단일 설계는 기회 손실**이며, gap<-10% + score>4.0 + d_ma5>ma10 조건이 가장 강력한 v21 후보 규칙. E2b O3 예외와 교집합 영역 공존 → v20.9 이후 v21에서 규칙 조합 통합 검토.
**후속**: `improvement_todo.md` "v21 E2 예외 규칙 후보" 등록. `bt_e2f_rule_combos.py` (추가 검증용) 스크립트 작성 권장.
**산출**: `e2_research_snapshots.csv` (1,476행), `e2_virtual_trades.csv` (1,476행), `e2_research_analysis.md`, `e2_research_rules.md`

---

## 2026-04-20 #40: E2 예외 규칙 조합 검증 (11 케이스) — ❌ Strict 채택 없음
- **파일**: `backtest/scripts/bt_e2_combined_exception.py`
- **시뮬**: v20.8.1 정합 + S1 (`e2_gap_score_exception` cfg 추가, core/simulator.py)
- **모드**: infinite / KS OFF / AI Gate OFF / Range New C6 / BD
- **기간**: 2024-01-01 ~ 2026-04-19 (28.0개월, 5034봉, E2 활성 29.3%)
- **목적**: #39 E2 연구 도출 규칙을 실제 시뮬 거래 환경에서 조합/Blacklist 포함 검증

**전체 비교표** (최종자산 기준 정렬):

| ID | 최종자산 | ret(%) | MDD(%) | BEAR(%) | 예외 | 승률 | PF | 거래 | E2a 대비 |
|---|---|---|---|---|---|---|---|---|---|
| **E2d5** | 24,624,789 | +146.25 | 20.92 | +3.93 | 6 | 33.3 | 1.80 | 36 | **+678,712** |
| **E2b** | 24,584,676 | +145.85 | 20.92 | +3.76 | 5 | 40.0 | 1.92 | 35 | **+638,599** |
| **E2c3** | 24,460,109 | +144.60 | 20.92 | +1.23 | 1 | 100.0 | - | 31 | +514,033 (과적합) |
| **E2d4** | 24,361,270 | +143.61 | 20.92 | +2.82 | 8 | 50.0 | 1.11 | 38 | +415,193 |
| **E2c2** | 24,021,799 | +140.22 | 20.92 | -0.57 | 6 | 66.7 | 1.15 | 36 | +75,723 |
| E2a | 23,946,077 | +139.46 | 20.92 | -0.94 | 0 | - | - | 30 | (baseline) |
| E2d2 | 23,813,010 | +138.13 | 20.92 | +0.50 | 8 | 50.0 | 0.92 | 38 | -133,067 |
| E2d3 | 23,616,047 | +136.16 | 20.92 | -0.33 | 9 | 44.4 | 0.77 | 39 | -330,029 |
| E2c1 | 23,482,609 | +134.83 | 20.92 | -2.80 | 7 | 57.1 | 0.82 | 37 | -463,467 |
| E2d1 | 23,278,506 | +132.79 | 20.92 | -1.75 | 9 | 44.4 | 0.74 | 39 | -667,570 |
| E2-OFF | 23,091,183 | +130.91 | 21.33 | -3.33 | 0 | - | - | 39 | -854,894 |

**채택 조건 (AND 전부)**:
1. E2a 대비 최종자산 +500K 이상
2. BEAR/횡보 악화 없음
3. MDD ≤ 21%
4. 예외 진입 ≥ 10건 ← **전 케이스 미달 (최고 E2d3/d1=9건)**
5. 과적합 경고 없음

**핵심 발견**:
- **샘플 희소성 병목**: 28개월 E2 활성 1,476봉 중 예외 진입 최대 9건 → `≥10` 문턱 미달로 Strict 전면 기각
- **E2d5 (O3 OR gap+score+ma5+Trend_Up + BL)**: 자산 +679K / BEAR +3.93% / 6건 승률 33% PF 1.80 — 가장 우수한 절대 성과
- **E2b 단독 (O3 예외, #38 정합)**: +639K / 5건 평균 +1.48% PF 1.92 — 샘플 5건으로 작지만 수익성 최고
- **E2c3 (days>141 AND adx≤40)**: 1건만 발동 (+9.14%), 100% 2025-11 이후 집중 → ⚠️ **과적합 경고** (#39 연구 n=43 대비 급감; 시뮬 사이징/청산 상호작용 탓)
- **E2c1 (gap+score 단독)**: -463K 자산 손실 + BEAR -2.80% (악화) → 단독으로는 부정적
- **E2c2 (+ma5>ma10 필터)**: E2c1 대비 +539K 회복, 6건 승률 66.7% → ma5 필터가 핵심 품질 guard
- **Blacklist 효과 (d1 vs d3)**: 자산 +337K (9건→9건, 일부 진입 교체). d2 vs d4: +548K (가장 큰 개선). 2~5회 차단만으로 유의미
- **O3 ↔ gap+score 겹침 0%**: 완전 독립 signal → OR 조합 논리적 타당
- **현재 시장 (2026-04-18)**: gap=-6.37% (>-10% 미달) + adx=40.6 (>40 미달) → 전 케이스 진입 불가 상태

**Blacklist 효과 요약**:
- E2d3 vs E2d1: +337K (차단 2회)
- E2d4 vs E2d2: +548K (차단 2회) — 가장 큰 방어
- E2d5: BL 5회 차단 (Trend_Up 제한 효과 합산)

**판정**: ❌ Strict 채택 없음. 단, **Soft 기준으로 재평가 시 E2d5/E2b/E2d4 순으로 유망**. 예외 진입 ≥5 완화 + "수익 절대값" 기준으로는 E2d5 1순위.

**v21 제안**:
- **옵션 1 (보수)**: E2b 단독 (v20.9 = #38의 후속) 적용 — 검증된 O3 예외만 유지
- **옵션 2 (공격)**: E2d5 포팅 — O3 + gap+score+ma5+Trend_Up + Blacklist. BEAR 구간 +3.93% / O3 단독 대비 +40K. 단 샘플 6건으로 Shadow 매칭 검증 필수
- **옵션 3 (혼합)**: 프로덕션은 E2b만, Shadow에 E2d5 병행 운용 → 3~6개월 추가 표본 수집 후 재평가

**후속 액션**:
- `improvement_todo.md` v21 후보 규칙 확정 (E2b/E2d5/Shadow 병행)
- Shadow AI v2.0과 별도 **Shadow E2 exception logger** 고려 — 실전 진입 후보 시각화
- E2c3 과적합: 단일 사례 의존 → 추가 BEAR 사이클 데이터 누적 후 재판정

**산출**: `backtest/results/bt_e2_combined_exception.md`, `e2_combined_lead_entries.csv` (59건)
**시뮬 변경**: `backtest/core/simulator.py`에 cfg 11개 추가 (`e2_gap_score_exception` 계열 + blacklist, 기본값 모두 OFF → 기존 E2b 동작 완전 보존)

---

## 2026-04-20 #41: v20.8.1 시뮬레이터 정합 점검 — ⚪ 해당없음 (재실행 불필요)
- **파일**: `backtest/results/sim_v208.1_audit.md`
- **목적**: 프로덕션 v20.8.1 신규 로직 4건(AR1 PerfDegrade OFF / AR2 재시작 리셋 / AR3 롤백 가드 / AR4 CSV)이 `backtest/core/simulator.py`에 반영되어야 하는지 점검

**점검 결과**:

| AR | 프로덕션 위치 | 시뮬 위치 | 상태 | 영향 |
|---|---|---|---|---|
| AR1 | `btc_bot_v281.py:398-399` ENABLE_PERF_DEGRAD_TRIGGER=False + `:3425-3446` | **없음** (재학습 로직 자체 부재) | ⚪ 해당없음 | 없음 |
| AR2 | `btc_bot_v281.py:1533-1540` _load_status 직후 리셋 | **없음** (영속 status 없음) | ⚪ 해당없음 | 없음 |
| AR3 | `btc_bot_v281.py:1305-1334` _do_train 내 롤백 가드 | **없음** (trainer.py는 단발 학습) | ⚪ 해당없음 | 없음 |
| AR4 | `btc_bot_v281.py` btc_retrain_history.csv 기록 | **불필요** (시뮬 학습 1회) | ⚪ 해당없음 | 없음 |

**핵심 근거**:
- 시뮬레이터는 `simulate()` 외부에서 `train_model(df_train)`을 **1회만** 호출 → 반환된 frozen 모델로 28개월 전 구간 평가 (`bt_e2_combined_exception.py:610`)
- 재학습 트리거 3종 (Periodic 30캔들 / Regime 15캔들 / PerfDegrade 20캔들) **전부 시뮬 미구현**
- AR1 = "트리거 끄기" / AR3 = "재학습 후 검증" → 둘 다 **적용 대상 부재**
- 11 케이스 (E2a~E2d5) 모두 **동일한 frozen 모델 공유** → 상대 순위 절대 불변
- AI Gate OFF 패치 적용 → AR3 간접 영향 (모델 거부 시 Shadow sync → threshold 변화) 경로도 차단

**판정**: 🟢 **재실행 불필요**. 기존 #38 (E2b Soft 후보), #40 (E2d5 수익 1순위) 결과 그대로 유지. v21 제안 방향 불변.

**장기 고려 사항**:
- 시뮬에 walk-forward 재학습을 추가하면 실전 성과 재현 정확도 향상 가능 (단, 현재는 "단발 학습" 구조로 모든 케이스 일관성 확보)
- AR3 부재 → 시뮬이 프로덕션보다 비관적/낙관적 어느 방향인지는 indeterminate (실험 필요)
- 당분간 CLAUDE.md + backtest_log.md에 "시뮬은 단발 학습, 프로덕션 재학습 정책 미재현" 명시 유지

**산출**: `backtest/results/sim_v208.1_audit.md`
**시뮬 변경 없음**. 커밋 불필요.

---

## 2026-04-20 #42: 장기 BEAR 포함 E2 재검증 (52개월, 5 케이스) — ✅ E2b+6mo 채택
- **파일**: `backtest/scripts/bt_e2_longterm_52mo.py`
- **시뮬**: v20.8.1 정합 + S1(e2_gap_score) + S2(e2_dynamic_tiers) cfg 추가
- **기간**: 2022-01-01 ~ 2026-04-19 (52.3개월, 9413봉 4H, **2022 BEAR 13개월 포함**)
- **학습**: 2021-06-01 ~ 2021-12-31 (1284봉, walk-forward pre-period)
- **E2 BEAR 활성**: 40.9% / 연속 최장 285일
- **B&H**: 피크 30.77M @ 2025-10-09, 종료 19.42M, CAGR +16.71%, 최대 MDD 88.33%

**전체 성과표** (CAGR 순):

| ID | 최종 | CAGR | MDD | Sharpe | BULLcap | 거래 | 예외 | E2a 대비 |
|---|---|---|---|---|---|---|---|---|
| **E2b+6mo** | **27.54M** | **+26.60%** | **20.81%** | **1.48** | 93.2% | 68 | 16 | **+836K** |
| E2a | 26.71M | +25.70% | 20.81% | 1.45 | 94.6% | 53 | 0 | baseline |
| E2b | 26.63M | +25.61% | 20.81% | 1.44 | 90.1% | 65 | 13 | -80K |
| E2-OFF | 24.04M | +22.66% | **32.93%** | 1.11 | 87.2% | 84 | 0 | -2,662K |
| Dynamic | 21.37M | +19.34% | 27.06% | 1.10 | 79.3% | 95 | 43 | -5,332K |

**구간별 수익률**:

| ID | 2022 BEAR | 2023 회복 | 2024 BULL | 2025 재하락 |
|---|---|---|---|---|
| E2a | -4.07% | +12.72% | +167.21% | -7.57% |
| E2b | -6.84% | +12.72% | +162.03% | -3.18% |
| **E2b+6mo** | -8.96% | **+19.31%** | +162.03% | -3.18% |
| Dynamic | -20.98% | +17.03% | +162.03% | -11.75% |
| E2-OFF | **-30.47%** | +45.02% | +164.17% | -9.69% |

**2023 회복기 첫 진입 타이밍**:
- E2a / E2b: 2023-01-22 (D+21)
- E2b+6mo: **2023-01-05 (D+4)** ← 6개월 게이팅 덕에 17일 조기 진입
- Dynamic: 2023-01-01 (D+0) ← 너무 빠름 (많은 실수)

**핵심 발견**:
1. **E2 차단은 장기 BEAR 방어에 필수**: E2-OFF MDD 32.93% vs E2a 20.81% — E2 OFF는 MDD 12%p 악화 (+2022 BEAR -30% vs E2a -4%)
2. **E2b+6mo = 최적 타협점**: 6개월 엄격 차단 + 이후 완화 → BEAR 방어 + 회복기 조기 진입 → CAGR +0.91%p, **MDD 증가 없음**
3. **E2b 단독 부족**: O3 예외만으로는 회복기 진입 시점이 E2a와 동일 (2023-01-22), 의미 있는 개선 없음 (-80K)
4. **Dynamic 공격적 → 재앙**: 43 예외 (vs 16), 2022 BEAR -20.98%, MDD 27% → BEAR 방어 파괴
5. **기회비용 측정**:
   - 2022 BEAR: E2 보호 +26.4%p
   - 2023 회복: E2 기회손실 -32.3%p (E2-OFF가 빨리 진입해 이득)
   - 2024 BULL: E2 보호 +3.0%p (소폭)
   - 순이익 (E2a - E2-OFF): +2.66M → E2 차단의 장기 가치 명확
6. **E2b+6mo**: 2022 BEAR 손실 소폭 확대 (-4.07%→-8.96%)지만 2023 회복 이득 (+12.72%→+19.31%)이 상쇄하고도 남음

**Dynamic 실패 원인**:
- T2/T3 (gap≤-20%/-30%, score 완화)는 "더 깊이 빠진 곳에서 바닥 매수" 컨셉 → 실제로는 하락 가속화 중간의 fake rally 진입
- T1 32건, T2 36건, T3 27건 — 43건 실제 진입 (중복 제거)
- 평균 PnL -0.15%, 승률 30.2%, PF 0.95 — 기대치 하회

**판정**: ✅ **E2b+6mo 채택 후보 1순위** (v21 프로덕션 후보)
- 기존 #40 (28개월, Strict 미통과) 결과와 **다른 결론** — 2022 BEAR 표본이 추가되어야 진정한 E2 가치가 드러남
- 28개월만 보면 E2-OFF도 준수하나, 2022 BEAR 포함 52개월에서는 E2 차단이 결정적 방어

**v21 제안 업데이트**:
- **1순위**: **E2b+6mo** = O3 예외 + `e2_require_days_since_e2=180` 게이팅
- 2순위: E2a 유지 (보수적 옵션)
- ❌ 기각: E2b 단독 (이득 미미), Dynamic (MDD 악화)

**후속 액션**:
- `improvement_todo.md` v21 규칙 업데이트 (E2b+6mo 1순위)
- #40 결과와 재비교 (28mo vs 52mo): 기간 의존성 분석 필요
- 프로덕션 포팅 시: `btc_bot_v281.py`에 `E2_GAP_SCORE_EXCEPTION + E2_REQUIRE_DAYS_SINCE_E2=180` 추가

**산출**: `backtest/results/bt_e2_longterm_52mo.md`, `e2_longterm_lead_entries.csv` (72건), 캐시 `backtest/btc_4h_longterm_cache.csv` (10838봉)
**시뮬 변경**: `backtest/core/simulator.py`에 `e2_dynamic_tiers` cfg 추가 (기본 None → 기존 동작 보존)

---

## 2026-04-20 #43: E2 차단 기준 지표 재설계 (12 케이스) — ✅ F10 권고 (교체 후보)
- **파일**: `backtest/scripts/bt_e2_timeframe_study.py`
- **시뮬**: v20.8.1 정합 / 예외 전면 OFF / KS OFF / AI Gate OFF (순수 차단 기준 효과 측정)
- **기간**: 2022-01-01 ~ 2026-04-19 (52.3개월, 2022 BEAR 포함)
- **케이스**: 10종 차단 기준 + E2a(F2 alias) + E2-OFF

**전체 성과표** (CAGR 기준 정렬):

| ID | 차단 기준 | 최종 | CAGR | MDD | 차단% | 페이크% | 승률 |
|---|---|---|---|---|---|---|---|
| **F10** | **F2 OR F5** | **28.79M** | **+27.92%** | **20.83%** | 62.3 | 6.4 | 36.2 |
| F5 | 4H EMA21<EMA55 역배열 | 27.71M | +26.78% | 29.64% | 47.8 | 12.7 | 35.2 |
| F7 | 일봉 EMA50<EMA200 데드크로스 | 27.59M | +26.65% | **19.93%** | 35.9 | 8.2 | 34.7 |
| **F2** | 일봉 종가<EMA200 (현 E2) | 27.40M | +26.45% | 20.86% | 41.2 | 5.8 | 36.5 |
| F9 | F2 AND F5 | 26.37M | +25.33% | 29.64% | 26.7 | 11.8 | 35.5 |
| F1 | 4H 종가<EMA200 | 25.68M | +24.56% | 23.34% | 48.6 | 9.7 | 37.1 |
| F3 | 일봉 종가<EMA50 | 24.68M | +23.40% | 23.92% | 47.8 | 9.7 | 32.3 |
| F6 | 일봉 EMA21<EMA55 역배열 | 24.44M | +23.13% | 19.43% | 48.6 | 5.9 | 35.3 |
| F4 | 주봉 종가<EMA50 | 24.43M | +23.11% | 24.39% | 31.7 | 10.3 | 32.8 |
| E2-OFF | 차단 없음 | 24.03M | +22.64% | **32.93%** | 0 | 14.3 | 33.3 |
| F8 | 주봉 EMA21<EMA55 역배열 | 23.48M | +21.99% | 23.15% | 29.0 | 8.9 | 32.1 |

**2022 BEAR 방어** (13개월, BTC 크래시):

| ID | 수익 | 진입 | MDD |
|---|---|---|---|
| F7 | **-0.42%** | 1 | 1.27% |
| **F2/F10** | -1.56% | 2 | 8.54% |
| F6 | -8.14% | 5 | 13.08% |
| F5/F9 | -27.50% | 19 | 28.88% |
| E2-OFF | -30.47% | 25 | 32.08% |

**핵심 발견**:
1. **F10 (F2 OR F5) 유일 과적합 방어**: 2022 BEAR Top3 ∩ 2025 재하락 Top3 공통 → 다른 케이스들은 특정 BEAR에만 우수 (F7=2022 / F5/F9=2025)
2. **F10의 CAGR +1.47%p 개선, MDD 중립**: 20.83% vs F2 20.86% — 리스크 증가 없이 수익 개선
3. **2024 BULL 피크 캡처 F10 단독 100% 초과 (101.99%)**: F2는 97.06%. F10이 BULL 후반 상승까지 더 포착
4. **F10 거래수 감소 (52→47)**: 더 선별적인 진입, 품질 유지
5. **4H 기반 단독 (F1/F5) 변동성 큼**: F1 전환 271회 (페이크 148), F5 전환 143회 (페이크 17). F2 OR로 묶이면 안정화
6. **주봉 기반 (F4/F8) 열위**: 전환 3~7회로 너무 적어 회복 시점 늦어짐 (F8 첫 진입 D+184)
7. **데드크로스 (F7)**: 전환 5회, 차단 35.9%, MDD 19.93% (최저), 2022 BEAR 방어 99.6% — "차분한 보수 대안"으로 유력
8. **E2-OFF 참조**: CAGR +22.64% / MDD **32.93%** — E2 차단 자체가 BEAR 방어에 결정적

**엄격 AND 판정 결과**: 전 케이스 FAIL
- 병목: "2023 회복 ≤ D+15" — F5/F9만 통과 (D+4.4)이나 MDD 초과
- F10은 D+21.2 (F2와 동일) — 이는 F10 고유 결함 아님
- Soft 판정에선 F10이 명백한 1순위

**수익/손실 로그 분석 핵심 패턴**:
- **손실**: 대부분 ATR손절 (케이스 대부분 8~10/10), RSI 평균 50~60 구간, ADX 24~31 (중간) — 즉 "모호한 구간의 진입"
- **수익**: 트레일링/계단손절 엔딩 다수, RSI 중립, ADX 21~27 (살짝 낮음) — 안정 추세
- **F10의 손실 패턴**: 페이크아웃 비율 10% (F5 40% 대비 매우 낮음) — OR 구조가 F5의 노이즈 필터

**Jaccard 겹침 매트릭스**:
- F2 ↔ F6 = 0.76 (일봉 계열 높음)
- F4 ↔ F7 = 0.75 (주봉↔데드크로스)
- F1 ↔ F3 = 0.84 (4H vs 일봉 EMA50 유사)
- **F2 ↔ F5 = 0.43** — **독립 신호** → F10 (OR)가 효과적 이유

**판정**: 🎯 **F10 Soft 채택 권고** (엄격 AND는 FAIL이나 실용 관점 1순위)
- F2 → F10 교체: 리스크 중립, 수익 +1.47%p
- **구현**: 프로덕션 E2 로직에 "4H EMA21 < EMA55" 조건 추가 (OR)
- 4H EMA는 이미 기존 계산에 있음 → 추가 데이터 fetch 불필요
- **Alternative F7**: "차분한 보수 대안" — MDD 최저 19.93%, 전환 5회만

**v21 방향 업데이트**:
- 기존 #42 E2b+6mo 권고는 **예외 규칙** (진입 허용) 레이어
- #43 F10 권고는 **차단 기준 지표** 레이어
- **두 레이어 독립적으로 적용 가능**: F10 차단 + E2b+6mo 예외 병행
- 단, 차단 기준 변경 영향 범위가 크므로 순차 적용 권장 (1단계 F10, 2단계 E2b+6mo)

**리스크**:
- F10 차단 비율 62.3% (F2 41.2% → +21%p 증가) — 과도 차단 시 BULL 캡처 손실 가능
- 4H EMA 역배열 (F5)은 본래 노이즈 높음 (페이크 flip 17회) — 단독 사용 시 위험, OR로 쓰면 완화
- 52개월은 단일 사이클만 포함 — 2021 이전 BEAR (2018, 2020)에서는 미검증
- 프로덕션 단발 학습 시뮬 한계 → 실전 효과는 Shadow 매칭 검증 필요

**현재 시장 (2026-04-18 21:00, price 112.8M)**:
- F2: 차단 ON | F10: 차단 ON | F7: 차단 ON
- → 지금 F10 배포해도 즉시 영향 없음 (F2와 동일 동작)
- → 향후 F2 OFF 시 F5 상태에 따라 F10 동작 분기

**산출**:
- `backtest/results/bt_e2_timeframe_study.md` (475행 — 표 5개 + 로그 분석 6개)
- `backtest/results/e2_timeframe_loss_cases.md` (389행 — 손실 deep-dive 케이스별 5건)
- `backtest/results/e2_timeframe_transitions.csv` (784 전환 이벤트)
- `backtest/results/e2_timeframe_trades.csv` (668 진입/청산)

**시뮬 변경 없음** (기존 bear_block 인터페이스만 사용).

---

## 2026-04-21 #44: F10/F7 심층 검증 — ✅ v21 Option B (F10 + E2b) 확정

**배경**: #43 F10 Soft 1순위 확정 전 3개 분석 패키지 (추가 재실행 금지, 기존 trades.csv 재활용).

**분석 1 — F10 vs F2 Trade-Delta**
- 공통 40건 중 39쌍 완전 동일 exit_ts + 1쌍 경로 분기
- F2_only 12건 (+0.63%, BULL Range leading_signal) = F10 기회비용
- F10_only 7건 (-0.69%, 모두 pyramid) = 피라미드 경로 분기 (구현 버그 아님)
- 단순 PnL% 합산: F10 **net -12.4%p 불리**. 실제 +1,389K 우위는 **복리·capital allocation 경로 효과** → 정량 귀속은 재시뮬 필요 (🔴)

**분석 2 — 2024-03-16 공통 손실 (-7.14%)**
- 유사 패턴 검색: Range + RSI 45-55 + ADX 18-24 + mom20b ±2% → 52mo **526봉** 매칭
- Avg fwd-19b **-0.07%**, 승률 48.5% → **통계적 노이즈** (꼬리 위험)
- 5 방어 필터 중 4개 차단 가능하나 모두 터미널 **-12% ~ -42%** 감소
- ATR 손절이 이미 정상 작동 (-7.14%에서 멈춤) → **추가 필터 비경제적**

**분석 3 — F7 (데드크로스) 과적합**
- 2022 BEAR EMA50/200 이격 **-27.52%**, 2025 **-16.77%** (1.64x)
- F7 vs F2: 2022 1건 vs 2건 (F7 +1건 방어), 2025 0건 vs 0건 (동률), 2024 BULL 캡처 97.73% vs F10 101.99% (**-4.26%p**), 2023 회복 D+55 vs D+21.2 (**+34일 지연**)
- 판정: 과적합 아닌 **F2 subset (중복적)**. BULL 참여 부족 + 회복 지연이 CAGR/캡처 손실

**v21 최종 권고**: **Option B — F10 (F2 OR F5) + E2b (O3 + 6mo) 유지**

| Option | 내용 | CAGR | MDD | 판정 |
|---|---|---|---|---|
| A | F10 단독 | +27.92% | 20.83% | OK but E2b 미포함 |
| **B** | **F10 + E2b** | **~+28%+α** | **~21%** | **✅ 채택** |
| C | F7 단독 | +26.65% | 19.93% | BULL 지연 |
| D | F7 + E2b | ~+27%+α | ~20% | C 한계 상속 |
| E | F10 + 3/16 필터 + E2b | <+27% | 15-22% | 과적합 위험 |

**신뢰도 종합**:
- 🟢 F10 자산 우위 존재 (원 리포트 확정)
- 🟢 2024-03-16 = 노이즈 (526봉 표본)
- 🟢 F7 = F2 중복 (이격/거래수/BULL 캡처 정량)
- 🟡 F10 우위 메커니즘 정량 귀속 (재시뮬 필요)
- 🔴 다음 BEAR F7 vs F10 예측 (2 샘플만)

**산출**:
- `backtest/results/f10_f7_final_audit.md` (종합, 본 권고)
- `backtest/results/f10_trade_delta.md` + `f10_f2_delta_trades.csv`
- `backtest/results/loss_2024_03_16_deepdive.md` + `similar_losses_pattern.csv` (526행)
- `backtest/results/f7_overfit_audit.md` + `f7_transitions_detailed.csv` (5 전환)

**운영 규칙 추가**: trades.csv 재활용 분석 시 "근사 터미널/MDD/PF"는 상대 순위 비교만 유효, 절대값 신뢰 금지. 정확 값은 시뮬 재실행 필요.


---

## 2026-04-21 #45: Strong Trend 분리 연구 (ADX 30+ 공격 파라미터) — ❌ 전면 기각

- **파일**: `backtest/bt_strong_trend_split.py` + `backtest/core/simulator.py` (strong_trend_* cfg 신규)
- **기간**: 2023-01-01 ~ 2026-04-19 (40.1개월, 7223봉, btc_4h_longterm_cache 사용)
- **config**: v20.9.4 프로덕션 정합 (F10 + E2b + E2b+6mo + Range C6 + BD). **AI Gate OFF** (Strong 단독 효과 측정). 두 KS 모드 병행: auto_recover 20% (정합) + OFF (단독 효과)
- **B&H**: 피크 84,575,600 @ 2025-10-09 / 종료 53,383,270 (+433.83%)
- **가설**: ADX 30+ 구간은 강한 추세 → 트레일링 ATR×5.0~6.0 + step_lookback 3.0+로 포지션 오래 유지 → BULL 캡처 향상
- **ADX 평가**: 동적 (현재 봉 ADX 기준, entry-time 고정 아님)

### KS OFF (Strong 단독 효과, 40mo 연속)

| id | label | final_eq | ret% | MDD% | PF | n | wr% | BULLcap% | vs_B&H% |
|---|---|---|---|---|---|---|---|---|---|
| **B0** | 현 프로덕션 (TU 4.5/2.5, Strong OFF) | **28,492,584** | **+184.93** | 20.86 | 2.36 | 55 | 36.36 | **35.07** | 53.37 |
| C1 | trail 5.0 / step 2.5 / ADX 30+ | 28,449,820 | +184.50 | 20.86 | 2.36 | 55 | 36.36 | 35.02 | 53.29 |
| C6 | trail 5.5 / step 2.5 / ADX 30+ | 28,300,002 | +183.00 | 20.86 | 2.35 | 55 | 36.36 | 34.83 | 53.01 |
| C2 | trail 5.5 / step 3.0 / ADX 30+ | 22,466,950 | +124.67 | 20.86 | 2.26 | 56 | 35.71 | 27.65 | 42.09 |
| C3 | trail 6.0 / step 3.0 / ADX 30+ | 22,466,950 | +124.67 | 20.86 | 2.26 | 56 | 35.71 | 27.65 | 42.09 |
| C4 | trail 5.5 / step 3.0 / ADX 28+ | 22,466,950 | +124.67 | 20.86 | 2.26 | 56 | 35.71 | 27.65 | 42.09 |
| C5 | trail 6.0 / step 3.5 / ADX 30+ | 22,466,950 | +124.67 | 20.86 | 2.26 | 56 | 35.71 | 27.65 | 42.09 |

### B0 대비 Δ (KS OFF)

| id | Δret%p | Δmdd%p | ΔBULLcap%p | 판정 |
|---|---|---|---|---|
| C1 | -0.43 | 0.00 | -0.05 | 🔴 기각 (거의 동일) |
| C6 | -1.93 | 0.00 | -0.24 | 🔴 기각 (미세 악화) |
| C2/C3/C4/C5 | **-60.26** | 0.00 | **-7.42** | 🔴 **대폭 악화** |

### 핵심 발견

1. **step_lookback 3.0+ → -60%p**: step 2.5(B0) vs step 3.0/3.5(C2-C5) 의 단일 변수 영향 명확. Strong 구간에서 step_lookback 확대 시 TP 도달 후 손절선이 더 낮게 형성 → 역방향 변동 시 손실 확대 (특히 피라미딩 깊은 경우 복리 손실).
2. **trail_m 상향 효과 미미**: 4.5→5.0(C1) -0.43%p, 4.5→5.5(C6) -1.93%p. Strong 구간에서 trail_m 의미 있게 작동하지만 B0 대비 소폭 손실.
3. **C2=C3=C4=C5 동일**: trail 5.5/6.0/ADX 28/30 차이 무의미. Strong 활성 시점에 trail_m 값 차이가 이탈 시점에 영향 거의 없음 + ADX 28~30 사이 추가 거래 없음.
4. **BULL 피크 (2024-10~2025-10)**: B0 156.45% vs Strong 변형 154.72~156.07% → Strong은 BULL 캡처에도 기여 없음
5. **BEAR 2025 (10-09 이후)**: 전 케이스 -3.18% 동일 → Strong 관련 없음
6. **TU 평균 holding**: B0 81.0봉 vs C2-C5 78.2봉 (-2.8봉) → Strong step 3.0이 오히려 TU 포지션을 더 빨리 종료시킴 (역설적)

### KS_ON (v20.9.4 정합) 병기

KS auto_recover 20%에서 모든 케이스 MDD 20.07%로 조기 발동 → BULL 캡처 13-17%로 급감. 그러나 B0 +46.53% vs Strong 그룹 +16.33% 의 **상대 순위는 KS OFF와 동일** → 결론 불변.

### 결론 및 권고

- **Strong Trend 분리 전면 기각**. 현 프로덕션 TU 파라미터 (trail 4.5 / step 2.5) 이 이미 최적.
- **핵심 교훈**: ADX 30+ 구간에서 "더 공격적"이 자동으로 "더 좋음"이 아님. step_lookback 확대는 이익 보호 약화 → 대폭 악화.
- **trail_m 미세 튜닝 여지 없음**: 4.5가 5.0/5.5/6.0 중 최적 확인.
- **BULL 캡처 개선은 Strong 분리로 불가능** → 다른 방향 탐색 필요 (예: 조기 진입, pyramiding tier 조정, AI Gate 개선).

### 과적합 점검 (2022 BEAR)

본 백테스트는 2023-01-01 ~ 2026-04-19 (40개월) 연속이라 2022 BEAR 포함하지 않음. Strong 분리가 BEAR 대응에 해로울 가능성은 있으나 BULL/횡보에서도 이미 기각 → 추가 2022 BEAR 검증 불필요 (매몰비용).

### 신규 simulator 파라미터 (참고용, 기본값 비활성)

```python
"strong_trend_adx_threshold":  0,      # 0=비활성 (default)
"strong_trend_trail_m":        None,
"strong_trend_step_lookback":  None,
```

**산출**:
- `backtest/results/bt_strong_trend_split.md` (본 요약)
- `backtest/results/bt_strong_trend_split.csv` (14행 = 7 케이스 × 2 KS 모드)
- `backtest/core/simulator.py` (strong_trend_* 파라미터 추가, 기본값 비활성 → 기존 백테스트 무영향)

---

## 2026-04-23 #46: 회복장 개선 Range step + init 재탐색 (8 케이스, 52mo) — ❌ 전면 기각

- **파일**: `backtest/bt_recovery_capture.py`
- **기간**: 2022-01-01 ~ 2026-04-19 (52.3개월, 9413봉 4H, btc_4h_longterm_cache)
- **config**: v20.9.4 프로덕션 정합 (F10 + E2b + E2b+6mo + TU BD + infinite step). AI Gate OFF (전략 단독 효과 측정, 동일 모델). KS disabled.
- **B&H**: 피크 30,769,898 @ 2025-10-09 / 종료 19,421,651 (+94.22%) — 구간별: 2022 -63.52%, 2023 +169.45%, 2024 +148.74%, 2025 -20.33%
- **가설**: Range step_lookback 완화(3.0→3.5/4.0) + init 확대(0.70→0.75/0.80) → 2023 회복기 홀딩 강화 → 회복기 수익 개선. 단 BEAR 방어/BULL 효과/MDD 악화 없어야 채택.

### 전체 성과 (52개월)

| id | step/init | 최종자산 | CAGR% | MDD% | Sharpe | n | wr% | PF | BULL_cap% | vs_B&H% |
|---|---|---|---|---|---|---|---|---|---|---|
| **B0** | 3.0 / 0.70 | **27,542,772** | **+26.60** | **20.81** | 1.48 | 68 | 35.29 | 2.09 | 93.19 | 141.81 |
| C3 | 3.0 / 0.75 | 27,556,926 | +26.62 | 21.18 | 1.47 | 68 | 35.29 | 2.11 | 93.31 | 141.89 |
| C4 | 3.0 / 0.80 | 27,589,025 | +26.65 | 21.55 | 1.46 | 68 | 35.29 | 2.12 | 93.50 | 142.05 |
| C1 | 3.5 / 0.70 | 26,250,620 | +25.19 | **48.08** | 0.86 | 29 | 27.59 | 4.33 | 135.57 | 135.16 |
| C2 | 4.0 / 0.70 | 26,250,620 | +25.19 | **48.08** | 0.86 | 29 | 27.59 | 4.33 | 135.57 | 135.16 |
| C5 | 3.5 / 0.75 | 26,209,082 | +25.15 | **48.08** | 0.86 | 29 | 27.59 | 4.34 | 135.35 | 134.95 |
| C6 | 4.0 / 0.80 | 26,171,940 | +25.11 | **48.08** | 0.86 | 29 | 27.59 | 4.35 | 135.16 | 134.76 |
| C7 | 2.5 / 0.70 | 25,687,264 | +24.56 | 21.35 | 1.41 | 71 | 35.21 | 2.02 | 86.91 | 132.26 |

### 구간별 수익 (%) — B0 대비 Δ

| id | 2022_BEAR | 2023_회복 | 2024_BULL | 2025_재하락 | total |
|---|---|---|---|---|---|
| B0(기준) | -8.96 | +21.94 | +107.05 | +19.88 | +175.43 |
| C1/C2 | 0 | **+23.99** | **+41.69** | **-40.21** | **-12.92** |
| C3 | 0 | -0.19 | -0.27 | +0.41 | +0.14 |
| C4 | 0 | -0.37 | -0.53 | +0.87 | +0.46 |
| C5 | 0 | +23.76 | +41.69 | -40.21 | -13.34 |
| C6 | 0 | +23.56 | +41.69 | -40.21 | -13.71 |
| C7 | 0 | 0 | -10.18 | -2.30 | -18.56 |
| B&H | -63.52 | +169.45 | +148.74 | -20.33 | +94.22 |

### 채택 기준 체크 (AND 6)

기준: (1) 2023 +10%p / (2) 2022 -3%p 이내 / (3) 2024 -2%p 이내 / (4) 2025 -2%p 이내 / (5) MDD ≤ 22% / (6) total +5%p 이상

| id | 1 | 2 | 3 | 4 | 5 | 6 | 통과 | 결과 |
|---|---|---|---|---|---|---|---|---|
| C1 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 3/6 | ❌ 기각 |
| C2 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 3/6 | ❌ 기각 |
| C3 | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | 4/6 | ❌ 기각 |
| C4 | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | 4/6 | ❌ 기각 |
| C5 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 3/6 | ❌ 기각 |
| C6 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 3/6 | ❌ 기각 |
| C7 | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | 2/6 | ❌ 기각 |

**전원 6/6 미달 → 전면 기각**.

### 핵심 발견

1. **step_lookback 완화(≥3.5) → 두 얼굴**: 2023 회복기 +24%p **극대 개선**, 2024 BULL +42%p **극대 개선** 하지만 2025 재하락을 B&H처럼 -20% 정통으로 맞음 → **Δ2025 -40%p, MDD 48%** 로 전체 수익 오히려 -13%p. Range P2는 RANGE_NEW에서 trailing 비활성이라 상위 TP 레벨에서 step만 의존 → step_lb 완화 시 이익 보호 완전 소실 → B&H에 근접한 장기 홀딩 = 2025 drawdown 흡수. 기간종료 1건이 +202% (단일 포지션이 2023~2026 끝까지 보유).
2. **C1 = C2, C5 ≈ C6 동일화**: step_lb 3.5와 4.0이 실질 동일. 원인 — lv2 이하에서 stop 후보가 floor_pct(-5%) 바닥에 걸려 breakeven만 유효 + 상위 lv는 실제로 잘 도달하지 않음 → step_lb 추가 완화 무의미.
3. **init 확대 단독 효과 무의미**: 0.70→0.75(C3) Δtotal +0.14%p, 0.70→0.80(C4) +0.46%p. n/wr/Regime 분포 전부 B0와 동일. TP1 도달 시 이미 본전 stop이라 초기 사이즈 차이가 거래 결과에 의미있게 기여하지 않음.
4. **step_lb 축소(C7, 2.5) → 전 구간 악화**: 2023 동일, 2024 -10%p, 2025 -2%p, total -19%p. Range TP 도달 후 step 너무 빨리 올라 이익 실현 지나치게 공격적 → 포지션 조기 종료 + 재진입 손실.
5. **2022 BEAR 방어 완전 동일**: 모든 케이스 E2 예외 진입 10건(O3 7 / gap 3), pnl -6.51%, 구간 -8.96% 동일. E2 로직은 Range step/init과 완전 독립.
6. **Regime 효과**: step 완화 시 Trend_Up 17→8건 (-53%), Range 42→17건 (-60%) — 포지션 장기 보유로 재진입 기회 대폭 감소. 승률도 Range 36%→29%로 하락하지만 평균 PnL +1.68%→+11.83% → 승자 사이즈로 버티는 형태.

### 회복기 홀딩 전략의 근본 한계 (2023 회복기 딜레마)

2023 회복기는 **단방향 상승 구간 (B&H +169%)** 이라 홀딩 강화 전략이 국지적으로 유리. 하지만 동일 홀딩 전략이 **2024 BULL 피크 후 2025 재하락도 그대로 맞음**. 회복기 개선과 재하락 방어는 **이번 Range step 축에서 trade-off** 임이 재확인됨 (#36 결과와 일치).

### 권고

- **Range step/init 추가 완화 전면 기각** → v20.9.4 B0 (step 3.0 / init 0.70) 유지가 최적.
- **회복기 개선 방향 전환 필요**: 이번 축(Range step 완화)으로는 MDD 악화 없이 개선 불가. 다른 방향:
  - (A) **Regime-aware 조기 진입**: 2023-01 ~ 2023-06 특정 조건 (BNC30/funding/외부 지표) 시 Range init 일시 상향
  - (B) **2024 BULL 피크 탐지 후 2025 재하락 조기 축소** (기존 v19 시도에서 기각된 BULL_exit 재검토)
  - (C) **Range P2 trailing 선택적 ON** (현재 RANGE_NEW에서 trailing 비활성 ← 이번에 재확인된 약점) — 수익 보호와 기회 포착 균형 재설계
- **C7(step 축소) 완전 기각**: step 2.5 역시 B0 3.0보다 전체적으로 열등. 현 프로덕션 유지.

### 산출

- `backtest/results/bt_recovery_capture.md` (요약 + 판정)
- `backtest/results/bt_recovery_capture.csv` (8 케이스 × 18 지표)
- `backtest/results/bt_recovery_capture_segments.csv` (케이스 × 4 구간 + B&H)
- `backtest/results/bt_recovery_capture_regime.csv` (케이스 × 5 Regime × 3 지표)
- `backtest/results/bt_recovery_capture_exits.csv` (케이스 × 청산사유 × 2 지표)
- `backtest/results/bt_recovery_capture_2023_trades.csv` (2023 회복기 전체 거래, 8 케이스)
- `backtest/results/bt_recovery_capture_diff_analysis.md` (상위 3 케이스 vs B0 거래 단위 diff)

### 프로덕션 영향

없음. 백테스트 전용. 봇 재시작 불필요. v20.9.4 유지.

---

## 2026-04-24 #47: 실거래 PF 감점 영향 (4 케이스, 52mo) — 🟢 Phase 2 P2 채택

### 배경

프로덕션 `calc_position_size` L858: `if 0 < recent_pf < 1.0: risk_pct *= 0.5`. `calc_recent_stats` n=30 이나 실제 가드는 `len(sells) >= 5`. n<30 구간에서 감점 발동 가능 → 통계적 불안정성 우려.

**Phase 1 선행 확인**: 현재 `recent_pf=9.47` (n=5 SELL 기반 pf=2.84/0.30), 감점 미적용. `get_ai_gate_threshold` 의 pf 인자는 dead arg (본문 미사용). 상세는 `pf_investigation_phase1.md`.

### 케이스 (4)

| id | 설명 | pf_penalty_mode |
|---|---|---|
| B0 | 현행 | `current` |
| P1 | 감점 OFF | `off` |
| P2 | n<30 가드 (trade_count>=30 시만 발동) | `guard_30` |
| P3 | Shadow rolling PF 500봉 사용 | `shadow_rolling` |

### 전체 성과 (52개월, AI Gate ON + KS 20%)

| id | final_eq | CAGR | MDD | 2022 | 2023 | 2024 | 2025 | penalty_n |
|---|---|---|---|---|---|---|---|---|
| B0 | 23,634,160 | +22.17% | 20.49% | -7.8% | +7.8% | +99.5% | +19.3% | 6/62 |
| **P1** | **24,123,312** | **+22.75%** | **18.85%** | -10.8% | **+13.7%** | +99.5% | +19.3% | 0 |
| **P2** | **24,123,312** | **+22.75%** | **18.85%** | -10.8% | **+13.7%** | +99.5% | +19.3% | 0 (skip 6) |
| P3 | 23,142,083 | +21.57% | 19.45% | -7.2% | +6.4% | +98.7% | +18.0% | 26 |

### 핵심 발견

- **B0 감점 6건이 모두 trade_count<30 구간에서 발동** → P2 guard_30 으로 완벽 회피. P1/P2 결과 동일.
- **P1/P2 vs B0**: CAGR +0.58%p, MDD -1.64%p, 2023 회복기 +5.9%p 개선. 2022 BEAR 만 -3%p 악화. 종합 우위.
- **P3 (shadow rolling)**: 감점 41.9% 초과 발동 → 오히려 -0.60%p 악화. rolling PF 는 감점 신호원으로 부적합.

### 권고

**P2 (guard_30) 채택**. 프로덕션 `calc_position_size` L858 에 `if trade_count >= 30:` 선행 가드 추가.

### 산출

- `bt_real_pf_penalty_impact.md` / `.csv`
- `pf_investigation_phase1.md` / `pf_investigation_summary.md`

---

## 2026-04-24 #50: R1 심화 Prescreen v2 (7 슬라이스) — 🔴 R1 전체 기각 (실전 HARD 1건뿐, R2와 중복)

### 입력
`backtest/results/e2_virtual_trades.csv` (1,476 행, 2024-07 ~ 2026-04)

### 슬라이스 7종

| id | 조건 | n | WR | avg | 판정 |
|---|---|---|---|---|---|
| R1-base | gap[-7,-3] + score>4 + ema | 41 | 41.5% | -0.66% | 🔴 NO-GO |
| R1-A | gap[-7,-3] + ema + ma5_above_ma10 | 54 | 50.0% | +0.08% | 🔴 NO-GO |
| R1-B | gap[-7,-3] + ema + **hit_tp5_first==1** | 32 | 100% | +4.70% | 🟢 HARD **(post-hoc)** |
| R1-C | gap[-5,-1] + ema | 107 | 64.5% | -0.04% | 🔴 NO-GO |
| R1-D | gap[-7,-3] + ema + **MFE>3%** | 37 | 89.2% | +3.57% | 🟢 HARD **(post-hoc)** |
| R1-E | gap[-7,-3] + ema + 7d_pct<0 | 7 | 57.1% | +0.41% | 🔴 NO-GO |
| R1-F | gap[-7,-3] + ema (no score) | 60 | 55.0% | +0.54% | 🟢 HARD (실전 가능) |

### 핵심 결론

- R1-B/D 는 **청산 후 산정되는 값** (hit_tp5_first / MFE) → 실전 적용 불가
- R1-F 만 실전 가능하나 R2-B (ema_ok 단독) 와 동치 → Phase B에서 교차검증
- score > 4.0 추가 시 오히려 성과 급락 (R1-F +0.54% → R1-base -0.66%)

### 산출

- `backtest/results/e2_gap_recovery_prescreen_v2.md`
- `backtest/scripts/analyze_e2_gap_recovery_v2.py`
- `/tmp/r1_v2_verdict.json` (Phase B 연계용)

---

## 2026-04-24 #54: F7a 심화 검증 — 🔴 F7a 채택 재고 (#53 판정 뒤집음)

### 배경
#53에서 F7a "실질 채택 권고" → v20.9.9 배포 전 3가지 의문 심화 검증.

### 핵심 발견 (기각 방향)

**A. 2022-10 worst_month Δ=-2.82%p 원인 규명**:
- 2022-09~11 기간 F2/F7 **둘 다 100% ON** (동일 차단 상태)
- 즉 차단 기준 변경이 영향 준 게 아님
- **실제 원인**: F7a는 gap 예외로 3건 진입 (전부 손실 -8.96%p), B0는 1건 (+2.92%p)
- `합계 (F7a - B0) = -11.88%p`

**B. F11a 2025 Δ=0 이유**:
- 2025 기간 F2 ON ∧ F7 OFF = **312봉** (F2만 차단)
- **F2 OFF ∧ F7 ON = 0봉** → F7은 항상 F2 subset (2025 한정)
- F11 ≡ F2 → F11 추가 기여 없음
- F7은 회복장(BULL)엔 F2보다 덜 엄격

**C. F7a gap 예외 7건 품질 분석**:
- WR **43%**, avg +3.15%, median **-1.60%**, PF 2.59
- 7건 중 **4건 손실 (-13.85%p 합)**, 2건 소소 수익 (+3.54%p)
- 1건 대박: **2023-01-05 +32.38%**
- **F7a 전체 개선의 대부분은 이 1건에 의존** (+32 - 14 + 3 = +21%p)

### 구조적 원인

F7a의 gap 예외 조기 발동:
- `bars_since_e2_a` 카운터가 F7 기준이면 F2 기준보다 다른 시작점
- F7 = EMA50<EMA200 은 **F2보다 일찍 시작**할 수 있음 (2021년 중반부터)
- 2022 중반 F7 bars ≥ 1080 먼저 도달 → gap 예외 경로 조기 활성
- 결과: 2022-07부터 예외 진입 7건 (B0는 2023-01까지 대기)
- 이 7건 품질이 낮음 (median 음수) + 1건 대박 의존

→ **F7a 개선은 구조적 우위가 아니라 bars 카운터 시작점 차이 + 단일 거래 운**

### F7의 lagging 특성 재고

- F2 (일봉<EMA200): 즉시 반영, lag 없음
- F7 (EMA50<EMA200 데드크로스): EMA50 50일 평균 → **신호 지연 ~2주**
- F7이 더 오래 활성 (39.1% vs 36.1%) → 반등 초기 차단 유지 → 회복 참여 지연
- 일반론: F7은 "늦게 차단 해제" = 보수적 → 회복장에서 기회 상실

### 판정 번복

- 🔴 **F7a 기각 — F2 (v20.9.8) 유지 확정**
- #53 실질 판정이 **단일 거래 (+32.38%) 의존성 간과**
- 2023-01 거래 1건 빼면 F7a ≈ B0 (52개월 기준 미미한 차이)
- **과적합 가능성**: 단일 거래 운에 의존한 개선 (#48 Recovery Regime R5 사례와 유사)

### v20.9.9 계획

- 🔴 **v20.9.9 (F7 채택) 취소**
- 🟢 **v20.9.8 (F2 채택) 유지 확정**
- F7은 **다음 BEAR 전환 시 재평가** (실거래 환경)

### 기록 교훈

- 월별/구간별 개선이 실제로 차단 기준 변경에서 오는지, 아니면 파생 경로(예: bars 카운터, gap 예외 발동 타이밍)에서 오는지 항상 구분 필요
- 단일 대박 거래 제거 (+32%) 시 개선이 지속되는지 재검증이 "과적합 방지"의 표준 절차

### 산출

- `backtest/results/f7a_deep_analysis.md`
- `backtest/scripts/analyze_f7a_deep.py`

---

## 2026-04-24 #53: F2/F7/F11 E2 차단 기준 재평가 (7 케이스, 52mo) — 🟡 실질 채택 권고 (#54에서 기각)

### 배경
v20.9.8 F2 채택 후 후속. #43 당시 F7 (일봉 EMA50<EMA200 데드크로스) 이 F10에 밀려 미채택. 예외 규칙 문맥 변화 후 재평가.

### 7 케이스 전체 성과

| id | block | exc | final_eq | CAGR | **MDD** | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| B0 (v20.9.8) | F2 | ON | 26.78M | +25.77% | 19.28% | -8.1% | +20.1% | +98.2% | +22.5% |
| M5 | F2 | OFF | 25.40M | +24.24% | 19.28% | -4.1% | +14.5% | +98.2% | +16.7% |
| **F7a** | **F7** | **ON** | **28.68M** | **+27.80%** | **16.80%** | **-6.0%** | **+22.1%** | **+102.5%** | **+23.4%** |
| F7b | F7 | OFF | 27.26M | +26.29% | 16.80% | **-0.4%** | +14.1% | +102.5% | +18.4% |
| F11a | F11 | ON | 28.15M | +27.24% | 18.24% | -7.1% | +23.3% | +100.7% | +22.5% |
| F11b | F11 | OFF | 26.99M | +26.01% | 18.24% | **+0.0%** | +15.2% | +100.7% | +16.7% |

### F7a 실질 평가 (모든 구간 개선)

| 지표 | B0 | F7a | Δ |
|---|---|---|---|
| CAGR | +25.77% | +27.80% | **+2.02%p** |
| **MDD** | 19.28% | 16.80% | **-2.49%p** |
| 2022 total | -8.1% | -6.0% | +2.13%p |
| 2023 total | +20.1% | +22.1% | +2.01%p |
| 2024 total | +98.2% | +102.5% | +4.33%p |
| 2025 total | +22.5% | +23.4% | +0.91%p |
| 거래수 | 61 | 60 | -1.64% |

**전 4개 구간 개선 + MDD 2.49%p 개선** — 과적합 징후 없음.

### Jaccard 차단 구간 유사도

- F2↔F7: 0.606 (40% 다른 구간)
- F2↔F10: 0.597
- F7↔F10: 0.469
- F2 활성: 36.1% / F7 활성: 39.1% / F11 활성: 46.8%

### 자동 판정 vs 실질 판정

**자동 (spec 엄격)**: 🔴 F7a 기각 — 2022-10 월별 delta -2.82%p 로 "월별 악화 없음" 미충족

**실질 (총합+전 구간)**: 🟢 **F7a 채택 강력 권고**

자동 판정 기준 "월별 악화 없음" 이 월별 재분배(단월 -2.82%p, 타월 개선으로 총합 +2.13%p) 까지 잡아내 과도하게 엄격. 타 3구간 + MDD + CAGR 전부 개선이고 과적합 없음.

### 추가 발견

- **F7b (F7, 예외 OFF)**: 2022 BEAR **-0.4%** (거의 무손실 방어), MDD 16.80%. 단 회복기 -5.99%p 열위 (예외 경로 의존)
- **F11b (F11, 예외 OFF)**: 2022 BEAR **+0.0%** (완전 무손실), 하지만 회복기/2025 -5%p 열위

### 권고

🟢 **v20.9.9 후보: F7a 채택** (`e2_block_mode = "F7"`)

**변경 최소**:
- `E2_BLOCK_MODE` 상수 "F2" → "F7"
- `bear_block_f7_a` precompute 함수 추가 (일봉 EMA50<EMA200)
- 프로덕션 `_update_e2_bear_mode` 에 F7 계산 추가
- 텔레그램/대시보드 "F2 일봉 < EMA200" → "F7 일봉 EMA50 < EMA200 데드크로스"

**배포 전 추가 검증** (선택):
1. 2022-10 월별 -2.82%p 악화 원인 거래별 확인
2. F7 차단 구간의 F2 와 겹치지 않는 40% 구간 특성
3. F7 기준 bars_since_e2 median/분포

### 시뮬레이터 변경 (구현됨)

- `e2_block_mode` 에 "F7" / "F11" 추가
- mod 필드 `bear_block_f7_a` 지원

### 산출

- `backtest/results/bt_e2_f7_f11_ablation.md`
- `backtest/results/bt_e2_f7_f11_ablation.csv`
- `backtest/scripts/bt_e2_f7_f11_ablation.py`

---

## 2026-04-24 #52: F2/F10/F5 Ablation + 진입 타이밍 Diff (5 케이스, 52mo) — 🟢 AY 확정

### 배경

#51 AY (F2 단독) 후보의 CAGR +2.17%p 개선 원리 규명 필요. 특히 거래 수 62 동일하면서 E2 차단 945건 감소 → 진입 타이밍 이동 가설 검증.

### 케이스 (5)

| id | block | exc | 의도 |
|---|---|---|---|
| M1 | F10 | ON | 현행 v20.9.4 |
| M2 | F2 | ON | AY 재현 |
| M3 | F5 | ON | 대칭성 검증 |
| M4 | F10 | OFF | 순수 차단 비교 |
| M5 | F2 | OFF | 순수 차단 비교 |

### 전체 성과

| id | final_eq | CAGR | MDD | n | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| **M1 (현행)** | 24.12M | +22.75% | 18.85% | 62 | -10.8% | +13.7% | +99.5% | +19.3% |
| **M2 (AY)** | **26.78M** | **+25.77%** | 19.28% | 61 | **-8.1%** | **+20.1%** | +98.2% | **+22.5%** |
| M3 (F5) | 8.45M | -3.85% | 20.11% | 11 | -15.5% | 0% | 0% | 0% |
| M4 (F10 예외OFF) | 21.30M | +19.25% | 16.55% | 47 | -4.1% | -7.4% | +103.1% | +18.0% |
| M5 (F2 예외OFF) | 25.40M | +24.24% | 19.28% | 51 | -4.1% | +14.5% | +98.2% | +16.7% |

### 🎯 개선 원리 (M1 vs M2 pairing)

- M1 총 62건, M2 총 61건, **매칭 57건 (±24h)**
- M1만 5건, M2만 4건
- 매칭 쌍 타이밍 diff: median=**0h**, mean=-0.7h (거의 동시 진입)
- 매칭 쌍 PnL diff sum: +0.59%p (미미)
- **M1-only 5건 PnL합: -13.02%p** (전부 손실)
- **M2-only 4건 PnL합: +0.61%p** (거의 중립)

→ **M2 개선의 본질 = M1 손실 거래 5건 회피**. 타이밍 이동 아님.

### M1-only 손실 거래 (F5 제거로 회피된 trap)

| entry_ts | regime | reason | PnL |
|---|---|---|---|
| 2022-10-05 Range | ATR손절 | -3.40% |
| 2022-10-27 TU | 트레일링 | -2.26% |
| 2023-12-16 Range | 계단손절 | -1.52% |
| 2023-12-25 Range | ATR손절 | -2.86% |
| 2025-03-25 TU | ATR손절 | -2.99% |

→ 회복기 초기/조정 구간에서 F5 (4H EMA21<EMA55) 거짓 신호로 잘못된 진입. F5 제거가 이를 필터링.

### 판정 기준 (4/4 통과)

| 기준 | 요구 | 실측 | 판정 |
|---|---|---|---|
| CAGR > M1+1%p | Δ≥+1.0 | +3.02 | ✅ |
| MDD ≤ M1+1%p | Δ≤+1.0 | +0.44 | ✅ |
| 2022 월별 ≥ -0.5%p | worst≥-0.5 | -0.21 (2022-11) | ✅ |
| 2024 BULL ≥ M1-2%p | Δ≥-2.0 | -1.36 | ✅ |

**🟢 AY 채택 확정 — v20.9.8 배포 권고**

### 이상 케이스 분석

- **M3 (F5 단독)**: CAGR -3.85%, 매매 11건뿐, 2022 -15.5% — **F5만으로 BEAR 방어 불가 → KS 영구 중단**
- **M4 vs M5**: 예외 OFF 시에도 F2가 F10보다 우위 (+4.99%p CAGR). F5 제거가 예외 유무와 독립적으로 유효
- **예외 기여도**: M1-M4 = +3.50%p (F10) vs M2-M5 = +1.53%p (F2) → F10이 더 엄격하므로 예외 경로가 더 필요

### 권고

**v20.9.8 (AY 채택)**:
- `e2_block_mode = "F10"` → `"F2"` (프로덕션 변경)
- `bears_since_e2` 카운터: F10 기준 → **F2 기준으로 precompute 필요** (프로덕션 배포 시 마이그레이션)
- 기존 E2b+6mo 예외 경로 (O3 / gap+score / bars≥1080) 유지

### 산출

- `backtest/results/bt_e2_block_mode_ablation.md`
- `backtest/results/bt_e2_block_mode_ablation.csv`
- `backtest/results/ablation_timing_diff.csv` (M1 vs M2 raw pairing)
- `backtest/scripts/bt_e2_block_mode_ablation.py`

### 시뮬레이터 변경

- `e2_block_mode` 에 `"F5"` 단독 모드 추가 (M3 지원용)

---

## 2026-04-24 #51: R2 × R3 교차 백테스트 (7 셀, 52mo) — 🟢 AY (F2 단독) 채택 후보

### 축 정의

- **R2** (진입 예외 추가): A=미적용 / B=ema_ok 단독 / C=ema_ok + bars≥360
- **R3** (E2 차단 조건): X=F10 (F2 OR F5, 현행) / Y=F2 단독

### 7 셀 결과

| id | R2 × R3 | final_eq | CAGR | MDD | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| B0 / AX | 현행 | 24.12M | +22.75% | 18.85% | -10.8% | +13.7% | +99.5% | +19.3% |
| **AY** | **- × F2** | **26.01M** | **+24.92%** | **19.28%** | **-10.8%** | **+20.1%** | **+98.2%** | **+22.5%** |
| BX | ema × F10 | 8.28M | -4.30% | 18.57% | -17.2% | **0%** | **0%** | **0%** |
| BY | ema × F2 | 8.28M | -4.30% | 18.57% | -17.2% | 0% | 0% | 0% |
| CX | ema+360 × F10 | 8.19M | -4.54% | 19.49% | -18.1% | 0% | 0% | 0% |
| CY | ema+360 × F2 | 8.19M | -4.54% | 19.49% | -18.1% | 0% | 0% | 0% |

### 판정

- 🟢 **AY GO**: ΔCAGR +2.17%p, 2023 회복기 +6.4%p, 2022 악화 없음, MDD +0.43%p (<21% 하한 통과)
- 🔴 **R2 전면 기각**: BX/BY/CX/CY 모두 CAGR -27%p 급락, 2023 이후 매매 정지 (KS 영구 중단 추정)

### R3=F2 단독 개선 원인

- v20.9 E2b+6mo 예외 (O3/gap+score/bars≥1080) 추가로 F5 엄격함의 이점 희석
- F5 (4H EMA21<EMA55) 제거 시 회복 초기 EMA 혼란기 진입 허용 → 2023 회복기 +6.4%p
- F2 (일봉 EMA200) 는 유지 → 2022 BEAR 동일 방어 (-10.8%)

### R2 (ema 예외) 실패 원인

- BEAR 중 순간 EMA 정배열 전환 = dead cat bounce → trap
- 초기 손실로 Kill Switch 발동 → auto_recover → 재발동 → 영구 중단
- 2023 이후 매매 0건 → 거래 62→20 급감

### 권고

- **v20.9.8 후보**: `e2_block_mode = "F10"` → `"F2"` 검토 (추가 ablation 후 결정)
- **R2/R1 전면 기각** — ema_ok 기반 예외 재시도 금지

### 추가 검증 과제 (#52 제안)

- F2 vs F10 vs F5-only 3방향 ablation
- 진입/청산 시점 diff (거래 수 62 동일하나 타이밍 차이 확인)
- 2022 BEAR 세분화 (총합 -10.8% 동일하나 월별 분포는?)

### 산출

- `backtest/results/bt_r2_r3_grid.md` / `.csv`
- `backtest/results/r1_r2_r3_final_verdict.md` (종합 판정)
- `backtest/scripts/bt_r2_r3_grid.py`

### 시뮬레이터 cfg 추가

- `r2_ema_exception_mode`: None | "B" | "C" (기본 None = 현행)
- `r2_ema_exception_bars`: 360 (C 모드 기본)
- `r2_ema_exception_ratio`: 0.40 (예외 진입 사이즈)

---

## 2026-04-24 #49: check_ai_gate threshold arg 복원 영향 (4 케이스, 52mo) — ✅ 제거 권고

### 배경

`pf_production_log_audit §5` 발견: production `check_ai_gate(xgb_prob, threshold, ...)` L719 의 `threshold` 인자가 본문 미사용 (dead). `get_ai_gate_threshold()` 출력 전부 무효화 — AI_UNRELIABLE_GATE/dynamic_threshold/LOSS_MODE_GATE/MARKET_VOLATILE_GATE/MARKET_RANGE_GATE 모두 현재 프로덕션 11일간 is_reliable=False 상태이나 실제 gate 결정에 영향 0. 복원 vs 제거 결정 근거 필요.

### 케이스 (4)

| id | 설명 | ai_pass 로직 |
|---|---|---|
| B0 | 현행 (dead) | `(xp>=rth) OR (xp>=dth)` |
| G1 | threshold 단독 | `xp >= gate_thresh` |
| G2 | AND 엄격 | `(xp>=gate_thresh) AND legacy` |
| G3 | OR 완화 | `legacy OR (xp>=gate_thresh)` |

`gate_thresh` = reliable(0.55) or unreliable(0.62) base + market bump (Volatile 0.65/Range 0.60) + cons_loss bump (LOSS 0.65), clip [0.50, 0.70]. `is_reliable = rolling_pf(500) >= 1.0`.

### 결과

| id | final_eq | CAGR | MDD | n | wr | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|
| **B0** | **24,123,312** | **+22.75%** | **18.85%** | **62** | 32.3% | -10.8% | +13.7% | +99.5% |
| G1 | 8,057,703 | **-4.90%** | 20.11% | 17 | 11.8% | -10.2% | -10.2% | **0.0%** |
| G2 | 8,057,703 | -4.90% | 20.11% | 17 | 11.8% | -10.2% | -10.2% | 0.0% |
| G3 | 24,123,312 | +22.75% | 18.85% | 62 | 32.3% | -10.8% | +13.7% | +99.5% |

### 핵심 발견

- **G1/G2 완전 동일**: `gate_thresh > legacy_th` 이므로 AND 중복 (G2 로직 의미 없음)
- **G3 = B0 완전 동일**: OR 에 더 엄격한 조건 추가 = tautology
- **BEAR 방어 기대 완전 무효**: B0/G1/G2 모두 `bear_n=9` 동일 (2022 진입 차단 0건)
- **수익 구간만 차단**: 2023 +13.7% → -10.2%, 2024 +99.5% → **0%**
- 원인: 테스트 기간 `rolling_pf<1.0` 49.4% → 대부분 불신(0.62) + 시장 bump = gate_thresh 상시 0.65~0.70 → XGB mean 0.48 대비 너무 높음

### 결론

🟢 **dead 코드 제거 권고** (B0 === G3 === 현재 프로덕션 = optimal)

### 권고 (프로덕션 변경 — 별건 지시서)

1. `check_ai_gate` 시그니처 `threshold` arg 제거
2. `get_ai_gate_threshold()` 함수 삭제
3. 호출부 4곳 (L2337, L2479, L3094, L3809) `get_ai_gate_threshold(...)` 삭제
4. 상수 AI_UNRELIABLE_GATE/LOSS_MODE_GATE/MARKET_VOLATILE_GATE/MARKET_RANGE_GATE/MIN_THRESH/MAX_THRESH 사용처 재검토 후 제거
5. 전제: `ENABLE_PERF_DEGRAD_TRIGGER = False` 유지

### 산출

- `backtest/results/bt_check_ai_gate_threshold.md` / `.csv`
- `backtest/scripts/bt_check_ai_gate_threshold.py`

---

## 2026-04-24 #48: rolling AI PF 효과 (4 케이스, 52mo) — ⚪ 중립 (PERF_DEGRAD 활성 조건부)

### 배경

`ai_engine.profit_factor` = 학습 시점 test set 1회 스냅샷 (현재 0.38, 매 30캔들 갱신). rolling PF (200/500/1000봉) 로 교체 시 시계열 안정성 + PERF_DEGRAD 트리거 정합성 검증.

### 케이스 (4)

| id | mode | window | final_eq | pf_std | unreliable_bars | avg_thresh |
|---|---|---|---|---|---|---|
| B0 | static (0.38) | - | 24,123,312 | 0.00 | 0 | 0.634 |
| R1 | rolling | 200 | 24,123,312 | **4.92** | 168 | 0.656 |
| R2 | rolling | 500 | 24,123,312 | 1.41 | 99 | 0.647 |
| R3 | rolling | 1000 | 24,123,312 | **0.83** | 52 | 0.641 |

### 핵심 발견

- **4 케이스 전부 동일 성과** (entries identical). rth += 0.05 bump 가 발동해도 xp 가 충분히 높아 ai_pass 변화 없음.
- **PF 변동성은 window 반비례**: R1 4.92 → R2 1.41 → R3 0.83.
- **현 static 0.38 은 rolling 평균(1.43~2.58) 대비 저평가** — 한 번의 불운한 스냅샷이 4일간 유지됨.

### 권고

- **즉시 채택 불필요** (entries 동일, 직접 성과 개선 없음).
- **PERF_DEGRAD 재활성 논의 시 선행 필수**: 현재 OFF (v20.8.1 AR1) 라 숨어있지만 재발 시 static 0.38 은 영구 트리거 상태. R3 (1000봉) 선행 후 PERF_DEGRAD 복구 검토.

### 산출

- `bt_rolling_ai_pf.md` / `.csv`

---

## 2026-04-25 #63 Phase 1: Range 진입 품질 프로파일링 — 🔴 NO-GO

### 배경

#62 Phase 1에서 Range ATR 손절 15건 전원 손실 (MFE 평균 0.42% → 진입 직후 즉시 역배). Entry-side 필터 연구.

### 데이터

B0 Range 42건 → A=ATR손절 15, B=비ATR(계단/트레일/기간) 27.
진입 시점 지표 6개 + score/xgb/adx 수집.

### 지표별 분리력 (sep = |mean_A - mean_B| / pooled_std)

| 지표 | mean_A | mean_B | sep |
|---|---:|---:|---:|
| atr_pct | 0.33 | 0.45 | 0.53 |
| score | 4.65 | 4.30 | 0.36 |
| entry_slip | 0.21 | 0.07 | 0.24 |
| bar_pos | 0.53 | 0.48 | 0.22 |
| xgb | 0.65 | 0.61 | 0.21 |
| adx | 20.68 | 21.32 | 0.18 |
| mom20b | -0.87 | -1.23 | 0.12 |
| bb_pos | 0.37 | 0.38 | 0.02 |
| rsi14 | 46.3 | 46.1 | 0.01 |

### 필터 효과 (GO 기준: 차단율 ≥ 70% AND FP < TP×0.5)

자동 cutoff 중 최고: atr_pct min 0.358 → 차단율 52%, 순효과 +6.9% (미달).
하드 cutoff bar_pos max 0.80 → **TP=3 / FP=2, 차단율 60%, 순효과 +14.9%** (차단율 미달, 단 FP 2건 모두 손실거래라 실질 positive).

### 결정적 관찰

- 6개 지표 중 의미 있는 분리력은 atr_pct(0.53)뿐, 나머지 5개 sep < 0.3
- "추격 진입" 가설 기각: ATR손절이 **저변동 구간**(A atr_pct 0.33 vs B 0.45)에서 발생
- score/xgb 모두 A에서 더 높음 — 룰/AI 게이트 구분 불가

### 판정

🔴 **NO-GO** (단일 필터 중 차단율 ≥ 70% 충족 없음). 단 bar_pos 0.80 단일 최소 검증(#63-B) 실시.

### 산출

- `bt_63_entry_quality_phase1.md` / `bt_63_phase1_entries.csv`
- `scripts/bt_63_entry_quality_phase1.py`

---

## 2026-04-25 #63-B: bar_pos_max 단일 필터 검증 (52mo, 4 cases) — 🟡 YELLOW

### 배경

#63 Phase 1에서 bar_pos ≥ 0.80 cutoff가 TP/FP 비 3:2, 순효과 +14.9%로 원안 block_rate 70% 미달이나 유일한 net-positive 후보. 복리/피라미딩 포함 실제 시뮬 효과 검증.

### 케이스

| ID | cutoff | 최종자산 | CAGR | 2023 | 2024 | 차단 |
|---|---|---:|---:|---:|---:|---:|
| B0 | — | 27,542,773 | +26.60% | +21.94% | +107.05% | 0 |
| F1 | 0.80 | 27,635,731 | +26.70% | +22.07% | +107.12% | 6 |
| F2 | 0.85 | 27,570,855 | +26.63% | +22.07% | +107.05% | 3 |
| F3 | 0.75 | 27,583,038 | +26.65% | +20.70% | +107.33% | 10 |

### 핵심 발견

- **Phase 1 재현성 4/5 (80%)**: F1이 예상 5건 중 4건 차단, 2025-12-07 한 건 미차단(경로 차이)
- **CAGR 델타 F1 +0.10%p/년** → **GO 기준(+0.5%p) 미달**. F2 +0.03, F3 +0.04 모두 미달
- **Range 진입수 42 → 41 (F1)**: 차단되어도 다음 봉에서 대체 진입 → Range ATR 15건 그대로
- **Phase 1 이론 +14.9% (52mo 누적) → 실제 +0.34% (52mo 누적)** ≈ **45배 감쇠**. 복리 환경에서 경로 자체가 재설정되어 단건 회피 효과 상쇄
- MDD/2024 BULL/2022 BEAR/Range 진입수 감소율 모두 GO 기준 통과. **CAGR만 미달**

### 판정

🟡 **YELLOW** — 전 case B0 이상(CAGR +0.03~+0.10)이나 개선폭 노이즈 수준. 프로덕션 반영 불필요. `improvement_todo.md`로 관찰 항목 아카이브.

### 구조적 결론

bar_pos 필터는 Phase 1 단건 회피 효과가 복리 경로 재설정으로 거의 소멸. 회복기 Range ATR 구조적 한계(`project_recovery_roadmap` 기조)와 일치. 후속 축(Shadow AI / 외부 신호) 전환 권고.

### 산출

- `bt_63b_bar_pos.md` / `bt_63b_bar_pos.csv` / `bt_63b_blocked_trades.csv` / `bt_63b_trades.csv`
- `scripts/bt_63b_bar_pos.py`
- simulator.py: `range_bar_pos_max` cfg + `range_bar_pos_blocked_n` stats 추가

---

## 2026-04-25 #65: E2 F2 EMA 기간 단축 (200 → 150/120/100, 52mo, 4 cases) — 🔴 RED

### 배경

E2 BEAR 차단(F2: 일봉 종가 < EMA200)이 회복기 진입 기회 제약 가능성. EMA 단축 시 차단 해제 시점 빨라져 회복 초입 진입 기회 검증.

### 케이스 (4)

| ID | EMA | 최종자산 | CAGR | MDD | 2022 | 2023 | 2024 | 2025 | F2 ON일 | OFF건 | OFF30d | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| B0 | 200 | 27,542,773 | +26.60% | 20.81% | -8.96% | +21.94% | +107.05% | +19.88% | 642 | 25 | +4.04% | baseline |
| E150 | 150 | 26,577,228 | +25.55% | 21.21% | -6.58% | +21.88% | +105.99% | +13.37% | 696 | 20 | +7.59% | 🔴 FAIL |
| E120 | 120 | 26,933,959 | +25.94% | 21.10% | -6.42% | +19.68% | +106.29% | +16.63% | 724 | 25 | +11.98% | 🔴 FAIL |
| E100 | 100 | 28,558,773 | +27.67% | 21.21% | -4.40% | +24.57% | +105.99% | +16.48% | 731 | 24 | +7.71% | 🔴 FAIL |

### 핵심 발견

- **E100이 GO 기준 5/6 통과 (CAGR/MDD/2022/OFF30d/Days 잔존), 단 2023 회복 +2.63%p < +3.0%p 한 항목 미달** → AND 기준상 FAIL
- **E100 2022 후반부 LUNA 시점(2022-11-06) 잘못 OFF → 30d 후 -23.32%** (false positive, BEAR 잘못 해제 위험 실증)
- **F2 ON 일수가 EMA 단축 시 오히려 증가** (642 → 731일): 짧은 EMA가 chop 구간에서 더 자주 cross → flicker 빈발. 가설(차단 시점 단축)과 반대
- **2025 재하락 모든 단축 case에서 손실 확대** (-3.4 ~ -6.5%p): E120/E100은 2025-08-30 첫 ON이지만 2025 수익률 하락
- OFF 30d 평균 양수 (+7.6 ~ +12.0%) 모든 case에서 통과 — 해제 자체의 정당성은 평균적으로 OK
- B0 회귀 통과: 27,542,773 정확 일치 (production-정합 baseline)

### 판정

🔴 **RED** — 모든 단축 case (E150/E120/E100) FAIL. EMA200 유지 확정 권고.

**기각 사유**:
- E150: CAGR -1.05%p, 2023 -0.07%p (개선 없음)
- E120: CAGR -0.66%p, 2023 -2.26%p (악화)
- E100: 2023 +2.63%p (+3.0%p 기준 미달, LUNA 잘못 해제 사례)

### 권고

- `rejected_experiments.md` → #65 EMA 기간 단축 (200→150/120/100) 영구 기각 등록
- EMA200 = 시장 표준 + LUNA 같은 long-tail BEAR에서 잘못된 OFF 방어 (E100은 1건 false positive 실증)
- 회복기 진입 개선은 EMA 단축이 아닌 다른 축(Shadow AI / O3 예외 정교화 / gap 예외 임계 조정)에서 모색

### 산출

- `bt_65_ema_period_verdict.md` / `bt_65_ema_period_key_numbers.md` / `bt_65_ema_period_full.md`
- `bt_65_ema_period.csv` / `bt_65_e2_blocks.csv`
- `scripts/bt_65_ema_period.py`

---

## 2026-04-25 #65-R: E100 trade-level 재분석 — 🟡 RE-EVAL (RED → 관찰 보류)

### 배경

#65 RED 판정에서 E100의 "2022-11-06 OFF 후 30d -23.32%" 는 buy-and-hold 가정. 실제 매도 로직 발동 시 trade 단위 PnL 재측정으로 false positive 위험 과장 가능성 검증.

### 핵심 발견 (B0 회귀 통과: 27,542,773)

| 분석 | 결과 |
|---|---|
| A. LUNA 윈도우 E100-only trade | 1건, **+5.64%** (buy-hold -23.32% → 위험 과장 실증) |
| Portfolio-level (final equity) | E100 28,558,773 vs B0 27,542,773 = **+3.69% (+1.0M KRW)** |
| Trade 분류 | 공통 55, B0-only 13, E100-only 8 |
| Segment Δ | 2022 +4.56%p / 2023 +2.63%p / 2024 -1.06%p / 2025 -3.40%p |
| GO 미달 폭 | 2023 +2.63%p vs 기준 +3.0%p = **0.37%p** 차이 |
| 2022 BEAR 전체 | E100-only 1건 +2.92%, B0-only 4건 -10.38% |

### 결정적 통찰

- **Trade-level naive sum 한계**: per-trade PnL%는 그 시점 사이즈 기준이라 복리/피라미딩 무시. naive 합산이 음수여도 portfolio-level final equity는 양수일 수 있음.
- **회복기 진입 시점**: E100 첫 진입 2023-01-17 vs B0 2023-01-05 → E100이 **12일 늦음**. EMA 단축으로 차단은 빨리 풀렸지만 score/AI 게이트가 진입 지연. EMA200이 회복기 지연의 주된 원인 아님.
- **잔여 우려 (2025 재하락 -3.40%p)**: E100 ON 시작이 B0보다 2개월 빠름에도 손실 확대 → 단순 "빠른 ON"이 보호 효과 없음.
- **A 결론**: false positive 위험은 매도 로직(ATR/계단/AI Sell)이 흡수. buy-hold 가정 기반 #65 기각 사유 1건 무효화.

### 재판정

🟡 **RE-EVAL** — #65 영구 기각 → 관찰 보류 (E100만)

- E150/E120: 영구 기각 유지 (CAGR/2023 모두 미달)
- **E100**: 영구 기각 → **관찰 보류 강등** (5월 중순 Shadow AI 평가 시 #64 B3 와 동시 결정)

### 산출

- `bt_65_R_e100_reanalysis_verdict.md` / `_key_numbers.md` / `_full.md`
- `bt_65_R_e100_trades.csv` (E100-only 8 + B0-only 13 trade 상세)
- `scripts/bt_65_R_e100_reanalysis.py`

---

## 2026-05-01 #69: simulator v20.9.4 FULL 정합 검증 (Reference vs F10+bars1080) — 🔴 FAIL (±0.5% 미달)

### 배경

v20.9 정합 작업(simulator.py 에 F5/F10 + bars_since_e2 추가) 이후 한 번도 끝까지 돌리지 못한 FULL 비교를 #68 후속으로 실행. `bt_v20_9_validation.py` 가 scaffold + 단위 테스트 상태였던 것을 `backtest/scripts/bt_e2_longterm_52mo.py` 의 데이터/모델 파이프라인을 import 해 두 케이스를 동일 데이터로 병렬 실행하도록 완성.

### 케이스

| 케이스 | block_mode | F5 | days/bars | 의미 |
|---|---|---|---|---|
| Reference | F2 | OFF | days 180 | bt_e2_longterm_52mo `E2b+6mo` 와 동일 (외부 F10 OR + 일 단위 카운터) |
| Simulator v20.9.4 | F10 | ON | bars 1080 | 프로덕션 정합 (4H봉 카운터, simulator 내부 F5 OR) |

기간 2022-01-01 ~ 2026-04-19 (52.3mo, 9413봉 4H), AI Gate OFF, 동일 model/data/지표.

### 결과

| 케이스 | 최종자산 | 거래 | MDD | CAGR | Sharpe | BULLcap | 예외진입 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reference (E2b+6mo, days 180) | 27,542,773 | 68 | 20.81% | +26.60% | 1.48 | 93.2% | 16건 |
| Simulator v20.9.4 (F10, bars 1080) | 26,626,794 | 65 | 20.81% | +25.61% | 1.44 | 90.1% | 13건 |
| **Δ** | **-3.326%** | -3 | 0.00%p | -0.99%p | -0.04 | -3.1%p | -3건 |

**판정 (±0.5%)**: 🔴 **FAIL** — Δ -3.326% 가 허용 오차 6.6배 초과.

### 의미

- 거래수 -3 + 예외 -3 → F10(=F2 OR F5) 또는 simulator 내부 F5 재계산 경로가 reference 보다 **일부 진입을 추가 차단**.
- MDD 동일 (20.81%) 인데 final equity -3.3% → 차단된 3건 모두 평균 +수익 트레이드.
- BULLcap -3.1%p 가 진입 누락 패턴과 일치 — BULL 구간 일부 진입이 F5 OR 로 막힘.
- bars 1080 (= 180일 × 6봉/일) 단위 변환 vs days 180 정합 여부도 분리 필요.

### 후속 액션

1. **봇 재시작 보류** — 트레이딩 로직 변경은 #68 (월간 리포트) 한정이라 재시작 자체는 안전하나, 시뮬 정합 FAIL 상태에서 v20.9.4 simulator 의 백테스트 결과를 의사결정 근거로 쓰면 안 됨. 사용자 별도 지시 시 진행.
2. **divergence 원인 분리** (별도 #번호):
   - 케이스 A: F2 + days 180 (Reference)
   - 케이스 B: F2 + bars 1080 — 일↔봉 단위 변환만 단독 검증
   - 케이스 C: F10 + bars 1080 (현재 FAIL)
   - A vs B 가 ±0.5% 면 단위 변환 OK → F5 ON 이 원인. 아니면 `precompute_bars_since_e2` 와 `precompute_days_since_e2` 의 boundary 차이.
3. **rejected_experiments.md 등록 보류** — 기각 아닌 정합 결함이므로 관찰/수정 항목 (`improvement_todo.md`).

### 산출

- `backtest/bt_v20_9_validation.py`: scaffold + FULL 검증 로직 (`_run_full_validation` + 결과 비교 + MD 저장)
- `backtest/results/bt_v20_9_validation.md` (이번 세션 결과)
- `backtest/scripts/bt_e2_longterm_52mo.py`: 변경 없음 (데이터/모델 파이프라인 재사용만)

---

## 2026-05-01 #69-A: simulator divergence 원인 분리 + 영구 수정 — 🟢 PASS (±0.000%)

### 배경

#69 FULL 검증이 -3.326% FAIL 한 원인을 3 케이스 분리 + 거래 단위 diff 로 추적:
  - A: F2 + days 180 (Reference, bt_e2_longterm_52mo `E2b+6mo`)
  - B: F2 + bars 1080 (단위 변환만, F5 OR 영향 배제)
  - C: F10 + bars 1080 (프로덕션 정합)

### 1차 실행 (버그 미수정)

| 케이스 | 최종자산 | 거래 | Δ vs A |
|---|---:|---:|---:|
| A: F2+days180 | 27,542,773 | 68 | +0.000% |
| B: F2+bars1080 | 26,626,794 | 65 | -3.326% |
| C: F10+bars1080 | 26,626,794 | 65 | -3.326% |

A↔B Δ -3.326%, B↔C Δ +0.000% → **F5 OR 무영향, 단위 변환 경로가 원인**.

### 거래 단위 diff (A vs C, 1차)

A에만 5건, C에만 2건. 가장 큰 누락은 **2023-01-05 회복기 첫 진입 PnL +32.38% (via_e2_exception=True, gap+score)**. 5건 중 4건이 gap+score 예외 진입.

### 근본 원인

`simulator.py` 의 E2 gap+score 예외 평가 (line 1401):
```python
if _gs_ok and E2_REQUIRE_BARS_SINCE_E2 > 0:
    _bars_a = mod.get("bars_since_e2_a")
    if _bars_a is None or int(_bars_a[ai]) < E2_REQUIRE_BARS_SINCE_E2:
        _gs_ok = False
```

caller 가 `mod` 딕셔너리에 `bars_since_e2_a` 를 안 넣으면 `mod.get()` 가 `None` 반환 → 조건문이 항상 `True` (None or anything) → **모든 gap+score 예외가 silent block**. 진입은 차단되고 로그도 안 남음.

`bt_e2_longterm_52mo.py:run_case` 의 `mod` 딕셔너리에 `bars_since_e2_a` 가 **누락**되어 있던 것이 원인. F2/days180 모드는 `days_since_e2_a` 만 사용해 영향 없었지만, F10/bars1080 케이스는 silent block.

### 수정

1. **`backtest/scripts/bt_e2_longterm_52mo.py:run_case`**: `mod["bars_since_e2_a"] = precompute_bars_since_e2(bear_arr)` 추가. import 도 동기화.
2. **`backtest/core/simulator.py`**: 같은 캐스 재발 방지 — `E2_REQUIRE_BARS_SINCE_E2 > 0` + `bars_since_e2_a` 누락 시 `ValueError` raise (silent block 대신 명시적 fail).
3. **`backtest/bt_v20_9_divergence.py`**: 3 케이스 + 거래 단위 diff + MD 자동 생성 도구화.

### 2차 실행 (버그 수정 후)

| 케이스 | 최종자산 | 거래 | MDD | Δ vs A |
|---|---:|---:|---:|---:|
| A: F2+days180 | 27,542,773 | 68 | 20.81% | +0.000% |
| B: F2+bars1080 | 27,542,773 | 68 | 20.81% | +0.000% |
| C: F10+bars1080 | 27,542,773 | 68 | 20.81% | +0.000% |

**판정 (±0.5%)**: 🟢 **PASS** — 3 케이스 모두 완전 일치. simulator v20.9.4 정합 회복.

### 프로덕션 영향

- **트레이딩 봇 (`btc_bot_v290.py`) 자체 영향 없음** — 봇은 simulator 를 사용하지 않고 `self.status["bars_since_e2"]` 를 직접 관리. 이번 버그는 백테스트 평가에만 영향.
- **과거 #42, #51, #52 등 simulator 사용 백테스트 결론은 재검증 필요할 수 있음** — F10 + bars 모드를 썼던 케이스 한정. F2 + days 사용 케이스는 영향 없음.

### 산출

- `backtest/bt_v20_9_divergence.py` (신규, 영구 정합 회귀 검증 도구)
- `backtest/results/bt_v20_9_divergence.md` (3 케이스 + diff 결과)
- `backtest/results/bt_v20_9_validation.md` (재실행 — PASS 갱신)
- `backtest/scripts/bt_e2_longterm_52mo.py` (mod 누락 수정)
- `backtest/core/simulator.py` (defensive raise 추가)

---

## 2026-05-01 #69-B Phase 1: silent block fix 후 #42 baseline 재검증 — 🟢 영향 미미 (Δ 0.000%)

### 배경

#69-A 에서 `bt_e2_longterm_52mo.py:run_case` 의 `mod["bars_since_e2_a"]` 누락 + simulator 의 silent block 영구 수정. silent block fix 가 영향 줄 수 있는 범위 — bars 모드(`e2_require_bars_since_e2 > 0`)를 사용하는 백테스트들의 결과가 변경 가능.

### Phase 1: #42 (E2b+6mo, bt_e2_longterm_52mo) 재실행

| 케이스 | 최종자산 (이전) | 최종자산 (fix 후) | Δ |
|---|---:|---:|---:|
| E2a              | 26,706,444 | 26,706,444 | +0.000% |
| E2b              | 26,626,794 | 26,626,794 | +0.000% |
| **E2b+6mo (1순위)** | **27,542,773** | **27,542,773** | **+0.000%** |
| Dynamic          | 21,374,142 | 21,374,142 | +0.000% |
| E2-OFF           | 24,043,973 | 24,043,973 | +0.000% |

작성일/소요시간 외 모든 수치 완전 일치 (md diff 2 lines: 작성일 timestamp + "총 소요" 0.1s 차이만).

### 영향 범위 분석 (영향 받았을 후보 스크립트 점검)

bars 모드 사용 스크립트 18개 점검 — 각각 자체 `mod` dict 빌드 시 `bars_since_e2_a` 를 직접 넣고 있어 silent block 영향 **없음**:

| 스크립트 | bars_set | bars_mod | 영향 |
|---|:-:|:-:|---|
| bt_64_range_weight.py | ✓ | ✓ | 없음 |
| bt_65_ema_period.py | ✓ | ✓ | 없음 |
| bt_66_e100_b3_combo.py | ✓ | ✓ | 없음 |
| bt_63b_bar_pos.py | ✓ | ✓ | 없음 |
| bt_r2_r3_grid.py | ✓ | ✓ | 없음 |
| bt_rolling_ai_pf.py | ✓ | ✓ | 없음 |
| bt_real_pf_penalty_impact.py | ✓ | ✓ | 없음 |
| bt_check_ai_gate_threshold.py | ✓ | ✓ | 없음 |
| bt_e2_f7_f11_ablation.py | ✓ | ✓ | 없음 |
| bt_e2_block_mode_ablation.py | ✓ | ✓ | 없음 |
| bt_recovery_capture.py | ✓ | ✓ | 없음 |
| bt_recovery_regime.py | ✓ | ✓ | 없음 |
| bt_range_exit_enhance.py | ✓ | ✓ | 없음 |
| bt_strong_trend_split.py | ✓ | ✓ | 없음 |
| bt_v21_core_bull.py | ✓ | ✓ | 없음 |
| analyze_f7a_deep.py | ✓ | ✓ | 없음 |
| analyze_2023_recovery_exits.py | ✓ | ✓ | 없음 |
| **bt_v20_9_validation.py** | ✓ | **✗** | **있었음** (#69-A 에서 fix + PASS 검증) |

### 판정

- **#42 baseline Δ = 0.000% (< 0.5% 임계)** → 🟢 영향 미미
- silent block 버그의 실제 영향 범위는 **`bt_v20_9_validation.py` 단독** — 그 외 #62~#66 등 모든 후속 백테스트는 자체 mod 에 `bars_since_e2_a` 를 정상 전달했으므로 영향 없음.
- **Phase 2 (#62~#66 재실행) 보류** — silent block 은 이론적으로 모든 bars 모드 백테스트를 위협했지만, 실제 코드는 각 스크립트가 mod 를 직접 빌드해 영향이 한정됐음.

### 의미

- #65 E100 회복기 +2.63%p 미달 결론 — 그대로 유효 (영향 없음)
- #64 B3 / #66 C1 보류 결정 — 그대로 유효
- #62 / #63 기각 결론 — 그대로 유효
- 결정 변경 case 0건 → improvement_todo.md / rejected_experiments.md 업데이트 불필요

### 산출

- `bt_e2_longterm_52mo.md` 재생성 (수치 동일, 작성일만 갱신)
- `e2_longterm_lead_entries.csv` 재생성 (72건 동일)
- 영향 범위 점검 grep 결과 (위 표)

### 학습된 교훈

silent block 같은 무음 결함은 caller 마다 mod dict 를 손으로 빌드하는 패턴에서 발생. 이번 fix 의 defensive `raise ValueError` (simulator.py) 가 향후 같은 패턴 재발을 즉시 차단. 추가로 `mod` 에 들어가야 하는 array 들을 헬퍼 함수(`build_e2_mod(bear_arr)`)로 묶어 caller 의존성 줄이는 후속 정리 권장.

---

## 2026-05-02 #70: F2 EMA 단독 최적화 (F5 OFF 격리, 52mo, 10 cases) — 🟢 Phase 2 진행 가치

**스크립트**: `backtest/scripts/bt_70_f2_ema_isolated.py`

### 목적
F10 = F2 OR F5 구조에서 F5 OFF 후 F2 EMA 기간 단독 효과 격리 측정. #65 V자 곡선 (EMA100 best, EMA120/150 dip) 의 원인이 F5 호흡인지 EMA 본질 패턴인지 분리.

### 케이스 (B0 = F10 회귀 baseline + 9 cases F5 OFF)
B0(F10 EMA200) / E50 / E75 / E100 / E125 / E150 / E175 / E200 / E250 / E300

### 결과 (52mo, AI_OFF, 1080 bars E2b+6mo 예외 유지)
| ID | EMA | F5 | 최종자산 | CAGR | MDD | Sharpe | F2 ON일 | OFF건 |
|---|---:|:---:|---:|---:|---:|---:|---:|---:|
| B0 | 200 | ON | 27,542,773 | +26.60 | 20.81 | 1.48 | 642 | 25 |
| E50 | 50 | OFF | 24,988,887 | +23.77 | 25.22 | 1.33 | 750 | 48 |
| E75 | 75 | OFF | 23,877,880 | +22.46 | 23.92 | 1.28 | 741 | 40 |
| E100 | 100 | OFF | 28,558,773 | +27.67 | 21.21 | 1.53 | 731 | 24 |
| E125 | 125 | OFF | 27,428,026 | +26.48 | 21.10 | 1.50 | 720 | 24 |
| E150 | 150 | OFF | 26,577,228 | +25.55 | 21.21 | 1.45 | 696 | 20 |
| E175 | 175 | OFF | 28,276,791 | +27.38 | 20.73 | 1.52 | 674 | 17 |
| E200 | 200 | OFF | 27,542,773 | +26.60 | 20.81 | 1.48 | 642 | 25 |
| **E250** | **250** | **OFF** | **28,615,598** | **+27.73** | **17.63** | **1.50** | **567** | **17** |
| E300 | 300 | OFF | 25,597,476 | +24.46 | 22.19 | 1.33 | 512 | 11 |

### 핵심 관찰

1. **F5 기여분 = 0**: B0 (F10) ↔ E200 (F2 only) → final 27,542,773 동일.
   - 52mo 전 구간에서 F2 ON 시점이 F5 ON 시점을 완전 포함 (F5 ⊆ F2).
   - F5 (4H ema21<ema55) 가 F2 (일봉 close < EMA200) 의 sub-set 으로 동작 → 현행 F10 = F2 OR F5 사실상 F2 단독과 등가.
2. **E250 신규 best**: CAGR +27.73% (E200 +1.13%p), **MDD 17.63%** (E200 −3.18%p) — 수익+안전 동시 개선.
   - 2024 BULL +115.4% (E200 +107.0%, +8.4%p) → 더 긴 EMA 가 강세장 손익 보존.
   - F2 ON일 567 (E200 642, −75일) → 차단 빈도 감소.
3. **V자 패턴 일부 재현**: E100(+27.67) → E125(+26.48) → E150(+25.55) → E175(+27.38) → E200(+26.60) — 비단조 (증가 3, 감소 5).
   - #65 의 EMA100 ↔ EMA200 V자가 F5 OFF 격리에서도 유사하게 재현 → EMA 기간의 본질 패턴 (F5 영향 아님).
4. **EMA50/75 chop**: F2 ON 일수 740~750 (전체의 38%), OFF 전환 40~48회 — chop 빈발로 CAGR/MDD 모두 악화.
5. **EMA300 과대**: F2 ON 512 (가장 적음) 인데 CAGR +24.46% (저조) → 차단 늦어 BEAR 손실 보존 실패.

### 판정

- **🟢 E250 Phase 2 진행 가치 확정**: F5 OFF 격리에서 E250 이 E200 보다 CAGR/MDD/final 모두 우수.
- **F5 sub-set 발견**: F10 = F2 OR F5 의 F5 가 사실상 redundant (52mo 데이터 한정). F5 단독 최적화 (Step 2) 의미 재검토 필요 — F5 단독으로는 의미 있을 수 있으나 F2 와 OR 조합에서는 추가 가치 없음.
- **EMA250 단일 후보 부상**: #65 의 EMA100 (회복기 미달로 RED) 와 다른 축. EMA250 은 BULL 보존 + MDD 감소 → 회귀 기각 가능성 낮음.

### 다음 단계

1. **#71 (가칭) — EMA250 F10 검증**: F5 ON (production 정합) + EMA250 단일 case GO 기준 (#65 와 동일) 통과 여부 검증.
   - 통과 시 v20.9.5 후보로 등록 (E2_DAILY_EMA_PERIOD: 200 → 250)
   - 실패 시 F2 단독 효과는 F10 로 옮길 때 재현 안 됨 → 보류
2. **F5 sub-set 검증 추가**: 다른 기간 (2018~2021) 에서도 F5 ⊆ F2 성립하는지 확인 (overfitting 위험).
3. **rejected_experiments.md 업데이트 불요**: 신규 best 발견이므로 #65 E100 결론 유지.

### 산출

- `bt_70_f2_ema_isolated_verdict.md` / `_key_numbers.md` / `_full.md`
- `bt_70_f2_ema_isolated.csv` (10 cases summary)
- `bt_70_f2_transitions.csv` (case별 F2 ON↔OFF 전환)
- 총 실행시간: 8.2s (FullStart 2022-01-01 ~ 2026-04-19, 9413 bars × 10 cases)

---

## 2026-05-02 #71: Hybrid EMA state machine (52mo, 7 cases) — 🔴 RED (모든 V case FAIL)

**스크립트**: `backtest/scripts/bt_71_hybrid_ema.py` (Phase 1: B0+V1 / Phase 2: V2~V6 추가)

### 목적
#70 결과 — E250 단독 best, 회복기 -0.94%p 늦음. Hybrid mode 로 두 strength 결합 가능성 검증.
- WAIT (close < EMA_ENTRY → 차단), HOLD (close > EMA_ENTRY 후 → 해제, EMA_HOLD 깨질 때까지 유지)

### 케이스 (F5 OFF, baseline = #70 E250)
B0(250/250) / V1(100/250) / V2(150/250) / V3(100/200) / V4(75/250) / V5(100/300) / V6(50/200)

### 결과 (52mo, AI_OFF)

| ID | Entry | Hold | 최종자산 | ΔCAGR | ΔMDD | Δ2022 | Δ2023 | Δ2024 | Δ2025 | Whip | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| B0 | 250 | 250 | 28,615,598 | - | - | - | - | - | - | 12 | baseline |
| V1 | 100 | 250 | 29,235,518 | +0.64 | +0.91 | +5.02 | +3.34 | -2.37 | -5.76 | 25 | 🔴 |
| V2 | 150 | 250 | 27,479,767 | -1.20 | +0.91 | +2.99 | +0.88 | -2.37 | -8.12 | 25 | 🔴 |
| V3 | 100 | 200 | 28,275,314 | -0.36 | +3.58 | +5.02 | +3.34 | -9.36 | -5.76 | 13 | 🔴 |
| V4 |  75 | 250 | 27,468,444 | -1.21 | +0.91 | +1.62 | -0.01 | -2.37 | -5.76 | 43 | 🔴 |
| V5 | 100 | 300 | 27,590,647 | -1.08 | +3.18 | +5.02 | +3.17 | -8.31 | -9.00 | 32 | 🔴 |
| V6 |  50 | 200 | 24,731,966 | -4.26 | +7.75 | -10.71| +2.44 | -4.34 | -2.36 | 59 | 🔴 |

### GO 기준 통과 (AND 6: ① CAGR≥B0 ② MDD≤+1.0%p ③ 2023≥+1.5%p ④ 2024≥-1.0%p ⑤ 2025≥-1.0%p ⑥ whip≥-2.0%p)
모든 V case 4/6 이하 통과 → 전부 FAIL.

### 핵심 관찰

1. **V1 회복기 가설 입증**: 2022 BEAR +5.02%p, 2023 회복 +3.34%p — 빠른 진입(EMA100) 효과 명확.
2. **하지만 BULL/재하락에서 손실**: V1 2024 -2.37%p, 2025 -5.76%p — 짧은 EMA_ENTRY 로 차단해제 빨라 재하락 깊은 dip 까지 보유.
3. **강제 청산 hook 부재 영향**: HOLD→WAIT 전환 시 차단만 활성, 기존 포지션은 자체 EXIT 사용 (production E2 동작 동일). 이로 인해 짧은 EMA_ENTRY 의 빠른 재진입 + 느린 EXIT 조합이 재하락에서 손실 누적.
4. **V3 (100/200) MDD +3.58%p**: 안전 기준 완화 시 즉각 MDD 악화 — EMA_HOLD=200 부족.
5. **V5 (100/300) 회복은 유지하나 BULL/재하락 모두 손상**: 안전 강화로도 V1 의 BULL/재하락 약점 보완 못함.
6. **V6 (50/200) 극단 케이스**: BEAR -10.71%p, MDD +7.75%p, whipsaw 59회 — 짧은 EMA_ENTRY 의 chop 위험 입증.

### 트레이드오프 정량화

V1: 회복기 +8.36%p (2022+2023) ↔ BULL/재하락 -8.13%p (2024+2025) → 거의 상쇄.
- 회복기 strength 와 BULL 보유 strength 는 동시 달성 불가 (현 simulator 설계 하에서).
- 강제 청산 hook 추가하면 V1 가 통과할 가능성 있으나 — production E2 동작 변경 필요 + 백테스트/실거래 sync 위험.

### 판정

- **🔴 모든 Hybrid V case FAIL** — Phase 2 grid 전체 통과 0건.
- **#70 E250 single 결론 유지**: state machine 추가 가치 없음.
- **rejected_experiments.md 등록 권고**: Hybrid EMA state machine (EMA_ENTRY/EMA_HOLD 분리) 영구 기각.
- **재검토 트리거**: simulator 강제 청산 hook 추가 시 (production E2 동작 변경 동반) — 별도 ablation 필요.

### 다음 단계

1. **#70 E250 단독 → v20.9.5 후보 등록**: F2 EMA 200 → 250 변경 (F5 OFF 가능성 별도 검토 — F5 sub-set 발견은 전 기간 한정).
2. **v20.9.5 후보 검증 추가**: F10 + EMA250 (production 정합 F5 ON) 백테스트 — F5 OFF 결론 확정 전 안전 검증.
3. **회복기 개선 다른 축 탐색**: state machine 외 — 외부 신호 / AI Gate 회복 감지 / 진입 사이즈 조정.

### 산출

- `bt_71_hybrid_ema_verdict.md` / `_key_numbers.md` / `_full.md`
- `bt_71_hybrid_ema.csv` (7 cases summary)
- `bt_71_state_transitions.csv` (case별 W↔H 전환 이벤트)
- 총 실행시간: Phase 1 2.6s + Phase 2 7.4s

---

## 2026-05-02 #72: 3-phase stepped entry (52mo, 5 cases) — 🔴 RED (모든 W case FAIL)

**스크립트**: `backtest/scripts/bt_72_stepped_entry.py` (Phase 1: B0+W7 / Phase 2: W1~W3 ratio sweep)

### 목적
#71 V1 의 BULL/재하락 손실 (-8.13%p) 을 사이즈 축소 + EMA250 풀모드 전환으로 해결 시도.
- WAIT (close < EMA100) → bear_block, no entry
- EARLY (EMA100 ≤ close < EMA250) → Leading path, 30~50% size, P0 단일
- FULL (close ≥ EMA250) → 정상 풀모드 (regime / pyramiding)

### 케이스 (F5 OFF, baseline = #70 E250, AI_OFF)
B0 (250/250) / W1 (30%) / W2 (40%) / W3 (50%) / W7 (30%, single)

### 결과 (52mo)

| ID | Entry/Hold | EARLY% | 최종자산 | ΔCAGR | Δ2022 | Δ2023 | Δ2024 | Δ2025 | EARLY 평균 PnL | E→F% | 판정 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| B0 | 250/250 | - | 28,615,598 | - | - | - | - | - | - | - | base |
| W1 | 100/250 | 30 | 28,454,854 | -0.17 | +6.06 | -0.95 | -0.90 | -6.86 | +2.14% | 57 | 🔴 |
| W2 | 100/250 | 40 | 28,633,126 | +0.02 | +6.06 | +0.36 | -0.90 | -7.38 | +2.14% | 57 | 🔴 |
| W3 | 100/250 | 50 | 28,809,744 | +0.20 | +6.06 | +1.67 | -0.90 | -7.90 | +2.14% | 57 | 🔴 |
| W7 | 100/250 | 30 | 28,454,854 | -0.17 | +6.06 | -0.95 | -0.90 | -6.86 | +2.14% | 57 | 🔴 |

GO 기준 (AND 6: ① CAGR≥+0.3 ② MDD≤+1.0 ③ 2023≥+2.0 ④ 2024≥-1.0 ⑤ 2025≥-1.0 ⑥ EARLY>-1.5%): 모든 W case 4/6 통과 → FAIL.

### 핵심 관찰

1. **EARLY trade 자체는 안전 (+2.14% 평균, ratio 무관)** — 6건 모두 동일 entry pool, size 만 변경.
2. **EARLY → FULL 성공률 57%** (7건 중 4건 FULL 도달, 3건 WAIT 회귀).
3. **Phase 통계 동일**: W1~W7 모두 WAIT 670일 / EARLY 45일 / FULL 970일 / W→E 7회 / E→F 4회. ratio 만 다름.
4. **선형 트레이드오프 확인**: ratio 30→50% 키울수록 회복 +0.7%p / 2025 -1.0%p. **2023≥+2.0 AND 2025≥-1.0 동시 통과 불가능**.
5. **2025 -7%p 손실은 EARLY phase 와 무관** — FULL phase 39건 진입이 BULL 막바지/재하락 초입에 들어가 자체 stop hit. EMA100 기반 빠른 차단해제 → FULL 진입 timing 어긋남.
6. **Simulator native 한계**: EARLY phase 내 step-pyramiding hook 없음 → W1~W6 의 진짜 단계 추가매수 효과 검증 불가. 단 ratio sweep 결과 (linear) 로 보아 step pyramiding 도 본질 문제 (FULL 잘못 진입) 해결 못 할 것으로 추정.

### 판정

- **🔴 모든 W case FAIL** — Phase 2 ratio sweep 추가 가치 없음 확정.
- **State machine 접근 자체 한계**: 단순 Hybrid (#71) 와 단계별 진입 (#72) 모두 FAIL.
- **공통 원인**: EMA100 빠른 차단해제 → BULL 막바지/재하락 초입에 풀 진입 → 자체 stop hit → 손실 누적.
- **rejected_experiments.md 등록 권고**: Hybrid (#71) + Stepped (#72) state machine 변형 영구 기각.

### 다음 단계

1. **#73 (가칭) — F10 + EMA250 production 정합 검증**: F5 ON 복귀 + EMA200→250 단일 변경 검증.
   - 통과 시 v20.9.5 후보 (E2_DAILY_EMA_PERIOD: 200 → 250)
   - F5 ⊆ F2 결론 (#70) overfit 위험 점검
2. **회복기 개선 다른 축**: state machine 외 — 외부 신호 / AI Gate 회복 감지 / 진입 사이즈 동적 조정.
3. **Step pyramiding simulator 패치**: 보류 (본질 문제 미해결 예상).

### 산출

- `bt_72_stepped_entry_verdict.md` / `_key_numbers.md` / `_full.md`
- `bt_72_stepped_entry.csv` / `bt_72_phase_transitions.csv`
- 총 실행시간: Phase 1 3.3s + Phase 2 6.3s

---

---

## 2026-05-04 #82: 손절선 전략 비교 (5 옵션, 52mo) — 🟢 B2 채택 권고

### 배경

5/2~5/4 매매 분석에서 출발: 첫 진입 116.2M → TP1/TP2 추매 → 본전 매도(-0.42%) 직후 가격 회복(117M). 작은 변동에 본전 터치 = 회복 미캡처. 사용자 제안: TP 도달 시 손절선을 TP -X% 로 설정해 작은 변동 흡수.

### 5 옵션 (손절선 로직만 변경)

- **B0**: 현행 (Lv1=본전, Lv2+=lookback 기반, FLOOR -5%)
- **B1**: TP -5% (도달한 TP × 0.95, 사용자 제안)
- **B2**: TP -3% (절충, 도달한 TP × 0.97)
- **B3**: 단계별 (-3% / 본전 / TP1 / TP2 ...)
- **B4**: B1 + 부분 손절 (70% → secondary -8% 에서 30%)

### 베이스

v20.9.4 정합, E2 OFF (사용자 사양: v20.9.11 베이스), Range New ON, AI Gate ON, step_mode=infinite, range_initial_ratio=0.70, range_step_lookback=3.0. 학습 2021-06~2021-12 1회. 백테스트 2022-01-01 ~ 2026-04-18 (52.3개월, 9413봉).

### 결과 (52mo)

| 옵션 | CAGR | MDD | PF | Win | N | BEAR'22 | BULL'24 | RANGE'25 | 회복캡처 | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| B0 | +20.43% | 36.55% | 1.60 | 34.2% | 79 | -34.79% | +160.24% | -8.22% | 38.5% | 기준 |
| B1 | +21.36% | 48.08% | 2.57 | 24.3% | 37 | -38.00% | +281.15% | -36.41% | 58.3% | 🔴 FAIL (MDD+11.5%p, N -53%) |
| B2 | +21.52% | 36.33% | 1.57 | 37.5% | 88 | -34.56% | +163.32% | -4.18% | 35.6% | 🟢 PASS |
| B3 | +20.09% | 37.81% | 1.52 | 38.1% | 84 | -36.09% | +145.59% | -4.54% | 36.1% | 🟡 회귀 (CAGR -0.34%p) |
| B4 | +17.84% | 48.08% | 2.46 | 22.2% | 36 | -44.62% | +281.15% | -36.41% | 57.1% | 🔴 FAIL (CAGR -2.6%p, BEAR-9.8%p) |

### 핵심 인사이트

1. **B1 (사용자 제안 TP-5%): CAGR↑ 0.93%p, MDD ↑ 11.5%p, 거래수 절반(79→37)**. PF는 2.57로 가장 높고 회복 캡처율도 58.3%지만, 거래수 절반화로 N±50% 룰 위반 + RANGE'25 -36% (Range 변동에서 큰 타격).
2. **B2 (TP-3% 절충): 모든 메트릭 미세 개선 (CAGR +1.09%p, MDD -0.22%p, BEAR +0.23%p, RANGE +4%p), 거래수 +9건**. PASS 조건 4개 모두 충족 — 위험 거의 없는 단일 변경.
3. **B3 (단계별)**: CAGR -0.34%p로 회귀. RANGE는 개선되지만 BULL 캡처 약화 (160→145).
4. **B4 (TP-5% + 부분손절)**: 부분손절 발동 3회만 — 효과 미미. CAGR -2.59%p + BEAR -9.83%p 큰 손실. 부분 청산 후 잔여 30%가 secondary -8%에서 추가 손실 누적.
5. **회복 캡처와 거래수의 상충**: TP-5% 류(B1/B4)는 회복 캡처율 ↑(58%) 이지만 손절 빈도↓ → BULL/RANGE 변동성 노출. TP-3% (B2)는 회복 캡처율은 B0와 비슷하나 거래수가 ↑ → 분산 효과로 안정.

### 판정

- **🟢 B2 채택 권고**: CAGR/MDD/BEAR/N 4개 채택 조건 모두 충족. 변경 폭 최소(loss-keeping bound -3% 추가). 회귀 위험 작음.
- **🔴 B1 (사용자 원안)**: CAGR 개선되나 MDD +11.5%p / 거래수 -53% 으로 FAIL. RANGE'25 -36%가 결정적.
- **🔴 B4 (사용자 원안 + 부분손절)**: 부분 청산 3회만 발동 → 의도된 효과 미발현. 가장 부진 (CAGR -2.6%p).
- **🟡 B3**: 단계별 정교화 효과 없음 (CAGR -0.34%p, BULL -14.6%p). Range 안정성은 ↑ 하지만 BULL 손실로 상쇄.

### 산출

- `bt_82_verdict.md` / `bt_82_key_numbers.md` / `bt_82_full.md`
- `bt_82_trades_B[0-4].csv` (5건)
- 실행 시간: ~10초 (5 케이스)

### 다음 단계

1. **v20.9.12 — B2 단일 변경 적용 검토**: 시뮬레이터 `step_stop_variant="B2"` + `step_stop_offset_pct=0.03` cfg override.
2. **1주 모니터링**: 손절 빈도, 회복 캡처, BULL/Range 캡처율 추적.
3. **위험**: 시뮬-프로덕션 갭 — B2 효과는 step_mode="infinite" 경로에 한정. 프로덕션 v20.9.x도 동일 경로 사용 중이므로 정합.

---

## #97. AI Gate 가치 검증 (4년) — A ≈ B 미미 (2026-05-18)

### 배경

봇의 AI Gate (XGB) 가 4년 장기 백테스트에서 실제로 성과에 기여하는지 확인.
사용자 질의 ("봇 vs AI 제외 비교"): A (v20.9.16 현행) vs B (AI Gate 제거, score+risk+E2만).

### 방법

- 기간: 2022-01-01 ~ 2026-04-19 (52.3개월, 4.30년, BEAR+회복+BULL+재하락 포함)
- 동일 E2 설정 (F10 + bars_since_e2=1080 + O3 + gap_score 예외)
- 동일 모델/데이터/리스크 (start_capital 10M KRW)
- A: 원본 `bp.get_xgb_th` (regime별 55~65% threshold)
- B: `patch_ai_gate_off()` → threshold 0.0 (XGB pass 사실상 무조건 통과)

스크립트: `backtest/bt_ai_value_4year.py`

### 결과

| 케이스 | 최종자산 | CAGR | MDD | Sharpe | 거래수 | 승률 | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| A (AI ON) | 26,777,595 | +25.77% | 19.28% | 1.45 | 61 | 37.7% | **2.43** |
| B (AI OFF) | **27,542,773** | **+26.60%** | 20.81% | **1.48** | 68 | 35.3% | 2.09 |
| B&H | 19,421,651 | +16.71% | 88.33% | 0.58 | — | — | — |

**Δ (A − B)**: final **-2.78%** / CAGR **-0.83%p** / MDD **-1.52%p** / Sharpe **-0.02** / N **-7**

### 구간별

| 구간 | A | B | Δ |
|---|---:|---:|---:|
| 2022_BEAR | -8.13% | -8.96% | +0.84%p |
| 2023_회복 | +17.54% | +19.31% | -1.77%p |
| 2024_BULL | +157.58% | +162.03% | -4.45%p |
| 2025_재하락 | -3.69% | -3.18% | -0.51%p |

### 판정: **A ≈ B (AI 가치 미미)**

- 최종자산/CAGR/Sharpe: B 약간 우위 (차이 -0.83%p, 미미)
- MDD: A가 1.52%p 우위 (방어 효과는 존재)
- PF: A 2.43 > B 2.09 → AI 가 진입 품질 향상에 약간 기여, 절대 수익엔 미반영
- 거래수: A가 7건 적음 → AI 가 일부 진입 차단 (BULL/회복기 위주)
- **봇 인프라 (자동화/E2/리스크/Score)** 가 주된 가치. AI Gate 단독 효과는 거의 없음.

### 시사점

1. **현행 AI Gate 유지** 의 정량적 근거 약함 — CAGR/Sharpe 손해 또는 무차익
2. **방어용 (MDD)** 측면에선 작은 가치 — 제거 시 MDD +1.52%p 노출
3. **AI 교체/개선 방향** 정당화:
   - TB3 Range 보조 게이트 (#shadow_analysis_20260511 — Range PF 5.22)
   - Phase 3 AI 교체 (recovery roadmap)
4. **파라미터 튜닝/예외 추가** 보다 **모델 교체** 가 우선 — A ≈ B 상태에서 모델 개선 시 직접 알파 기대 가능

### 산출

- `bt_ai_value_4year.md` (raw URL 별도)
- 실행 시간: 0.8초 × 2 케이스 (모델 학습 별도)

### 다음

- Shadow AI 5월 평가 (TB3 n>=50) → AI 교체 의사결정 데이터
- 현행 v20.9.16 유지, 변경 보류

---

## #85 — 진입 타이밍 개선 (고점 추격 해결) — 2026-06-01

### 배경
실거래 4건(4/14~5/16) 전부 손절·TP1 0회·진입가 108→116→118→120M 상승 = 고점 추격 의심.
EMA 정배열 즉시 진입 vs 눌림목/RSI/고점거리 필터 5종 비교.

### 설정
v20.9.17 정합 (AI OFF / E2 OFF / B2 손절선), 2022-01~2026-05 (53.7mo, 9671봉), 데이터 캐시 end=2026-05-31.
진입 조건만 변경 (EMA path 한정). simulator `bt85_mode` 추가 (pullback/rsi/high_dist/combo).

### 결과 (B0 기준)
| 옵션 | CAGR | MDD | PF | N | TP1% | 손절수 | 판정 |
|---|---:|---:|---:|---:|---:|---:|:---:|
| B0 현행 | +20.25% | 34.51% | 1.39 | 95 | 53% | 69 | 기준 |
| B1 눌림목 | **+24.28%** | **24.99%** | **1.56** | 86 | 53% | 61 | FAIL(Win% -0.8%p만) |
| B2 RSI | +15.62% | 22.02% | 1.46 | 80 | 55% | 55 | FAIL(CAGR) |
| B3 고점거리 | +11.92% | 28.81% | 1.36 | 85 | 47% | 59 | REJECT(CAGR-5%p) |
| B4 복합 | +15.35% | 21.24% | 1.47 | 78 | 55% | 53 | FAIL(CAGR) |

### 판정: **모두 기각 (B0 유지)** — 단 B1 은 관찰 보류 (E2 ON 확인 필요)
- **B2/B3/B4**: CAGR 회귀 (-4.6~-8.3%p), 명확 기각.
- **B1(눌림목)**: 경제적으로 전 지표 우위 (CAGR +4.03%p, MDD -9.52%p, PF +0.18, Sharpe +0.19, TP1 +0.9%p) — 승률 -0.8%p 단 하나로 기계적 GO/FAIL 탈락. 사실상 GO 급.
- **path-substitution(#63) 부분 확정**: 재진입율 18~44%, 손절수 69→53~61 (12~23%↓, 완전 불변 아님). #63 의 "손절 불변" 은 AI 제거 후 부분적으로만 성립.
- **TP1 도달**: 실거래 0% vs 시뮬 B0 53% — 시뮬은 4/02 눌림목 진입(101.6M) 1건 보유 → +13.7% 익절. 진입가/타이밍이 승패 결정 (낮게 일찍 → 승, 높게 늦게 → 패).
- **E2 OFF 한계**: B1 우위 상당분이 BEAR'22(-23% vs -32%)에서 발생 → 프로덕션 E2(F2) ON 시 중복. 단 BULL'24(+152% vs +128%) 개선은 E2 독립 → **E2 ON 확인 백테스트(#85-R) 필요**.

### 산출
`bt_85_verdict.md` / `bt_85_key_numbers.md` / `bt_85_full.md` (raw URL 별도), `bt_85_trades_B0~B4.csv`

---

## #85-R — 눌림목(B1) E2 ON 정합 검증 (순증분 격리) — 2026-06-01

### 목적
#85 는 E2 OFF → B1 우위가 E2 중복인지 확인. E2 ON (production F2) 에서 B0 vs B1 재측정.

### 설정
E2 ON (F2 + O3 예외 + gap_score 예외, v20.9.17 정합) / AI OFF / B2 손절선, 2022-01~2026-05.

### 결과
| 옵션 | CAGR | MDD | PF | N | Win | 손절 |
|---|---:|---:|---:|---:|---:|---:|
| B0 (E2 ON) | +21.19% | 23.23% | 1.97 | 75 | 40.0% | 48 |
| B1 (E2 ON) | +19.22% | 23.06% | 1.91 | 74 | 36.5% | 49 |

Δ(B1−B0): CAGR **-1.97%p**, MDD -0.17%p(무개선), PF -0.06, Win -3.5%p, 누적 -1.63M.

### E2 중복 격리 (시기별 Δ B1−B0, E2 OFF#85 → E2 ON)
| 구간 | Δ(OFF) | Δ(ON) | 해석 |
|---|---:|---:|---|
| BEAR'22 | +8.94%p | +2.38%p | E2 중복 |
| RECOVERY'23 | -12.38%p | -10.40%p | 일관 손해 |
| BULL'24 | +24.27%p | **-1.16%p** | 베이스라인 아티팩트 (순증분 0) |
| RANGE'25~ | +0.62%p | -0.00%p | 부분 |

### 판정: **B1 최종 기각**
- E2 ON 시 B1 우위 완전 소멸 (CAGR↓·PF↓·Win↓·MDD 무개선).
- #85 의 매력(CAGR +4%p, MDD -9.5%p)은 ① BEAR=E2 중복 ② BULL=E2-OFF 베이스라인 아티팩트(B0 가 베어꼬리 진입으로 자멸).
- E2 ON(=프로덕션) 에선 눌림목 필터가 좋은 추세 진입만 잘라 손해. → rejected_experiments #85 B1 기각 등재.
- **결론: 진입 타이밍 필터(눌림목/RSI/고점거리) 전부 기각. 진입 조건은 현행 유지. 회복기 손해는 진입 타이밍이 아닌 다른 원인(#85 시나리오 C).**

### 산출
`bt_85R_verdict.md` / `bt_85R_key_numbers.md` / `bt_85R_full.md` (raw URL 별도), `bt_85R_trades_B0/B1.csv`

---

## #86 — 청산 로직 분석 (5월 3패 원인 추적, 청산 측) — 2026-06-01

### 목적
#85/#85-R 로 진입 타이밍 5종 기각 → 5월 3패 원인이 진입 아님 입증. 본 분석은 **청산 측** 검증.
실거래 4건(4/14~5/16) 전량 인트라캔들 하드스톱(ATR/계단), TP1 도달 0회.

### 설정
E2 ON (F2+O3+gap_score, v20.9.17 정합) / AI OFF / B2 손절선, 2022-01~2026-05. 진입=현행 고정, EXIT cfg 만 변경.
시뮬 변경: `core/simulator.py` 에 **시간청산 hook 추가(cfg `time_exit_bars`, 기본 None=OFF gated)** — C0~C3 byte-identical (C0=#85-R B0 정합 확인).

### 5 가설 결과
| 옵션 | 청산 변형 | CAGR | MDD | PF | N | TP1 | 판정 |
|---|---|---:|---:|---:|---:|---:|:---:|
| C0 | 현행(B2+트레일 4.5/3.5) | +21.19% | 23.23% | 1.97 | 75 | 63% | 기준 |
| C1 | 트레일 타이트 ATR×3.0 | +21.45% | 23.15% | 1.90 | 79 | 63% | FAIL(PF) |
| C2 | 트레일 느슨 ATR×6.0 | +21.70% | 23.23% | 1.84 | 73 | 64% | FAIL(PF) |
| C3 | 부분익절+코어(TP1 50%) | +14.75% | 21.28% | 1.85 | 57 | 63% | REJECT(CAGR) |
| C4 | 시간청산 18봉 미익절 | +13.58% | 34.06% | 1.93 | 117 | 43% | REJECT(CAGR/MDD) |

### MFE / 청산 타이밍 (C0)
- 손절거래 평균 보유 **38.8봉**, 손절거래 MFE **+1.79%** (= 작은 유리한 움직임 후 역행) → 진입 직후 초기 stop 지배.
- 전체 MFE 평균 +7.53%, MFE 반납 5.08%p — 트레일링은 이익 구간에서만 작동, 진입 직후 손절을 못 막음.

### RECOVERY'23 청산 패턴
- C0 회복기 **수익 +52.4%(N=18, Win 39%)** — 백테스트상 회복기는 손실 구간 아님. 실거래 5월 손실은 **RANGE'25~ 구간 클러스터**(C0 RANGE -1.16%).
- C2(느슨)로 회복기 +47.5%(불변~소폭↓) → "**너무 빨리 잘랐다**" 가설 **기각**.
- C4(시간청산)는 회복기 **-10.08%** 로 파괴 (조기 컷이 회복 수익 제거).

### 판정: **청산도 현행(C0) 최적 — 5종 전부 기각**
- 트레일링 튜닝(C1/C2): CAGR ±0.5%p, PF 하락 → 무의미.
- 부분익절(C3): BULL'24 +120%→+75% (큰 추세 상단 잘라먹음) → CAGR -6.4%p.
- 시간청산(C4): MDD 34%·Win 23%·회복기 -10% → 적극 유해.
- **실거래 4건은 MFE 자체가 미미 → C0~C4 어떤 청산도 구제 불가**. 청산이 빠른/늦은 문제 아니라 진입 직후 역행 구조. 진입(#85 기각)·초기 손절선 외 레버 없음.
- → rejected_experiments: 청산 변형(트레일 타이트/느슨, 부분익절, 시간청산) 등재 대상.

### 산출
`bt_86_verdict.md` / `bt_86_key_numbers.md` / `bt_86_full.md`, `bt_86_trades_C0~C4.csv`

---

## 아카이브 참조

초기 탐색 (#1~#19), 외부 데이터 시도 (#16~#19), 기각된 TU 조합 등:
→ `backtest_log_v1.md`

---

## 2026-11-12 #99: 시뮬 production 정합 수리 + 운영 중 결정 4건 재확인 — B1 재확인 / P3·B2·K4 판정 보류

- 파일: `bt_99_prod_parity.py` (validate|matrix), 상세 `results/bt_99_parity_full.md`, 수치 `results/bt_99_matrix.csv`
- 기간: 2022-01-01 ~ 2026-11-11 (연장 데이터 `btc_4h_ext_cache.csv`), 시작 10M
- 목적: 전체 코드 점검에서 시뮬이 production 과 다른 점(O3 진입, 종가 손절·3봉 무손절, 초기 손절 식, 확정봉 EMA) 발견 → opt-in 옵션으로 수리한 "새 기준(PARITY)"에서 운영 중 결정 재확인.
- ⚠️ **새 기준 수치는 기존 P3/ST/S/F/C 세계 수치와 직접 비교 금지** (손절 모델·데이터 기간·O3 가 다름).

| 변형 (새 기준) | K4 전체 | K4 최대거래 제외 | K0 전체 | K0 최대거래 제외 |
|---|---|---|---|---|
| 기준 (K4·P3·B1·B2) | 21,159,038 | 16,580,034 | 23,100,303 | 18,562,531 |
| P3→ST | 27,809,768 | 22,075,120 | 29,861,899 | 24,625,518 |
| B1 끔 | 15,071,935 | 12,464,984 | 19,340,616 | 15,541,911 |
| B2→구 계단손절 | 27,050,501 | 23,274,359 | 25,994,468 | 21,220,638 |

- 기준 K4: CAGR +16.67% / MDD 20.73% / PF 1.13 / N91. 실거래 6~10월 대조: 기존 시뮬 합 −14.33% → 새 기준 −4.31% (실거래 +5.56%).
- 기존 방식 2×2 (~05-31): O3on+K4 33.07M / O3on+K0 28.79M / O3off+K4 31.71M / O3off+K0 36.42M — #87-R 의 K4 우위는 O3 on 에서만 성립.
- **결론**: B1 유지(4조건 모두 우위). P3·B2·K4 는 새 기준에서 열세/근거 없음이나, 독립 검증이 새 기준의 남은 불일치 3건(트레일 고점 봉 고가 / 계단 TP·피라미딩 종가 판정 / 봉내 청산 봉 자산 평가)을 확인 → **production 변경 없이 판정 보류.** 기존 B0 33.07M(CAGR +31%)는 기대 수익률로 사용 금지.
- 회귀: `bt_93f_switch_regression.py` 5세계 PASS 유지 (시뮬 옵션 기본 off).

---

## 2026-11-12 #99-B: 1시간 하위 봉 순서 재현 후 재판정 — KS PF 트리거 제거 권고 / P3 판정 불가 / B1·B2 유지

- 파일: `bt_99_prod_parity.py` (validate|matrix|ks), 시뮬 옵션 `intrabar_sub` (기본 off), 데이터 `btc_1h_ext_cache.csv`, 수치 `results/bt_99b_matrix.csv`, 상세 `results/bt_99_parity_full.md`
- 기간: 2022-01-01 ~ 2026-11-11, 시작 10M. ⚠️ 기존 세계·#99 1차 수치와 직접 비교 금지.

| 변형 (새 기준 B) | K4 전체 | K4 최대거래 제외 | K0 전체 | K0 최대거래 제외 |
|---|---|---|---|---|
| 기준 (K4·P3·B1·B2) | 16,923,513 | 15,276,226 | 23,189,386 | 19,481,827 |
| P3→ST | 22,294,458 | 19,852,381 | 28,489,762 | 24,561,815 |
| B1 끔 | 16,269,181 | 13,737,799 | 20,971,627 | 17,618,647 |
| B2→구 계단손절 | 12,486,491 | 10,709,243 | 19,241,738 | 16,286,550 |

- 실거래 6~10월 대조: 시뮬 합 +1.02% (실거래 +5.56%, 기존 시뮬 −14.33%), 매칭 건 평균오차 0.67%p.
- Kill Switch 분해: MDD 트리거만 = K0 와 동일 (MDD 트리거 0회 발동). K4 손해 −6.3M 는 전부 PF 트리거 (발동 353회, 전체 봉의 22% 정지).
- 독립 검증: 수치 전부 재현. ST−P3 는 민감도에 따라 +5.4M ~ −5.8M (부호 뒤집힘). K0−K4 는 전 조합 +4.6M ~ +9.3M.
- **결론**: ① KS PF 트리거 제거 권고 (MDD 트리거 유지, 사용자 승인 대기) ② P3 판정 불가 — 현행 유지 + 실거래 모니터링 ③ B2·B1 현행 유지.
- 회귀: `bt_93f_switch_regression.py` 5세계 PASS 유지.

## 2026-11-13 #100: 손실 청산 후 재진입 제한 + ADX 구간 진입 차단 — 🔴 채택 0건 (재진입 제한 기각 / ADX 27~35 가설 보류)

**동기**: 실거래 로그 분석(15거래, 2026-04~11). 손절 뒤 48h 안에 손절가보다 +1.8~3.1% 높게 재진입한 4건 전부 손실(합 −9.35%), Trend 진입 10건 합 −10.34%, candle_log 에서 EMA 통과 봉 중 ADX 25~30 구간의 24봉 뒤 평균 −0.97%.
**가설**: (a) 손실 청산 뒤 재진입을 늦추거나 청산가 위 재진입을 막으면 이득 (b) ADX 중간대 진입 차단이 이득. 판정 기준은 실행 전 고정: 새 기준 B 와 기존 B0 부호 일치 AND 4구간 3/4 비악화 AND 최대거래 제외 후 우위.
**시뮬 수정** (opt-in, 기본 동작 불변): `stop_cooldown_bars` / `stop_reentry_guard_bars` / `stop_reentry_guard_pct` (`core/simulator.py` `_b100_loss`). 백업 `simulator.py.bak.pre_100_cd`. 회귀 5세계 수정 전·후 PASS (33,070,501 등). 실행 `bt_99_prod_parity.py b100` → `results/bt_100_matrix.csv`, `bt_100_run.log`. 데이터 ~2026-11-11.

기준 최종자산: 새기준B·MDD만(= production v20.9.27, PF 트리거 없음) 23,189,386 / 기존B0·K4 27,667,339 / 기존B0·K0 24,085,944.

| 변형 | 새기준B Δ (4구간 비악화) | 기존 K4 Δ | 기존 K0 Δ | 판정 |
|---|---|---|---|---|
| 손실후 쿨다운 3봉 | −2.69M (2/4) | −0.53M | −0.07M | 기각 |
| 손실후 쿨다운 6봉 | −2.99M (2/4) | −1.02M | −0.51M | 기각 |
| 손실후 쿨다운 12봉 | −0.91M (2/4) | −0.49M | +0.78M | 기각 (부호 불일치) |
| 청산가 초과 재진입 금지 6봉 | −2.23M (2/4) | −1.46M | −1.29M | 기각 |
| 청산가 초과 재진입 금지 12봉 | −1.43M (2/4) | −0.94M | −0.03M | 기각 |
| 청산가+1% 초과 재진입 금지 12봉 | +2.08M (4/4, 최대거래 제외 +1.75M) | −0.35M | +0.15M (2/4) | 채택 불가 (부호 불일치, 인접 0% 는 전부 음수) |
| ADX 25~30 진입 차단 | −0.71M (3/4) | −1.73M | +2.15M | 기각 (부호 불일치) |
| ADX 27~35 진입 차단 | +1.00M (2/4, 최대거래 제외 +0.92M) | +0.03M | +6.26M (4/4, 제외 +4.78M) | 채택 불가 → 가설 보류 |

- **재진입 제한이 지는 이유**: 새 기준 BULL 구간 −27 ~ −32%p, 10% 이상 거래 9→8건. 손절 직후 재진입이 큰 상승을 잡는 경우가 실거래 표본(4건)보다 많음. 새 기준 기준 실행의 "손실 뒤 12봉 내 재진입" 25건 중 청산가+1% 초과 14건(단순합 −10.9%), 0~1% 7건(+2.0%) — 1% 경계의 우위는 소수 거래 의존.
- **ADX 27~35**: 세 세계 모두 양수이나 새 기준에서 BULL −11.7%p / RANGE −1.2%p 로 2/4. `CLAUDE.md` "고ADX 진입은 진다" 는 가설 지위 유지.
- **독립 검증**: 수치 전부 csv 재계산·일부 재실행 일치, 판정 5건 동의. 지적 사항 → (1) "최대거래 제외"는 수익률(%) 최대 거래 기준 (새 기준은 상위 3건이 19/18/17% 로 근접, 원화 기준 재확인은 미검증) (2) `_b100_loss` 미연결 청산 경로 2개(`TU_Down전환`, MR 청산 — 이번 실행에서 해당 거래 0건, 재사용 시 연결 필요) (3) 기존 K4 의 최대거래 제외 수치는 KS 경로 영향으로 불안정(쿨다운 3봉 −5.15M) (4) 참고: PF 트리거를 켠 새 기준(16,923,513)에서는 +1% 금지 +5.63M / ADX 27~35 +3.36M / 쿨다운 12봉 +2.52M 로 커지거나 부호가 바뀜 — KS 경로 증폭이라 근거로 쓰지 않음 (production 은 v20.9.27 에서 PF 트리거 제거됨).
- **부수 발견 (시뮬↔production 불일치)**: 시뮬은 Trend_Up 손절 뒤 쿨다운 0봉, production 은 regime 무관 4시간(`COOLDOWN_STOPLOSS=14400`). `improvement_todo.md` `#V26_AUDIT` 등재.
- **결론**: production 변경 없음.

## 2026-11-13 #101: ADX 기준을 고정값 대신 유동(롤링 분위)·방향(3봉 변화)으로 — 🔴 채택 0건 (유동 540봉·순위형 기각 / 유동 180봉·ADX 방향 크기조절 보류)

**동기**: `#LOG_PATTERN_SCAN` (봉 단위 통계) — 정배열 봉에서 ADX 수준(≥27)은 예측력 0, ADX 3봉 상승은 4일 뒤 +0.99~1.19% vs 전체 +0.62%. 사용자 제안 "ADX 를 고정값 대신 유동적으로".
**판정 기준(실행 전 고정)**: 새 기준 B 와 기존 B0 부호 일치 AND 4구간 3/4 비악화 AND 최대거래 제외 후 우위, CAGR ±0.5%p 이내면 MDD 낮은 쪽.
**시뮬 수정** (opt-in): `mod["init_size_mult_a"]` — P2(Trend_Up·Range 피라미딩) 초기 진입 금액에만 봉별 배수, 추가매수·잔액투입 미적용 (`core/simulator.py` `_ism101`). 백업 `simulator.py.bak.pre_101_adx`. 회귀 5세계 수정 전·후 PASS. 유동 regime 은 스크립트에서 regime 배열만 재구성(고정 27/23 재구성 = 원본 완전 일치 assert). 실행 `bt_99_prod_parity.py b101` / `b101c` → `results/bt_101_matrix.csv`, `bt_101_control.csv`, 로그 `bt_101_run.log`, `bt_101_control.log`.

기준: 새기준B·MDD만(= production v20.9.27) 23,189,386 / 기존B0·K4 27,667,339 / 기존B0·K0 24,085,944.

| 변형 | 새기준B Δ | 기존 K4 Δ | 기존 K0 Δ | 판정 |
|---|---|---|---|---|
| 유동 regime 180봉 분위 | −0.10M (MDD 25.26→23.81, 3/4, BULL 123.4→106.4) | +2.57M (최대거래 제외 −3.86M) | +4.29M (4/4) | 보류 — 세계 간 부호 불일치 + 창 민감 |
| 유동 regime 540봉 분위 | −0.14M | −2.13M | −1.03M | 기각 |
| 크기: ADX 상승 1.0 / 아니면 0.75 | +0.38M (MDD 24.26) | −0.35M (MDD 22.95) | 0.00M (MDD 24.46) | 보류(관찰) |
| 크기: ADX 상승 1.15 / 아니면 0.85 | +1.33M (3/4, 제외 +1.05M) | −0.02M (2/4) | +0.11M | 채택 불가 (위와 같은 가설로 관찰) |
| 크기: 180봉 상위30% 1.0 / 0.75 | −0.73M | +0.74M | −0.28M | 기각 |
| 크기: 180봉 상위30% 1.15 / 0.85 | +0.08M | −2.64M | −0.46M | 기각 |

- **유동 regime**: 창 길이에 비단조로 민감 (검증 추가 실행, 새 기준: 120봉 +2.07M / 180봉 −0.10M / 240봉 +2.38M / 360봉 +1.71M / 540봉 −0.14M). 분위 수준(55.5% / 39.7%)은 전체 기간에서 구해 미래 정보 소량 포함(전·후반 54.3/38.0 vs 56.8/41.3). 재검토하려면 창 격자 + 과거 구간만으로 분위 결정.
- **ADX 방향 크기조절 (1.0/0.75)**: CAGR 차이 세 세계 모두 ±0.5%p 이내, MDD 는 모두 낮지만 BULL 은 모두 악화(123.4→113.8 / 186.4→166.9 / 186.4→166.9).
  - 검증의 무작위 대조 100개(상승 여부 배열을 원형 이동): 새 기준에서 실제 규칙은 대조 상위 6% (거래 단위 순열 p=0.03, 최대거래 제외 0.05) — 약한 증거. 기존 K4·K0 에서는 대조 분포 중앙(53% / 57%) — 증거 없음.
  - **MDD 감소는 ADX 정보가 아니라 노출 축소 효과**: 아무 봉이나 0.75 로 줄여도 92~98% 가 기준보다 MDD 낮음.
  - 기존 K0 의 0.00M 은 종점 우연(자산 비율 1.05 → 0.98 → 1.00). 기존 K4 는 두 번째로 큰 거래를 빼면 조건 이탈.
  - 새 기준 지연 1~6봉 중 5개 양수 → 방향성은 일관, 표본 늘면 재평가.
- **시뮬↔production 차이**: production ADX 는 진행 봉 포함(`btc_bot_v290.py` ~L518), 시뮬은 확정 봉 — "3봉 변화"를 production 에 넣으려면 감사표 필요.
- **독립 검증**: 수치 전부 재현, 회귀 PASS, 레버리지 없음(최대 0.92), look-ahead 없음. 판정 전 항목 동의(채택 0).
- **결론**: production 변경 없음.

## 2026-11-14 #102: "하락 위험" 지표(CMF·RSI·DI·범위 하단)에서 진입 보류/축소 — 🔴 전 변형 기각

**동기**: `#INDICATOR_SCAN` (봉 단위, 지표 약 50개) — CMF 낮음·RSI 낮음·DI− 우위·20봉 범위 하단에서 7일 내 −8% 확률이 약 2배 (5개 연도 일관). 진입 필터로 쓰면 이득인지 확인.
**판정 기준(실행 전 고정)**: 새 기준 B 와 기존 B0 부호 일치 AND 4구간 3/4 비악화 AND 최대거래 제외 후 우위.
**조건**: CMF20·RSI14 의 540봉 롤링 순위 ≤20 / CMF<0 / DI+≤DI− / 20봉 범위 위치 ≤30 / 위험점수 = 앞 4개(CMF 하위·RSI 하위·DI−·범위 하단) 합. 시뮬 무변경 (기존 `skip_entry_mask_a`·`init_size_mult_a` 사용). 실행 `bt_99_prod_parity.py b102` → `results/bt_102_matrix.csv`, `bt_102_run.log`. 회귀 5세계 PASS.

**기존 규칙과의 겹침** (새 기준 기준 실행 116건): 전체 봉 중 조건 비율 CMF 하위 20% / DI− 49% / 범위 하단 30% → 실제 진입 중 9% / 16% / 11% (EMA·Trend_Down 차단이 먼저 걸러 냄). 남은 해당 거래는 오히려 평균이 높음: CMF 하위 10건 +2.44% vs 비해당 +0.06%, RSI 하위 9건 +2.90% vs +0.04%, DI− 19건 +0.94% vs +0.13% (해당 거래 9~22건, +10% 이상 각 2건 — "반등 초입 진입이 수익원" 은 가설 수준).

| 변형 | 새기준B Δ (4구간) | 기존 K4 Δ | 기존 K0 Δ |
|---|---|---|---|
| 보류: CMF 하위20% | −5.10M (2/4) | −12.44M | −2.87M |
| 보류: CMF 음수 | −0.26M (2/4, MDD 25.26→17.51, 대박 9→6) | −3.59M | −0.08M (2/4, MDD 25.80→21.43) |
| 보류: RSI 하위20% | −4.17M (2/4) | +1.95M | +4.15M |
| 보류: DI− 우위 | −3.89M (2/4) | −5.84M | +0.06M |
| 보류: 범위 하단30% | −3.96M (2/4) | +3.82M | +6.55M |
| 보류: 위험점수≥1 | −3.54M (2/4) | −3.38M | +0.20M |
| 보류: 위험점수≥2 | −4.34M (2/4) | −3.29M | −0.52M |
| 축소 0.5배: CMF 음수 | −1.30M (1/4) | +0.76M | −0.27M |
| 축소 0.5배: 위험점수≥1 | −0.46M (3/4) | −3.50M | −1.88M |

- 새 기준에서 9개 전부 수익 감소, +10% 이상 거래 9 → 6~8건.
- **보류: RSI 하위 / 범위 하단**: 기존 세계 양수이나 새 기준 −4.17M / −3.96M → 부호 불일치 기각.
- **보류: CMF 음수**: 수익 열세가 아니라 **구간 조건 미달로 기각**. PF 트리거 없는 두 세계(새 기준·기존 K0) 모두 수익 동률(CAGR −0.27%p / −0.08%p) + MDD −7.75%p / −4.37%p 이나, 4구간 2/4 (두 세계 모두 BULL 악화; 새 기준 BULL +123→+98, RECOV +38→+27 를 BEAR −15.7→−7.5, RANGE −11.4→−2.2 와 맞바꿈) + 대박 9→6. 재검토 트리거: 수익보다 낙폭 방어를 우선하는 운영 목표로 바뀔 때.
- **축소 0.5배: 위험점수≥1**: 새 기준 CAGR −0.49%p·MDD 25.26→25.01 로 형식상 동률이나 최대거래 제외 시 MDD 31.12 vs 29.03 악화, 기존 K4 −3.50M / K0 −1.88M → 기각.
- 김치 프리미엄은 이미 production 사용(#K2: >3% 시 ×0.5)이라 제외.
- **독립 검증**: 수치 전부 일치, 새 기준 3케이스 재실행 일치, look-ahead·인덱스 정합 확인, 전 변형 기각 동의. 기존 세계 변형·최대거래 제외 실행은 재실행 미검증(csv↔로그 일치만).
- **결론**: production 변경 없음. 봉 단위 "하락 위험" 통계는 기존 차단 규칙이 이미 반영 — 진입 필터 추가 여지 없음.

## 2026-11-14 #103 (사전 점검): "하락 위험" 지표로 보유 비중 축소 — 🔴 근거 없음, 시뮬 구현 미진행

**동기**: 사용자 제안 — #102 의 하락 위험 지표를 진입 필터가 아니라 보유 중 비중 축소에 사용.
**방법**: 시뮬 무변경. 세 세계 기준 실행의 거래(새기준B·MDD만 116건 / 기존 K4 91건 / K0 94건)에 대해 보유 봉마다 조건을 대입한 **1차 근사** (KS 경로·피라미딩 상호작용·복리 미반영). 조건 13종: CMF 하위20%·CMF<0·RSI 하위20%·DI−·범위 하단30%·위험점수≥1/≥2·CMF 음수 전환·DI− 전환·종가<EMA21·종가<EMA55·RSI<40·RSI<45. 실행 `bt_99_prod_parity.py b103p` → `results/bt_103_probe.csv`, `bt_103_probe2.csv`, `bt_103_probe.log`.

**(1) 조건 첫 발생 봉에서 매도 후 끝** — 그 봉 종가 → 실제 청산가까지 잔여 수익률:
- 13개 조건 × 3세계 전부 잔여 평균 **양수** (새 기준 +0.63 ~ +1.73%, 기존 +1.33 ~ +2.55%). 팔았으면 손해.
- 중앙값은 음수(−0.6 ~ −1.6%), 61~73% 는 팔았으면 소폭 이득. 그러나 +10% 이상 거래의 대부분에서 조건이 발생하고(새 기준 9건 중 3~7건, 기존 11건 중 7~11건) 그 잔여 평균이 +15 ~ +24%.
- 구조: 자주 1% 안팎을 아끼고, 드물게 +20% 를 놓침. 조건은 추세 중 눌림에서도 켜짐.

**(2) 조건이 켜진 동안만 0.5배, 꺼지면 복구** — 거래별 포지션 수익률 변화 합 (전환 1회 비용 = 0.5 × COST_RATE):
- 11개 상태 조건 × 3세계 × 5개 연도 **전부 음수** (새 기준 −30 ~ −83%p, 기존 −42 ~ −102%p).
- 변화 합 ≈ −비용 (예: 새 기준 CMF 하위 −35.3 = 비용 38.1 포함, RSI<40 −30.1 = 비용 26.1 포함) → 비용 전 효과는 0 근처. 보유 중 조건이 켜진 봉의 수익률에 방향 정보가 없고 전환 비용(174~673회)만 남음.

**해석**: 봉 전체에서는 이 조건들이 큰 하락 확률을 2배로 올리지만(#INDICATOR_SCAN), 보유 중에는 손절·계단손절·트레일링이 이미 하락을 끊어 내므로 추가 정보가 없음.
**조합 추가 점검 (2026-11-14)**: 지표 2개 조합 2,637개를 2022~2024 탐색 → 2025~2026 검증. 재현되는 것은 역배열 구간의 하락 조합뿐(밴드폭 확대+약세, ADX 상승+ATR 높음). 이를 보유 중 조건으로 대입(`bt_103_probe_combo.log`)하면 발생 4~10건, 잔여 수익 평균 +2~4% → 근거 없음. 상세 `improvement_todo.md` `#COMBO_SCAN`.
**판정**: 사전 점검 수준에서 근거 없음 → 시뮬 구현(부분 청산·복구 로직) 진행하지 않음. 독립 검증 미실시(정식 백테스트 아님). production 변경 없음.

## 2026-11-14 #104: 변동성 기준 진입 크기 (변동성 타겟팅) — 🔴 전 변형 기각

**동기**: 전문 퀀트 운용 방식 검토 — 진입 크기가 70~80% 로 사실상 고정이라 변동성에 따른 비중 조절을 시험. 기존 기각 목록에 변동성 사이징 없음.
**판정 기준(실행 전 고정)**: 새 기준 B 와 기존 B0 부호 일치 AND 4구간 3/4 비악화 AND 최대거래 제외 후 우위, CAGR ±0.5%p 이내면 MDD 낮은 쪽.
**방식**: 배수 = clip(과거 변동성 중앙값 / 현재 변동성, lo, hi). 변동성 = ATR14/종가 또는 42봉 로그수익률 표준편차. 기준 창 540봉(90일) 또는 2190봉(1년). 축소형 0.5~1.0 / 대칭형 0.6~1.19 / 강한 축소 0.3~1.0 → 6종 × (초기 진입만 / 전체 포지션) = 12변형 (ATR 축소형과 강한 축소는 결과가 거의 같아 독립 스펙은 사실상 5종).
**시뮬 수정** (opt-in): `size_mult_whole` — `init_size_mult_a` 배수를 TP1 추가매수·포지션 상한·잔액투입 상한에도 적용 (`core/simulator.py` `_b104`). 백업 `simulator.py.bak.pre_104_vt`. 회귀 5세계 수정 전·후 PASS. 실행 `bt_99_prod_parity.py b104` → `results/bt_104_matrix.csv`, `bt_104_control.csv`, `bt_104_run.log`.

기준: 새기준B·MDD만(= production v20.9.27) 23,189,386 (MDD 25.26) / 기존B0·K4 27,667,339 (25.80) / 기존B0·K0 24,085,944 (25.80).

- **수익**: 12변형의 최종자산 변화 새 기준 −2.42M ~ +0.56M / 기존 K4 −3.41M ~ −0.29M (12개 전부 음수) / 기존 K0 −1.51M ~ +0.07M. 세 세계 모두 양수인 변형 0개.
- **MDD**: 대부분 1~3%p 낮아지나 노출 축소 효과. 무작위 대조(같은 배수 배열을 원형 이동, 20회): "ATR% 축소형·전체 포지션" MDD 23.76 / 23.84 / 23.84 vs 대조 중앙 23.10 / 23.21 / 24.28, 최종자산은 대조의 상위 40 / 30 / 25%. 대칭형은 상위 30 / 15 / 50%. 검증의 상수 배수 대조(진입 봉 평균 배수 0.86)도 MDD 23.87~23.94 로 더 낮음.
- **형식상 근접 후보 3개 — 모두 조건 미달**:
  - 실현변동성 축소형·초기만: 새 기준 −0.48M (CAGR −0.51%p, MDD 24.33, 3/4) / K4 −0.35M (MDD 22.92, 3/4) / K0 0.00M (MDD 23.38, 3/4). 새 기준 CAGR 이 0.5%p 초과 하락, 대조와 구분 안 됨(대조 10회 중 4회가 최종자산 이상).
  - ATR% 1년 기준 축소형·초기만: 새 기준 +0.36M (MDD 24.30, 3/4, 검증 소규모 대조 10회를 전부 앞섬) / K4 −0.29M (2/4) / K0 −0.14M. 세계 간 부호 불일치 + K4 2/4 + 창 길이 민감(540봉 창은 0.00M) + 12변형 중 사후 선택, 효과 +1.6%.
  - 실현변동성 대칭형·초기만: 새 기준 +0.44M (3/4) / K4 −0.55M (CAGR −0.51%p, 2/4) / K0 +0.07M.
- **해석(가설)**: 손절선이 이미 ATR 기준이라 변동성이 일부 반영돼 있고, 단일 자산에서는 "언제 작게 들어가느냐"만 남는데 BTC 는 변동성 큰 시기가 큰 상승 시기와 겹침. 변동성 타겟팅의 주 효용은 다자산 위험 균형.
- **독립 검증**: 수치 전부 일치(새 기준 6건·K4 3건·대조 1건 재실행 소수점까지 동일), look-ahead 없음(절단 재계산 차이 0), 레버리지 없음, 전 변형 채택 불가 동의. 지적: 무작위 대조는 "전체 포지션" 2종에만 있었음 / 원형 이동 대조는 진입 봉 평균 배수(0.859)보다 노출이 조금 큼(전체 봉 평균 0.89) / `_b104` 는 MR 진입·`pyramid_distribution` 분기에 미연결(이번 세계에서는 꺼져 있어 무영향, 재사용 시 연결).
- **결론**: production 변경 없음.

## 2026-11-14 #105 (긴급 점검): E2 (일봉 EMA200 아래 진입 차단) 재평가 — 롤백 트리거 알림 대응, 🔴 E2 재활성 근거 없음 (독립 검증 전)

**동기**: 2026-11-14 13시경 텔레그램 "롤백 트리거: BTC 1주 −11.81%" 알림 (v20.9.10 #75-B E2 OFF 안전망). 알림 시점 무포지션(10-07 이후 진입 없음), 4H EMA 역배열·Trend_Down 차단 중, 봇 누적 +1.16%, 일봉 EMA200 대비 −13.6%.
**방법**: 시뮬 무변경, `skip_entry_mask_a` = 일봉 EMA200 gap < 0 / < −5% / < −10% (production E2 의 O3·gap 예외는 미모델). 실행 `bt_99_prod_parity.py b105` → `results/bt_105_e2.csv`, `bt_105_run.log`. 데이터 ~2026-11-11.

| 변형 | 새기준B·MDD만 (= production) | 기존B0·K4 | 기존B0·K0 |
|---|---|---|---|
| 기준 (E2 끔) | 23.19M / CAGR +18.89 / MDD 25.26 / BEAR −15.7 RECOV +38.2 BULL +123.4 RANGE −11.4 | 27.67M / MDD 25.80 | 24.09M / MDD 25.80 |
| E2 켬 (EMA200 아래 차단) | 19.00M (−4.19M) / MDD 23.51 / −0.9 / +4.0 / +90.0 / −3.5, 대박 9→6 | 21.20M (−6.47M) / MDD 31.11 | 21.20M (−2.89M) / MDD 31.11 |
| EMA200 −5% 아래 차단 | 22.40M (−0.79M) / MDD 20.63 / +1.5 / +7.0 / +123.4 / −8.3 | 24.88M (−2.79M) | 24.88M (+0.79M) / MDD 29.40 |
| EMA200 −10% 아래 차단 | 24.34M (+1.15M) / MDD 19.87 / +2.5 / +16.3 / +123.4 / −9.2, 대박 9→7 | 24.73M (−2.94M) | 24.73M (+0.64M) / MDD 25.53 |

- **E2 켬**: 세 세계 모두 손해. BEAR 는 막지만(−15.7 → −0.9) 회복 초입(RECOV +38 → +4)과 BULL 을 자름. EMA200 아래 진입 40건의 합은 −2.8% (2022 −28 / 2023 +27) 로 거의 0 — 하락장 손실과 회복 초입 이익이 상쇄.
- **−10% 아래만 차단**: 새 기준 +1.15M·MDD −5.4%p, 기존 K0 +0.64M, 기존 K4 −2.94M. 임계 3개 중 사후 선택, 대박 2건 손실, 독립 검증·대조 없음 → 가설 (`improvement_todo.md` `#105_E2_DEEP`). 현재 gap −13.6% 라 해당 구간.
- **조치**: production 변경 없음. 알림 문구의 "롤백 절차 .bak.v20.9.16" 은 구식 — 그 파일로 되돌리면 AI 포함 구버전으로 돌아가므로 실행 금지 (E2 재활성은 `E2_ENABLED` 설정 문제이지 코드 롤백이 아님).


## 2026-11-15 #106: 숏 전용 전략 수익성 점검 (신규 숏 시뮬) — 🔴 검증된 우위 없음, 자금 분할 운영 비권고 (독립 검증 완료)

**동기**: 사용자 질문 "롱과 별도로 숏 전용 봇을 자금 반반으로 운영". production·롱 시뮬(`core/simulator.py`) 무변경, 롱 회귀 5세계 PASS.
**방법**: 신규 `core/short_sim.py` (Binance BTCUSDT 무기한 4H, 1배, 수수료 0.05%+슬리피지 0.03% 편도, 실제 펀딩, 신호 다음 봉 시가 진입, 봉 내 손절 우선). 청산 = 롱 봇 거울상(초기 2.5ATR 손절 / 1.5ATR 무한 계단 / 3.5ATR 트레일 / EMA 정배열 전환). 기간 2022-01 ~ 2026-11-12. 실행 `bt_106_short.py`, `bt_106_combo.py` → `results/bt_106_short.log·csv`, `bt_106_combo.log`, `bt_106_trades_v*.csv`, `bt_106_eq_v*.csv`. 데이터 `fetch_binance_perp.py`.
**사전 기준**: ① 최종 > 1.0 ② 2022 제외 누적 ≥ 0 ③ 최대 거래 제외 > 1.0 ④ 무작위 진입 대비 상위 10%.

| 변형 | 최종(배) | CAGR | MDD | N | 2022 | 2023 | 2024 | 2025 | 2026 | 2022 제외 | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 EMA 역배열 내내 숏 (손절 없음) | 0.882 | −2.55 | 56.7 | 90 | +39.7 | −27.2 | −28.7 | −7.6 | +30.3 | −37.5 | 미통과 |
| 2 거울상: 역배열+하락추세 | 0.920 | −1.71 | 56.0 | 122 | +62.8 | −2.9 | −14.8 | −38.0 | +8.6 | −44.3 | 미통과 |
| 3 거울상+추격 금지 | 0.696 | −7.18 | 53.7 | 108 | +11.9 | −11.7 | −2.7 | −36.3 | +12.1 | −38.6 | 미통과 |
| 4 거울상+일봉 EMA200 아래 | 0.979 | −0.43 | 55.2 | 76 | +62.8 | −16.2 | −2.1 | −35.5 | +13.6 | −39.9 | 미통과 |
| 5 거울상+일봉 EMA200 −10% 아래 | 1.299 | +5.53 | 27.8 | 48 | +38.9 | −1.8 | 0.0 | −12.5 | +8.8 | −6.6 | ②만 미통과 |
| 6 20봉 저가 이탈 | 0.760 | −5.49 | 52.9 | 100 | +29.1 | −11.2 | −13.8 | −7.5 | −17.0 | −41.2 | 미통과 |
| 7 약세장 반등 되돌림 | 0.701 | −7.05 | 53.7 | 74 | +22.2 | −16.5 | −19.6 | −20.6 | +7.5 | −42.7 | 미통과 |
| 8 거울상+CMF 음수 | 0.724 | −6.42 | 57.4 | 112 | +15.8 | −0.2 | −14.7 | −32.9 | +7.9 | −38.3 | 미통과 |
| 9 역배열+EMA200 아래 | 0.752 | −5.70 | 60.9 | 95 | +24.2 | −19.9 | −7.7 | −30.2 | +17.2 | −39.5 | 미통과 |

- **분리 운영 합산** (리밸런싱 없음, 환율 무시, 롱 = 새 기준 B·MDD만 23,189,386 — 기대치 아님): 롱 100% CAGR +18.9 / MDD 25.3 → 롱50·숏50 변형 5 +13.0 / 18.4, 변형 2 +10.4 / 18.5. 롱50·현금50 +11.0 / 17.5. 숏 절반 ≈ 현금 절반.
- **변형 5 민감도**: 임계 −5% 1.026 / −7.5% 0.989 / −12.5% 1.230 / −15% 1.374, 비용 2배 1.210, 2023 이후만 0.933. 무작위 대조(거래 수 보정 500회) 상위 6.8% (역배열 봉 풀 9.2%).
- **독립 검증**: 수치 전부 재현, 독립 재구현(변형 2·4·5) 거래 시각 일치·손익 차 1e-15, 손계산 3건·원자료 API 대조 일치, 미래 참조·회계 오류 없음, 펀딩 부호·시각 맞음. 1시간 하위 봉 순서로 돌려도 변형 5 1.285배, 나머지 0.71~0.96배. 가정 22종(비용 0·펀딩 0·쿨다운·계단/트레일/손절 변경·고정 익절 등) × 9변형: 변형 5 외 8개는 어떤 가정에서도 2022 제외 −18.9% 이하(비용 0 이어도 마이너스), 최고치는 변형 5 + 계단·트레일 끔 1.513배로 롱 2.319배 미만. 2020-04~2021-12 표본 외는 9개 전부 손실(강세장이라 약세장 검증은 아님).
- **검증 지적**: 변형 5 의 ② 는 파라미터에 민감 — 22개 중 4개 가정에서 2022 제외가 +1.8 ~ +6.4% 로 바뀜. 2023 이후 거래 20건(2025 7건·2026 13건)뿐이고 2026 수익은 거래 1건 → "우위 없음 확정"이 아니라 **"2022 밖에서는 표본 부족으로 판정 불가, 플러스여도 4년 누적 +2~6%"**. 일봉 EMA200 워밍업(2019 시작 데이터로 1.299 → 1.277). `bt_106_short.py` 본문의 무작위 대조는 거래 수 불일치(70 vs 48) — combo 보정판이 유효.
- **결론**: 숏 봇 자금 분할 비권고, 현행 유지. production 변경 없음.

## 2026-11-15 #107: 숏 진입 신호 사건 연구 (26신호 × 보유 3종) — 🔴 후보 0건 (탐색, 독립 검증 전)

**방법**: `bt_107_short_scan.py` — Binance 무기한 4H(2019-09~), 신호 다음 봉 시가 숏 → 24h/72h/168h 뒤 종가 청산, 왕복 비용 0.16% + 펀딩. 탐색 2022-01~2026-11 / 검증 2020-07~2021-12. 사전 기준: 평균 순수익 > 0 AND 5개 연도 중 4개 이상 플러스 AND 2022 제외 > 0 → 검증 구간 재현. 결과 `results/bt_107_short_scan.log·csv`.
- **78회 검정 중 후보 0건.** 전체 봉 평균(아무 때나 숏) 72h −0.28% (2022 +0.56 / 2023 −0.99 / 2024 −0.81 / 2025 −0.13 / 2026 +0.02).
- 추세 추종 12종(EMA 역배열, 하락추세, EMA200 아래, 30일·7일 모멘텀, 20·55봉 저가 이탈, 일봉 데드크로스, MACD, 20주 평균, 고점 하락): 플러스 연도 1~2/5 (30일 모멘텀만 3/5), 2022 제외 전부 마이너스.
- 급등 되돌림 7종: 가장 나쁨 (RSI>70 72h −1.32, 볼린저 상단 −0.85, 3일 +10% −0.98). 역배열 중 RSI>60 만 24h +0.04 (3/5년, 2022 제외 −0.11).
- 수급 4종: 펀딩 과열 숏 마이너스(표본 2025~26 없음·2024 한 해뿐), 펀딩 음수 숏 5년 전부 손실(72h −0.84), 김프>3% −0.46.
- 변동성 3종: 급락봉 추격 24h −1.03, 압축 후 하방 이탈 −0.76, ATR 상위 5%+역배열 72h +0.29 (3/5년, 2022 제외 −0.16).
- **한계**: 4H 봉·고정 보유·BTC 단일. 1H/일봉, 알트 숏, 롱 포지션 헤지용 숏은 미검토. 독립 검증 미실시(탐색).
- **결론**: 숏 진입 알파 후보 없음. production 변경 없음.


## 2026-11-15 #108: 숏 변형 9개 손실 원인 분해 + 개선안 15개 시험 — 🔴 채택 0, 미결 후보 1 (독립 검증 완료)

**방법**: `bt_108_short_diag.py` (#106 거래 재분석: 청산 사유·도달 계단·MFE/MAE·진입 시 상태) → `bt_108_short_improve.py` (개선안 A~L, 2차 M~O, 익절 민감도). `core/short_sim.py` opt-in 추가(기본 끔, #106 결과 바이트 동일): `time_stop_bars`, `tp_mult`/`tp_frac`. 데이터 2019-09 시작(EMA200 워밍업 해소 → 변형 5 기준 1.277). 표본 내 2022-01~2026-11 / 표본 외 2020-04~2021-12. 결과 `results/bt_108_short_diag.log`, `bt_108_short_improve.log·csv`.
**사전 기준**: ① 표본 내 > 1 AND 2022 제외 ≥ 0 ② 표본 외 ≥ 0.95 AND 기준 초과 ③ 9개 변형 중 7개 이상에서 표본 내·외 모두 개선 ④ (필터형) 무작위 블록 제외 대조 상위 10%.

- **손실 원인 (공통)**: 승률 28~38% × 평균 이익 ≈ 평균 손실의 2배 = 본전 구조. 이익은 3계단 이상 간 거래(18.5~33%)에서만. 손실 거래의 53~63% 가 유리한 쪽으로 1ATR 이상 갔다가 되돌려 손실. 계단 0 거래는 전부 손실(평균 −3.25~−4.27%). ATR% ≥2.5 진입은 9개 모두 마이너스(변형 1·5 는 약함). 수수료·슬리피지 −8~−20%p, 펀딩 +2.2~+10.1%p — 주원인 아님.
- **변형별**: 1 손절 없음 → 2023·24 상승장 −27/−29% / 2·4·8 2025년 −33~−38%, ADX≥35 늦은 진입 손실 / 3 추격 금지가 최악(숏은 EMA21 에서 멀수록 양호 — 롱과 반대) / 5 30일 수익률 플러스 구간 진입 손실 / 6 이탈 직후 반등, 초기 손절 39건 −157% / 7 MFE<0.5ATR 손절 다수 / 9 flip 청산 18건 −45%.
- **개선안 (표본 내 개선 수 / 표본 외 / 둘 다, 9개 중)**: A 조기 본전 0/5/0 · C 12봉 시간 청산 1/4/1 · K(A+C) 0/6/0 — 손절 조이기는 표본 내 악화. D 고변동 제외 8/7/6 · E ADX≥35 제외 5/5/3 · F 30일 수익률 −15~0% 7/8/6 · G 추격만 8/6/5 · H RSI<40 6/3/3 · I(D+E) 5/7/4 · J(D+E+F) 9/8/8 · L 1/9/1. **B 1.5ATR 절반 익절 7/9/7 (③ 충족)** 이나 ① 통과 변형 없음(변형 5: 1.424, 2022 제외 −0.9%).
- **1차(A~L) 전 기준 통과 0.** ①② 동시 충족은 G×변형 5 뿐, ④ 상위 23% 로 탈락.
- **2차(결과를 본 뒤 추가한 M·N·O)**: 변형 1 + N(B+F) 1.483 / 표본 외 1.192 / 무작위 상위 5%, 변형 1 + O(B+D+F) 1.594 / 0.965 / 상위 4% — **사전 기준 4개 모두 충족**(③ N 7/9, O 9/9). 탈락 사유는 사후 조합이라는 점.
- **독립 검증**: 로그·csv 전부 재현 일치, 새 옵션 회계 손계산 일치, #106 불변. 변형 1 + N/O 추가 점검 — 유리: ETH 표본 내 재현(1.470 / 1.401, 2022 제외 +6.8 / +4.5%), 최대 거래 제외 1.287 / 1.390, 비용 2배 1.352 / 1.456, 익절 위치·비율 12조합 모두 표본 내 1.20~1.55. 불리: 30일 수익률 룩백 180봉에서만 성립(120봉 0.993, 150봉 0.976, 240봉 1.003), 2023·2024 두 자산 모두 마이너스, ETH 표본 외 0.428 / 0.887, 2022 제외 +12.9% 는 4년 누적(연 3% 수준, MDD 24%). → **"약한 후보, 미결"** (`improvement_todo.md` `#108_SHORT_V1F`).
- **결론**: 채택 없음. 숏 봇 비권고 유지. production 변경 없음.

## 2026-11-15 #109: 숏 빠른 익절형 (전량 익절 + 재진입) — 🔴 통과 0/27 (독립 검증 완료)

**방법**: `bt_109_short_tp.py` — `tp_full_close` opt-in(목표가 도달 시 전량 청산, 신호 유지 시 다음 봉 재진입). 목표가 1.0/1.5/2.0 ATR × 변형 9. 대조: 무작위 진입 200회, ETHUSDT 무기한(이 연구에서 처음 사용), 비용 2배, 익절·손절 배수 민감도. 결과 `results/bt_109_short_tp.log·csv`, `bt_109_first_only_check.log`.
- **#108 의 "익절 100%" 호성적(변형 2: 2.061배)은 구현 효과**: `tp_full_close=False` 에서는 익절 뒤 수량 0 포지션이 손절·전환까지 남아 재진입을 막음(= 추세당 1회 익절). 재진입을 허용하면 변형 2 는 0.986배.
- **27개 중 사전 기준 통과 0.** BTC 표본 내 > 1: 변형 3(1.0·1.5ATR), 변형 5(전 목표가, 1.17~1.49), 변형 1·2·4(2.0ATR, 1.03~1.24). ETH 표본 내는 27개 전부 0.19~0.57배.
- 청산 사유(변형 2, 1.5ATR): 익절 176건 +498% vs 손절 89건 −422% + flip 14건 −44% — 승률 62% 로도 손익비 1.5:2.5 를 못 넘김.
- "추세당 1회" 방식: BTC 변형 2 2.061 → ETH 0.542 (재현 안 됨). 단 변형 5 는 BTC 1.536 / ETH 1.079 (2022 제외 +24.4%), 변형 8 은 1.304 / 1.114 로 양쪽 플러스 — 미결 관찰.
- **검증 지적**: 익절을 시장가(수수료 0.05%+슬리피지)로 매기고 진입 봉 익절을 막아 숏에 다소 불리. 지정가(수수료 0.02%, 슬리피지 0)+진입 봉 익절 허용 시 BTC 변형 2 0.986 → 1.411, 변형 5 1.491 → 1.854 로 오르나 ETH 는 27개 전부 1 미만(0.27~0.92) → 통과 0 유지. `tp_cooldown` 은 0 외 미시험.
- **결론**: 빠른 익절형 채택 없음. production 변경 없음.

## 2026-11-15 #110: 가장 나은 숏 후보 + 롱 결합 — 🔴 분할 운영은 전부 롱 단독 미만, 같은 자금 겹침만 우위 (탐색, 독립 검증 전)

**방법**: `bt_110_long_short_combo.py` — 롱 = 새 기준 B·MDD만(2.319배, CAGR +18.90, MDD 25.3 — 기대치 아님). 숏 후보 4개(A 변형 5 1.277 / B 변형 5+1.5ATR 익절·재진입 1.491 / C 변형 5+추세당 1회 익절 1.536 / D 역배열+절반 익절+30일 필터 1.483) — 같은 기간 성적으로 고른 것이라 **낙관적 상한**. 결과 `results/bt_110_combo.log·csv`.
- **분할(자금 나눠 따로 운영)**: 롱 90/숏 10 CAGR −0.84 ~ −1.12%p, 80/20 −1.70 ~ −2.28%p, 70/30 −2.58 ~ −3.49%p. MDD 는 −2.1 ~ −6.8%p. 숏 단독이 2.32배를 넘어야 롱 단독을 이김(현재 1.28~1.54).
- **분할 + 숏 계좌 레버리지 2~3배**: 16개 중 14개가 롱 단독 미만(−0.11 ~ −2.14%p). 숏 C 3배만 +0.70 / +1.39%p (MDD −4.6 / −7.2) — 미검증 관찰(#109)인 "추세당 1회 익절"에 레버리지를 얹은 것이라 근거 약함. 숏 계좌 MDD 35~63%.
- **겹침(같은 자금으로 롱이 쉴 때 숏)**: 숏 크기 30% → CAGR +2.45 ~ +3.68%p, 50% → +3.81 ~ +5.86%p (MDD −3.3 ~ +1.2), 100% → +6.16 ~ +11.01%p (MDD 최대 +7.9). 롱·숏 동시 보유 봉 0.2~2.5%, 수익률 상관 ≈ 0. 개선의 대부분은 2022년(−16% → −8 ~ +29%), 2025년은 악화(+23 → +7~+19, D 만 개선).
- **한계**: 겹침은 롱·숏이 한 거래소·한 증거금에 있어야 가능 — 현 구조(업비트 현물 KRW)에서는 불가. 롱을 선물로 옮기면 김프·환율·펀딩(롱 지불)·청산 위험이 새로 생기고 롱 시뮬부터 다시 해야 함. 숏 후보 자체가 2022년 의존·미채택.
- **결론**: 현 구조에서 숏 결합은 롱 단독보다 수익이 낮음. production 변경 없음.

## 2026-11-18 #136: 최근 2년 현행이 추세보다 좋은 이유 — 🔎 분석 (시장이 "큰 추세 없는 횡보·하락"으로 바뀜 + 현행의 작은 손실 사이징)
- **스크립트**: `bt_136_recent_why.py` → `results/bt_136_recent_why.log`. 비교 = 현행 v20.9.28 (#133 곡선) vs 추세 ALL 4H 1/4 · 일봉 (비용 0.08%). 업비트 KRW.
- **① 시장 성격**: 반기 추세 효율 (|순변화| ÷ 4H 변화 합) 2018-03~2023 평균 0.074 → 2024~ 0.041 → 2025~ 0.030 (절반 이하). 2025~ BTC −29%, 25H1 +4% (효율 0.007, 거의 제자리 왕복).
- **② 추세가 크게 이긴 반기 = 큰 지속 추세장**: 19H1 (BTC +228%) 4H1/4 +172 vs 현행 +74 · 20H2 (+192%) +158 vs +75 · 21H1 +46 vs +6 · 21H2 +45 vs +2 · 23H1 +56 vs +9. 2024H2 이후 이런 반기 없음 → 추세 우위 소멸. 2025H1~2026H2 반기 4개 모두 현행 ≥ 4H1/4 (+10/+8/+2/+8 vs +6/+4/−1/+5).
- **③ 포착률 (BTC 상승봉·하락봉 수익 중 전략이 가져간 비율)**: 2018-03~2023 현행 22% / 20%, 4H1/4 39% / 34% (추세가 더 많이 탐) → 2025~ 현행 33% / 29%, 4H1/4 28% / 26% (역전). 4H1/4 노출 2025~ 29~33% (예전 45~60%) — 짧게 들어갔다 나오는 신호만 반복.
- **④ 추세 보유 구간**: 이긴 구간 평균 최고 +28.7% → 남긴 +17.6% (2018~2023) vs 2025~ 최고 +11.8% → 남긴 +6.1%. 되돌림은 비슷 (5~8%p) 하지만 상승 폭이 작아져 되돌림이 이익의 절반을 먹음. 승률 21% → 12%.
- **⑤ 현행 거래 (자산 기준, 사이징 반영)**: 손실 평균 자산 −2.2% (가격 기준 −3.4% — 손실 거래는 비중이 작음). 2025~ 30건 승률 43% 이익 +5.41% / 손실 −2.29%, 누적 +32.4% → 최대 1건 (2026-08-19 +13.0%) 제외 +17.2% (4H1/4 같은 기간 약 +15%, 이 쪽도 2026-08 +13.2% 포함). 큰 하락월 (25-02 −21.8%, 25-11 −16.9%, 26-02 −21.5%) 에 현행 −0.3 / 0.0 / 0.0.
- **원인 요약**: (1) 최근 시장에 추세 전략이 돈 버는 '수개월 지속 큰 상승'이 없음 (2) 현행은 계단 익절로 짧은 상승을 확정하고 손실은 작게 (사이징) → 횡보·하락장에 유리 (3) 현행의 우위는 최대 거래 1건을 빼면 4H1/4 와 비슷 (+17 vs +15%) — "현행이 확실히 낫다"가 아니라 "추세 쪽 강점이 사라졌다"에 가까움.
- **한계**: 현행 거래 목록은 2020~ 시작 시뮬 (bt_121) — 자산 기준 누적 +32.4% 가 #133 곡선 +31.9% 와 맞아 경로 동일로 봄. 현행 노출은 '자산이 움직인 봉' 근사. 2년은 짧은 표본.

## 2026-11-18 #135: 4H 추세 확인 — 이웃 기간·실제 비용·현행과 반반 — 🟢 4H 1/3~1/6 넓은 구간에서 일봉보다 우위 (탐색, 독립 검증 전)
- **실제 비용 측정**: 업비트 수수료 0.05% + 봇 실매수 13건 (봉 시작 직후, 약 170만 원) 체결가 − 봉 시가 평균 +0.028% / 호가창 시장가 1,000만 원 0.013%, 1억 0.048% → 편도 약 0.08% 가정이 실측과 맞음 (매도는 체결가 미기록으로 미측정).
- **① 이웃 기간 (4H, 일봉 기간 대비 비율) CAGR / MDD, 비용 0.08% → 0.15% → 0.3%**: 1/3 +63.16 / 34.9 → +58.59 → +49.23 · 1/4 +62.05 / 28.1 → +56.07 → +43.99 · 1/6 +65.31 / 31.1 → +57.31 → +41.44 · 1/8 +58.18 / 27.7 → +48.48 → +29.65 · 1/12 +55.04 / 26.0 → +42.70 → +19.46 · 일봉 +49.66 / 30.5 → +48.64 → +46.49. → 0.15% 까지 1/3~1/6 전부 일봉보다 우위 (봉우리 하나가 아닌 넓은 구간), 1/3 이 회전 최소 (40배/년) 로 비용에 가장 강함. 2025~ 최근: 1/3 +11.4 / 1/6 +6.1 / 일봉 −0.6 / 현행 +16.0.
- **③ 현행 + 추세 반반 (매일 재조정) CAGR / MDD, 0.08%**: + 일봉 +40.83 / 27.1 · **+ 4H 1/6 +47.54 / 25.9** · **+ 4H 1/4 +46.14 / 24.1** · + 4H 1/8 +44.38 / 23.3 (현행 +30.24 / 29.7). 0.15%: + 1/6 +43.94 / 26.8, + 1/4 +43.42 / 24.7, + 일봉 +40.35. 0.3%: + 일봉 +39.33 가 4H 조합보다 높음. 구간: 18-19·20-21·22-23 은 반반 전부 우위, 24-26 은 비슷 (+33.9 vs +34.4), 2025~ 는 현행 +16.0 > 반반 +7.7 ~ +12.0.
- **한계**: #131~#135 에서 비교한 변형이 많음 (다중 비교) — 1등 수치는 낙관적. 매도 체결 비용 미측정. 독립 검증 전.

## 2026-11-18 #134: 추세 ALL 의 봉 길이 — 일봉 vs 4H vs 1H — 🟡 비용이 낮으면 4H·짧은 기간이 가장 높음, 비용 민감 (탐색)
- **설정**: `bt_134_trend_timeframe.py`, 업비트 KRW 롱만, ALL 정의 #131. "같은 기간" = 일수 × 봉수(4H ×6, 1H ×24) → 판단만 자주 / "짧게" = 숫자를 봉 수로 (4H 1/6, 1H 1/24). 1H 데이터 2020~ 라 1H 는 2021~ 비교.
- **2018-03~2026-11 CAGR / MDD (비용 0.3% → 0.08%)**: 일봉 +46.49 / 32.0 → +49.66 / 30.5 · 4H 같은 기간 +42.87 / 39.5 → +49.78 / 36.3 · **4H 짧게 +41.44 / 36.2 → +65.31 / 31.1 (79.2배, 구간 +60.7 / +185.9 / +34.0 / +33.2)**. 2021~: 일봉 +37.52 · 4H 짧게 +47.74 · 1H 같은 기간 +33.50 · 1H 짧게 +12.09 (0.08%). 현행 4H 전략 2018-03~ +30.24%, 2021~ +19.70%.
- **비용 민감도 (2018-03~ CAGR)**: 일봉 0.05% +50.1 / 0.15% +48.6 / 0.30% +46.5 · 4H 짧게 +68.9 / +57.3 / +41.4 (손익분기 약 0.27%, 회전 70배/년, 비중 변경 368회/년) · 4H 같은 기간 +50.7 / +47.5 / +42.9. 1봉 지연 (0.08%): 일봉 +43.6 MDD 34.9 / 4H 짧게 +64.1 MDD 35.2.
- **해석**: 판단만 자주 하는 것(같은 기간)은 이득 없음. 기간을 1/6 로 짧게 한 4H 는 수수료가 실제 수준(0.05% + 슬리피지)이면 크게 우위이나 거래가 하루 1회꼴이라 비용·슬리피지 가정에 결과가 좌우됨. 1H 는 열세. 봉 길이·기간은 결과를 보고 고르는 단계 → 이웃 기간(1/4, 1/8) · 실제 체결 비용 확인 필요.

## 2026-11-18 #133: 업비트 현행 + 일봉 추세 반반, 2018 약세장 포함 — 🟢 사전 기준 4/4 통과 (연구 후보, 독립 검증 완료)
- **설정**: `bt_133_upbit_combo_2018.py`, 데이터 `upbit_4h_2017.csv` (`fetch_upbit_4h_2017.py`, 2017-09-26~, 기존 파일과 종가 최대 차 0.09%). 현행 v20.9.28 시뮬 2018-03 시작 (2020~ 7.38배 동일). 일봉 #131 정의 롱만. 반반 = 매일 재조정 (재조정 비용 미반영).
- **2018-03~2026-11 (CAGR / MDD, 구간 18-19 / 20-21 / 22-23 / 24-26)**: 단순 보유 +27.37% / 74.1 · **현행 9.96배 +30.24% / 29.3 (+17.8 / +66.5 / +7.0 / +34.4)** · ALL 단독 27.68배 +46.49% / 32.0 · SMA 단독 38.17배 +52.00% / 36.0 · **현행 + ALL 반반 17.90배 +39.33% / 27.5 (+31.7 / +92.9 / +14.7 / +31.4)** · 현행 + SMA 반반 21.29배 +42.13% / 28.9.
- **판정 (현행 + ALL 반반, 0.3%)**: ① CAGR +39.33 vs +30.24 O ② MDD 27.5 vs 29.3 O ③ 구간 비악화 3/4 O (2024~2026-11 만 −3.0%p) ④ 비용 2배 +37.31% O → 통과. 2018 약세장: 현행 −2% / ALL −10% / 반반 −5%.
- **검증 (verifier)**: 전 수치 소수점까지 재현, 미래 참조 없음. 재조정 비용 반영 +38.85% (−0.48%p) / 재조정 없음 18.82배 +40.13% MDD 28.7 (3/4) / 일봉 체결 1일 지연 반반 +36.53% MDD 27.7 (3/4), 지연+비용 0.6% +34.55% / 우위 큰 날 5일 제외 +34.97%. 최근 약세: 2023-07~ 반반 +34.38 vs 현행 +34.99, 2025-01~ +6.42 vs +16.04 (−9.6%p). 우위는 2019 (+74 vs +35)·2021 (+44 vs +8) 에 집중. 약한 고리: ① ALL 은 #131/#132 결과를 본 뒤 고름 ② 최근 열세가 국면 탓인지 우위 소멸인지 미구분 ③ 2018-19 현행은 1H 하위 봉 없는 4H 판정.
- **한계**: 반반 비율·ALL 선택은 #132 (2020~) 결과를 본 뒤 → 2018-19 만 표본 밖. 2020 이전 1H 하위 봉 없음 (현행은 4H 봉내 판정). 재조정 비용 미반영.

## 2026-11-18 #132: 일봉 추세 후속 — 업비트 데이터에 적용 + 최근 구간 약세 원인 — 🟢 업비트에서도 현행 4H 전략보다 전체 우위 (탐색, 연구 후보)
- **정정**: #131 앙상블 정의 = ±1 신호 평균 후 0 미만 0 (5개 중 3개 플러스 → 비중 0.2). "플러스 개수 비율"(→ 0.6) 정의도 함께 계산 (`bt_132_daily_trend_upbit_recent.py` mode=count).
- **① 업비트 KRW 일봉, 롱만, #131 정의 (비용 0.3% / 0.08%)**: TSMOM 12.41배 +44.36% MDD 30.3 / 15.08배 · **SMA 19.33배 +53.98% MDD 28.3** / 22.85배 · DONCH 10.41배 +40.70% MDD 28.0 · **ALL 14.24배 +47.27% MDD 27.3** / 16.80배 — 업비트 현행 7.38배 +33.83% MDD 29.7 보다 전부 높음. OOS(2023-07~) 는 비슷 (현행 +34.9 vs ALL +32.6 / 0.08% +36.3, SMA +31.1 / +35.3, TSMOM +27.0 / +31.3). 같은 전략이 업비트에서 바이낸스보다 강함 (#130 단기 완충과 같은 방향). 개수 정의는 MDD 37~44 로 악화.
- **② 최근 약세 원인 (바이낸스 TSMOM vs 업비트 현행, 반기 14개)**: 차이가 효율비(추세 깔끔함)와 상관 +0.63, BTC 수익률과 +0.66. 효율비 상위 절반 반기 +16.6%p, 하위 절반 −0.3%p. 2024H2~2026 은 횡보·하락 구간이 많아 현행(계단 익절로 짧은 파동 수확)이 우위. 일봉 추세는 큰 추세장에서 이기고 횡보장에서 짐.
- **현행 + 일봉 추세 반반 (업비트, 매일 재조정, 비용 0.3%)**: +ALL 10.80배 +41.46% **MDD 20.7** (OOS +34.39) · +SMA 12.69배 +44.83% MDD 23.0 (OOS +33.74) · +TSMOM 10.17배 +40.21% MDD 22.8. 일 수익률 상관 0.53~0.58 → 분산 효과로 MDD 가 둘 다보다 낮음.
- **한계**: 일봉 추세는 비중 최대 100% (현행 시뮬은 사이징·피라미딩) / 업비트 데이터 2019~ 라 약세장(2018) 확인 불가 / 사후 분석 포함, 독립 검증 전.

## 2026-11-18 #131: 바이낸스용 새 전략 — 일봉 추세 (봉내 손절 없음) — 🟡 전체 CAGR 은 업비트 초과, 사전 기준 ② (최근 구간) 미달 → "못 이김" (탐색)
- **설정**: `bt_131_daily_trend.py` (독립 벡터 백테스터), 바이낸스 현물 일봉 (UTC 0시 종가, 데이터 `binance_spot_4h_2017.csv` 2017-08~). 가족 TSMOM(30/60/90/120/180일) · SMA(50/100/150/200) · DONCH(20/10, 55/20, 100/50) · ALL, 앙상블(평균) × 롱만(LO)/롱숏(LS) × raw/변동성 목표(VT, 목표 71% = 2017-08~2019-12 중앙). 비용 현물 0.13%, 선물 0.08% + 펀딩. 선택 = IS(2020-01~2023-06) CAGR 최고 1개.
- **기준**: 업비트 현행 7.38배 +33.83% MDD 29.7 (IS +32.80 / OOS +34.93). 바이낸스 단순 보유 10.28배 +40.43% MDD 76.6 (2018-19 −20.3%).
- **선택 = TSMOM 롱만 raw**: 10.90배 **+41.65% MDD 28.9** | IS +56.95 / **OOS +27.24** | 2018-03~2019 +19.7% (보유 −20.3%) | 연도 20:+151 21:+52 22:−2 23:+67 24:+71 25:0 26:−4. 판정 ① 전체 O ② OOS > 업비트 ✗ ③ 약세장 O ④ 단일값 4/5 O → 못 이김.
- **기타 롱만 앙상블**: SMA 12.18배 +43.96% MDD 43.0 (OOS +31.71) · ALL 9.30배 +38.40% MDD 29.9 (OOS +27.22) · DONCH 5.12배 +26.89%. VT 는 대체로 수익 감소. **롱숏(LS) 은 전부 롱만보다 열세** (+12 ~ +30%, MDD 45 ~ 58).
- **해석**: 일봉 추세(롱만)는 업비트 현행보다 2020~2023 상승장에서 훨씬 강하고 약세장 방어도 됨, 그러나 최근(2023-07~) 은 업비트가 우위 (2025: 0 vs +20, 2026: −4 vs +10). 숏 추가는 일봉 추세에서도 손해. 수치는 USDT 기준 (원화 환산 시 바이낸스 쪽 +약 17% 누적).
- **검증 (verifier)**: 수치 독립 재현 일치 (10.902 / +41.65 / MDD 28.9 / OOS +27.24 / 2018-19 +19.66). 미래 참조·비용 누락 없음 (shift 제거 시 116배로 확인). 체결 1일 지연 10.23배 +40.34% / 비용 2배 9.50배 +38.85% / 지연+비용2배 8.92배 +37.56% (OOS +25.81) / 최대 기여 월 제외 7.42배 vs 업비트 5.50배. 연도별 업비트 대비 3/7 우위 → 채택 조건(구간 비악화) 미달, 판정 "못 이김" 유지. 연속 비중이라 "최대 거래 1건 제외" 정의 불가 (비중>0 연속 구간 기준이면 2.34배). 데이터 중복·모순 0, 4H 결측 16봉.
- 결과 `results/bt_131_daily_trend.log` / `.csv`.

## 2026-11-18 #126~#130: 바이낸스 롱이 업비트보다 낮은 이유 — 🔴 원인 = 업비트 가격 자체의 단기 완충 (김프가 BTC 와 반대로 움직임), 바이낸스에서 재현 불가 (탐색)
- **#126 거래 정밀 비교** (`bt_126_upbit_vs_binance_forensic.py`, 같은 규칙 v20.9.28, 2020-01~2026-11): 업비트 vs 선물 — 공통 진입(±2봉) 51건뿐, 자산 로그 격차 110.8%p 중 공통 거래 차 12.6%p, 한쪽만 진입 거래 98%p (업비트만 102건 +80.6% / 선물만 145건 −14.6%). 봉별 요소 일치율 거래량 vol_ok 78%·OBV 79%·regime 80%, 공통 거래에서 선물이 34/51건 먼저 청산 (보유 26.6 vs 42.6봉). 현물판: 공통 58건, 바이낸스 36건 먼저 청산, 격차 60.3%p.
- **#127 신호 데이터** (`bt_127_binance_spot_signal.py`, 현물 수집 `fetch_binance_spot.py`): 선물 2.438 / 선물 가격+현물 거래량 2.893 / **현물 계좌 (비용 0.13%) 4.038 (+22.56%, MDD 42.4, 원화 환산 4.73배)** / 현물 0.08% 4.797. 선물 약점의 큰 몫은 펀딩·선물 가격.
- **#128 고정 % ×변동성 비율** (`bt_128_binance_vol_scale.py`): 바이낸스 ATR% 가 매년 업비트의 1.15~1.24배 (2019 1.17). 현물 K1 (×1.17) 4.486 (+1.9%p) 이나 뒤 구간 −2.7%p, 이웃 ×1.10/×1.25 도 뒤 구간 −2.3 ~ −3.0 → 미통과. 선물 K1 은 앞 −13.2 / 뒤 +10.4 로 반대. 눌림목 % 는 효과 0.
- **#129 업비트 잡음 민감도** (`bt_129_upbit_noise.py`, 가격 0.05%/봉 × 10시드): 7.68 ~ 9.07배 (중앙 8.33, 원본보다 전부 높음 — 4H 잡음·1H 원본 불일치 영향 가능) → 업비트 결과는 운이 아님, 바이낸스 4~4.7배는 범위 밖.
- **메커니즘 확인** (비용 0.3%·김프 사이징 끔 동일 조건): 업비트 가격+업비트 거래량 6.227 / 업비트 가격+바이낸스 거래량 7.873 / 바이낸스 현물 1.819 / 바이낸스 × 환율·김프 30일 추세 1.161 → 거래량·환율 추세 아님. 원화/USDT 비율 R 의 4H 변동이 BTC 와 상관 −0.53 (1일 −0.55, 30일 −0.11) → 업비트 가격은 단기 변동만 약 13% 작고 30일 변동은 같음. 업비트 김프 사이징 효과 7.383 vs 끔 6.227. 업비트 비용 0.13% 가정 시 9.144.
- **#130 완충 가격으로 신호** (`bt_130_binance_damped_signal.py`, β·k 를 2019 로만 추정 k=12 β=0.147, R² 0.06): 완충 가격 자체 시뮬은 4.0 ~ 5.9배로 좋아지나, 같은 신호를 실제 바이낸스 가격에 체결하면 2.99 ~ 3.63배 (완충 없음 같은 방법 4.297) → 전부 악화. 업비트의 이득은 신호가 아니라 "완충된 가격에 실제로 체결되는 것" 에서 나옴.
- **결론**: 같은 전략으로 바이낸스 롱이 업비트를 이길 길은 찾지 못함. 바이낸스 최선 = 현물 계좌 4.04배 (원화 4.73배) vs 업비트 7.38배. 업비트 우위는 원화 시장 구조(김프의 단기 역방향 움직임 + 김프 사이징)에서 나오는 구조적 몫.

## 2026-11-18 #125: 바이낸스 선물 롱 전용 개선 (잦은 거래 줄이기 중심, 구간 분리) — 🔴 견고한 개선 없음, 사전 기준 미통과 (탐색)
- **설정**: `bt_125_perp_long_tune.py`, 기준 v20.9.28 선물 롱 2.438배 (2020-01~2026-11). 선택 구간 IS 2020-01~2023-06 / 확인 구간 OOS 2023-07~2026-11. 1단계 장치 9종 28개 단독 → 장치별 IS 최고 → 2단계 IS 탐욕적 조합 → 최종 기준 ① OOS +1%p ② MDD ③ 최대 거래 제외 ④ 옆 값(×0.85/×1.15) ⑤ 비용 2배.
- **1단계 (IS Δ / OOS Δ)**: 초기 3.0ATR +14.1 / +0.7 (3.82배) · 손절 종가 확대 +9.9 ~ +10.9 / +0.3 ~ +1.5 · 재진입 금지 12봉 +2% +8.0 / −1.3 · 손실 뒤 12봉 금지 +5.2 / −2.0 (24봉 −4.9 / −5.7) · 계단 간격 2% +4.2 / −5.1, 4% −5.0 / +7.5 · 계단 TP 간격 2.0 −2.3 / +5.7 · 트레일 ATR 배수 효과 0 (고점 −5% 가 항상 우선). → 앞뒤 구간 부호가 같은 건 "손절 덜 민감하게"(초기 손절 넓힘·종가 판정) 계열뿐, 거래 횟수를 직접 줄이는 장치(쿨다운·재진입 금지)는 OOS 악화.
- **초기 손절 배수 비단조**: 2.0 2.95 / 2.5 2.44 / 3.0 3.82 / 3.5 3.37 / 4.0 2.33배, 최종안에서 2.55 → 2.38배 — 3.0 은 잡음 속 봉우리일 가능성.
- **2단계 최종안** = 초기 3.0ATR + 계단 간격 2%: 3.748배 +21.24% MDD 30.6 (기준 43.3), 최대 제외 2.879 (1.894), 비용 2배 2.717 (1.839) — 그러나 ① OOS +16.28% < 기준 +20.73% ✗, ④ 2.55ATR 2.381배 ✗ → 미통과. 계단 2% 는 IS +4.5 / OOS −5.2 (과적합 전형).
- **참고**: 같은 OOS 구간 업비트 롱 +34.93% (IS +32.8%) vs 바이낸스 기준 +20.73%. 결론: 바이낸스 롱 규칙 조정으로는 견고한 개선을 찾지 못함, 격차는 #123 대로 신호 데이터·가격 경로 쪽.
- 결과 `results/bt_125_scan_eq.csv` / `_meta.json`, `bt_125_greedy.log`.

## 2026-11-18 #124: 업비트 단독 vs 바이낸스 단독 (연동 없음, 롱 개선안 + EMA50<200 숏) — 🟡 최선 바이낸스안이 업비트와 수익 비슷, MDD 더 큼 (탐색, 낙관 편향)
- **설정**: `bt_124_binance_standalone.py`, 2020-01~2026-11. 바이낸스는 바이낸스 데이터로만 신호, 계좌 한 포지션 (롱 우선, 쉴 때 숏). 수익률만 비교 (업비트 원화 / 바이낸스 USDT).
- **결과 (최종 / CAGR / MDD, 2022~ CAGR / MDD)**: 업비트 롱만 7.38배 +33.83% 29.7 (+22.34% / 20.0) · 바이낸스 L0 현행+숏 4.58배 +24.83% 38.6 (+15.45 / 33.1) · L1 전부 종가+숏 6.45배 +31.23% 33.4 (+22.74 / 33.4) · **L2 초기 3.0ATR+숏 7.18배 +33.29% 33.4 (+19.93 / 33.4)** · L3 L1+L2+숏 5.48배 +28.13% 33.4 (+22.09 / 33.4).
- **롱만**: L0 2.44 / L1 3.45 / L2 3.82 / L3 2.93 — 두 개선을 합치면 각각보다 나빠짐 (2021: L2 +21% vs L3 −15%) → 규칙 변경 효과가 불안정.
- **해석**: 바이낸스 최선안(L2+숏)은 업비트와 CAGR 비슷(−0.5%p)하나 MDD +3.7%p, 2022~ 는 CAGR −2.4%p·MDD +13.4%p. 바이낸스 쪽은 숏 진입(30개 중 1등)·롱 개선안(#123 결과 보고 선택) 모두 같은 기간 선택 → 실제는 더 낮을 가능성. 업비트 단독 우위 유지.
- 결과 `results/bt_124_binance_standalone.log` / `.csv`.

## 2026-11-18 #123: 바이낸스 선물 롱 개선 분석 — 🟡 신호를 업비트 데이터로 내면 2.44 → 4.57배, 바이낸스 데이터 그대로는 초기 손절 3.0ATR·전부 종가 판정이 후보 (탐색, 독립 검증 전)
- **설정**: `bt_123_perp_long_improve.py`, 2020-01~2026-11, 시뮬 무변경. 기준 = 바이낸스 선물 롱 v20.9.28 2.44배 +13.87% MDD 43.3 (2022~ +7.24% / 34.4).
- **A 원인 진단 (업비트 시뮬 봉별 비중 → 다른 가격)**: 방법 보정 — 업비트 가격·비용 0.3% 6.80배 (실제 7.38, 오차 약 −8%). **업비트 신호 → 바이낸스 체결 (0.08% + 펀딩) 4.57배 +24.80% MDD 41.0 (2022~ +20.21% / 22.2)**, 비용 2배 3.74배. → 격차 6.80 → 2.44 중 신호 데이터(바이낸스 거래량·봉 모양) 몫이 4.57 → 2.44, 가격 경로(김프·환율, 2021 −16 vs +3) 몫이 6.80 → 4.57.
- **B 규칙 변경 (사전 기준 ① 2020~·2022~ CAGR +0.5%p ② MDD +1%p 이내 ③ 자기 최대 제외 우위)**: B1 전부 4H 종가 3.45배 +19.79% (+5.9) MDD 34.8 (−8.5), 2022~ +6.9 — 통과 · B2 계단+트레일 종가 3.44배 (+5.9) MDD 42.1, 2022~ +2.4 — 통과 · **B3 초기 손절 3.0ATR 3.82배 +21.59% (+7.7) MDD 33.4 (−9.9), 2022~ +4.2 — 통과** · B4 계단 7% 1.37배 악화 · B5 운영 방식 전환 끔 2.32배 미통과.
- **주의**: 비교는 USDT 기준 — 원화로 환산하면 바이낸스 계좌는 환율 상승분(단순 보유 업비트 12.08 vs 바이낸스 10.32, 약 17% 누적)만큼 더해짐 (업비트 가격엔 환율·김프 포함). B1·B3 는 #112 에서 ETH 악화 (BTC 한정 효과 가능). 조합 (B1+B3, 업비트 신호 + 숏) 미시험.
- 결과 `results/bt_123_perp_long_improve.log`, `bt_123_perp_eq.csv`, `bt_123_upbit_expo.csv`.

## 2026-11-18 #122: 업비트(현물 롱만) vs 바이낸스(선물 롱 + EMA50<200 데드크로스 숏, 한 포지션) 같은 금액 — 🔴 바이낸스 계좌가 업비트보다 열세 (비교만, 사전 기준 없음)
- **설정**: `bt_122_binance_ls_account.py`. 업비트 = 현물 v20.9.28 (#121 동일). 바이낸스 = 선물 롱 v20.9.28 (perp_bt, #118 perp 2020 동일 2.438배) + 숏 #121 EMA50<200 전환·청산 C, 숏은 선물 롱 무포지션일 때만·선물 롱 진입 시 청산.
- **2020-01~2026-11 (2022~)**: 업비트 롱만 7.38배 +33.83% MDD 29.7 (+22.34% / 20.0) · 바이낸스 롱만 2.44배 +13.87% / 43.3 (+7.24% / 34.4) · 바이낸스 숏만 1.88배 +9.63% / 13.0 · **바이낸스 롱+숏 4.58배 +24.83% / 38.6 (+15.45% / 33.1)** · 두 계좌 합계 5.98배 +29.78% / 28.5 (+19.42% / 25.5).
- **해석**: 숏은 바이낸스 롱 단독 대비 +11%p 기여하나, 바이낸스 선물 롱 자체가 업비트보다 −20%p 약해 (#111·#118 과 같은 문제) 바이낸스 계좌 전체가 업비트 롱만보다 −9%p, MDD +9%p. 연도별 바이낸스 롱+숏 우위는 2021·2023·2024 (2022 −31%, 2025 −4%).
- 결과 `results/bt_122_binance_ls_account.log`, 선물 롱 거래 `bt_122_perp_long_trades.csv`.

## 2026-11-18 #121: BTC 숏 진입 EMA 비교 (기울기 하락 / 교차), 롱과 겹치지 않게 한 포지션 — 🟡 사전 기준 통과 0 (2022~ 합산 MDD 에서 전부 탈락), 최우수 = EMA50<200 데드크로스 전환 (탐색, 독립 검증 전)
- **조건 (사용자)**: BTC 만, 롱(업비트 v20.9.28, #118 동일 153건 7.383배) 우선 — 숏은 롱 무포지션일 때만, 롱 진입 봉 종가에 숏 청산. `core/short_sim.py` opt-in `force_exit` 추가 (백업 `.bak.pre_121`, 회귀 B/C 1.614/1.756 일치). 청산 = 기존 숏 C (−1.5ATR 전량 익절, 추세당 1회). `bt_121_short_ema_entry.py`.
- **사전 기준**: 숏 단독 ① 20-21·22-26 >1 ② 최대 거래 제외 >1 ③ 비용 2배 >1 ④ N≥20 ⑤ 같은 자금 합산 2020~·2022~ 모두 CAGR > 롱 +0.5%p AND MDD ≤ 롱 +1%p (롱 단독 2020~ +33.83% / 29.7, 2022~ +22.34% / 20.0).
- **①~④ 통과 (8개)**: EMA50<200 전환 1.828 (MDD 13.0, N 35, 승률 86%, PF 3.79, 손실 연도 0) · EMA50<100 전환 1.404 (15.6) · EMA21<100 전환 1.274 · EMA21<50 상태 1.634 · 기울기 EMA200(1봉) 상태 2.413 (MDD 38.8, N 483) · 기울기 EMA100(6봉) 상태 2.397 (42.0) · 참고 EMA21<50 −1% 상태 1.861 / 전환 1.721.
- **⑤ 합산**: 2020~ CAGR +4.8 ~ +18.3%p 개선, 그러나 2022~ MDD 가 롱 20.0 → 21.4 ~ 32.2 로 전부 +1%p 초과. EMA50<200 전환: 2020~ +46.12% (+12.3%p) MDD 28.6 (−1.1) / 2022~ +30.95% (+8.6%p) MDD 28.6 (+8.6).
- **경향**: 기울기는 느린 선(100·200)만 유효, 21·50 기울기 전부 실패. 교차는 느린 쌍일수록 전환(데드크로스 봉) 신호가 좋고 상태 신호는 나쁨 (EMA100<200 상태 0.740). 30개 비교 → 다중 비교 주의.
- 결과 `results/bt_121_short_ema_entry.log` / `.csv`, 롱 거래 `bt_121_long_trades.csv`.

## 2026-11-18 #120: 숏 진입 3종 × 일봉 EMA200 필터 × 빠른 익절 — 🟡 진입1(EMA21<EMA50 −1%) 만 통과, 2a·2b 전멸 (탐색, 독립 검증 전)
- **설정**: `bt_120_short_filter_tp.py`, core/short_sim.py 옵션만 (시뮬 무변경). 청산 B(−1.5ATR 전량 익절·재진입) / C(같은 익절, 추세당 1회). 필터 = 직전 일봉 종가 < 일봉 EMA200. 사전 기준 ① 20-21·22-26 둘 다 >1 ② 최대 거래 제외 >1 ③ 비용 2배 >1 ④ N≥20.
- **진입1 (EMA50−EMA21 ≥ 1%)**: 6/8 통과. 상태+C 1.865 (CAGR +9.5%, MDD 38.8, N 142) · 상태+필터+C 1.551 (+6.6%, 23.1, 82) · 전환+C 1.581 (+6.9%, 34.7) · 전환+B 1.305 · 전환+필터+B 1.273 (MDD 18.2) · **전환+필터+C 1.359 (+4.6%, MDD 11.4, PF 1.67, N 36, 손실 연도 0)**. 상태+B 0.501 / 상태+필터+B 1.133 은 미통과.
- **진입2a·2b (200 이평 하락 전환)**: 16개 전부 미통과 (상태 0.15~0.66, 전환 0.73~1.06). 필터를 붙여도 개선 없음. 필터만 상태 진입은 0.13~0.16 (필터 자체는 신호 아님).
- **참고**: 기존 변형 5 + B/C 1.614 / 1.756, 숏D 진입 + C 1.786 (2022~ 성적으로 고른 것).
- **해석**: 청산을 빠른 익절로 바꾸자 진입1 이 #119 (0.33 / 1.09) → 1.27 ~ 1.87 로 살아남 → 숏의 핵심은 청산. C(추세당 1회) 가 B 보다 대체로 우위.
- **한계**: 24 조합 비교 (다중 비교), 진입1 문턱 1%·EMA50 이웃값 미시험, 잡음·ETH 교차 미시험, 2020 년 전환 신호 −30% (필터 없을 때). 결과 `results/bt_120_short_filter_tp.log` / `.csv`.

## 2026-11-18 #119: 숏 진입 2종 (사용자 지정) × 현물 손절 거울상 — 🔴 후보 0 (탐색, 독립 검증 전)
- **설정**: `bt_119_short_entry_mirror.py` + 신규 `core/short_mirror.py` (현물 v20.9.28 손절 숏 거울상: 초기 max(+2.5ATR, +5%) / 계단 TP −1.5ATR 간격, 계단선 TP×1.03 4H 종가 판정 / 비상 ×1.08 / 트레일 min(최저+3.5ATR, 최저×1.05, 진입×1.05) 3봉 유예 / 진입 ATR 고정). 피라미딩·부분익절 미반영. 시뮬 확인: 손절 끄고 flip 만 두면 short_sim 과 최종 1.274502 · N 28 정확 일치. Binance BTC 무기한 4H, 비용 0.08% + 펀딩, 레버리지 1배.
- **진입**: 1) (EMA50−EMA21)/EMA50 ≥ 1% / 2a) 4H SMA200 6봉 기울기 하락 / 2b) 일봉 SMA200 전일 대비 하락. 각각 상태·전환 신호, 정배열 청산 추가판. 참고: 숏A·숏D 진입에 같은 손절.
- **결과 (2020-01~2026-11 전체 최종)**: 진입1 상태 0.329 / 전환 1.091 · 2a 상태 0.676 / 전환 0.884 (+정배열 청산 1.024) · 2b 상태 0.328 / 전환 0.999 · 숏A 0.664 (기존 손절 1.106) · 숏D 0.589 (기존 2.009). 사전 기준 ①②③ 모두 통과 0개. 상태 신호는 상승장 연도 대부분 손실.
- **원인**: 청산의 약 80% 가 트레일링 (진입1 상태 261/309). 현물 손절 구조(크게 먹을 때까지 들고 가기)는 숏에서 반등 흔들림에 반복 손절. 같은 진입에서도 기존 숏 청산(1.5ATR 익절)보다 크게 열세 → 숏은 손절보다 "빨리 이익 확정" 쪽이 맞다는 #108/#109 결과와 일치.
- 결과 `results/bt_119_short_entry_mirror.log` / `.csv`.

## 2026-11-18 #118: 선물 롱 + 숏 재시험 (v20.9.28 기준) — 🔴 기각 유지, 사전 기준 0/4 (독립 검증 완료)
- **목적**: #113 은 기준이 v20.9.27 이전(+18.90%)이고 선물 롱 최고안 L2 는 트레일 느슨화 섞임 → 양쪽을 v20.9.28 규칙(계단 손절 4H 종가 + 비상 −8% + 보유 중 운영 방식 전환)으로 다시. 숏 4개는 고를 때 안 본 2020~2021 에서도 확인. `bt_118_perp_ls_v28.py`, 시뮬 무변경 (회귀 5세계 PASS). 재현: 업비트 "v27 전환 끔" 2.319 / 선물 1.274 = #113 과 동일.
- **기준 S (업비트 현물 v20.9.28)**: 2022~ 2.652배 / +22.22% / MDD 20.0 (v27 전환 끔 2.319 / +18.90 / 25.3) · 2020~ 7.383 / +33.83% / 29.7. 최대 거래(2024-01-28 +31.2%) 제외 1.958.
- **선물 롱 v20.9.28 단독**: 2022~ 1.405배 / +7.25% / MDD 34.4 (S −15.0%p) · 2020~ +13.87% / 43.3 (S −20.0%p). v28 효과 선물에선 작음 (1.274 → 1.405, MDD 29.6 → 34.4 악화).
- **롱 + 숏 (30 / 50%)**: 2022~ +9.5 ~ +12.5% (S 대비 −9.7 ~ −12.8%p), MDD 25.7 ~ 31.5 · 2020~ +15.0 ~ +20.4% (S −13.4 ~ −18.8%p). 숏 효과 자체는 선물 롱 대비 +2.2 ~ +5.3%p.
- **숏 2020~2021 (선택에 안 쓴 기간) 단독**: A 0.866 (손실) / B 1.083 / C 1.143 / D 1.355. 숏 B·C·D 는 표본 밖에서도 이익.
- **판정**: ①~⑦ 모두 0/4 → 기각 유지. 원인은 숏이 아니라 선물 롱 (#111 과 같은 구조로 추정 — 단순 보유 차이는 작음 1.730 vs 1.618, 격차는 손절→재진입 경로).
- **검증 (verifier)**: 14개 롱 곡선·숏 A/B 결합 독립 재계산 전부 일치. 2020 설정 문제 2건 (선물 4H 데이터 2019-09 시작 → gap200 이 2020-03-28 전 비어 숏 A/B/C 2020-03 폭락 구간 신호 없음, 보정 시 숏A ⑤ 0.903 여전히 미통과 / 선물 1H 하위 봉 2021-01 부터) — 결론 영향 없음. 참고: 업비트 v28 롱에 같은 숏을 붙이는 가정(운용 불가)은 +2.5 ~ +6.0%p → "숏 무가치" 결론은 아님.
- 결과 `results/bt_118_perp_ls_v28.log` / `.csv`, 곡선 `bt_118_eq_*.csv`.

## 2026-11-17 #117: T3(계단 손절만 4H 종가 판정) 비상 손절 폭 비교 + 횡보 진입만 좁게 — 🟡 사전 기준 통과 후보 없음 → 비상 −8% 유지 (잠정, 독립 검증 전)
- **방법**: `bt_117_disaster_width.py`. 업비트 현물 2020-01 ~ 2026-11-11, 새 기준 B·MDD만, **운영 방식 전환 켬(현재 production 동작)**. 시뮬 opt-in `disaster_stop_pct_range` 추가 (Range·range_new 진입만 다른 폭, 백업 `core/simulator.py.bak.pre_117`, 회귀 5세계 PASS). 비상 손절 = 계단 손절선 대비 −X% 봉내 접촉 시 즉시.
- **사전 기준** (기준 = T3+−8%): (a) CAGR −1.0%p 이내 (b) 자기 최대 거래 제외 후 현행 대비 우위 (c) 급락 봉(시가→종가 하위 20) 맞은 거래 손익 합 ≥ T3+−8%.
- **결과** (최종 배수 / CAGR / MDD / 자기 최대 제외): 현행 4.625 / +25.01% / 29.2 / 3.608 · **T3+−8% 7.383 / +33.83% / 29.7 / 5.451** · −5% 6.905 / +32.53% · −4% 6.793 / +32.21% · −3% 6.718 / +32.00% · 횡보만 −4% = 전체 −4% (동일) · 횡보만 −3% = 전체 −3% · 횡보만 −2% 6.313 / +30.81% / 29.1. 최악 거래 전 변형 −6.7% (초기 손절 구간), 계단손절 최악 현행 −3.0% / T3 −3.8% / 횡보 −2% −4.1%.
- **급락 봉 (시가→종가 하위 20)**: 보유 중 맞은 거래 현행 3건 합 −11.5% / T3 전 변형 2건 −6.4% (2021-05-13 −9.4% 봉은 T3 무포지션). 계단 손절 상태에서 맞은 사례 1건: 2023-03-23 (−6.1%, Lv1) 현행 −1.2% / T3 −2.2% (종가 대기 비용 −1.0%p).
- **판정**: 좁힌 폭 전부 (a) 미달 (−1.3 ~ −3.0%p). 좁은 비상 손절은 봉내 꼬리(종가는 회복)에서 팔려 비용만 발생, 급락 봉 손익은 개선 없음. 비상 손절 발동은 전부 횡보 진입 포지션(추세 진입은 트레일링이 먼저 걸림). → **T3 + 비상 −8% 유지**. 한계: 급락 봉을 계단 손절 고비중으로 맞은 표본 1건, 잡음·비용 2배 미실시.

## 2026-11-17 #116: 보유 중 Regime 전환에 따른 운영 방식 변경 (production `_check_regime_switch`) 효과 — 🟡 전환 있음이 −2.5 ~ −3.8%p 열세 (누수 수정 후), 소수 큰 추세 구간 의존 → 연구 후보. T3 우위는 두 세계 모두 유지 (독립 검증 완료)
- **실거래 조사** (btc_bot.log 2026-04-19~ / btc_trade.csv, 12거래): 8거래에서 전환 37회 (한 거래 최대 14회). 주문이 달라진 건 2회 — 04-07, 09-21: 전환 순간 가격이 TP1·TP2 위라 부분익절 2건이 1분 안에 연속 체결(약 50% 매도), 09-21 은 2.5시간 뒤 Trend_Up 복귀로 밀린 단계 일괄 처리 → 1,143,725원(자산 약 46%) 재매수. v20.9.23 외부입금 오탐의 원인 거래. 나머지 전환은 TP 도달 전 손절돼 주문 무영향.
- **production 방식별 규칙**: Trend_Up = 계단 손절 + 추가매수 / Range(전환) = TP1(+1.8ATR) 25% 매도 + 손절선을 본전으로 **덮어씀**(max 아님 — 계단선이 더 높았어도 내려감) / Volatile·Trend_Down = TP1·TP2 부분익절(ADX≥30: 25%+25%, 아니면 40%+40%), 계단 손절 인상 중단 / Range 진입(range_new)은 전환 없음.
- **방법**: 시뮬 opt-in `mode_switch_prod` (하위 봉 경로, 백업 `core/simulator.py.bak.pre_116`, 회귀 5세계 PASS, 옵션 끔 = 23,189,386 불변). `bt_116_mode_switch.py 2022|2020`. 한계: 봉 단위 근사(30초 떨림 미재현), Volatile 진입 포지션 전환 미모델.
- **2022-01~** (최종 / CAGR / MDD / 자기 최대 제외): 전환 없음 2.319 / +18.90% / 25.3 / 1.948 · 전환 있음 2.148 / +17.03% / 24.2 / 1.862 (연도 −15/+39/+49/+24/−2, RECOV +38 → +28) · T3 전환 없음 2.844 / 21.2 / 2.050 · T3 전환 있음 2.825 / +23.82% / 19.9 / 2.056.
- **2020-01~**: 전환 없음 5.309 / +27.55% / 29.4 / 4.142 · 전환 있음 5.019 / +26.51% / 29.6 / 3.916 · T3 전환 없음 8.022 · T3 전환 있음 7.871 / +35.08% / 30.2 / 5.728.
- **사전 판정**: (a) 전환 있음이 CAGR −1.86 / −1.04%p, 자기 최대 제외도 열세(−0.086 / −0.226) → "진입 방식 유지"로 production 을 맞추는 안이 제안 후보. (b) T3 − 기준은 전환 있는 세계에서도 +6.79 / +8.57%p (제외 +0.194 / +1.812) → T3 유지.
- **의미**: 지금까지의 백테스트(전환 없음)는 실제 봇보다 연 1~2%p 낙관적일 수 있음 (근사 모델 기준). 전환을 없애면 실제 봇이 백테스트와 같아지고, 부분익절 연속 체결·일괄 재매수 같은 비의도 주문도 사라짐.
- 결과 `results/bt_116_mode_switch_{2022,2020}.log` / `.csv`.

- **⚠️ 검증 정정 (verifier, 2026-11-17) + 재실행**: 위 1차 수치(−1.86 / −1.04%p)는 **구현 누수**가 있던 값 — 전환된 방식에서도 4H 종가 계단·추가매수 루프가 실행됨. 게이트 추가 후 재실행 (회귀 PASS, 옵션 끔 23,189,386 불변):
  - 2022-01~: 전환 없음 2.319 / +18.90% / 25.3 → **전환 있음 1.977 / +15.06% / 24.2** (−3.83%p, 자기 최대 제외 1.948 → 1.714, 연도 −15/+38/+38/+24/−2, 대박 9 → 6건). T3·전환 있음 2.652 / +22.22% / 20.0 (기준 대비 +7.16%p, 제외 +0.243).
  - 2020-01~: 전환 없음 5.309 / +27.55% → **전환 있음 4.625 / +25.01% / 29.2** (−2.54%p, 제외 4.142 → 3.608). T3·전환 있음 7.383 / +33.83% / 29.7 (+8.82%p, 제외 +1.843).
  - 잡음 12시드 (verifier, 엄격 구현): 전환 있음 − 없음 음수 11/12, 중앙 −1.97%p (범위 −4.04 ~ +3.10). 손해는 큰 추세 3구간(2023-01, 2024-01~02)에 집중 — 3구간을 양쪽에서 막으면 −0.59 / −0.16%p 로 거의 소멸. 4구간 중 전환 제거 쪽이 3/4 비악화 (BEAR 만 −1.1%p).
  - 실거래 정정: 전환이 일어난 거래는 12거래 중 **7거래**(Trend_Up 진입 전부), 주문이 달라진 건 **1회 (09-21)**. 04-07 부분익절은 전환이 아니라 v18.3 → v18.4 재시작 직후 발생. 09-21 재매수 실제 가격은 약 114.87M (기록 112.46M 은 잔고 근사) → 매도가보다 +0.5% 비싸게 되삼, 자산 영향 약 −0.3% (추정).
  - breakeven 의 손절 본전 덮어쓰기: 코드상 사실이나 실거래·시뮬 모두 손절선이 실제로 내려간 사례 0건.
  - 남은 불일치: 봉 중간 Volatile 전환(실거래 전환 37회 중 20회)은 봉 단위 시뮬이 못 잡음 — 실제 값은 1차(−1.9)와 수정(−3.8) 사이로 추정 / 전환 시 `pyramid_level` 재산정(잔액 투입 조건) 미모델 (영향 작음).
- **정정된 판정**: 전환 제거("진입 방식 유지")가 유리하다는 방향은 일관 (시드 11/12, 4구간 3/4). 크기는 −1 ~ −4%p 로 모델 의존, 큰 추세 3구간 의존 → **연구 후보**. T3 는 전환 유무와 무관하게 유지. 지금까지의 백테스트(전환 없음)는 실제 봇보다 낙관적일 가능성.
## 2026-11-17 #115: 손절 종가 판정안 급락 스트레스 (업비트 현물, 2020-01 ~ 2026-11) — 🟡 "계단 손절만 4H 종가"(T3)만 사전 기준 통과 → 검증 후: 수익 우위는 견고, 낙폭 기준 통과는 Kill Switch 의존 — 조건부 후보
- **방법**: `bt_115_stop_stress.py`. 데이터 `upbit_4h_2019.csv` / `upbit_1h_2020.csv` (`fetch_upbit_ext.py`, 공개 시세). 새 기준 B·MDD만, 시작일만 2020-01 로 당김 (XGB 는 2022 이전 전체 학습 — gate 꺼짐·사이징 미세 영향). 2022 이후 수치는 시작 자산·KS 상태가 달라 #114 와 같지 않음.
- **전체 7년** (최종 배수 / CAGR / MDD / 최악 거래 / 2020~21 수익률·MDD / 자기 최대 거래 제외): 기준 5.309 / +27.55% / 29.4 / −6.7% / +128.8%·28.0 / 4.142 · T5 계단+트레일 8.376 / +36.31% / 31.5 / −6.7% / +186.0%·31.5 / 5.805 · T5+비상 −8% 8.263 / 32.4 / 최악 −9.4% · T5+비상 −5% 7.704 · **T3 계단만 8.022 / +35.46% / 29.9 / −6.7% / +180.8%·29.9 / 5.783** · T3+비상 −8% = T3 (한 번도 안 걸림) · T1 전부 8.075 / MDD 33.3 / 최악 −9.5% · T1+비상 −8% 5.955 (최악 −11.9%, 제외 시 기준 미만).
- **연도** 기준 +146 / −7 / −16 / +49 / +53 / +23 / −1 → T3 +156 / +10 / −12 / +34 / +85 / +18 / +11 (2023·2025 악화, 나머지 5개 연도 개선). 7년으로 넓히면 자기 최대 거래 제외 우위가 +1.64배로 커짐 (#114 의 "2024 의존" 약점 완화 — 2021 도 개선).
- **급락 봉** (4H 시가→저가 하위 15개): 보유 중 맞은 건 4건뿐 (나머지 11개는 전 변형 무포지션 — 2020-03, 2021-05-19 포함). 그 거래 손익 합: 기준 −14.8% / T5 +4.7% / T5+비상 −0.3% / T3+비상 +9.5% / T1+비상 −32.0%. 2024-12-03 (업비트 저가 −33%, 종가 0%): 기준 −3.0% (손절선 가격 체결 가정 — 실제로는 더 나빴을 것) / T5 −5.3% / T3 −3.0%. 2021-04-07 (저가 −10.6%, Lv1): 기준 −1.5% / T3 −3.0% / T5 −4.4% / T5+비상 −9.4% (비상 손절이 꼬리 바닥에서 체결 → 더 나쁨).
- **사전 판정**: T3(+비상 −8%) ①②③④ 통과. T5 는 MDD 악화(전체 +2.1, 2020~21 +3.5)로 ①② 미달. T1 계열 미통과.
- **읽기**: 계단 손절만 종가로 바꾸고 초기 손절·트레일은 30초 판정 유지(T3)가 낙폭을 거의 안 늘리면서 이득 대부분을 가져감. 비상 손절은 T3 에선 불필요(무발동), T5·T1 에선 꼬리 바닥 체결로 손해. 한계: 급락 봉을 TP1 이후 고비중으로 맞은 사례는 여전히 1~2건, 봉내 손절 체결가는 손절선 가격 가정(기준에 유리), 독립 검증 전.
- 결과 `results/bt_115_stop_stress.log` / `.csv`.

- **⚠️ 검증 (verifier, 2026-11-17)**: 수치 전부 재현, 확장 데이터 품질 문제 없음 (덧붙인 구간 4H 결손 0, 1H 결손 21봉, 폴백 18봉/4,386봉), 시작일 당김 왜곡 없음 (2022 이후 거래는 #114 와 완전 동일). 수익 우위는 잡음 12/12 (자기 최대 1·2건 제외도 12/12), 비용 2배 2.544 → 4.097, 보수적 체결(min(손절선, 1H 종가)) 3.737 → 6.300 에서 유지. 정정:
  - **"낙폭 거의 불변"은 Kill Switch 의존**: T3 는 2021-05-05 롤링 MDD 20.2% 로 KS 발동 → 47일 정지해 5월 급락을 쉼 (기준은 0회). KS 끄면 T3 7.716배 / MDD 32.6 (기준 +3.2%p). 잡음 시드에서 낙폭 기준 통과 6/12. → "사전 기준 통과"는 원본 경로에서만.
  - **급락 봉 합계 차(−14.8 vs +9.5)는 손절 방식과 무관한 두 거래**(KS 정지로 빠진 −6.2%, 기준이 먼저 청산한 +19.7%)에서 나옴. 같이 맞은 3건은 T3 가 같거나 나쁨 (−3.0/−3.0, −4.2/−4.2, −1.5/−3.0). 급락 스트레스의 실질 표본은 1건.
  - **"7년 확장으로 2024 의존 완화"는 과장**: 새 증거는 2020~21 뿐이고 그 이득은 2021-02-15 진입 한 건 (T3 +20.0% vs 기준 +2.6%) 에 집중. 같은 구간을 양쪽에 막는 방식의 제외: 1건 3.097 → 4.626, 2~3건 2.251 → 3.080, 4건 1.968 → 2.196, 5건 1.512 → 1.578. T3 가 이긴 달 24 / 진 달 36.
  - **Range 진입은 TP1 이후 봉내 손절이 전혀 없음** (트레일링이 원래 없어서): T3 청산의 31% (48건), 평균 비중 0.95, 봉내 최대 이탈 −5.7%. Trend_Up 진입은 트레일선이 약 2% 아래 백스톱으로 작동. 2020-03 형 봉(종가 −15%)을 이 상태로 맞은 사례 없음.
  - 비상 손절 −8% 는 표본 내 무발동 = 무비용 보험 ("불필요"가 아님). −5% 7.502, −3% 7.299.
  - 4구간 (2022~2026): −16/+38/+124/−11 → −12/+25/+161/−1, 3/4 비악화 (RECOV −13%p). 2023·2025 는 시드 10/12 에서 악화. T5 보다 T3 가 낫다는 것은 지지 (T5 MDD 중앙 +2.9).
- **정정된 판정**: T3 는 CLAUDE.md 채택 조건(절대수익·4구간 3/4·최대 1건 제외 우위)을 수익 쪽에서 충족. 낙폭은 KS 꺼짐·잡음에서 +3%p 안팎 악화 가능, Range 고비중 무손절 꼬리 위험 미시험 → **조건부 후보: "T3 + 비상 손절 −8%" 형태로, 위 약점을 명시해 승인 요청.**
## 2026-11-17 #114: 손절 규칙별 판정 방식 (봉내 접촉 vs 종가) + 간격 넓히기 + 비상 손절 — 🟡 "계단·트레일만 4H 종가 판정"(T5)이 두 세계 모두 기준 충족 → 검증 후: 방향은 견고, 업비트 우위는 2024년 두 거래 의존 — 연구 후보 (채택 권고 아님)
- **production 손절 확인** (`btc_bot_v290.py`): 초기 = min(진입가 −2.5ATR, −5%) / 계단 = 도달 TP × 0.97 (B2) / 트레일 = max(고점 − 3.5·4.5ATR, 고점 −5%, 진입가 −5%) (3봉 이후, Range 진입은 없음) → 30초마다 현재가 ≤ 손절선이면 즉시 전량 매도 (`_check_hard_stop`). 손절 유예(3봉)는 초기 손절이 더 낮아 사실상 미작동.
- **방법**: `bt_114_stop_rules.py upbit|perp`. 시뮬 opt-in `stop_close_tf` / `stop_close_rules` / `disaster_stop_pct` (하위 봉 경로 전용, 백업 `core/simulator.py.bak.pre_114`, 회귀 5세계 PASS). 종가 판정 = 4H 마지막 1H 봉 종가 ≤ 손절선이면 그 종가에 체결. 자기 최대 기여 거래 제외 병기. 기존 B0 세계는 원래 종가 손절이라 해당 없음.
- **업비트 현물** (새 기준 B·MDD만, 기준 2.319배 / +18.89% / MDD 25.3 / N 116 / 최악 거래 −6.2% / 자기 최대 제외 1.948): T1 전부 종가 3.148 / +26.60% / 23.9 / 최악 −8.1% / 제외 2.182 · T2 초기만 2.318 (변화 없음) · **T3 계단만 2.844 / +23.99% / 21.2 / 제외 2.050** · T4 트레일만 2.318 (MDD 22.7) · **T5 계단+트레일 2.919 / +24.65% / 23.7 / 최악 −6.2% / 제외 2.023** · T6 전부 1H 종가 2.545 (최악 −12.7%, 제외 1.792 ↓) · W1 계단 5% 2.462 (제외 ↓) · W2 계단 7% MDD 50.3 · W3·W4 트레일 7·10% ±0.4%p · W5 2.671 (제외 ↓) · D1~D3 T1+비상 손절 2·3·5% 2.698 / 2.724 / 2.831 (제외 −0.08 / −0.06 / +0.01). 4구간 비악화 T1·T3·T5 3/4 (RECOV 악화: +38 → +25~26), 연도는 2023·2025 악화, 2024 +52 → +85~109.
- **BTC 선물** (기준 1.274 / +5.11% / 29.6 / 제외 1.036): T1 1.869 (MDD +1.5) · T2 1.551 · T3 1.509 (MDD +2.2) · T4 1.217 · **T5 1.752 / +12.23% / 30.4 / 제외 1.433** · T6 1.698 · W1 1.518 · W2 1.643 · W5 1.772 · D1~D3 1.745 / 1.740 / 1.784.
- **읽기**: ① 수익을 깎는 것은 계단 손절(TP × 0.97)의 봉내 접촉 판정. 업비트에서 초기·트레일 단독은 효과 0. ② 간격 넓히기는 종가 판정을 대체하지 못함 (업비트에서 최대 거래 제외 시 열세, 7% 는 MDD 폭증). ③ 비상 손절을 붙이면 이득이 줄고(업비트 +7.7 → +3.8~5.0%p) 최악 거래도 안 줄어듦 — 최악 손실은 초기 손절 구간에서 나오므로 T5(초기 손절은 봉내 유지)가 같은 목적을 더 싸게 달성.
- **사전 기준**: 두 세계 모두 통과 = T5 뿐. T1·T3 은 업비트 통과·선물 MDD 초과. 이웃(T3, T1) 부호 동일.
- **한계**: 업비트 개선이 2024 한 해에 집중 (자기 최대 제외 우위 +0.07 ~ +0.23 로 얇음), 2023·2025 는 악화. T1 크기는 모델에 따라 3.15 (이 구현, 1H 고가로 TP 감지) ~ 3.65 (#112 검증, 4H 경로). 이익 구간의 급락 꼬리(수익 반납) 표본 부족. production 변경은 로직 변경 프로토콜 — verifier + 사용자 승인 전 변경 없음.
- 결과 `results/bt_114_stop_rules_{upbit,perp}.log` / `.csv`.

- **⚠️ 검증 (verifier, 2026-11-17)**: 수치 전부 재현, opt-in 구현 결함 없음 (기본값에서 거래·자산곡선 완전 일치, 종가 청산은 전부 4H 마지막 1H 봉 종가 체결, 미래 정보·중복 청산 없음). 정정·보강:
  - 잡음 20시드: 업비트 T5−기준 18/20 양수 (중앙 +0.55), 선물 12/12 → 방향 견고. 그러나 **자기 최대 1건 제외 시 업비트 12/20, 중앙 +0.03 (동전 던지기)**, 2건 제외 시 1.657 → 1.584 역전. 업비트 우위는 2024-01~03 (+44.4%)·2024-11 (+27.8%) 두 거래 의존. 선물은 제외 후에도 12/12.
  - "원금 쪽 꼬리 위험은 현행과 같음"은 부분만 맞음: TP1 이후에는 봉내 손절선이 전혀 없음 (비중 85~100%), lv0·3봉 이후엔 트레일선이 종가 판정으로 바뀌어 같은 거래가 −2.96% → −5.30% 인 사례. lv1+ 거래 최악 −2.67% → −4.37% (업비트).
  - "계단 손절이 원인"·"간격 넓히기는 대체 불가"는 업비트 한정. 선물은 T2 초기만 1.551 ≥ T3 1.509, W5 1.772 ≥ T5 1.752.
  - T5 와 T3 는 구분 불가 (시드 11/20, 비용 2배에선 T3 1.843 > T5 1.816). 두 세계는 같은 가격 경로라 독립 표본 아님.
  - 위험 (T5): 종가 청산 76/94건, 손절선 대비 초과 하락 평균 −0.64%, 최악 −3.25%, 합 −48.3%p. 시험 기간 최악 4H 10봉 중 보유한 봉 1개뿐 → TP1 이후 큰 급락 봉은 미시험. 비상 손절 −8% 는 표본에서 한 번도 안 걸려 비용 0 (−5% 2.860, −3% 2.743).
  - production 구현: `status["stop_loss"]` 하나에 초기·트레일·계단이 합쳐져 있어 분리 저장 필요 (status 스키마·복원·표시), 새 캔들 판정 시점·청산 직후 재진입 차단·봇 중단 시 규칙 필요. 실거래 하드스톱 13건 중 11건은 그 봉 종가가 체결가보다 높았으나(같은 방향), 거친 역산으로는 이득 증거 없음.
- **정정된 판정**: 봉내 접촉 → 4H 종가 판정 방향은 잡음·비용에 견고. 업비트 우위 크기는 2024년 두 거래 의존으로 불확실, TP1 이후 꼬리 위험 미검증 → **연구 후보**. 승인 요청 전 필요: 2020~2021 급락 봉 포함 스트레스 시험 / 비상 손절(−8%) 포함안 / production 설계안.
## 2026-11-17 #113: BTC 선물 한 계좌 롱 + 숏 같이 운영 — 🟡 롱이 종가 경로일 때만 현재 방식 초과, 사전 기준 ④ 미충족 (탐색, 독립 검증 전)
- **범위**: BTC 만, 롱·숏 같은 증거금 (사용자 지정). `bt_113_perp_long_short.py`. 비용 편도 0.08% + 펀딩, 2022-01 ~ 2026-11-11, USDT 기준. 비교 기준 = 업비트 현물 롱 단독 CAGR +18.90% / MDD 25.3%.
- **롱 단독**: L0 현 규칙 1.274 / +5.11% / 29.6 · L1 초기 손절 3.0ATR 1.536 / +9.23% / 29.4 · L2 종가 경로(D) 2.390 / +19.64% / 26.2.
- **롱 + 숏** (숏 크기 30 / 50%, 숏 후보 4개 범위): L0 +7.3 ~ +10.3% (MDD 23.0 ~ 28.2) · L1 +11.5 ~ +14.6% (23.4 ~ 28.7) · L2 +22.1 ~ +25.5% (23.8 ~ 27.3). 숏 100%: L0 +10.6 ~ +14.8 / L1 +14.9 ~ +19.3 / L2 +25.8 ~ +30.7% (MDD 28.0 ~ 33.4).
- **숏을 붙인 효과** (같은 롱 단독 대비): 30% +2.2 ~ +3.7%p, 50% +3.4 ~ +5.9%p, MDD 는 숏B·C 에서 −2.4 ~ −6.6%p. 롱·숏 수익률 상관 ≈ 0. 효과는 주로 2022년 (L2: −14% → −4 ~ +9%), 2025년은 악화.
- **사전 기준**: L0·L1 통과 0/4. L2 는 숏B·숏C 2/4 통과 (숏A 는 2022 제외 미달, 숏D 는 50% 에서 MDD 초과) → ④ 미충족.
- **한계**: L2 는 트레일 느슨화가 섞인 낙관적 값 (순수 종가 판정 1.72배 기준이면 합산은 더 낮음 — 미계산). 숏 후보는 같은 기간 성적으로 고른 것. 같은 손절 변경을 업비트 현물에 적용하면 롱 단독 +30.5% (#112 검증) → "선물로 옮겨 같이 운영"의 순이득은 여전히 미확인. 청산·증거금 모델 없음.
- 결과 `results/bt_113_long_short.log` / `.csv`.

## 2026-11-17 #112: 선물용 롱 백테스터 + 변동성 보완책 13종 — 🟡 "종가 기준 손절"만 큰 개선 (탐색, 독립 검증 전)
- **러너**: `perp_bt.py` (선물용 롱 백테스터 — Binance 무기한 4H+1H, 비용 편도 0.08%, 실제 펀딩 사후 차감, 김프 사이징 끔, `PERP_SYMBOL=BTC|ETH`). 실험 `bt_112_perp_vol.py`. 현물 시뮬·production 무변경.
- **#111 원인 분석**: 보유만 했다면 업비트 1.72배 / 선물 1.60배로 가격 차이는 작음. 대박(≥10%) 거래도 9건 vs 7건으로 비슷. 격차는 같은 추세 구간에서 업비트 32건 +54% vs 선물 61건 −16% (손절→재진입 반복). 선물 봉은 고저 폭 중앙 1.18% (업비트 0.98%), 아래 꼬리 상위 1% 2.26% (1.75%), 3봉 내 청산 7건 −28% (2건 −9%).
- **BTC 선물 결과** (최종 배수 / CAGR / MDD / N, 기준 1.274 / +5.11% / 29.6 / 148): A 초기 손절 3.0ATR 1.536 / +9.23% · 3.5ATR 1.472 / +8.28% | B 트레일 넓히기 1.259 (변화 거의 없음) | C 계단 간격 넓히기 변화 0 (옵션이 현 계단손절 구조에서 실효 없음 — 미확인) | **D 종가 기준 손절 2.390 / +19.64% / 26.2 / 94** (최대 거래 제외 1.947 vs 기준 1.036, 3봉 내 청산 0건, 평균 보유 27 → 51봉) | E 손절 뒤 쉬기·재진입 금지 1.303 ~ 1.425 | F 전부 넓히기 1.455 ~ 1.518.
- **ETH 선물 교차 확인** (4H 봉내 손절, 기준 0.746): A −1.5 ~ −2.8%p, E −0.2 ~ −2.8%p, F −1.5 ~ −2.8%p (전부 악화) / D 0.810 (+1.6%p, 단 MDD 35.5 → 42.5, 비악화 연도 2/5).
- **판정**: A·E·F 는 BTC 에서만 개선, ETH 에서 악화 → 기준 ⑤ 미충족 (BTC 과적합 가능성). D 는 BTC ①②③ 충족·ETH 최종은 개선이나 MDD 악화, 이웃 값 없음(④ 미확인) → **유력 후보, 미확정**. ETH 는 이 전략으로 어떤 손절 방식에서도 손실.
- **D 의 주의점**: 봉 중간 급락에 무방비 (4시간 종가까지 손절 없음) → 레버리지 사용 시 청산 위험, 시뮬은 과거에 발생한 갭만 반영. 1시간 종가 손절 같은 중간안 미시험. 업비트 현물에서도 종가 손절 시뮬(기존 B0)이 봉내 손절(새 기준 B)보다 높게 나오던 것과 같은 방향 — "봉내 손절이 수익을 깎는다"는 가설로 `improvement_todo.md` `#112_CLOSE_STOP` 등재.
- 결과 `results/bt_112_perp_vol_{BTC,ETH}.log` / `.csv`.

- **⚠️ 검증 정정 (verifier, 2026-11-17)**: 수치는 전부 재현. 그러나 D(`close_stop=True`)는 판정 시점만 바꾼 것이 아님 — 종가 판정 + 트레일 고점 고가→종가 + 진입 후 3봉 유예 + 계단 TP 감지 4H 종가. **판정 시점만 바꾼 순수 효과 = 1.274 → 1.724배 (CAGR 약 +11.9%, MDD 25.9, N 100)**, 나머지 +0.63 은 트레일 느슨화. 위의 "최대 거래 제외 1.947" 과 ETH "0.810 (+0.237)" 은 제외 방법 결함(기준의 최대 거래 구간을 씌움) → 자기 최대 거래 제외 시 D 1.670 / 순수 1.292 (기준 1.036), ETH +0.030 뿐. B·C 는 옵션이 현 설정에서 실효 없음(B: 5% 트레일이 항상 지배, C: B2 계단손절은 `step_stop_offset_pct` 사용) → 사실상 미시험.
- **견고성 (verifier)**: 잡음 20시드 D−기준 20/20 양수 (+0.75 ~ +1.58), 순수 종가−기준 20/20 (+0.32 ~ +1.11), 비용 2배 D 2.172 vs 기준 1.050. 1H 종가 중간안 1.698 (MDD 32.1, 효과 약함 — 이득은 4시간 기다림에서 나옴). 위험: 최악 거래 −8.17% (기준 −5.73%), 손절선 초과 손실 합 −68.6%p, 보유 중 최대 역행 −10.9% (2~5배 청산선 미도달, 10배 1건). 급락 봉 최악 5개 중 1개만 경험 → 꼬리 위험 미검증.
- **업비트 현물에서도 같은 방향 (verifier)**: 새 기준 B 23,189,386 → 순수 4H 종가 36,479,265 (CAGR +30.5%, MDD 21.5, N 79) / D 동일 변경 37,473,814. 2024-01 한 거래에 개선 집중(제외해도 +5.07M). 1H 종가는 +2.26M 이나 자기 최대 거래 제외 시 −1.57M. → 선물 고유 문제가 아니라 "봉내 손절 vs 종가 손절" 문제.
- **정정된 판정**: 4H 종가 판정은 방향이 견고한 연구 후보, 순수 효과 약 1.27 → 1.72배, 꼬리 위험 미검증. A·E·F 는 ETH 에서 악화 (BTC 한정 운영이면 참고만).
## 2026-11-15 #111: 롱 전략을 바이낸스 무기한 선물 봉으로 재시뮬 + 숏과 한 계좌 결합 — 🔴 기각 (사전 기준 0/4, 독립 검증 완료)
- **질문**: #110 의 "같은 자금 겹침"을 실제로 하려면 롱도 선물이어야 함 → 롱을 선물 데이터로 돌려도 우위가 남는가.
- **방법**: `bt_111_perp_long.py` (upbit | binance | combo). 시뮬 본체 그대로, 입력 봉만 교체 (`bt_99_prod_parity.py` env `BT_EXT_4H`/`BT_EXT_1H`). 새 기준 B·MDD 트리거만, 김프 사이징 끔, 펀딩 사후 차감 (`core/simulator.py` opt-in `mod["record_bar_pos"]`, 백업 `.bak.pre_111`, 회귀 5세계 PASS). 기간 2022-01 ~ 2026-11-11. production 무변경.
- **롱 단독** (최종 배수 / CAGR / MDD / N): 업비트 현물 2.319 / +18.90% / 25.3 / 116 · 업비트 김프 끔 1.924 / +14.42% / 28.3 / 113 · 선물 봉 비용 0.3% 0.887 / −2.44% / 37.5 / 139 (+펀딩 0.802) · 선물 봉 비용 0.08% 1.417 / +7.43% (+펀딩 1.274 / +5.11% / 29.6 / 148, 펀딩 합 −10.6%p). 연도 선물(0.08%+펀딩) −29/+50/+44/−14/−4 vs 업비트 −16/+50/+52/+23/−1. 보유 여부 일치 81.8%.
- **선물 롱 + 숏 겹침** (숏 크기 30~50%, 후보 4개): CAGR +7.3 ~ +10.3% → 업비트 현물 롱 단독보다 −8.6 ~ −11.6%p (선물 롱 단독 대비로는 +2.2 ~ +5.2%p). 사전 기준(① CAGR > 현물 롱 +0.5%p ② MDD ③ 3/4 후보 ④ 2022 제외) 통과 0/4.
- **검증 (verifier)**: 수치 전부 재현 (csv 바이트 일치). 주입 결함 없음 (시각 정렬·결측·일봉 경계·kp·1H 하위 봉·가격 스케일 확인). 격차 원인 = 가격 경로(김프·환율) + **거래량 패턴** (가격 업비트·거래량 선물 1.655 / 가격 선물·거래량 업비트 1.242 / 둘 다 선물 0.887). 같은 봉 진입 25건뿐 — 문턱값(vol_ratio, regime 경계, 눌림목 1.5%) 근처에서 갈림. 펀딩은 봉 내 손절 봉 누락으로 약 0.6%p 과소 (1.274 → 1.267). 선물 롱 비용 0% 로 놓아도 숏 30~50% 합산 +11.9 ~ +15.0% < 통과선 +19.4%. 업비트도 비용 0.08% 면 2.836배 → 현 비교는 선물에 유리한 조건.
- **부수 관찰**: 롱 전략 결과는 입력 데이터(가격·거래량)의 작은 차이에 민감. 가격에 작은 잡음(봉당 0.05%)을 넣은 12회에서 업비트 1.22 ~ 2.18 (원본 1.924 는 상위 25% 근처), 선물 0.72 ~ 1.12. 방향(업비트 > 선물)은 유지되나 격차 크기는 신뢰 불가. "업비트에 알파" 해석은 근거 부족. → `improvement_todo.md` `#111_DATA_SENS`.
- **판정**: 롱을 선물로 옮겨 숏과 같이 운영하는 안 기각. "못하다는 증명"이 아니라 "낫다는 증거 없음". 수치는 방향 판단용, 기대 수익률 아님. 결과 `results/bt_111_combo.log` / `bt_111_combo.csv` / `bt_111_{upbit,binance}_*.csv`.
