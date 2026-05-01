# BTC Bot 개선 작업 관리 (v2)

> 운영 중인 v20.9.x 관련 항목만 유지. 옛 내용은 `improvement_todo_v1.md` 참조.
> 완료 항목 · v19.9 실전검증 · v20.0~v20.6 관찰 · v21 E2 연구는 v1 참조.

## v20.9.10 E2 OFF 모니터링 + 사후 비교 (2026-05-02 ~)

**배포일**: 2026-05-02 04:02 KST
**변경 요약** (`btc_bot_improvement.md` v20.9.10 참조):
- `E2_ENABLED = False` (실로그 분석 #74 기반)
- 다중 EMA 일봉 로깅 (`ema100_d / ema150_d / ema200_d / ema250_d / ema300_d` + gap)
- 가상 차단 시나리오 (`virtual_e2_block_e200 / e250 / gap5`) 자동 기록
- 텔레그램 4H 리포트 / 대시보드 OFF banner
- **#75-B 자동 알림 3종**: 일손실 -3% / 누적 -5% / BTC -10% in 1주 (24h dedup)

### 1주일 (~2026-05-09)
- [ ] 매매 빈도 측정 (목표 주 3~5건)
- [ ] 누적 수익률 추적 (vs B&H)
- [ ] 일손실 -3% 도달 횟수
- [ ] 첫 진입 결과 분석 (`btc_trade.csv` + `btc_confirmed_trades.csv`)
- [ ] `btc_candle_log.csv` 새 컬럼 (다중 EMA + 가상 차단 + actual_block_reason) 정상 기록 확인

### 1개월 (~2026-06-02)
- [ ] 5월 월간 리포트 (E2 OFF 첫 달, `python btc_bot_v290.py --monthly-report 2026-05`)
- [ ] vs B&H (4월 -7.83%p 에서 개선?)
- [ ] vs 가상 E2 ON (`virtual_e2_block_e200` 컬럼 활용)
- [ ] vs 가상 EMA250 (`virtual_e2_block_e250` 컬럼 활용)
- [ ] vs 가상 gap -5% (`virtual_e2_block_gap5` 컬럼 활용)

### 3개월 (~2026-08-02) — 진짜 평가
- [ ] 표본 충분 확인 (월 10~15건 × 3 = 30~45건)
- [ ] 여러 시장 페이즈 포함 검증
- [ ] 실데이터 기반 결정:
  - **E2 OFF 유지** (수익 우위 명확 시)
  - **E2 부분 ON** (gap < -15% 큰 BEAR 만)
  - **E2 다시 ON** (BEAR 손실 큼)
  - **EMA250 적용** (가상 비교 우위 시, #70 best 결과)

### 비교 데이터 소스
- `btc_candle_log.csv`: 실거래 + 가상 시나리오 자동 기록 (v20.9.10 컬럼 13개 추가)
- `btc_trade.csv` / `btc_confirmed_trades.csv`: 정확한 매도 사유
- `btc_monthly_history.json`: 월간 누적 (B&H/Edge 자동)

### 롤백 트리거 (자동 알림 작동, #75-B)
- 일손실 -3% (`tg_error` 24h dedup, `last_alert_daily_loss`)
- 누적 손실 -5% (`tg_error` 24h dedup, `last_alert_cumulative_loss`)
- BTC -10% in 1주 (`tg_error` 24h dedup, `last_alert_btc_weekly`)
- Kill Switch 자동 발동 (기존 v20.8 로직)

### 롤백 절차 (사용자 판단)

```bash
cp /root/tradingbot/btc_bot_v290.py.bak.pre_20.9.10 \
   /root/tradingbot/btc_bot_v290.py
systemctl restart btc_bot.service
```

### 참고 백테스트
- **#70 E250 best**: CAGR +27.73%, MDD 17.63% (52mo)
- **#74 실로그 분석**: E2 차단 net edge 음수 (BULL 후반 24건 중 88.2% 수익 신호)
- **#71/#72 Hybrid/Stepped**: 영구 기각 (state machine 한계)

---

## 현재 봇 상태 (v20.9.4, 2026-04-21)

### v20.9.x 관찰 항목 (F10 + E2b+6mo 배포 이후)

- [ ] **bars_since_e2 카운터 정상 증가 + F5 flicker 시 0 리셋** (Option B flicker 정책 검증)
- [ ] **O3 발동 시 첫 예외 진입 검증** — E2b 트리거링 (40% 사이징 + pyramid_locked=True)
- [ ] **Day 1080 도달 시 (~2026-10) gap 예외 활성화 확인** — E2b+6mo 진입 조건
- [ ] **2024-2025 BULL 피크 캡처 101% 실전 재현** — F10 장점 검증
- [x] ~~**신호 로그 e2_bear_block "BUY" 표시 버그**~~ → **v20.9.4 완료** (BLOCK 표기 + 대시보드 빨강)
- [ ] **F5 flicker 1주일 통계** — 평균 ON-streak / 일일 빈도
- [ ] **텔레그램 OR/AND 트리 사용자 가독성** — v20.9.1 UI 개선 효과 측정
- [ ] **대시보드 5개 바 시각화 검증** (v20.9.3 bi/pctBar 통일)
- [ ] **BULL 구간 F10 차단 증가 (62.3% vs F2 41.2%) 기회 손실 측정**
- [ ] **다음 BEAR 이격 심도** — F7 가설 재검증 기회 (F10 vs F7 #44 결론 재확인)

### #47/#48 PF 시스템 점검 (2026-04-24)

- [x] **#47 Phase 2 P2 (guard_30) 프로덕션 적용** — ✅ **v20.9.5 배포 완료 (2026-04-24)**
  - `calc_position_size` L862-864: `if trade_count >= 30 and 0 < recent_pf < 1.0: risk *= 0.5`
  - 호출부 4곳 `trade_count=stats["trade_count"]` 전달
  - 즉시 거동 변화 0 (현재 recent_pf=9.47)
- [x] **실거래 PF 투명화 (텔레그램 + 대시보드)** — ✅ v20.9.5 완료
  - 텔레그램: `PF_AI (학습)` / `PF_실거래 (n=5)` / `사이징감점: N/A (n<30)` 세 줄 분리
  - 대시보드 AI Gate 카드에 수익팩터(실거래) + 사이징 감점 행 추가
  - status.json: `live_real_pf`, `live_real_pf_n`, `live_real_penalty_active` 3필드 신규
- [ ] **SELL 30건 도달 후 P2 첫 발동 시 재평가** — 월 ~5건 기준 6~12개월 예상. 발동 시점 `recent_pf`, BEAR/회복기 구간 여부 기록 필요
- [x] **#49 check_ai_gate threshold arg 복원 백테스트** — ✅ 완료 (2026-04-24)
  - 파일: `backtest/results/bt_check_ai_gate_threshold.md` / `.csv`
  - 결과: G1/G2 CAGR -27.66%p 대폭 악화 (거래 62→17), G3 = B0 (no-op)
- [x] **v20.9.6 dead 코드 제거** — ✅ 완료 (2026-04-24)
  - `get_ai_gate_threshold()` 함수 + `_calibrate_threshold()` 함수 삭제
  - 호출부 4곳 정리, `check_ai_gate` 시그니처 정리
  - MARKET_*_GATE / MIN_THRESH / MAX_THRESH / THRESHOLD_ADJUST_STEP / THRESHOLD_PF_* 제거
  - 유지 (호환): AI_GATE_THRESHOLD, AI_UNRELIABLE_GATE, LOSS_MODE_GATE, dynamic_threshold 필드
- [x] **v20.9.6 AR2 조건부 리셋** — ✅ 완료 — ≥50 일 때만 리셋
- [x] **v20.9.6 consecutive_train_rejects CSV 영속화** — ✅ 완료
- [x] **v20.9.6 텔레그램 timeout WARN 소거** — ✅ 완료 — ReadTimeout/ConnectTimeout 별도 처리
- [x] **v20.9.6 배포 후 관찰** — ✅ AR2 조건부 리셋 + CSV 복원 작동 확인
- [x] **v20.9.7 카운터 결함 수정** — ✅ 완료 (2026-04-24)
  - 결함 A (Critical): train_async 호출부 3곳 즉시 리셋 제거, _do_train accepted 시 플래그 동기화
  - 결함 B (Medium): last_candle_time status.json 영속화
### #50/#51 R1/R2/R3 교차 연구 (2026-04-24)

- [x] **#50 R1 심화 Prescreen v2** — ✅ 완료
  - HARD GO: R1-B/D (post-hoc 필터, 실전 불가) + R1-F (gap+ema, R2-B와 동치)
  - **R1 전면 기각**
- [x] **#51 R2 × R3 grid** — ✅ 완료
  - 🟢 **AY GO**: R3=F2 단독 → CAGR +2.17%p, 2023 회복기 +6.4%p
  - 🔴 R2 (ema 예외) 전면 기각: CAGR -27%p 급락, 2023 이후 매매 정지
- [x] **#52 Ablation 완료** — ✅ 2026-04-24
  - 🟢 AY 채택 확정 — 4/4 판정 기준 통과
  - M2 CAGR +3.02%p (vs M1), 2022 BEAR **+2.7%p 개선** (-10.8 → -8.1)
  - **개선 원리 규명**: M1 손실 5건 (-13.02%p) 회피. 타이밍 이동 아님 (median diff=0h)
  - F5 제거가 회복기 초기 F5 거짓 신호 필터링
  - M3 (F5 단독): 대재앙 확인, F5는 BEAR 방어 불가
- [x] **🟢 v20.9.8 프로덕션 배포 완료** — AY 채택 (`e2_block_mode: F10 → F2`)
  - E2_BLOCK_MODE "F10" → "F2", E2_F5_ENABLED True → False
  - status.json 마이그레이션: bars_since_e2 0 리셋 (F10→F2 기준 전환)
  - 텔레그램/대시보드 F5 표시 제거
  - BOT_VERSION 20.9.8
### #53 F7/F11 재평가 (2026-04-24)

- [x] **#53 F2/F7/F11 Ablation** — ✅ 완료
- [x] **🔴 F7a 기각 (#54 심화 분석)** — v20.9.9 배포 취소
  - 원인: F7a 개선은 2023-01 gap 예외 1건 (+32.38%) 과 **bars 카운터 시작점 차이**에 의존
  - 2022-09~11 F2/F7 둘 다 100% 활성, 2025 F7⊆F2 → F7 차단 기준 자체의 구조적 우위 아님
  - gap 예외 7건 WR 43%, median -1.60% (품질 낮음)
  - F7은 **다음 BEAR 전환 시 실거래 환경에서 재평가**
- [x] **v20.9.8 (F2) 유지 확정**

### #57 O3 grid + PASS 봉 검증 (2026-04-24)

- [x] **Branch 1 PASS 봉 검증** — ✅ 완료
  - 파일: `backtest/scripts/verify_pass_bars.py`, `backtest/results/pass_bars_verification.md`
  - 결과: 🟢 **논리 버그 아님** — 15개 PASS 봉 전원 VWAP 차단으로 설명
  - #56 analyzer 누락 gate: VWAP / OBV_block / close-prev gap (추후 보완)
- [x] **Branch 2 O3 Grid (9 케이스, 52mo)** — ✅ 완료
  - 파일: `backtest/scripts/bt_o3_grid.py`, `backtest/results/bt_o3_grid.md`, `.csv`
  - 원본 precompute_o3 100% 정합 검증 (B0 172 firings 일치)
  - 자동 판정: 전부 REJECT / NO-GO
- [x] **G5 인사이트 → #58 후보 도출**
  - G5 (lookback=20, rec=1.0%): CAGR +2.45%p, 2023 회복 +11.14%p, 2022 BEAR +2.56%p 개선, MDD -1.25%p — 5/6 GO 통과
  - 유일 실패 기준: O3-예외 PF=0 (n=3 통계 의미 없음)
  - **시사**: O3 자체가 net-negative. gap_score+180d 경로가 회복기 alpha 전체 보유
- [ ] **#58 후보: O3 제거 또는 극도 엄격화 연구** (다음 세션)
  - 옵션 A: `e2_o3_exception=False` + gap_score 단독
  - 옵션 B: rec ≥ 1.0% (G5 유지)
  - 가설: gap_score만으로 회복기 진입 충분, O3 BEAR 오발 완전 제거
  - 백테스트 설계: 52mo × (O3 ON rec=0.5 / O3 OFF / rec=1.0 / rec=1.5) 4 케이스
- [x] **O3 lookback/rec 파라미터 grid 기각** — 최적화 불가

### #56 재진입 Gate 병목 분석 (2026-04-24)

- [x] **#56 분석 완료** — 🔴 단일 gate 완화 NO-GO / O3 threshold 연구 여지
  - 파일: `backtest/scripts/analyze_reentry_gates.py`, `backtest/results/reentry_gate_analysis.md`
  - **Gate 고도 중첩**: EMA 실패 87%, AI 67%, SCORE 63%, REGIME_DOWN 38%, E2_BLOCK 25%
  - **단일 해제 효과 미미**: 어느 gate 하나만 해제해도 baseline 5봉 → 최대 19봉 (3%)
  - **03-09→03-15 +13.37% gap = E2_BLOCK 18봉 주범**: O3 예외 미발동
- [ ] **#57 후보: O3 signal 조건 grid search** — 회복기 3월 반등 패턴 캡처
  - 현행 O3: 20-bar low break + 0.5% recovery
  - 후보: 30-bar low + 0.3% recovery / bnc60 / wave bounce 등
  - 목적: 2023-03-11~13 구간과 유사 패턴 발견
- [x] **EMA / AI / Score 단일 완화 실험 기각** — 효과 3% 이내로 무의미

### #62 Range/Volatile regime 전용 exit 로직 선행 분석 (2026-04-24)

- [x] **Phase 1 완료 → 🔴 연구 종료**
  - 파일: `backtest/results/bt_regime_exit_tuning_phase1.md`
  - 입력: `bt_recovery_regime_trades.csv` (B0 68건, 52mo)
  - 6 가설 중 5개 기각 (R2/R3/V1/V2/V3), R1만 미약 여지 (기대 +3~5%p, 계단손절 교란 risk)
  - 구조적 발견: **"수익→손실 전환" MFE 패턴은 regime 특성이 아닌 4H 전략 구조 특성** (TU/Range/Volatile 모두 MFE≥1% 50~56%)
  - Volatile ATR손절 1/9(11%), Range ATR손절 MFE 0.42% — 손절 완화 레버 없음
- [x] **대안 축 검토: entry timing** → #63에서 수행, 🔴 NO-GO
- **결정**: 로드맵 유지 (Shadow AI 5월 중순 → Phase 3 AI 교체). Phase 2 진행 불필요.

### #63 Range 진입 품질 필터 연구 (2026-04-25)

- [x] **Phase 1 완료 → 🔴 NO-GO**
  - 파일: `backtest/results/bt_63_entry_quality_phase1.md` / `bt_63_phase1_entries.csv`
  - B0 Range 42건 → A=ATR손절 15, B=비ATR 27, 진입 시점 9지표 비교
  - 최고 분리력 = atr_pct (sep 0.53), 나머지 5지표 sep<0.3
  - "추격 진입" 가설 기각 — A가 오히려 저변동(atr_pct 0.33 vs 0.45)
  - 단일 필터 중 차단율 ≥ 70% 충족 없음 (최고 bar_pos 0.80 @ 60%)
- [x] **#63-B bar_pos 0.80 단일 최소 검증 완료 → 🟡 YELLOW**
  - 파일: `backtest/results/bt_63b_bar_pos.md` + 3개 CSV + `scripts/bt_63b_bar_pos.py`
  - simulator.py: `range_bar_pos_max` cfg + `range_bar_pos_blocked_n` stats 추가
  - 4 cases (B0/F1=0.80/F2=0.85/F3=0.75), CAGR 델타 F1 +0.10%p (GO 기준 +0.5%p 미달)
  - Phase 1 재현 4/5 (80%), Phase 1 이론 +14.9% → 실제 +0.34% (45배 감쇠)
  - Range ATR 15건 수 변화 없음 (차단되면 다음 봉에서 대체 진입)
- **결정**: 프로덕션 반영 불필요. 복리 경로 재설정으로 단건 회피 효과 소멸. 
  회복기 Range ATR 구조적 한계 수용. Shadow AI / 외부 신호 축 전환.

### #55 2023 회복기 Exit 패턴 분석 (2026-04-24)

- [x] **#55 분석 완료** — 🟡 청산 완화 연구 GO
  - 파일: `backtest/scripts/analyze_2023_recovery_exits.py`, `backtest/results/recovery_2023_exit_analysis.md`
  - **#42 +6.59%p gap의 본질 = 2023-01-05 Trend_Up 예외 진입 단일 거래 (+32.38%p)**. 설명력 111%, Feb 이후 20건 E2a와 공유
  - **#52 +6.47%p gap = F5 제거로 M1 손실 5건 회피** (#52에서 이미 규명)
  - Whipsaw 0건 → 빠른 재진입 아닌, 개별 trade stop 조기화가 문제
- [ ] **v21 청산 완화 후보 연구** (다음 세션)
  - 5 케이스 공통: HARD (MFE≥+3% & pnl≤0) 평균 5건/-7%p, SOFT 평균 3~4건/+11%p
  - 이론상 회수 상한 HARD+SOFT ≈ +55%p (회복기 한정)
  - 실제 trigger: Feb~5월 변동성 구간 ATR/계단 손절 반복
  - 제안: `bars_since_e2 ∈ [1080, 2160]` 회복기 flag 하 ATR_STOP 확대 / 트레일링 lag 증가 grid search
- [x] **E2b+6mo 유지 확정** — 17일 조기 진입 메커니즘 핵심, 예외 경로 추가 확장 불필요
- [ ] **v20.9.8 배포 후 관찰**:
  - 2022-10 패턴 재현성 (다음 BEAR에서 F5 거짓신호 회피 효과)
  - Volatile regime 진입 안전성 (2023-12-14 -5.32% 유사 패턴 회피 여부)
  - bars_since_e2 예외 경로 발동 빈도 (F2 median 0 → 예외 활성 드물 예상)
  - E2 BEAR 해제 타이밍: F2만 봤을 때 vs F10 대비 빨라졌는지
- [x] **R1/R2 기각** (재시도 금지)
  - R1 독립 조건 (gap+score+ema 등) 전체 기각
  - R2 ema_ok 예외 전면 기각 — BEAR dead cat bounce trap

- [ ] **v20.9.7 배포 후 관찰**:
  - 결함 B 즉시 검증: 재시작 후 candles_since_retrain 유지 확인
  - 결함 A 검증 (시간 소요): 다음 Regime 전환 + AR3 거부 동시 발생 시 카운터 유지되는지
  - 30캔들 주기 정기 재학습 첫 발동 (4/29 예상)
  - 텔레그램 WARN 건수 감소 (v20.9.6 효과)
- [ ] **WIN_STREAK 보너스 조건도 통계 유효성 재검토** — `recent_pf ≥ 1.2` 가 n=5 에서 쉽게 만족. guard 적용 논의
- [ ] **Kill Switch min_trades=20 vs THRESHOLD_ADJUST_TRADES=30 불일치 확인** — 의도된 차이인지 검증
- [ ] **재시작 141회/32일 원인 진단** — systemd 정책 / OOM / network 확인
- [ ] **#48 rolling AI PF 도입 보류** — ⚪ 직접 효과 없으나 (entries identical), PERF_DEGRAD 재활성 논의 시 선행 필수 (R3 1000봉 권고)

### #45 Strong Trend 분리 연구 결과 (2026-04-21)

- [x] **Strong Trend (ADX 30+) 공격 파라미터 검증 완료** — ❌ 전면 기각
  - 파일: `backtest/bt_strong_trend_split.py` + `backtest/results/bt_strong_trend_split.md`
  - B0 (현 프로덕션 TU 4.5/2.5): +184.93%, BULL cap 35.07% (KS OFF, 40mo)
  - C1~C6 모두 B0 대비 -0.43 ~ -60.26%p 악화
  - **핵심 교훈**: step_lookback 3.0+는 이익 보호 약화 → 대폭 악화. trail_m 4.5가 이미 최적
  - **BULL 캡처 개선 방향**: Strong 분리는 불가 → 다른 경로 (조기 진입 / pyramiding / AI Gate) 탐색
  - simulator.py에 `strong_trend_*` 파라미터 추가 (기본값 비활성, 기존 백테스트 무영향)

### v20.9.4 관찰 항목 (2026-04-21 배포 이후)

- [ ] **자정 (KST 00:00) 경과 시 E2 일일 카운터 자동 리셋 작동 확인**
  - 로그 검색: `grep "E2 일일 카운터 리셋" btc_bot.log`
  - 기대 포맷: `E2 일일 카운터 리셋: 2026-04-21 → 2026-04-22 (전일 차단 N, O3예외 M, gap예외 K)`
  - 텔레그램/대시보드 "오늘 차단 N건" 0부터 시작
- [ ] **MR 다음 발생 시 status 필드 일관성 확인**
  - `status.pyramid_locked=False`, `status.e2_exception_type=""`
  - `pos_trail_m=0.0`, `pos_step_lookback=0.0`, `pos_init_ratio=0.0`, `range_new_mode=False`
  - 직전 포지션의 잔여값이 status에 남지 않음
- [ ] **대시보드 신호로그 탭 BLOCK 빨강 표시 시각 확인**
  - 다음 E2 차단 이벤트 발생 시 `signal=BLOCK` 빨강
  - 기존 `event=e2_bear_block` + warn 색상은 유지
- [ ] **simulator.py FULL 정합 검증 실행** (bt_v20_9_validation.py)
  - bt_e2_longterm_52mo.py 데이터 파이프라인 import 필요 (현재는 뼈대)
  - Reference (days 180) vs Simulator v20.9.4 (bars 1080) 최종자산 ±0.5% 일치
  - 52개월 실행 시 모델 학습 + 시뮬 2회 = 수 분 소요

### v20.8.1 관찰 항목 (AI 재학습 정책 개선 — AR1~AR4)

- [ ] **AR1 (PerfDegrade OFF) 효과 측정**
  - PF 0.42 → ? 추이 (기존엔 PerfDegrade가 추가 악화 유발)
  - 30캔들 누적 (Periodic) 단독 재학습 후 PF 변화 (다음 ~5일 후)
  - PerfDegrade OFF로 인한 학습 누락 시 모델 stale 위험 평가

- [ ] **AR2 (재시작 candles 리셋) 효과 측정**
  - 봇 재시작 시 즉시 학습 발동 차단 확인 (로그에 "AR2: candles_since_retrain N→0 리셋")
  - 재시작 후 첫 30캔들 동안 학습 없는지 (5일 정도 관찰)

- [ ] **AR3 (롤백 가드) 동작 확인**
  - 다음 학습 시 PF 악화 시나리오 발생 → 거부 알림 수신 확인
  - 거부 시 ai_last_train_dt 미갱신 → Shadow RF 동기화 안 함 검증
  - consecutive_train_rejects 카운터 정상 갱신
  - 5회 연속 거부 케이스 발생 시 강제 채택 + 경고 알림

- [ ] **AR4 (CSV 영속화) 무결성**
  - btc_retrain_history.csv 누락/중복 없는지
  - 헤더 1회만, 매 학습 1행 추가
  - 거부 케이스도 정상 기록 (accepted=False)

- [ ] **Shadow 자동 정합 검증**
  - shadow_bot.log에서 RF 재학습 발동 시점이 ai_last_train_dt 변경과 정확히 매칭
  - AR3 거부 시 Shadow RF 학습 skip 확인 (False 거부 케이스에서 RF 메타 미갱신)

- [ ] **대시보드 v20.8.1 표시 검증**
  - Kill Switch 카드: 24h 카운트, 자동복구 잔여시간, 한도 20%
  - 포지션 카드: 진입모드 (Range New / TU 피라미딩), 사이징, 트레일링, 계단lookback
  - E2 BEAR 행: 활성/정상 + 일봉/EMA200/이격/누적 차단
  - AI 재학습 탭: 최근 5건 표시, 거부 케이스 색상 구분
  - 도움말 탭: 텔레그램 명령 + 시스템 정책 표시

- [ ] **장기 효과 측정 (~05-05, 2주 누적)**
  - 학습 횟수 (v20.8 대비 감소 예상)
  - 거부율 (예상: 30~40%)
  - 평균 PF (단조 하락 멈췄는지)
  - 강제 채택 발생 빈도

### v20.8 관찰 항목 (Kill Switch 자동복구 + 24h 재발동 방지)

- [ ] **Kill Switch 발동 시 분석** (중요)
  - 발동 시점 시장/포지션 상황 (가격 급락 / 깊은 피라미딩 여부)
  - 자동복구 효과 실측 (MDD 10% 회복까지 소요 시간 / 재진입 타이밍)
  - MDD 25% 상향 검토 (자동복구 있어도 발동 빈번 시)
  - 24h 내 재발동 발생 여부 (2회째 안전장치 작동 확인)

- [ ] **/killswitch status 명령 응답 확인**
  - 텔레그램에서 `/killswitch status` 입력 시 이력 정확히 표시되는지
  - last_killswitch_at, killswitch_count_24h 필드 정상 갱신

- [ ] **자동복구 알림 수신**
  - Kill Switch 발동 후 24h + MDD<10% 충족 시 "🟢 Kill Switch 자동 해제" 알림
  - 알림 누락 없는지

- [ ] **status 신규 필드 정상 초기화**
  - last_killswitch_at: 0.0 (초기) → 발동 시 갱신
  - killswitch_count_24h: 0 → 발동마다 증가 → 24h 경과 시 리셋
  - last_killswitch_recovered_at: 0.0 → 자동복구 시 갱신


## 대기 중 (Todo)

### Shadow AI 평가 (2026-05-05 목표)

- [ ] **Shadow v2.0 RF/Online 성과 평가** (2026-04-17 도입)
  - 30건 누적 (~5일) → XGB/RF/Online 상관관계 분석
  - 100건 누적 (~17일) → Precision/PF 비교 + 앙상블 시뮬
  - 판정 기준:
    * RF가 XGB와 상관 0.9+ → 앙상블 효과 미미, RF 포기 검토
    * Online이 Regime 전환 시 빠르게 적응하는지 관찰 (ADWIN 발동 로그)
    * 매매 도입은 반드시 백테스트 기반
  - 초기 학습 (2026-04-17): RF Prec=45.6% PF=1.05, Online n_learned=1461

- [ ] **pandas 3.0.1 → 2.3.3 다운그레이드 영향 관찰** (Shadow v2.0 부작용)
  - 배경: river 의존성으로 강제 다운그레이드 (2026-04-17 배포 시)
  - 위험: 프로덕션 봇(v20.2)이 pandas 3.x API 사용 시 런타임 에러 가능성
  - 초기 확인: 배포 직후 양 서비스 정상 동작, 에러 로그 0건
  - 관찰:
    * btc_bot.log에서 pandas 관련 warning/FutureWarning/deprecation
    * pandas_ta 지표(ATR/ADX/RSI/OBV) 계산 결과 정합성
    * 백테스트 시뮬레이터 B0 재현 시 기존 결과 일치 여부
  - 판단 기준:
    * 1주일 무사고 → 영향 없음 확정
    * warning 발생 → 해당 코드 경로 수정
    * 런타임 에러 → 즉시 롤백 및 river 버전 조정 검토

- [ ] **Online 모델 ADWIN 드리프트 감지 발동 추적**
  - 배경: River ARFClassifier에 ADWIN 드리프트 감지 내장
  - 기대: Regime 전환 시 ADWIN이 개별 tree를 재설정 → 빠른 적응
  - 추적 방법:
    * online_meta.json의 n_learned 추이 (매 100건마다 저장)
    * Regime 전환 타이밍과 Online prob 급변 상관관계
    * (선택) River ARF의 개별 tree n_drifts_detected 로깅 추가
  - 판단: Regime 전환 후 1~3 캔들 내 Online prob가 방향성 변경하면 유효

- [ ] **Shadow v2.0 초기 예측 분포 추이 관찰**
  - 초기 1건 (2026-04-17 13:00):
    * XGB 40.3% / RF 44.4% / Online 56.6%
    * XGB-RF 차이 +4.1%p, XGB-Online 차이 +16.3%p
  - 가설: Online이 뚜렷하게 높은 건 최근 데이터 가중치 때문일 수 있음
  - 추적: 30건 누적 후 모델별 평균 prob, std, bias 분석
  - 판단 기준:
    * Online prob이 지속적으로 XGB+10%p 이상 → 과적합 의심
    * 모든 모델이 상승 편향(평균 >0.55) → 라벨링 문제 재검토


### 우선순위 2 (장기)

- [ ] 다중 자산 분산
  - 설명: BTC + ETH + SOL 등 업비트 현물
  - 목적: 수익 기회 확대 + 포트폴리오 분산

- [ ] 온체인 데이터 피처 추가
  - 설명: Binance API에서 펀딩비/미결제약정 참조 → XGB 피처로 투입
  - 목적: 시장 센티먼트 반영

- [ ] 7-에이전트 코드 모듈 분리
  - 설명: 단일 파일 → agents/ 폴더 모듈화
  - 목적: 유지보수성 + 멀티 전략 확장 기반


- [ ] **Shadow E2 exception logger (신규 권장)** — v21 연구 후속
  - Shadow AI와 별개 — 실시간 E2 예외 후보 진입점 기록
  - 로그 포맷: 타임스탬프, gap, score, ma5>ma10, days_since_e2, bnc30, adx, O3 firing, trigger, 허용/차단, 가상 20봉 PnL
  - 목적: 11 케이스 결과 실전 검증 + 표본 누적 (목표 각 규칙 20+건)
  - 구현: `shadow/e2_exception_tracker.py` + `shadow/e2_exception_history.csv`

## 5월 중순 Shadow AI 평가 시 동시 결정 후보

1. **Shadow AI Phase 3 교체 여부** (XGBoost → CatBoost / RF / Ensemble)
   - 트리거: RF n≥30 도달
   - 현재: XGB Prec 32.0% PF 3.26 / RF Prec 29.6% PF 3.46 (n=27)

2. **#64 B3** — Range `range_initial_ratio` 0.70 → 0.40
   - 결과: MDD -2.15%p, Sharpe +0.031, CAGR -0.15%p
   - 출처: `bt_64_range_weight.md`

3. **#65 E100** — F2 EMA200 → EMA100
   - 결과: portfolio +3.69%, 회복 +2.63%p (기준 -0.37%p), BEAR도 우위
   - 출처: `bt_65_R_e100_reanalysis_key_numbers.md`

조건: AI Gate 변경 시 #64 B3 / #65 E100 재검증 필요 (변수 격리)


### 코드 정리 (완료)

- [x] **build_e2_mod 헬퍼 도입** (#69-A/B 후속, 2026-05-01)
  - `backtest/core/simulator.py` 에 `build_e2_mod(bear_arr, **extras)` 추가
  - bars_since_e2_a 자동 포함 → silent block 재발 영구 차단
  - caller 전환: `bt_e2_longterm_52mo.py:run_case` (실제 버그 출처) + `bt_v20_9_divergence.py`
  - 회귀: #42 5 케이스 모두 byte-equivalent (27,542,773 정확 일치) + #69-A 3 케이스 모두 ±0.000%
  - 18개 기타 백테스트 스크립트는 자체 mod 빌드에 이미 bars_since_e2_a 명시 → 영향 없어 미전환 (cosmetic 변경 회피)
  - 추가 안전장치: simulator 의 defensive `raise ValueError` (mod 누락 시 명시적 fail)

### 데이터 검토 일정 (장기)

**5월 중순 (2026-05-15 ± 3일)**:
- [ ] Shadow AI 첫 평가 (n≥100 도달 시점)
  - shadow_predictions.csv n≥100 확인
  - regime별 분포 점검
  - 모델 우열 추세 (자동 리포트 4주차)
- [ ] candle_log.csv 점검
  - 행 수 / MAX_ROWS 제한값 확인
  - 데이터 무결성 (NaN 비율)
  - 컬럼 정상 기록 여부
- [ ] #64 B3 / #65 E100 보류 결정 재검토 (Shadow 결과 따라)

**6월 초 (2026-06-01)**:
- [ ] 5월 월간 리포트 점검 (전월 대비 활성 첫 사용)
- [ ] Shadow AI 추세 추이 (n≈200 예상)
- [ ] Online 모델 우세 지속 여부

**7월 중순 (2026-07-15 전후)**:
- [ ] candle_log.csv 본격 분석
  - 진입 조건 × 결과 매트릭스 (+4봉/+8봉)
  - 신호 강도별 정확도
  - 시장 상태별 신호 신뢰도
  - E2 차단의 실효성 검증 (거짓 차단 비율)
- [ ] Shadow AI 의사결정 (n≥300, 3개월)
  - 모델 교체 / 앙상블 채택 판단
  - regime별 우열 확정

**10월 중순 (2026-10-15)**:
- [ ] Day 1080 도달 (E2b+6mo gap 예외 활성화)
- [ ] 6개월 누적 데이터 완전 분석
- [ ] 봇 종합 재평가

### 정기 작업 (자동)

**매월 1일**:
- 월간 리포트 자동 생성 (v20.9.9, Telegram 발송)

**매주 월요일 08:00 KST**:
- Shadow AI 분석 자동 리포트 (#67 자동화)

**매 4H 봉**:
- candle_log.csv 자동 누적
- shadow_predictions.csv 자동 누적

### 보류 (조건부)
- [ ] **M3: FNG<25 Trend_Down 소규모 진입** — 관찰 후 적용 검토
  - 백테스트 #19: BULL +2.55pp, BEAR +1.22pp, 자산 +390K, MDD -1.1%p
  - 발동 4건으로 통계 부족, 평균 PnL ≈ 0
  - 판단 기준: FNG<25 발생 시 텔레그램에 "M3 시그널" 로그 추가 → 가상 진입으로 5건 이상 추적 → 평균 PnL > +0.5%면 프로덕션 적용
  - Fear & Greed API를 봇에 연동하여 일별 FNG 값 수집 시작 (M3 적용 전 데이터 인프라 선행)
- [ ] **T5: Range 고점근접 Score 역전** — IS -13.49%pp, 단독 위험. 실거래 데이터 축적 후 재검토
- [ ] **T3: 강상승장 눌림 물타기** — 발동 0건. 조건 완화 후 재백테스트 필요


---

## 아카이브 참조

아래 내용은 `improvement_todo_v1.md`에서 검색:
- **v20.9 후보 및 v21 E2 예외 규칙 연구** (#38~#44, Option B 확정 근거)
- **v20.7 ~ v20.0 관찰 항목** (이미 배포된 버전들의 초기 관찰)
- **이전 봇 상태 (v20.0, 2026-04-14)**
- **우선순위 1 (v19.9 실전 검증)**
- **v20.5 / v20.3 / v20.2 관찰**
- **v20.0 실전 검증 (K2 김프, TB2 기각)**
- **완료된 우선순위 2 항목** (v20.5 _check_hard_stop 로그, CatBoost/LSTM 구조적 포기)
- **완료 (Completed) 전체** (v19.9, v19.1, v19.0, v18.9, v18.8, v18.5, v18.4, v18.3, v18.2, v18.1, Phase 1/2/3)
