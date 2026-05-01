# BTC Bot 개선 이력 및 계획

## 현재 운영 상태 (2026-05-02 기준)

| 봇 | 버전 | 상태 |
|----|------|------|
| 실전 봇 | **v20.9.10** | `btc_bot_v290.py` (#74 E2 OFF + 로그 강화(다중 EMA + 가상 차단) + 텔레그램 EMA 비교 + 대시보드 OFF banner) |
| 이전 버전 | v20.9.9 | `btc_bot_v290.py` (#68 월간 리포트 보강 — B&H/regime/거래분해/시스템/추이/누적 + GitHub auto_push + CLI 백필) |
| 이전 버전 | v20.9.8 | `btc_bot_v290.py` (E2 F10 → F2 — AY 채택, backtest #52) |
| 이전 버전 | v20.9.7 | `btc_bot_v290.py` (카운터 결함 수정 — AR3 거부 시 리셋 제거 + last_candle_time 영속화) |
| 이전 버전 | v20.9.6 | `btc_bot_v290.py` (AR2 조건부 리셋 + rejects 영속화 + check_ai_gate dead code 제거 + 텔레그램 timeout 처리) |
| 이전 버전 | v20.9.5 | `btc_bot_v290.py` (P2 guard_30 + 실거래 PF 투명화 / 대시보드+텔레그램 PF_AI vs PF_실거래 분리) |
| 이전 버전 | v20.9.1 | `btc_bot_v290.py` (v20.9.0 + 텔레그램 최종판정 버그 수정 + E2 OR/AND 트리 + 대시보드 바 통일) |
| 이전 버전 | v20.8.1 | `btc_bot_v281.py` (AI 재학습 정책 개선: AR1~AR4 + 대시보드 갱신) |
| 이전 버전 | v20.8 | `btc_bot_v208.py` (Kill Switch 자동복구 + 24h 재발동 방지) |
| 이전 버전 | v20.7 | `btc_bot_v207.py` (C6 — Range step 3.0 + init 70% + MDD 20%) |
| 이전 버전 | v20.6 | `btc_bot_v206.py` (BD + E2 + 하드스톱 팬텀 가드 + 텔레그램 정기만) |
| 이전 버전 | v20.5 | `btc_bot_v205.py` (Range New + _check_hard_stop 로그 보강) |
| 이전 버전 | v20.3 | `btc_bot_v203.py` (log_confirmed_trade 페어링 + 리포트 4H) |
| 이전 버전 | v20.2 | `btc_bot_v202.py` (H-2 중복차단 + C-3 폴백안전 + C-1 로거) |
| 이전 버전 | v20.1 | `btc_bot_v201.py` (무한 계단손절 S3 + 하드스톱 체결 강화) |
| 이전 버전 | v20.0 | `btc_bot_v200.py` (K2 김치 프리미엄 Modifier) |
| 이전 버전 | v19.9 | `btc_bot_v190.py` (청산 최적화: AI매도OFF + ATR 느슨화 + 피라미딩 개선) |
| 백업 | v16.3 | `btc_bot_v163.py` |

---

## v20.9.10 (2026-05-02) — #74 E2 OFF + 로그 강화 + 텔레그램/대시보드 개선

**근거**: `backtest/results/bt_74_real_log_e2_full.md` (실로그 분석: E2 차단 24건 중 88.2%가 수익 신호, BULL 후반 한정).
사용자 결정: 백테스트 의존도 ↓, 실거래 데이터 ↑, 매매 빈도 회복.

### 1. E2 완전 OFF (`E2_ENABLED = False`)

`btc_bot_v290.py:442`:
```python
# v20.9.10: 데이터 누적 모드
E2_ENABLED = False
```

**영향**: 
- F2/F5/F10 차단 평가 모두 SKIP (4 곳: line 3237/3734/3782/4306)
- `_update_e2_bear_mode` 호출되지 않음 → `live_e2_bear_mode` 등 status 필드 stale (대시보드 banner 로 명시)
- 다른 7중 안전장치 그대로 작동: AI Gate / EMA 4H / Score / 일손실 한도 / Kill Switch / ATR / 김프

**롤백 트리거**: 일손실 -3% / 누적 -5% / BTC -10% in 1주 → `E2_ENABLED = True` 후 재시작.

### 2. 로그 강화 — `btc_candle_log.csv` 컬럼 13개 추가

기존 23 + 신규 13:
- 다중 EMA 일봉: `ema100_d / ema150_d / ema200_d / ema250_d / ema300_d`
- 다중 gap: `gap_e100_d / gap_e150_d / gap_e200_d / gap_e250_d / gap_e300_d`
- 가상 시나리오: `virtual_e2_block_e200 / e250 / gap5` (사후 비교용)
- 메타: `actual_block_reason` (none/ai_gate/ema_4h/score/paused/kill_switch)
- 추가 lag: `price_after_24` / `pct_change_24` (4일 후 변화)

신규 헬퍼: `compute_multi_ema_daily(daily_close_series, periods=(100,150,200,250,300))`.

**효과**: 1~3개월 후 "EMA250이었다면?" / "gap -5% 였다면?" 등 비교 분석 가능 (백테스트 의존도 감소).

### 3. 텔레그램 4H 리포트 — 다중 EMA 비교 표시

E2 OFF 모드 진입 시 (line 3760~3776):
```
⚠️ E2: OFF (v20.9.10 데이터 누적 모드)
  📊 EMA 비교 (참고용, 일봉):
    🔴 EMA100: 119.2M (gap -2.4%)
    🔴 EMA150: 121.0M (gap -3.9%)
    🔴 EMA200: 124.0M (gap -6.9%)
    🔴 EMA250: 125.5M (gap -7.6%)
    🟢 EMA300: 110.0M (gap +5.7%)
```

기존 E2 ON 트리 표시는 `elif E2_ENABLED` 분기로 보존 (롤백 시 즉시 동작).

### 4. 대시보드 — E2 OFF banner

`dashboard/templates/index.html`:
- 위험 row: `⚠️ OFF (v20.9.10 데이터 누적 모드)` (warn 색상)
- 상세 카드 상단: 주황 banner + 롤백 트리거 명시
- 기존 차단 조건 / 편차 바 모두 보존 (`(참고용 — 평가 비활성)` 라벨 추가)

`status.json` 신규 필드: `e2_enabled_config` (config-OFF vs runtime-OFF 구분).

### 안전 절차

- 봇 재시작 후 첫 4H 캔들 평가 모니터링 (다중 EMA 로그 기록 확인)
- 일손실 / Kill Switch 정상 작동 확인
- 첫 진입 발생 시 텔레그램 알림 (기존 BUY 알림 활용)

### 산출

- `btc_bot_v290.py.bak.pre_20.9.10` (백업)
- `btc_candle_log.csv.bak.pre_20.9.10` (백업)
- `dashboard/templates/index.html.bak.pre_20.9.10` (백업)

---

## v20.9.9 (2026-05-01) — #68 월간 리포트 보강 + gate_thresh NameError 핫픽스 + simulator 정합 수정

**근거**: `improvement_todo.md #68` (월간 리포트), `btc_bot.log` 4/24~4/30 NameError 48회 (gate_thresh), `backtest_log.md #69-A` (simulator silent block 수정).

### gate_thresh NameError 핫픽스

- **증상**: 4/24 ~ 4/30 사이 `name 'gate_thresh' is not defined` 48회 발생. AI Gate 통과한 캔들마다 루프 에러로 한 캔들 스킵.
- **원인**: v20.9.6 에서 `get_ai_gate_threshold` dead code 제거 시 `gate_thresh` 변수 정의도 삭제했으나, 7개 callsite(`log_signal` 5회, `log_trade` 1회, `log_signal` MR 1회)는 여전히 변수 참조. 같은 함수에서 `_log_rth = REGIME_CONFIG.get(...)` 가 line 4276 에서 정의되고 있었으므로 실제 fix 는 references 만 교체.
- **수정**: btc_bot_v290.py L4293/4326/4368/4382/4508/4522/4630 — `gate_thresh` → `_log_rth` 일괄 치환.
- **검증**: 코드 정적 grep 으로 모든 live 참조 사라짐 확인 (주석만 잔존, 의도된 history 표기).

### 변경 사항

- **`btc_bot_v290.py`**:
  - 신규 상수: `MONTHLY_HISTORY_FILE` / `MONTHLY_REPORT_DIR` / `MONTHLY_REPORT_RAW_BASE` / `MONTHLY_AUTO_PUSH_SH` / `PRICE_4H_CACHE_FILE`
  - 신규 모듈 함수: `_monthly_btc_change` (4H 캐시 → pyupbit 일봉 fallback), `_monthly_regime_distribution`, `_monthly_ai_gate_pass_rate`, `_trade_decomposition` (entry regime / exit kind / 보유봉 / 피라미딩 / TP1·TP2), `_killswitch_count_in_month`, `_retrain_count_in_month`, `_push_monthly_report_to_github`, `generate_monthly_report` (전체 빌더)
  - 클래스 메소드 `_send_monthly_report(equity, ym=None)` → `generate_monthly_report` 위임
  - CLI 백필: `python btc_bot_v290.py --monthly-report YYYY-MM [--no-push] [--no-telegram]`
  - 히스토리 영속화: `btc_monthly_history.json` (return_pct/mdd/trades/win_rate/pf/btc_change/edge) — 다음 달부터 전월 대비 + 누적 자동 갱신
  - GitHub auto_push 연동: `backtest/results/monthly_report_<YYYY-MM>.md` 생성 후 raw URL 텔레그램 전달
- **테스트**: 4월(2026-04) 보강 리포트 즉시 생성 (5건 / 80% / PF 9.47 / MDD -0.30% / 봇 +2.54% / B&H +10.34% / Edge -7.80%p / Range 37% / TU 56% / TD 7% / AI 52%) — Telegram 발송 + GitHub raw URL 작동 확인

### 무손실 체크리스트 (#68 명세)

- ✅ 봇 자체 6지표 (월수익/MDD/거래/승률/PF/평균 수익·손실)
- ✅ 시장 비교 3지표 (BTC start→end / B&H / Edge)
- ✅ regime 분포 4구간 (Range/Trend_Up/Trend_Down/Volatile, candle_log 기반 — 데이터 부족 월은 표시)
- ✅ 거래 분해: entry regime / exit kind / 보유봉(수동매도엔 미기록 명시) / 피라미딩 / TP1·TP2
- ✅ 시스템 상태: AI Gate 통과율 / Kill Switch / 재학습 / E2 BEAR 스냅샷 / current_mdd
- ✅ 전월 대비: 첫 달은 "데이터 없음" 표시 (5월 리포트부터 활성)
- ✅ 누적: 시작 월 명시 + 누적 거래/수익/MDD/B&H 합산

### 운영 변경

- 매월 1일 00시 자동 호출 (`_check_monthly_report`) — 기존 cadence 유지
- 백필이 필요할 때만 CLI 사용 (재실행해도 monthly_history 의 해당 월 항목이 덮어쓰기되어 안전)

---

## v20.9.8 (2026-04-24) — E2 F10 → F2 (AY 채택, backtest #52)

**근거**: `backtest_log.md #52` — F2/F10/F5 ablation 4/4 판정 기준 통과.

### 시뮬 성과 예상

| 지표 | F10 (M1) | F2 (M2) | Δ |
|---|---|---|---|
| CAGR | +22.75% | **+25.77%** | **+3.02%p** |
| 2022 BEAR | -10.8% | -8.1% | **+2.7%p** (F5 거짓신호 5건 회피) |
| 2023 회복기 | +13.7% | +20.1% | **+6.4%p** |
| MDD | 18.85% | 19.28% | +0.44%p (허용 내) |
| 2024 BULL | +99.5% | +98.2% | -1.36%p (허용 내) |

### 변경 사항

1. **상수** (L441-443):
   - `E2_BLOCK_MODE = "F10"` → `"F2"`
   - `E2_F5_ENABLED = True` → `False`

2. **status.json 마이그레이션** (`_load_status` 내):
   - v20.9.x (F10 기준) → v20.9.8 (F2 기준) 전환 시 `bars_since_e2` 0 리셋
   - `live_e2_activation_date` None 리셋
   - 이유: F10 기준 카운터는 F2 기준과 다를 수 있음 → E2b+6mo 예외 180일 재시작 (보수)

3. **텔레그램 리포트** (L3304~):
   - "F10 = F2 OR F5" → "F2 — 일봉 < EMA200"
   - F5 (4H) 표시 라인 제거
   - 해제 조건: "F10 OFF (일봉>EMA200 AND 4H 정배열)" → "F2 OFF (일봉>EMA200)"

4. **대시보드** (`templates/index.html`):
   - 차단 조건 섹션 헤더: "F10 = F2 OR F5" → "F2 (일봉 EMA200)"
   - F5 4H EMA biBar 블록 전체 제거
   - 하단 서머리: "F10 = F2 OR F5 → 차단 중 (이유)" → "F2 (일봉 EMA200) → 차단 중"

5. **대시보드 API** (`app.py`):
   - `_thresholds.e2_block_mode: "F10"` → `"F2"`

6. **BOT_VERSION**: 20.9.7 → 20.9.8

### 유지 (호환)

- `live_e2_f5_active`, `live_ema21_4h`, `live_ema55_4h` status 필드 — 대시보드 UI에서 사용 안 하나 호환 유지
- `E2_F5_ENABLED = False` 일 때 `compute_e2_f5` 미호출, 자동으로 모두 False/0

### 주의사항

- **2022-10 단일월 +3.12%p 개선**이 2022 BEAR 개선의 대부분 (95%)
- M2-only 2023-12-14 -5.32% Volatile 손실 전례 존재
- bars_since_e2 median이 F10=31 → F2=0 (거의 항상 리셋) → E2b+6mo 예외 발동 빈도 감소 가능

### 롤백

```bash
systemctl stop btc_bot.service
sed -i 's|E2_BLOCK_MODE           = "F2"|E2_BLOCK_MODE           = "F10"|' /root/tradingbot/btc_bot_v290.py
sed -i 's|E2_F5_ENABLED           = False|E2_F5_ENABLED           = True|' /root/tradingbot/btc_bot_v290.py
sed -i 's|BOT_VERSION   = "20.9.8"|BOT_VERSION   = "20.9.7"|' /root/tradingbot/btc_bot_v290.py
# 텔레그램/대시보드 F5 복원: git revert 또는 수동
systemctl start btc_bot.service
```

---

## v20.9.7 (2026-04-24) — candles_since_retrain 카운터 결함 수정

**근거**: v20.9.6 배포 후 사용자 감사로 2개 결함 발견.

### 결함 A (Critical): AR3 거부에도 카운터 0 리셋

**기존 동작**:
```python
ai_engine.train_async(df_rt)       # 비동기 학습 시작
self._candles_since_retrain = 0     # ← 즉시 리셋 (결과 무관)
```

비동기 학습이 AR3 거부되어 모델 미교체되어도 카운터는 이미 0.
→ 거부된 학습이 **30캔들 주기 재학습을 영영 회피하는 경로** 됨.

**4/24 02:40 사례**:
- candles=16 → Regime 전환 → train_async → 즉시 0
- 학습 결과 AR3 거부 (PF 0.38→0.10)
- 모델 유지됐지만 카운터 잃음

**수정**:
- 호출부 3곳 (L3565, L3641, L3671) 즉시 리셋 제거
- `_do_train` `accepted=True` 블록 (L1401) 에서만 `self._counter_reset_pending = True` 플래그 세팅
- Bot 메인 루프 (L3735~) 에서 플래그 감지 → 동기 리셋

**ai_engine/Bot 분리 문제 해결**: 직접 참조 대신 플래그 기반. `getattr(ai_engine, '_counter_reset_pending', False)` 로 안전 접근.

### 결함 B (Medium): last_candle_time 비영속화

**기존 동작**:
- `self.last_candle_time = latest_candle` 만 하고 status.json 저장 안 함
- 재시작 시 None → 첫 iter에서 방금 처리한 캔들 재감지 → `+1` 중복

**수정**:
- `_load_status` default 에 `"last_candle_time": None` 추가
- `__init__` 에서 `self.status.get("last_candle_time")` 복원
- 캔들 감지 직후 `self.status["last_candle_time"] = str(latest_candle)` 저장

### 변경 파일

- `btc_bot_v290.py`:
  - L1401 _do_train accepted 플래그
  - L1568-1575 __init__ last_candle_time 복원
  - L1692 default dict
  - L3565/3641/3671 호출부 리셋 제거
  - L3735-3742 플래그 감지 동기화
  - L3753 last_candle_time 영속화

### 영향

- **결함 A 재발 방지**: 다음 AR3 거부 시점에도 카운터 유지 → 30캔들 주기 보장
- **결함 B 제거**: 재시작마다 +1 드리프트 사라짐
- 현재 매매 거동 변화 없음 (카운터 값 정확도만 향상)

### 롤백

```bash
systemctl stop btc_bot.service
sed -i 's|BOT_VERSION   = "20.9.7"|BOT_VERSION   = "20.9.6"|' /root/tradingbot/btc_bot_v290.py
# L3565/3641/3671 호출부에 `self._candles_since_retrain = 0` 복원
# _do_train accepted 블록의 _counter_reset_pending 제거
# __init__ last_candle_time 복원 로직 제거
# default dict 에서 last_candle_time 제거
systemctl start btc_bot.service
```

---

## v20.9.6 (2026-04-24) — AR2 개선 + rejects 영속화 + dead code 제거 + timeout 처리

**근거**: `restart_root_cause.md` (131회 재시작 = 전부 SIGTERM 수동), `bt_check_ai_gate_threshold.md` (#49 복원 확증 실패)

### 변경 사항

1. **AR2 조건부 리셋** (L1593~):
   - 수정 전: 재시작 시 `candles_since_retrain` 무조건 0 리셋
   - 수정 후: ≥50 일 때만 리셋, 그 외 값 유지
   - 근거: 131회 재시작에 매번 0 리셋으로 30캔들 누적 불가 (5일간 정기 재학습 0회)

2. **consecutive_train_rejects CSV 영속화** (`_load_status` 끝):
   - 수정 전: status.json=0, csv=1 불일치 발생 (4/24 사례)
   - 수정 후: CSV 최근 행의 `accepted=False` + `consecutive_rejects>status 값` 일 때 CSV 복원
   - 근거: AR3 5회 연속 거부 가드 정확성 보장

3. **check_ai_gate dead code 제거** (#49 백테스트 결과):
   - `get_ai_gate_threshold()` 함수 삭제 (L705-717)
   - `check_ai_gate` 시그니처에서 `threshold` arg 제거
   - 호출부 4곳 정리 (2309/2444/3062/3780)
   - `_calibrate_threshold()` 함수 + 호출 (L3745) 삭제
   - 상수 `MARKET_VOLATILE_GATE` / `MARKET_RANGE_GATE` / `MIN_THRESH` / `MAX_THRESH` / `THRESHOLD_ADJUST_STEP` / `THRESHOLD_PF_HIGH` / `THRESHOLD_PF_LOW` 제거
   - 유지 (호환): `AI_GATE_THRESHOLD`, `AI_UNRELIABLE_GATE`, `LOSS_MODE_GATE`, `dynamic_threshold` 필드
   - 텔레그램 리포트: `Threshold(동적)` 라인 제거, `Threshold 자동 보정` → `사이징 감점 가드` 설명 교체
   - 근거: #49 백테스트 G1/G2 복원 시 CAGR -27%p 대폭 악화. dead 상태가 optimal 확증.

4. **텔레그램 ReadTimeout/ConnectTimeout silence** (L2870~):
   - 수정 전: `except Exception as e: logger.warning(...)` — getUpdates 장기 폴링 자연 타임아웃이 52건 WARN
   - 수정 후: `ReadTimeout` / `ConnectTimeout` 별도 핸들링, WARN 소거
   - 근거: 장기 폴링(30s 서버 + 35s 클라이언트)에서 명령어 없을 때 타임아웃은 정상 동작

### 영향

- **AR2**: 재학습 빈도 증가 (현재 candles_since_retrain=1 유지 → 30봉 누적 시 첫 정기 재학습)
- **AR3**: 현재 복원 동작 확인 필요 (status=0 → csv=1 → 복원됨)
- **Dead code 제거**: 매매 행동 변화 없음 (#49 확증). 코드 청결 + 리포트 노이즈 감소.
- **Timeout**: WARN 건수 감소 (향후 32일 기준 50+건 → 0건 예상)

### 파일

- `btc_bot_v290.py`: AR2 + _load_status + check_ai_gate + telegram listener + constants + reports

### 롤백

```bash
systemctl stop btc_bot.service
sed -i 's|BOT_VERSION   = "20.9.6"|BOT_VERSION   = "20.9.5"|' /root/tradingbot/btc_bot_v290.py
# L1593 AR2 블록 복원 (무조건 0 리셋)
# check_ai_gate 시그니처 복원 + get_ai_gate_threshold 함수 복원 + 호출부 4곳
# 상수 복원
systemctl start btc_bot.service
```

---

## v20.9.5 (2026-04-24) — P2 guard_30 + 실거래 PF 투명화

**근거**: `pf_investigation_summary.md` (Phase 2 P2 채택), `pf_production_log_audit.md` (프로덕션 실측 확증)

### 변경 사항

1. **`calc_position_size` n<30 가드** (L858):
   - 수정 전: `if 0 < recent_pf < 1.0: risk_pct *= 0.5`
   - 수정 후: `if trade_count >= 30 AND 0 < recent_pf < 1.0: risk_pct *= 0.5`
   - 시그니처에 `trade_count=0` 추가. 호출부 4곳 (L3147 리포트, L3944/L3952 legacy Range/Trend, L4106 MR) 에 `trade_count=stats["trade_count"]` 전달.
   - 배경: n=5에서 단일 손실로 pf 급락 가능 → 통계 불안정성 선제 회피

2. **텔레그램 리포트 PF 이중 표시** (`_send_report`, L3203~):
   - 기존: 한 줄에 `PF:0.38` (ai_engine.profit_factor, 학습 기반)
   - 신규: 두 줄로 분리
     - `PF_AI:0.38 (학습)` — ai_engine.profit_factor
     - `PF_실거래:9.47 (n=5) ⚙️사이징감점:N/A (n<30)` — calc_recent_stats 기반
   - 사이징감점 라벨: `N/A (n<30) | 적용 (×0.5) | 미적용`

3. **status.json 신규 필드 3개** (매 `_send_report` 시 갱신):
   - `live_real_pf`: `stats["pf"]`
   - `live_real_pf_n`: `stats["trade_count"]`
   - `live_real_penalty_active`: guard_30+pf<1.0 충족 여부 bool

4. **대시보드 AI Gate 카드** (`templates/index.html`):
   - 기존 `수익팩터` → `수익팩터 (학습)` 라벨 변경
   - 신규 행: `수익팩터 (실거래)` (n 표시, 색상 코딩)
   - 신규 행: `사이징 감점` (N/A / 적용 / 미적용 배지)

### 영향

- **거동 변화**: 현 시점 0 (recent_pf=9.47 >> 1.0 이므로 기존 B0 경로도 감점 미발동)
- **장기 효과**: 30건 누적 전 n<30 구간에서 감점 발동 선제 차단
- **시뮬 예측** (Phase 2 P2, 52개월): CAGR +0.58%p, MDD -1.64%p, 2023 회복기 +5.9%p (2022 BEAR 방어 -3%p 상쇄됨)

### 파일

- `btc_bot_v290.py`: 시그니처 + guard + _send_report + status.json 기록
- `dashboard/templates/index.html`: AI Gate 카드 2행 추가
- `dashboard/app.py`: 변경 없음 (status.json passthrough 로 자동 전달)

### 롤백

```bash
systemctl stop btc_bot.service
sed -i 's|BOT_VERSION   = "20.9.5"|BOT_VERSION   = "20.9.4"|' /root/tradingbot/btc_bot_v290.py
# L862-864 guard 제거:
#   if 0 < recent_pf < PERF_LOW_PF_THRESHOLD:
#       risk_pct *= PERF_LOW_RISK_MULT
# 호출부 4곳 trade_count 인자 제거
# _send_report L3208~ 실거래 PF 블록 제거
systemctl start btc_bot.service
```

---

## [문서 이관] 2026-04-21 — CLAUDE.md에서 이관

CLAUDE.md 간소화 작업 중 이관된 내용. 정보 보존 위해 원본 그대로 옮김.

### Current Status (as of 2026-04-21)

| Bot | Version | Status |
|-----|---------|--------|
| Production | v20.9.1 | `btc_bot_v290.py` (v20.9.0 + 텔레그램 최종판정 버그 수정 + E2 OR/AND 트리 + 대시보드 바 통일) |
| Previous | v20.9.0 | `btc_bot_v290.py` v20.9.0 (F10 차단 + E2b+6mo 예외 + 리포트 E2 섹션, 패치 전) |
| Previous | v20.8.1 | `btc_bot_v281.py` (AI 재학습 정책 개선: PerfDegrade OFF + Restart 리셋 + 롤백 가드 + CSV) |
| Previous | v20.8 | `btc_bot_v208.py` (Kill Switch 자동복구 + 24h 재발동 방지) |
| Previous | v20.7 | `btc_bot_v207.py` (C6 — Range step 3.0 + init 70% + MDD 20%) |
| Previous | v20.6 | `btc_bot_v206.py` (BD + E2 + 하드스톱 팬텀 가드 + 텔레그램 정기만) |
| Previous | v20.5 | `btc_bot_v205.py` (Range New + _check_hard_stop 로그 보강) |
| Backup | v20.1 | `btc_bot_v201.py` (무한 계단손절 S3 + 하드스톱 체결 강화) |
| Shadow AI | v2.0 | `shadow/shadow_bot.py` (RandomForest + River ARF Online, 독립 프로세스) |

See `btc_bot_improvement.md` for full version history, incident log, and v18 roadmap.

### v20.8.1 핵심 기능 (AI 재학습 정책 개선)

#### AR1: PerfDegrade 트리거 OFF
- 상수: `ENABLE_PERF_DEGRAD_TRIGGER = False` (L398)
- 근거: 1/1 사례 (04-18) PF 0.54→0.42 추가 악화 (`backtest/results/ai_retrain_analysis.md`)
- Periodic (30캔들) + Regime 전환 트리거만 활성

#### AR2: 재시작 시 candles_since_retrain 자동 0 리셋
- 위치: `__init__` (L1448-1456) — `_load_status` 직후
- 근거: 영속값이 ≥30이면 첫 루프에서 즉시 Periodic 발동 (04-10/04-15 사례)
- 디스크 모델은 그대로 사용, 다음 30캔들 후 정기 재학습

#### AR3: 모델 롤백 가드 (PF 단독 -0.10)
- 상수: `ENABLE_ROLLBACK_GUARD=True`, `ROLLBACK_PF_THRESHOLD=0.10`, `MAX_CONSECUTIVE_REJECTS=5`
- 위치: `_do_train` (L1306-1407)
- 동작: `post_pf < pre_pf - 0.10` 시 신모델 거부, 기존 모델 유지
- 5회 연속 거부 시 강제 채택 + 텔레그램 경고
- 거부 시 `_save_ai_meta` 미호출 → Shadow 자동 sync (ai_last_train_dt 미갱신)
- Status: `consecutive_train_rejects`, `last_retrain_accepted`

#### AR4: 재학습 결과 CSV 영속화
- 파일: `/root/tradingbot/btc_retrain_history.csv`
- 컬럼: timestamp_kst, trigger_type, pre_pf, post_pf, pre_prec, post_prec, pre_acc, post_acc, samples_train, samples_test, regime, adx, accepted, reject_reason, consecutive_rejects
- 채택/거부 모두 기록 → 향후 효과 분석 즉시 가능

#### Shadow 자동 정합 (코드 변경 없음)
- Shadow는 `ai_last_train_dt` 변경 감지로 RF 동기화 (`shadow/shadow_bot.py:231`)
- AR3 거부 시 ai_last_train_dt 미갱신 → Shadow도 자동 skip

#### 대시보드 v20.8.1 갱신
- DASH1: Kill Switch 24h 카운트 + 자동복구 시각 + 한도 표시
- DASH2: 포지션 카드에 range_new_mode + pos_trail_m + pos_step_lookback + pos_init_ratio 표시
- DASH3: E2 BEAR 모드 표시 (status 신규 필드: `live_e2_bear_mode/live_daily_close/live_daily_ema200/live_e2_blocks_today`)
- DASH4: MDD 한도 0.15→0.20 (v20.7 정합)
- DASH5: AI 재학습 이력 탭 (최근 5건, btc_retrain_history.csv 활용)
- DASH6: 텔레그램 명령 도움말 탭

### v20.8 핵심 기능

#### 진입 로직
- **Range New (v20.5 R3)**: Range Score 5.0, P2 피라미딩 경로 통일, 트레일링/EMA역배열/Regime이탈 청산 OFF
- **TU 기존 P2 + BD (v20.6)**: TU 트레일링 ATR×4.5, step_lookback 2.5
- **E2 BEAR 모드 (v20.9.0, F10 기준)**: F10 = F2 (일봉<EMA200) OR F5 (4H EMA21<EMA55) 시 신규 진입 차단
  - v20.9.0 배포 (2026-04-21): F10 + E2b + E2b+6mo — #44 심층 검증 완료 (`backtest_log.md` #43/#44/#45)
  - **차단 기준 선정 근거 (#44 기반)**:
    - F10 vs F7 비교: F7은 F2 subset (중복 필터), BULL 캡처 -4.26%p, 회복 D+34 지연 → F10 채택
    - 2022 BEAR 이격 -27.52% vs 2025 -16.77% (1.64x) — F7 "대폭락 전용" 가설 부분 지지 (inconclusive, 샘플 2)
    - F10 우위 +1,389K는 복리·capital allocation 경로 효과 (단순 PnL 합산으론 -12.4% 불리)
    - 2024-03-16 유형 손실 방어 필터 추가 배제 — 유사 526봉 avg -0.07% 노이즈, 필터 4/5 차단해도 터미널 -12~42% 감소
  - **E2b 예외**: O3 유동성 흡수 시 40% 사이징 + 피라미딩 OFF (pyramid_locked=True)
  - **E2b+6mo 예외**: bars_since_e2 ≥ 1080 (180일) + gap ≤ -10% + score > 4 → 40% 사이징
  - **Flicker 정책**: Option B (F10 OFF 전환 시 bars_since_e2 즉시 0 리셋). 근거: `bt_e2_longterm_52mo.py:precompute_days_since_e2`
  - **상수**: `E2_BLOCK_MODE="F10"`, `E2_O3_EXCEPTION_ENABLED=True`, `E2_O3_EXCEPTION_RATIO=0.40`, `E2_GAP_SCORE_EXCEPTION_ENABLED=True`, `E2_GAP_THRESHOLD=-10.0`, `E2_SCORE_THRESHOLD=4.0`, `E2_REQUIRE_BARS_SINCE_E2=1080`, `E2_GAP_EXCEPTION_RATIO=0.40`
- **Range 사이징 70% (v20.7)**: TU는 80% 유지, Range만 70%
- **Range step_lookback 3.0 (v20.7)**: TU 2.5보다 더 완화

#### 청산 로직
- **하드스톱 (인트라캔들)**: 4H 봉 마감 대기 없이 stop 가격 도달 시 즉시 매도 (30초 폴링)
- **하드스톱 팬텀 가드 (v20.6)**: `_sync_balance` `_partial_selling` 가드로 sell_type 오분류 방지
- **계단손절**: TP 도달 시 손절선 인상 (lookback 적용, Range=3.0 / TU=2.5)
- **트레일링 (TU만)**: 고점 대비 ATR×trail_m (TU 4.5)

#### 리스크 관리
- **Kill Switch MDD 20% (v20.7)**: peak 대비 -20% 시 발동
- **Kill Switch PF 0.7**: 최근 20거래 PF 0.7 미만 시 발동
- **Kill Switch 자동복구 (v20.8)**: MDD < 10% 회복 + 발동 후 24h 경과 시 자동 해제
- **24h 재발동 영구 중단 (v20.8)**: 24h 내 재발동(count ≥ 2) 시 자동복구 비활성, 수동 `/killswitch reset` 필요
- **일손실 한도**: -5%

#### 상태 필드 (v20.8 기준)
- `pos_trail_m`, `pos_step_lookback`, `pos_init_ratio`: per-position 파라미터 (TU/Range 분기)
- `range_new_mode`: Range New 분기 표시
- `last_killswitch_at`, `last_killswitch_recovered_at`, `killswitch_count_24h`: Kill Switch 이력

### 텔레그램 명령

#### Kill Switch 관리
- `/killswitch off` — 수동 해제 (기존)
- `/killswitch status` — 현재 상태 + 발동/해제 이력 + 24h 카운트 조회 (v20.8 신규)
- `/killswitch reset` — 24h 카운터 초기화 + 강제 해제 (v20.8 신규, 비상 재시작용)

#### 기본 명령
- `/report` — 다음 루프에 즉시 리포트 전송
- `/pause`, `/resume` — 진입 일시 중단/재개
- `/log <keyword> [N]` — 로그 검색 (마지막 N건)

#### 리포트 정책 (v20.6)
- 정기 리포트만: 4H 봉 마감 6회/일 (KST 00/04/08/12/16/20)
- 매매 체결 알림: BUY / SELL / PYRAMID / REINVEST / SELL_PARTIAL 모두 즉시 발송
- 시스템 알림: Kill Switch 발동/해제, Regime 전환, AI 재학습, API 장애 등
- 이벤트 4종 (TP도달/손절근접/일손실근접/수익급변): v20.6에서 제거

### 봇 재시작 / 버전 업 시 필수 절차

```bash
# 기존 환경변수 충돌 방지 (반드시 먼저 실행)
unset UPBIT_ACCESS_KEY
unset UPBIT_SECRET_KEY
echo $UPBIT_ACCESS_KEY  # 빈값 확인
```

그 다음 봇 시작.

### Running the Bot

```bash
# 실전 봇 (systemd 관리)
systemctl start btc_bot.service    # 시작
systemctl stop btc_bot.service     # 종료
systemctl restart btc_bot.service  # 재시작
systemctl status btc_bot.service   # 상태 확인

# Shadow AI bot (독립 프로세스, systemd 관리)
systemctl start shadow_bot.service     # 시작
systemctl stop shadow_bot.service      # 종료
systemctl status shadow_bot.service    # 상태

# Legacy shadow bot (v17.2, nohup)
nohup /root/tradingbot/venv/bin/python btc_bot_v172_shadow.py >> btc_shadow.log 2>&1 &

# 환경 진단
/root/tradingbot/venv/bin/python check_env.py
/root/tradingbot/venv/bin/python btc_bottest.py
```

Logs: `btc_bot.log` (main), `btc_bot_error.log` (stderr), `btc_trade.log` (signal monitoring), `shadow_bot.log` (shadow AI), `btc_shadow.log` (legacy shadow).

크래시 시 자동 재시작 (RestartSec=30, 5분 내 3회 초과 시 중단) 및 텔레그램 알림 전송 (`notify_crash.sh`).

### Architecture Overview

This is a BTC/KRW automated trading bot for the Upbit exchange. It combines rule-based technical analysis with an XGBoost classifier in a 5-stage entry pipeline.

#### Key Files

| File | Purpose |
|------|---------|
| `btc_bot_v290.py` | Active production bot (v20.9.0 — F10 + E2b+6mo + 리포트/대시보드 E2) |
| `btc_bot_v281.py` | Previous version (v20.8.1, backup) |
| `btc_bot_v208.py` | Previous version (v20.8, backup) |
| `btc_bot_v207.py` | Previous version (v20.7, backup) |
| `btc_bot_v206.py` | Previous version (v20.6, backup) |
| `btc_bot_v205.py` | Previous version (v20.5, backup) |
| `btc_bot_v203.py` | Previous version (v20.3, backup) |
| `btc_bot_v202.py` | Previous version (v20.2, backup) |
| `btc_bot_v201.py` | v20.1 backup |
| `btc_bot_v200.py` | v20.0 backup |
| `shadow/shadow_bot.py` | Shadow AI v2.0 (RandomForest + River ARF Online, 독립 프로세스, 매매 영향 없음) |
| `btc_bot_v163.py` | Backup bot (v16.3) |
| `btc_bot_v172_shadow.py` | Shadow bot — same signals, no order execution |
| `btc_status.json` | Live state: position, AI metrics, trade stats, Kill Switch 이력 |
| `btc_status.json.v20.*.bak` | 버전별 status 백업 (롤백용) |
| `btc_4h.csv` | Historical 4H candle data |
| `pandas_ta/` | Local copy of pandas-ta (custom modifications) |
| `.env` | API keys (Upbit, Telegram) |
| `backtest/core/simulator.py` | 시뮬레이터 (Kill Switch 자동복구 포함, v20.8 정합) |
| `backtest/results/backtest_log.md` | 백테스트 결과 통합 로그 (이력 + 운영 규칙) |
| `backtest/results/sim_vs_prod_full_audit.md` | 시뮬-프로덕션 정합성 점검 (18 영역) |
| `backtest/results/ai_retrain_analysis.md` | AI 재학습 트리거 효과 분석 (v20.8.1 근거) |
| `backtest/results/bt_candle_count_vs_pf.md` | 캔들 누적 vs PF 백테스트 (옵션 B 기각 근거) |
| `backtest/results/v20.8.1_pre_check.md` | v20.8.1 Phase 1 사전 점검 결과 |
| `backtest/results/sim_v208.1_audit.md` | v20.8.1 시뮬 정합 점검 (AR1~AR4 ⚪ 해당없음, 2026-04-20 #41) |
| `backtest/results/bt_e2_combined_exception.md` | E2 예외 규칙 11 케이스 조합 검증 (2026-04-20 #40) |
| `btc_retrain_history.csv` | v20.8.1 AR4: 재학습 결과 영속 로그 |

Version history is tracked by filename: `btc_bot_v162.py` → `btc_bot_v162_backup.py` → `btc_bot_v163.py`. v16.3 (레거시): Bidirectional LSTM 사용, v18.0에서 XGBoost로 교체됨.

상세 내용은 `btc_bot_improvement.md` 참고.

### 봇 파일 버전 관리

- 파일명: `btc_bot_v{버전}.py` (예: `btc_bot_v200.py`, `btc_bot_v201.py`)
- 버전업 시 새 파일 생성, 기존 파일은 백업으로 유지
- systemd 서비스 파일(`btc_bot.service`)도 새 파일명으로 업데이트

### 백테스트 시뮬레이터 버전 관리

- 시뮬레이터(`backtest/core/`)는 프로덕션 코드를 따라감 (절대 반대 방향 금지)
- 프로덕션 코드가 원본, 시뮬레이터는 복제본
- 프로덕션 버전업 후 → 시뮬레이터를 프로덕션에 맞춰 업데이트
- 시뮬레이터 변경이 프로덕션 코드에 영향을 주면 절대 안됨
- 새 백테스트 작성 시 시뮬레이터/학습 함수를 복사해서 새로 만들지 말고, `core/` 모듈을 import해서 파라미터만 변경
- 백테스트 B0(기준선)은 항상 현재 프로덕션과 동일한 로직으로 실행
- `core/` 구조: `config.py`(파라미터) + `simulator.py`(매매 로직) + `trainer.py`(XGB 학습)

#### v20.8 시뮬레이터 정합성

시뮬레이터에 구현된 프로덕션 로직 (2026-04-19 18 영역 점검):

✅ **일치**:
- Kill Switch (MDD 20% + PF 0.7) (v20.7/8 추가)
- Kill Switch 자동복구 (MDD<10% + 24h + count<2) (v20.8 추가)
- Range New 청산 분기 (entry_regime=="Range" / range_new_mode)
- BD per-position 파라미터 (pos_trail_m, pos_step_lookback)
- E2 BEAR 모드 (`mod["bear_block"]` 일봉 EMA200 외부 precompute)
- Range 사이징 70% (range_initial_ratio cfg)
- Reinvest 8 조건 중 7 (Kill Switch 가드는 KS 공통 처리)
- Regime 히스테리시스 (ADX 27/23, precompute_v185)
- EMA/Score/VWAP/김프/O3/트레일링/계단손절

🟡 **차이 (영향 미미)**:
- AI Gate 처리: 시뮬은 OFF 기본 또는 통과율 추정 sampling (`ai_gate_pass_rates` cfg)
- 쿨다운: 시뮬 1 bar-based vs 프로덕션 5 time-based (4H 봉 단위라 거의 무시 가능)
- 하드스톱 인트라캔들: 시뮬 봉 close only (소폭 optimism)

⚪ **해당없음 — 시뮬 구조상 적용 대상 부재** (v20.8.1 점검, 2026-04-20 #41):
- AR1 (PerfDegrade trigger OFF): 시뮬은 **재학습 로직 자체 없음** (Periodic/Regime/PerfDegrade 3 트리거 전부 미구현)
- AR2 (재시작 candles 리셋): 시뮬은 영속 status 없음 → 재시작 개념 부재
- AR3 (롤백 가드): 시뮬은 `train_model()` 1회만 호출 (`bt_*.py`에서 외부 호출) → 신/구 모델 비교 대상 없음
- AR4 (CSV 영속화): 로깅 전용, 학습 1회 → 불필요
- **결과**: AR 4건 모두 시뮬 정합 대상 아님. 시뮬은 frozen 모델로 28개월 평가 → 모든 백테스트 케이스가 동일 모델 공유하므로 **상대 순위 불변** 보장.
- **주의**: 시뮬은 재학습 없음 → 프로덕션 실전 성과와 절대값 편차 가능 (direction indeterminate). 상대 비교만 사용.

상세는 `backtest/results/sim_vs_prod_full_audit.md` + `backtest/results/sim_v208.1_audit.md` 참고.

### Claude Code 작업 프로토콜

- 버그/개선 → 수정 후 즉시 배포 (`systemctl restart btc_bot.service`)
- 관찰 필요 항목 → `improvement_todo.md`에 추가
- 완료된 변경 → `btc_bot_improvement.md`에 기록
- 백테스트 결과 → `backtest_log.md`에 기록
- Claude.ai는 코드를 직접 짜지 않고 Claude Code에 전달할 지시서만 작성 (보유 코드가 최신본이 아니므로 직접 수정 시 꼬임)

### 주의사항

- `pandas_ta`는 pip 설치 불가 → `/root/tradingbot/pandas_ta/` 폴더에 직접 포함
- `pandas_ta_backup/`은 동일 내용 백업본 (`.gitignore`에 제외됨)
- `sys.path.append`로 로드 중 (코드 36번째 줄)

### v20.8 운영 주의사항

#### Kill Switch 발동 시 대응
1. 텔레그램 `tg_error` 알림 수신 (🛑 표시)
2. `/killswitch status` 명령으로 발동 사유 + 이력 조회
3. 24h 후 자동복구 대기 (MDD < 10% 회복 시 텔레그램 INFO 알림)
4. 24h 내 재발동 시 → 시스템 결함 의심 → 수동 점검 후 `/killswitch reset`

#### Kill Switch 발동 시 분석 TODO (`improvement_todo.md`)
- 발동 트리거 (MDD vs PF, 가격 수준, 시장 상황)
- 자동복구 효과 측정 (회복까지 소요 시간, 재진입 타이밍)
- MDD 25% 추가 상향 검토 (자동복구 있어도 빈번 시)
- 24h 재발동 시 안전장치 동작 확인

#### 일봉 EMA200 데이터 (E2 BEAR 모드)
- 매 4H 봉 시작 시 `_update_e2_bear_mode` 에서 갱신
- pyupbit 일봉 300봉 fetch (200일 EMA + 버퍼)
- 200일 데이터 부족 시 `E2_DATA_INSUFFICIENT_BEHAVIOR="allow"` 기본 (진입 허용)
- look-ahead 방지: `iloc[-2]` 전일 확정 봉 사용

#### Shadow AI v2.0 평가 일정
- 배포 2026-04-17 이후 RandomForest + River ARF Online
- 1차 판단 (~2026-04-22, 30건 누적): XGB/RF/Online 상관관계 + Regime별 편차
- 2차 판단 (~2026-05-05, 100건 누적): Precision/PF 비교 + 앙상블 시뮬
- 실거래 도입은 백테스트 기반 별도 검증 필수

#### 버전 롤백 절차
```bash
systemctl stop btc_bot.service
# systemd ExecStart 파일명을 이전 버전으로 변경
sudo sed -i 's|btc_bot_v208.py|btc_bot_v207.py|; s|v20.8|v20.7|' /etc/systemd/system/btc_bot.service
# 이전 버전 status 백업 복원
cp /root/tradingbot/btc_status.json.v20.7.bak /root/tradingbot/btc_status.json
systemctl daemon-reload && systemctl start btc_bot.service
```

### 트러블슈팅

#### sell_type 오분류 (v20.6 이전 발생)
- **증상**: 손실인데 `last_sell_reason="ATR트레일링(익절)"`로 표시
- **원인**: 팬텀 포지션 감지가 매도 진행 중에 `status.entry = 0` 리셋 → raw=0 → 오분류
- **해결**: v20.6 하드스톱 팬텀 가드 (`_sync_balance`에 `_partial_selling` 체크). 
- **v20.6 배포 후 재발 시**: `_partial_selling` 플래그가 해제되기 전에 phantom 감지가 먼저 트리거되는지 확인 (L1519)

#### 텔레그램 알림 너무 자주 옴 (v20.5 이전)
- **원인**: 이벤트 리포트 4종 (TP도달/손절근접/일손실근접/수익급변) 발동
- **해결**: v20.6에서 이벤트 리포트 전면 제거. 정기 리포트 6회/일만 수신
- **확인**: `EVENT_REPORTS_ENABLED = False` 플래그

#### Kill Switch 영구 중단 (v20.7 이전)
- **증상**: 한 번 발동 시 수동 `/killswitch off` 명령 전까지 거래 0
- **실전 영향**: 백테스트 23.97M → 현실 12.66M (-47%) 예상됨
- **해결**: v20.8 자동복구 도입 (MDD<10% + 24h)
- **확인**: `/killswitch status` 응답에 `마지막 자동복구` 시각 표시

#### legacy vs infinite 백테스트 결과 차이
- **증상**: 같은 전략이 모드에 따라 BULL +14%p 차이
- **원인**: 시뮬 기본값 `step_mode="legacy"` vs 프로덕션 `STEP_TP_INTERVAL_ATR=1.5` (infinite)
- **해결**: 백테스트 cfg에 `"step_mode": "infinite"` 명시
- **상세**: `backtest/results/sim_vs_prod_full_audit.md`

#### 백테스트 BULL 캡처 98% 주장이 실제 68%
- **증상**: 연속 운용 최종 자산 기준 B&H 대비 98% 캡처 표시
- **원인**: B&H 피크(31.26M @ 2025-10-09) 이후 -37% 폭락 → v20.6는 -8%만 떨어져 격차 수렴
- **실제 BULL 캡처**: 피크 기준 68% (32% 놓침)
- **확인**: `backtest/results/bt_v20.6_bh_gap_analysis.md`
- **개선 방향**: v20.7 C6 (Range step 3.0 + init 70%)로 피크 기준 83.57% 달성

### 이관된 섹션 목록

CLAUDE.md에서 이 파일로 이관된 섹션 (원본 제목 그대로):
1. Current Status (as of 2026-04-21)
2. v20.8.1 핵심 기능 (AI 재학습 정책 개선) — AR1~AR4 + Shadow 자동 정합 + 대시보드 갱신
3. v20.8 핵심 기능 — 진입 로직 / 청산 로직 / 리스크 관리 / 상태 필드
4. 텔레그램 명령 — Kill Switch 관리 / 기본 명령 / 리포트 정책
5. 봇 재시작 / 버전 업 시 필수 절차
6. Running the Bot
7. Architecture Overview + Key Files
8. 봇 파일 버전 관리
9. 백테스트 시뮬레이터 버전 관리 + v20.8 시뮬레이터 정합성
10. Claude Code 작업 프로토콜
11. 주의사항
12. v20.8 운영 주의사항 — Kill Switch 대응 / 분석 TODO / 일봉 EMA200 / Shadow AI 평가 일정 / 버전 롤백
13. 트러블슈팅 (sell_type 오분류 / 텔레그램 알림 빈도 / Kill Switch 영구 중단 / legacy vs infinite / BULL 캡처 98%)

백업 파일: `CLAUDE.md.bak.2026-04-21`

---

## v20.9.4 (2026-04-21) — 코드 리뷰 결과 4건 통합 수정

### 배경
v20.9.0 ~ v20.9.3 빈번한 패치 후 전체 코드 리뷰. 4가지 이슈 발견. 한 번에 통합 수정.

### 범위
봇 코드 + 시뮬레이터 + 대시보드 동시 수정. 봇/대시보드 재시작 필요.
거래 로직 변경 없음 (표시 정확성 + 백테스트 정합성 향상).

### 수정 내용

#### 1. 신호 로그 BLOCK 표기 (🔴)
- **파일**: `btc_bot_v290.py` `log_signal` (L1083), `dashboard/templates/index.html` (L853)
- **기존 버그**: 차단 이벤트(e2_bear_block 등)인데 `signal=BUY` 로 표시
- **수정**: `BLOCK_EVENTS` 집합 기반 decision 우선 판정
  - `e2_bear_block / vwap_block / obv_div_block / trend_down_block / adx_block` → "BLOCK"
  - `SELL*` → "SELL", `BUY*` → "BUY", 그 외 gate_pass → BUY / else SKIP
- **대시보드**: 신호로그 테이블에서 BLOCK 도 SELL 과 동일하게 빨강 표시 (`scls` 조건 확장)
- **검증**: 재시작 직후 13:00 이벤트 `signal=BUY` (옛 로그) → 16:51 이벤트 `signal=BLOCK` (신규 동작)

#### 2. E2 일일 카운터 자정 리셋 (🟡)
- **파일**: `btc_bot_v290.py` `BitcoinBot.__init__` + `_update_e2_bear_mode` (L2754)
- **기존 버그**: `_e2_blocks_today` / `_e2_o3_exceptions_today` / `_e2_gap_exceptions_today` 가 봇 재시작 전까지 0 으로 안 돌아감 → 자정 이후 "오늘 차단 N건" 누적 표시
- **수정**:
  - `self._e2_counters_date = None` 신규 속성
  - `_update_e2_bear_mode` 시작부에 KST 날짜 비교 → 변경 시 3개 카운터 + status 동기화 0 리셋
  - 리셋 로그: `E2 일일 카운터 리셋: 2026-04-21 → 2026-04-22 (전일 차단 N, O3예외 M, gap예외 K)`

#### 3. MR 진입 status 필드 보강 (🟡)
- **파일**: `btc_bot_v290.py` (L4080 근처 MR 진입 `status.update`)
- **기존 버그**: MR 진입 경로는 v20.5~v20.9.0 신설 필드 미초기화 → 직전 포지션 잔여값 가능성
- **수정**: `range_new_mode`, `pos_trail_m`, `pos_step_lookback`, `pos_init_ratio` (v20.5~v20.7 per-position 파라미터) + `pyramid_locked`, `e2_exception_type` (v20.9.0 E2 예외 속성) 7개 필드 명시 False/0.0/"" 초기화 — 다른 진입 경로(trend/pyramid/e2_exception)와 일관성

#### 4. simulator.py F5/F10 정합 (🔴)
- **파일**: `backtest/core/simulator.py`
- **배경**: 프로덕션 v20.9.0부터 E2 차단 = F10 = F2 OR F5 (일봉<EMA200 OR 4H EMA21<EMA55). 공통 시뮬레이터는 F2 단독만 구현 → 메모리 원칙 "시뮬레이터는 프로덕션을 따라감 / B0 = 현재 프로덕션 정합" 위배
- **수정**:
  - `precompute_bars_since_e2(e2_bear_a)` 헬퍼 추가 (Option B: ON→+1, OFF→즉시 0)
  - 신규 파라미터: `e2_block_mode` (F2|F10), `e2_f5_enabled`, `e2_require_bars_since_e2`
  - 기본값 "F2" / False / 0 (기존 백테스트 호환). 새 백테스트는 F10 opt-in
  - E2 차단 평가 로직: `_f2_active` (bear_block) OR `_f5_active` (mod["ema21_4h_a"] < ema55_4h_a)
  - gap+score 예외의 days 체크 → bars 체크 우선 분기 (`E2_REQUIRE_BARS_SINCE_E2 > 0` 이면 봉 단위, 아니면 legacy days)
- **신규 파일**: `backtest/bt_v20_9_validation.py` — 정합 검증 뼈대 스크립트
  - `precompute_bars_since_e2` 단위 테스트 PASS
  - FULL 실행(52개월)은 별도 단계 (`improvement_todo.md` 관찰 항목)

### 배포
- **백업**: `btc_bot_v290.py.bak.v20.9.3` / `backtest/core/simulator.py.bak.v20.9.3` / `dashboard/templates/index.html.bak.v20.9.3`
- `BOT_VERSION`: 20.9.1 → 20.9.4
- `systemctl restart btc_bot.service` / `systemctl restart btc_dashboard.service`
- 재시작 후 로그: `BTC AI Bot v20.9.4`, 기존 모델 사용(재학습 없음), E2 F2=ON F5=OFF F10=ON 정상

### 검증 (즉시)
- BOT_VERSION = "20.9.4" ✓
- systemctl status active ✓
- 신호 로그 BLOCK 표기 전환 확인 ✓ (`e2_bear_block` 이벤트: `signal=BUY` → `signal=BLOCK`)
- simulator.py + btc_bot_v290.py 문법 OK, BitcoinBot 35 methods 구조 유지 ✓
- precompute_bars_since_e2 단위 테스트 PASS ✓

### 관찰 필요 (improvement_todo)
- 자정 (KST 00:00) 경과 시 카운터 리셋 로그 발견 (내일 00:00 이후 확인)
- simulator.py FULL 정합 검증 (bt_v20_9_validation.py 실전 실행, ±0.5% 일치)
- MR 다음 발생 시 `status.pyramid_locked=False` / `e2_exception_type=""` 확인
- 대시보드 신호로그 탭에서 BLOCK 빨강 표시 시각 확인

### 롤백
```bash
systemctl stop btc_bot.service
cp /root/tradingbot/btc_bot_v290.py.bak.v20.9.3 /root/tradingbot/btc_bot_v290.py
cp /root/tradingbot/backtest/core/simulator.py.bak.v20.9.3 /root/tradingbot/backtest/core/simulator.py
cp /root/tradingbot/dashboard/templates/index.html.bak.v20.9.3 /root/tradingbot/dashboard/templates/index.html
systemctl start btc_bot.service
systemctl restart btc_dashboard.service
```

---

## v20.9.3 (2026-04-21) — 대시보드 바 컴포넌트 교체 (기존 biBar/pctBar 재사용)

**배경**: v20.9.2에서 E2 카드 신규 생성 시 편차형 지표에 자체 `progBar`/`devBar` 구현. 
이미 파일 L213-232에 `biBar`(중앙 기준 편차) + `pctBar`(0→현재 진행률) 헬퍼 존재.
김프 바가 biBar 사용 중이었음 — 중복 구현 + 시각 불일치 + 채움 방향 오류.

**범위**: `dashboard/templates/index.html` JS만. 봇 무중단.

### 수정 내용

**자체 헬퍼 제거**: progBar/devBar 삭제. 기존 biBar/pctBar 재사용.

**각 바 컴포넌트 선택**:
| 바 | 함수 | 파라미터 | 시각 |
|---|---|---|---|
| F2 일봉 | `biBar(gap, 15)` | ±15% 범위 | 중앙에서 편차만큼만 |
| F5 4H EMA | `biBar(ema4hGap, 3)` | ±3% 범위 | 중앙에서 편차만큼만 |
| bars 예외 | `pctBar((bars/1080)*100)` | 0→100% 진행률 | 왼쪽에서 현재 진행률 |
| gap 예외 | `biBar(-(gap-gapTh), 5)` | 기준선 -10% 중앙 | 좌=미달, 우=활성 (부호 반전) |
| score 예외 | `pctBar((rs/6.3)*100, {zone:[th,th,'line']})` | 진행률+경계선 | 4.0 지점 수직선 |

**렌더링 결과** (현재 상태 기준):
- F2 gap=-9.57% → 중앙에서 왼쪽으로 약 32% 빨강 채움 (biBar .neg)
- F5 +1.24% → 중앙에서 오른쪽으로 약 21% 녹색 채움 (biBar .pos)
- bars 2/1080 → 왼쪽 끝에서 0.19% 채움 (거의 빔, pctBar .bad)
- gap 값 +0.43p 미달 → 중앙에서 왼쪽으로 약 8.6% 빨강 (biBar .neg)
- score 5.1/6.3 → 왼쪽에서 80.95% 녹색 + 63.5% 지점 수직선 (pctBar + zone line)

### 검증
- 봇 uptime: 2026-04-21 09:55:36 KST 유지 (무중단 ✅)
- 대시보드 재시작만
- 바 5개 모두 기존 biBar/pctBar 호출 확인
- 김프 바와 시각 일관성 확보

---

## v20.9.2 (2026-04-21) — 대시보드 바 재설계 (봇 무중단 패치)

**배경**: v20.9.1 대시보드 E2 카드가 다른 리스크 카드와 시각 스타일 불일치 + 매일 변하는 원화 값을 바 스케일에 직접 넣어 부정확.

**범위**: 대시보드 전용 (`dashboard/templates/index.html` + `dashboard/app.py`). **봇 코드 수정 없음, 재시작 없음**. 봇 uptime 유지 (쿨다운/AI모델/status 영속).

### 공통 원칙
1. 바 스케일 = 편차 % 고정 (매일 불변)
2. 원화 값 + 편차 % = 텍스트에 병기
3. 모든 리스크 카드에 적용

### 수정 1: E2 카드 재설계 (4섹션)
- **Section 1 차단 조건**: F2 바 (-30%~+10%, 경계 0%), F5 바 (-5%~+5%, 경계 0%) — 각 바 하단에 KRW 원값 + 편차 KRW 병기
- **Section 2 예외**: O3 배지 + gap 완화 AND 3조건 (bars/gap/score 개별 바) — 각 바에 원화 편차 + 부족량 KRW 표시
- **Section 3 진입 판정 종합**: F10 OR 예외 → 최종 진입 허용/차단
- **Section 4 경과/카운터**: 시작일 + 오늘 카운터 + bars 카운트 시작 주석

### 수정 2: 기존 리스크 카드 원화 병기
- **MDD 카드**: peak / 현재 자산 / 낙폭 KRW 추가
- **일손실 카드**: 한도 도달 시 예상 손실 KRW 추가
- **김프 카드**: 김프 원화 근사 (`현재가 × 김프%`) — 환율 API 없이 계산

### 수정 3: `dashboard/app.py` 파생값 추가
- `live_daily_ema200_gap_krw`, `live_ema_4h_gap_krw`, `live_ema_4h_gap_pct`
- `live_bars_remaining` (1080 - bars_since_e2)
- `live_mdd_krw`, `live_peak_equity_krw`, `live_current_equity_approx`
- `live_kimp_krw_approx` (cur_price × kimp%)

### 배포
```
systemctl restart btc_dashboard.service   # 대시보드만 (3초)
# btc_bot.service는 건드리지 않음
```
- 봇 uptime 검증: ActiveEnterTimestamp 재시작 전/후 동일 (09:55:36 KST 유지) ✅
- API /api/status 파생값 모두 정상 노출
- 봇 거래 중단 없음

### 검증 (브라우저 재로드)
- E2 카드 바 스케일 고정 (편차 %)
- 바 하단에 KRW 값 + 편차 병기
- 김프/MDD/일손실에 원화 금액 추가 표시

---

## v20.9.1 (2026-04-21) — 텔레그램 최종판정 버그 수정 + E2 UI 개선

**배경**: v20.9.0 배포 후 첫 리포트(09:35 KST)에서 2가지 표시 이슈 발견:
1. 🔴 최종 판정 버그: E2 차단 중인데 "👉 매수 대기 🟢" 오표시
2. 🟡 E2 섹션 OR/AND 논리 관계 불명확 + 대시보드 바 스타일 불일치

로직 변경 없음. 표시만 수정 (patch 레벨 bump).

### 수정 내용

**수정 1: 최종 판정 버그 (치명적)**
- 원인: `can_enter` 계산에서 E2 조건 누락 → E2 차단 중인데 `can_enter=True` 평가
- 위치: `_send_report` L3095
- 수정: `can_enter`에 `not _e2_report_blocks` 조건 추가 + 최종 판정 분기에 E2 전용 메시지
- 결과: E2 활성 시 `"👉 차단: E2 BEAR 🐻 (F2) — 예외 대기 중"` + 해제 조건 줄 표시

**수정 2: E2 섹션 OR/AND 트리**
- 기존: `"🐻 E2 BEAR: ON (차단: F2)"` 단일 라인
- 신규: F2/F5 개별 badge + 예외 O3/gap완화 + gap완화 AND 3조건 (bars/gap/score) 개별 색상
- 포맷: 트리 문자 (├─, └─) + 색상 🟢/🔴

**수정 3: 대시보드 E2 카드 재디자인**
- 기존: 단순 테이블 4행
- 신규: 3섹션 (차단 조건 / 예외 조건 / 경과·카운터) + 프로그레스 바 통일
  - F2 바: -30% ~ +5% gap, 경계 0%
  - F5 바: -5% ~ +5% (EMA21-EMA55)%, 경계 0%
  - bars 바: 0 ~ 1080, 경계 1080
  - gap 바: -30% ~ 0%, 경계 -10%
  - score 바: 0 ~ 6.3, 경계 4.0
- 리스크 카드와 시각적 일관성

**수정 4: bars 초기화 주석**
- 대시보드 E2 카드 하단: `"※ v20.9.0 배포(2026-04-21 09:35) 이후부터 bars 카운트"`

### 검증
- `systemctl restart btc_bot.service` — active, v20.9.1 기동 확인 (09:55:36)
- 초기 리포트 전송 완료
- status.json `version: 20.9.1` 업데이트
- API `/api/status` 정상 노출

### 관찰 필요 (다음 4H 정기 리포트 KST 12:00)
- [ ] 텔레그램: "👉 차단: E2 BEAR 🐻 (F2)" 표시 확인
- [ ] E2 섹션 OR/AND 트리 렌더링 확인
- [ ] 대시보드 E2 카드 바 형태 렌더링 확인

---

## v20.9.0 (2026-04-21) — F10 차단 + E2b+6mo 예외 + 리포트/대시보드 E2 통합

**배경**: #43 (F10 도출) + #42 (E2b+6mo) + #44 (심층 검증 Option B 확정) 세 백테스트 결과를 단일 버전으로 통합 배포.

### 통합 4건
1. **E2 차단 기준 F2 → F10** (F2 OR F5): 2022/2025 공통 Top3 유일, 리스크 중립적 CAGR +1.47%p 개선
2. **E2b + E2b+6mo 예외 규칙**: O3 유동성 흡수 + bars≥1080(180일) & gap≤-10% & score>4 조건
3. **텔레그램 리포트 E2 섹션 추가**: v20.8.1에서 누락돼 있던 버그 수정 + F10/예외 상태 표시
4. **웹 대시보드 E2 BEAR 카드**: F2/F5/경과/예외 상세 + 포지션 카드에 e2_exception 뱃지

### 주요 구현
- **F5 계산**: `compute_e2_f5(df4h)` — 4H EMA21<EMA55 역배열 판정
- **F10 판정**: `_update_e2_bear_mode(df4h)` — F2 + F5 결합, 차단 사유(F2/F5/BOTH/NONE) 분류
- **bars_since_e2 추적**: Option B (매 OFF 즉시 0 리셋). 근거: `bt_e2_longterm_52mo.py:precompute_days_since_e2` 시뮬 정합
- **예외 평가 위치**: `gate_pass` 브랜치 내부 (rule_score 계산 후) — O3 우선, 다음 bars+gap+score
- **예외 진입 속성**: `entry_type="e2_exception"`, `pyramid_locked=True` → `_auto_reinvest` + 피라미딩 루프 스킵
- **상태 불변**: 포지션 보유 중 E2 OFF 전환되어도 pyramid_locked 유지 (청산 시에만 리셋)
- **포지션 청산 4곳**: pyramid_locked/e2_exception_type 리셋 추가

### 회귀 테스트 (±0.5% 허용)
- F10 (`bt_e2_timeframe_study.py`): 목표 28,791,315 → 실측 **28,791,315** (오차 **0**) ✅
- E2b+6mo (`bt_e2_longterm_52mo.py`): 목표 27,540,000 → 실측 **27,542,773** (오차 **+0.01%**) ✅
- 시뮬 unchanged — caller가 bear_block 배열 + days_since_e2 precompute로 cfg 주입

### 배포 검증
- `systemctl restart btc_bot.service` — active (running) 확인
- 초기 로그: `E2: F2=ON F5=OFF F10=ON (reason=F2) | 일봉 112,455,000 gap -9.57% | bars 1/1080` 정상
- status.json 신규 E2 필드 12개 모두 채워짐
- `/api/status` E2 fields + `_thresholds` (e2_require_bars=1080, gap_th=-10.0, score_th=4.0, mode=F10) 확인
- 대시보드 E2 카드 렌더링 정상 (4 row: F2 / F5 / 경과 / 예외 대기 / 오늘 카운터)

### 상수 (btc_bot_v290.py)
```python
E2_BLOCK_MODE           = "F10"        # F10 = F2 OR F5
E2_F5_ENABLED           = True
E2_O3_EXCEPTION_ENABLED = True
E2_O3_EXCEPTION_RATIO   = 0.40
E2_GAP_SCORE_EXCEPTION_ENABLED = True
E2_GAP_THRESHOLD        = -10.0
E2_SCORE_THRESHOLD      = 4.0
E2_REQUIRE_BARS_SINCE_E2 = 1080        # 180일 × 6봉/일
E2_GAP_EXCEPTION_RATIO  = 0.40
```

### 관찰 필요 (improvement_todo)
- F5 flicker (52mo 143회 전환) → bars_since_e2 1080 도달 드묾 → gap 예외 발동 빈도
- 다음 BEAR 이격 심도 (F7 vs F10 가설 재검증 기회)
- 피라미드 경로 분기 효과 실전 방향성
- BULL 구간 F10 차단 증가 (62.3% vs F2 41.2%)에 따른 기회 손실 모니터링

### 롤백 절차
```bash
systemctl stop btc_bot.service
sed -i 's|btc_bot_v290.py|btc_bot_v281.py|; s|v20.9|v20.8.1|' /etc/systemd/system/btc_bot.service
cp /root/tradingbot/btc_status.json.v20.8.1.bak /root/tradingbot/btc_status.json
systemctl daemon-reload && systemctl start btc_bot.service
```

---

## v20.8.1 (2026-04-20) — AI 재학습 정책 개선 (AR1~AR4) + 대시보드 갱신

### 배경 및 근거
- **분석 1** (`backtest/results/ai_retrain_analysis.md`): v19+ 도입 후 6건의 재학습 중 4건이 PF 악화. PF 1.17→0.38 (-67%) 단조 하락. PerfDegrade 트리거가 회복 의도와 정반대로 추가 악화 (1/1)
- **분석 2** (`backtest/results/bt_candle_count_vs_pf.md`): "캔들 추가 시 PF 개선" 가설 검증 → 평가 가능 2개 시점이 정반대 결과 → 옵션 B (캔들 +5/+15/+30/+60 추가) 기각
- **결론**: 옵션 A (단순 모델 롤백) + 안전장치 추가

### 패치 4건 (AR1~AR4)

#### AR1: PerfDegrade 트리거 OFF
- 상수: `ENABLE_PERF_DEGRAD_TRIGGER = False`
- 조건 블록 (L3309-3327)에 `ENABLE_PERF_DEGRAD_TRIGGER and` 가드 추가
- 기존 PERF_DEGRAD_* 상수 보존 (롤백 용이)

#### AR2: 재시작 시 candles_since_retrain 자동 0 리셋
- 위치: `BitcoinBot.__init__` (L1448-1456)
- 봇 시작 시 status의 영속 candles_since_retrain 무시하고 0으로 시작
- 04-10/04-15 사례 (재시작 즉시 Periodic 발동) 차단

#### AR3: 모델 롤백 가드 (PF 단독 -0.10)
- 위치: `_do_train` (L1306-1407)
- 동작:
  1. 학습 전 old_pf/old_prec/old_acc 저장 (기존 코드 유지)
  2. 학습 후 `ENABLE_ROLLBACK_GUARD AND has_old AND post_pf < pre_pf - 0.10` 시 거부
  3. 거부 시 디스크 모델/메타 미변경, consecutive_train_rejects += 1
  4. 5회 연속 거부 시 강제 채택 + 텔레그램 경고
  5. 정상 채택 시 카운터 0 리셋
- 중요: 거부 시 `_save_ai_meta` 미호출 → ai_last_train_dt 미갱신 → Shadow 자동 sync
- Status: `consecutive_train_rejects`, `last_retrain_accepted` 신규 필드

#### AR4: 재학습 결과 CSV 영속화
- 파일: `/root/tradingbot/btc_retrain_history.csv`
- 위치: `_do_train` 끝부분 (AR3 후처리와 통합)
- 기록: 채택/거부 모두 (consecutive_rejects 포함)
- 활용: 대시보드 DASH5 + 향후 트리거 효과 누적 분석

### 대시보드 v20.8.1 갱신 (DASH1~DASH6)
- DASH1: Kill Switch 24h 카운트 + 자동복구 시각/잔여시간 표시
- DASH2: 포지션 카드에 진입모드/사이징/트레일링/계단lookback 표시
- DASH3: E2 BEAR 모드 표시 (status에 신규 필드 4건 추가)
- DASH4: MDD 한도 0.15→0.20 (v20.7 정합)
- DASH5: AI 재학습 이력 탭 (최근 5건 표시)
- DASH6: 텔레그램 명령 도움말 탭

### Shadow 코드 변경 없음
- shadow_bot.py는 `_check_xgb_retrain`에서 `ai_last_train_dt` 변경만 감지
- AR3 거부 시 ai_last_train_dt 미갱신 → Shadow도 자동으로 RF 재학습 skip
- 별도 동기화 코드 불필요

### 사용자 결정 사항 (Phase 1 답변)
- Q1 → A (candles 리셋, 권장)
- Q2 → 대안 A (PF 단독 -0.10)
- Q3 → YES (5회 연속 거부 시 강제 채택)
- Q4 → YES (DASH5 AI 재학습 이력 표시 포함)

### 검증 항목 (Phase 3 배포 전)
1. 텔레그램 "버전 업그레이드 v20.8 → v20.8.1" 수신
2. status.json에 `consecutive_train_rejects`, `live_e2_bear_mode` 등 신규 필드
3. PerfDegrade 조건 충족해도 학습 안 됨
4. 다음 재학습 시 CSV 정상 기록
5. 다음 재학습 시 PF 악화 시 거부 알림
6. 대시보드 Kill Switch 한도 20%, E2 BEAR, 포지션 신규 필드 표시
7. 대시보드 AI 재학습 탭 데이터 표시
8. Shadow RF가 거부된 학습은 sync 안 함
9. 48h 크래시 0건

---

## v20.8 (2026-04-19) — Kill Switch 자동복구 + 24h 재발동 방지

### 배경
- v20.7 진실 평가 결과: 백테스트 23.97M → 실전 KS_PERM 12.66M (-47%)
- 원인: Kill Switch 1회 발동(2024-10-10) 후 3340 진입 차단, BULL 전체 놓침
- KS_AUTO 모드 백테스트: 18.06M → v20.6 대비 +5.39M 개선 확인
- 프로덕션에 자동복구 도입 결정

### 변경 사항 (4건)

#### KR1: Kill Switch 자동복구
- `_check_killswitch_auto_recover` 메서드 신규
- 조건 (AND): kill_switch=True AND current_mdd<10% AND 발동 후 24h 경과
- 동작: 자동 해제 + 텔레그램 INFO 알림
- 매 루프마다 체크

#### KR2: 24h 재발동 영구 중단 안전장치
- `_trigger_kill_switch` 통합 발동 메서드 신규
- 24h 내 재발동 시 killswitch_count_24h 누적
- count >= 2 시 자동복구 비활성 (영구 중단)
- 텔레그램 tg_error 경고 ("수동 /killswitch reset 필요")

#### KR3: 발동/해제 이력 추적 (status 신규 필드 3개)
- `last_killswitch_at`: 마지막 발동 epoch
- `last_killswitch_recovered_at`: 마지막 자동복구 epoch
- `killswitch_count_24h`: 24h 내 발동 누적

#### U1: 텔레그램 명령 확장
- `/killswitch status`: 현재 상태 + 이력 조회
- `/killswitch reset`: 24h 카운터 초기화 + 해제 (비상 재시작)
- `/killswitch off`: 수동 해제 (기존 유지)

#### S1: 시뮬레이터 동기화
- `backtest/core/simulator.py` auto_recover 모드에 24h guard 추가
- `kill_switch_recover_hours`, `kill_switch_max_24h_count` cfg 키 신규

### 백테스트 검증
| 시나리오 | v20.6 | v20.7 | v20.8 (auto_recover) |
|---|---|---|---|
| 낙관 (KS OFF) | 19.55M | 23.97M | 23.97M |
| 현실 (KS PERM) | 12.67M | 14.37M | - |
| 자동복구 + AI EST | - | - | **18.06M** |

### 배포 절차
1. btc_bot_v207.py → btc_bot_v208.py 복사
2. BOT_VERSION "20.7" → "20.8"
3. 신규 메서드 + status 필드 추가
4. systemd v207 → v208
5. 검증 (status 신규 필드, /killswitch status 명령)

### 관찰 항목 (improvement_todo.md 기록)
- 자동복구 실전 발동 시 효과 측정
- 24h 재발동 시 안전장치 동작 확인
- /killswitch status 명령 사용자 활용도

---

## v20.7 (2026-04-19) — C6 채택 (Range step + 사이징 + Kill Switch 상향)

### 배경
- v20.6 배포 후 28개월 연속 백테스트 + 정밀 분석 → BULL 피크 캡처 68%뿐 확인
- 12개월 미달 분석: Range 계단손절 11건이 핵심 (TU 5 vs Range 11, 2:1)
- v20.6 BD(TU 전용)는 Range 계단 11건 건드리지 못해 효과 제한적
- v20.7 R2a+TP_A 그리드 (9 케이스): TU 전용 튜닝 flat 확인 (all 3/5 기각)
- v20.7 Range grid (9 케이스) + size extreme (6 케이스) = 15 케이스 전면 백테스트
- **C6 (Range step 3.0 + init 70%) 채택**: 최종 23.97M, MDD 20.92%, BULL 피크캡 83.57%, BEAR +10.97%

### 백테스트 결과 (C6 vs B0 v20.6, 28개월 연속)
| 지표 | v20.6 | v20.7 C6 | Δ |
|---|---|---|---|
| 최종자산 | 19.55M | **23.97M** | **+4.42M (+22.6%)** |
| 수익률 | +95.46% | +139.70% | +44.24%p |
| CAGR | +33.85% | — | +7.46%p |
| OOS MDD | 26.10% | **20.92%** | **-5.18%p** |
| BULL 피크 캡처 | 68.26% | **83.57%** | +15.31%p |
| BEAR 수익 | +3.89% | **+10.97%** | +7.08%p |
| Sharpe (월간) | 1.01 | 1.23 | +0.22 |
| 거래수 | 40 | 30 | -10 |
| Range 계단손절 | 11 | 9 | -2 |
| 큰손실 (-3% 이하) | 15 | 12 | -3 |

### 변경 사항 (4건)

#### C6-1: Range 전용 step_lookback = 3.0
- `RANGE_STEP_LOOKBACK = 3.0` 신규 상수
- Range 진입 시 status["pos_step_lookback"] = 3.0 저장
- 계단손절 stop = first_entry + (new_lv - 3.0) × interval → ATR 1.5개 추가 여유
- TU는 TU_STEP_LOOKBACK=2.5 유지 (v20.6 BD)
- 전역 STEP_LOOKBACK=1.5 유지 (fallback용)

#### C6-2: Range 초기 사이징 = 70%
- `RANGE_INITIAL_RATIO = 0.70` 신규 상수
- Range 진입 buy_amount = equity × 0.70 (기존 80%)
- TU 진입은 PYRAMID_INITIAL_RATIO=0.80 유지
- pyramid_level 2+ 깊은 진입 시 포지션 상한 완화 (MDD 억제)

#### K1: MDD Kill Switch 15% → 20%
- MDD_STOP_PCT: 0.15 → 0.20
- 근거: C6 백테스트 OOS MDD 20.92% → 기존 15% 한도 달성 불가
- PF 기반 Kill Switch (KILL_SWITCH_PF=0.7)는 변경 없음

#### I1: per-position 파라미터 인프라 확장
- status["pos_init_ratio"] 신규 필드 (정보용, 진입 시 사이징 비율 기록)
- Reset 사이트 4곳 (phantom / 수동매도 / 하드스톱 / 메인 SELL) 갱신

### 배포 절차
1. btc_bot_v206.py → btc_bot_v207.py 복사
2. 상수 추가: RANGE_STEP_LOOKBACK, RANGE_INITIAL_RATIO
3. MDD_STOP_PCT 20%
4. 진입 블록 분기 추가
5. systemd ExecStart v206 → v207
6. systemctl daemon-reload && restart
7. 검증 (로그 + status + 텔레그램)

### 관찰 항목
- Range 진입 시 status.pos_step_lookback=3.0 + pos_init_ratio=0.7 확인
- TU 진입 시 status.pos_step_lookback=2.5 + pos_init_ratio=0.8 유지
- MDD 20% 한도 실전 발동 여부 (Kill Switch)
- BULL 피크 캡처 실전 측정 (백테스트 83.57% 재현)
- 깊은 피라미딩(lv 4+) 빈도 추적
- Range 계단손절 건수 (목표 감소)

---

## v20.6 (2026-04-19) — BD + E2 + 하드스톱 팬텀 가드 + 텔레그램 정기만

### 배경
5 라운드 백테스트 + 사전 점검 거쳐 도출:
1. TU 1차 단독 (legacy): B 채택 가능
2. TU 2차 조합 (legacy): B-simple / BD 양쪽 5/5 PASS
3. BD infinite 재검증: BEAR -2.83%p 실패 (legacy↔infinite 드리프트 발견)
4. R3 infinite 재검증: 5/5 PASS → R3 유지 확정
5. v20.6 후보 6 케이스: **R3+BD+E2 cont 16,005K 1순위**

E2가 BD의 BEAR 약점을 정확히 보완 (BEAR +1.63%p / MDD -2.71%p).

### 백테스트 채택안 (R3+BD+E2, infinite 모드)
| 지표 | BL | R3 | R3+BD | R3+BD+E2 | Δ vs BL |
|---|---|---|---|---|---|
| BULL | +20.87% | +45.35% | +54.85% | **+54.44%** | +33.57%p |
| BEAR | +1.58% | +4.84% | +2.01% | **+3.64%** | +2.06%p |
| cont_eq | 12,277K | 15,238K | 15,795K | **16,005K** | +30.4% |
| OOS MDD | 9.44% | 11.64% | 14.03% | **11.32%** | +1.88%p |

### 변경 사항

#### BD: TU 트레일링/계단 완화 (per-position 파라미터 인프라)
- `TU_ATR_TRAILING_MULT = 4.5` (기존 ATR_TRAILING_MULT 3.5)
- `TU_STEP_LOOKBACK = 2.5` (기존 STEP_LOOKBACK 1.5)
- status 딕셔너리 `pos_trail_m`, `pos_step_lookback` 필드 추가
- TU 피라미딩 진입 시 status에 TU 전용값 저장, 없으면 전역 fallback
- Range New(R3)는 변경 없음 (Range 진입은 pos_*=0 → 전역 상수 사용)
- `calc_trailing_stop(... trail_m=None)` 시그니처 확장

#### E2: 일봉 EMA200 기반 BEAR 모드 — 신규 진입 OFF
- `compute_e2_bear_mode()`: pyupbit 일봉 300봉 fetch → ta.ema(close, 200)
- 전일 확정 봉(iloc[-2]) 기준 (look-ahead 방지)
- `_update_e2_bear_mode()`: 4H 봉 시작 시 1회 갱신, 모드 전환 시 텔레그램 INFO
- 진입 경로 (TU/Range/MR 모두)에서 BEAR 모드면 차단
- 데이터 부족(200봉 미만) 시 기본 진입 허용 (E2_DATA_INSUFFICIENT_BEHAVIOR)

#### H1: 하드스톱 팬텀 감지 버그 수정 (2026-04-19 18:52 사건)
- `_sync_balance`에 `_partial_selling` 가드 추가 (L1519)
- 하드스톱 fallback: `_sync_balance()` → `upbit_get_all_balances()` 직접 호출
- sell_type 판정에 entry≤0 fallback — avg/first_entry 사용 또는 "인트라캔들하드스톱"+STOPLOSS 보수 기본
- 원 사건: status.entry 조기 0 리셋 → raw=0 → "ATR트레일링(익절)" 오분류 + COOLDOWN_TRAILING 오적용

#### H2: log_confirmed_trade 페어링 보강
- 수동 매수 감지(L1653) 경로에 log_confirmed_trade 추가 (과거 누락)
- log_confirmed_trade 예외 시 logger.error + tg_error (silent 실패 방지)
- 과거 7건 누락분(04-10~18 PYRAMID/REINVEST/수동SELL) 백필은 별도 작업

#### U1: 텔레그램 정기 리포트만
- `EVENT_REPORTS_ENABLED = False` 플래그
- E1(TP도달) / E2(손절근접) / E3(일손실) / E4(수익급변) 호출 경로 비활성화
- _send_report 방어: event_type 오는 경우 플래그 따라 skip
- 정기 6회/일(REPORT_HOURS_KST) + 매매 체결 알림 + 시스템 알림 유지

#### S1: 시뮬레이터 legacy P2 Range New 제외 누락 수정
- `backtest/core/simulator.py` legacy P2 trailing 조건에 `not (RANGE_NEW_ENABLED and entry_regime == "Range")` 추가
- infinite P2와 정합 (infinite는 이미 제외됨, legacy만 누락이었음)

### 배포 절차
1. systemctl stop btc_bot.service
2. systemd ExecStart v205 → v206 (완료)
3. btc_status.json `last_sell_reason` 수동 정정: "ATR트레일링(익절)" → "인트라캔들하드스톱"
4. systemctl daemon-reload && systemctl start btc_bot.service

### 관찰 항목 (improvement_todo.md 기록)

---

## v20.5 (2026-04-18) — Range New 전략 도입 + 하드스톱 로그 보강

### 배경
- BULL 언더퍼폼(+24%, B&H +75%) 근본 원인 조사. 7종 파라미터 조정 백테스트 전부 기각:
  regime gate / trailing mult / min_stop / trailing_pct / 사이징 / BULL 장기홀딩 / Trend_Down 50% 매도
- 진입 빈도 분석 결과 **BULL 상승 포착의 50%가 Range regime P1(breakeven)** 진입 — Regime=TU 판정이 ADX≥27 히스테리시스로 BULL의 20.6%에만 해당
- Range 전략을 P1(breakeven + 타이트 trailing) → P2(피라미딩 + 계단손절) 로 전환하고 Score 임계 타이트화가 유일한 실효 방향

### R1: Range New 전략 (백테스트 R3 채택)

#### 진입 변경 (Range regime만)
- **Score 임계 2.8 → 5.0** (타이트 필터, bt21_bars 분석 기반: BULL Range+EMA OK 봉의 p50=4.97, 5.0 이상 31%)
- 사이징: `calc_position_size` → `PYRAMID_INITIAL_RATIO` (80%, TU와 동일)
- 진입 모드: `breakeven` → `pyramid`

#### 청산 변경 (range_new_mode 포지션 한정)
- 트레일링 미적용 (`_update_trailing_stop` skip)
- Regime 전환 시 entry_type 유지 (`_check_regime_switch` skip)
- TP 기반 계단손절 + 피라미딩 + -5% ATR 하드스톱만 작동
- MR 경로/EMA역배열/regime 이탈 청산은 현 구조상 이미 트리거 없음

#### 구분 플래그
- `status["range_new_mode"]` 추가 (Range 진입 시 True, 청산 시 False)
- Trend_Up 진입 포지션은 이 플래그 False → 현행 로직 완전 유지
- `RANGE_NEW_ENABLED = True` 상수로 전체 경로 on/off 가능 (롤백 시 False)

#### 백테스트 결과 (공통 시뮬레이터 core/simulator.py, AI Gate OFF)

| 구간 | B0 (R3 base) | R3 (Range New) | Δ |
|---|---:|---:|---:|
| IS | +28.48% / MDD 19.9% | +28.48% / MDD 19.9% | — |
| BULL | +24.64% / MDD 7.4% | **+59.35%** / MDD 9.6% | **+34.71%p** |
| BEAR | +1.00% / MDD 10.2% | **+4.70%** / MDD 12.3% | +3.70%p |
| 연속자산 | 12,591K | **16,684K** | **+32.5%** |

- BULL 캡처율 32.7% → 78.7%
- OOS MDD 모두 15% 이하 (BULL 9.6%, BEAR 12.3%)
- IS MDD 19.9%가 유일 fail (4/5 통과) — 실전 OOS 기준이면 통과

추가 테스트:
- R3 + F1(ATR<85) + F3(ATR≥25) + M2(+2%→stop-3%): 전부 기각 (BULL 파괴)
- R3 + Trend_Down 50% 매도(D1): 기각 (BULL -9%p, 수익 잠식)

### L1: _check_hard_stop 로그 보강
- 주문 실패 경로 (L1649 근처) `logger.error` 추가
- verify 실패 경로 (L1664 근처) `logger.error` 추가
- 배경: 2026-04-14 23:38 하드스톱 체결 실패 당시 btc_bot.log 침묵 사건
- 영향: 기존 tg_error 유지, 가시성만 개선

### 검증 계획
- 다음 Range 진입 시 Score 5.0 임계 적용 확인 (로그)
- Range 진입 후 `btc_status.json` → `range_new_mode: true` 확인
- 현재 TU 보유 포지션 동작 불변 확인
- 48시간 `btc_bot_error.log` 크래시 0건
- Kill Switch 15% MDD 이중 방어 유지

### 롤백 절차
1. systemd ExecStart를 v203으로 복구
2. 또는 v205 내부 `RANGE_NEW_ENABLED = False`로 변경 후 재시작

---

## 아키텍처 참고

전체 구조, 5단계 진입 파이프라인, 주요 상수 등은 `CLAUDE.md` 참조.

---

## 2026-04-21 — CLAUDE.md 간소화

- **배경**: 매 세션 로드되는 파일이 비대화 (316줄) → 토큰 비용 + 최신 파악 어려움
- **작업**: 패치 이력 / 배포 상세 / 백테스트 결과를 `btc_bot_improvement.md` 상단 "[문서 이관] 2026-04-21" 섹션으로 이관
- **원칙**: CLAUDE.md는 현재 시점 운영 매뉴얼로만 유지 (100줄 이내, 원본 요약 금지)
- **이관된 섹션** (13건, 원본 그대로):
  1. Current Status table
  2. v20.8.1 핵심 기능 (AR1~AR4 + Shadow 정합 + 대시보드)
  3. v20.8 핵심 기능 (진입/청산/리스크/상태필드)
  4. 텔레그램 명령
  5. 봇 재시작 / 버전 업 필수 절차
  6. Running the Bot
  7. Architecture Overview + Key Files
  8. 봇 파일 버전 관리
  9. 백테스트 시뮬레이터 버전 관리 + v20.8 정합성
  10. Claude Code 작업 프로토콜
  11. 주의사항 (pandas_ta)
  12. v20.8 운영 주의사항 (Kill Switch / EMA200 / Shadow AI / 롤백)
  13. 트러블슈팅 5건
- **줄 수**: 316줄 → 102줄 (68% 감소)
- **이전 파일 백업**: `CLAUDE.md.bak.2026-04-21`
- **봇 재시작**: 불필요 (문서만 수정)

---

## 2026-04-21 — 문서 V1/V2 분리

- **배경**: 3개 핵심 문서가 누적 비대화 → claude.ai/Claude Code 매 세션 토큰 비용 증가 + 최신 파악 어려움
- **원칙**: 삭제 없이 분류. v2 = 운영 활성 / v1 = 아카이브. 정보 손실 0, 필요 시 v1 grep 가능
- **분리 결과**:
  - `improvement_todo.md`: 542줄 → **v2 171줄 + v1 425줄** (v2 활성 항목만: v20.9.x/v20.8.1/v20.8 관찰 + Shadow AI + 보류)
  - `btc_bot_improvement.md`: 2468줄 → **v2 903줄 + v1 1581줄** (v2: v20.5~v20.9.3 + 이관 섹션 + 이 기록)
  - `backtest/results/backtest_log.md`: 2510줄 → **v2 958줄 + v1 1573줄** (v2: 운영규칙 + #20~#44, v1: #1~#19 + Phase)
- **CLAUDE.md Related Documentation 갱신**: v2/v1 양쪽 링크 병기
- **백업 파일** (영구 보존):
  - `/root/tradingbot/improvement_todo.md.bak.2026-04-21`
  - `/root/tradingbot/btc_bot_improvement.md.bak.2026-04-21`
  - `/root/tradingbot/backtest/results/backtest_log.md.bak.2026-04-21`
- **정보 손실 검증**: 원본 줄수 ± 헤더 추가분만 차이 (improvement_todo +54, btc_bot_improvement +16, backtest_log +21)
- **봇 재시작**: 불필요 (문서만 수정)

---

## 아카이브 참조

v16.3 / v18.x / v19.x / v20.0~v20.4.1 패치 이력, 주요 사고 이력, Phase 1/2/3 개선, v20.1 쉐도우 AI 테스트 (CB/LSTM 구버전), Shadow v2.0 도입:
→ `btc_bot_improvement_v1.md`
