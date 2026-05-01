# btc_bot_v290.py 슬림화 결과

날짜: 2026-05-02
버전: v20.9.10 (운영 코드 변경 없음 — 주석/dead code 제거만)

## A. 검수 결과

| 항목 | 결과 |
|------|------|
| `python -m py_compile` | PASS (문법 0 에러) |
| AST parse | PASS |
| `E2_ENABLED = False` (line 326 → slim) | 정상 |
| `compute_multi_ema_daily()` | 존재 |
| `_check_rollback_triggers()` | 존재 |
| `candle_log` 13컬럼 추가 | 정상 (CANDLE_LOG_COLUMNS 28컬럼) |
| 자동 알림 (`last_alert_*` dedup) | 정상 (24h DEDUP 작동) |
| 백업 `btc_bot_v290.py.bak.pre_20.9.10` | 존재 |
| 백업 `btc_bot_v290.py.bak.pre_slim` (신규) | 존재 |
| `systemctl status` | active (running) |
| 봇 로그 | 정상 — AI 모델 로드, Regime 복원, 리포트 전송 |

## B. 슬림화 결과

| | 줄 수 |
|---|---|
| 슬림 전 | 5,004 |
| 슬림 후 | **4,772** |
| 감소량 | -232 (-4.6%) |

목표였던 -20%(4,000줄)에 미달. 그 이상은 실로직(5단계 진입 / 청산 / E2 OFF / 자동 알림 / 텔레그램·대시보드 / candle_log)을 건드려야 가능 — 보존 원칙 우선 적용.

### 카테고리별 삭제 항목

| 카테고리 | 라인 |
|---|---|
| 모듈 docstring (v18~v20.6 변경 이력 → 6줄 헤더로 압축) | -152 |
| EVENT_REPORTS_* dead code (상수 5종 + `_detect_report_event()` 함수 + `_should_send_report` event_type 분기 + `_send_report` event_type 분기 + `_last_event_report` / `_last_report_pnl` 인스턴스 변수 + run-loop 비활성화 주석) | -67 |
| `PYRAMID_MAX_LEVELS` (legacy 미사용 상수) | -1 |
| `# v20.9.6: ... 제거` 자체참조 데드 주석 (#49 dead code 메모 4건) | -8 |
| 상수 코멘트 트림 (호환 표시 단순화) | -4 |

총 -232 라인.

### 변경 안 한 항목 (보존)

- 5단계 진입 파이프라인 (AI Gate / Rule Score / 리스크 / 사이징 / 청산)
- 청산 로직 (ATR 손절 / 무한 계단 TP / TU 트레일링)
- Kill Switch / 일손실 / MDD
- E2 OFF 로직 (E2_ENABLED=False, F2/F5/F10 컴포넌트 그대로)
- 자동 알림 `_check_rollback_triggers()` (일손실 -3% / 누적 -5% / BTC 1주 -10%)
- 텔레그램 정기 리포트 (6회/일) + 매매 알림 + 시스템 알림
- 대시보드 status.json 필드 (모든 `live_*`, `last_alert_*`, `last_killswitch_*` 포함)
- candle_log (28컬럼: 기본 + multi-EMA + 가상 시나리오)
- v20.7+ 변경 인라인 주석 (현재 동작 설명 — 보존)
- 모든 status.update() 페이로드 / status.json 필드명 (백업 호환성)

## C. 호환성 검증

| 검증 | 결과 |
|---|---|
| AST parse + py_compile | PASS |
| systemctl restart 후 부팅 | OK (4초 내 active) |
| 모델 로드 / Regime 복원 / candles_since_retrain 복원 | OK |
| 첫 신호 처리 (07:43 KST) | AI Gate 통과 / Score 5.1 / 포지션 1.4M / 리포트 전송 OK |
| status.json 호환 | 모든 필드명 동일, 운영 중 라이브 상태 유지 |
| 롤백 가능성 | `cp btc_bot_v290.py.bak.pre_slim btc_bot_v290.py && systemctl restart btc_bot.service` |

## 백업 파일

| 파일 | 시점 |
|---|---|
| `btc_bot_v290.py.bak.pre_20.9.10` | v20.9.10 패치 직전 (5월 2일 03:51) |
| `btc_bot_v290.py.bak.pre_75-B` | #75-B 자동 알림 추가 직전 (04:23) |
| `btc_bot_v290.py.bak.pre_slim` | **이번 슬림화 직전 (07:38, 5,004줄)** |
| `btc_bot_v290.py.bak.v20.9.3` | v20.9.3 시점 (4월 21일) |
