# v20.9.20 배포 요약 — B1 눌림목 진입 필터 (#85-RR 채택)

**배포일**: 2026-06-12 · **유형**: 매매 로직 변경 (사용자 승인)

## 근거
#85-RR (E2 OFF production 정합, 전제 감사 22항목 + B0 회귀 통과):
- CAGR **+4.03%p** (B0 +20.25% → B1 +24.28%)
- MDD **-9.52%p** (34.51% → 24.99%)
- PF +0.18 (1.39 → 1.56) · 누적 +3.53M · 승률 -0.8%p (절대수익 원칙상 무시)
- #85-R(E2 ON) 기각은 **비프로덕션 베이스라인 오류**로 번복.

## 변경
| # | 영역 | 내용 |
|---|---|---|
| 1 | 상수 | `PULLBACK_EMA21_MAX_DIST = 0.015` |
| 2 | 진입 필터 | EMA-path(비-leading) 신규 진입: `(price-EMA21)/EMA21 ≥ 1.5% → SKIP`("눌림목 대기"). Leading/O3/E2예외·피라미딩·청산 무변경 |
| 3 | candle_log | `ema21_dist` 컬럼 + `actual_block_reason="pullback_wait"` |
| 4 | 리포트 | 대기 사유 "눌림목 대기 (EMA21 +X.X%)" + can_enter 반영 |
| 5 | 시뮬 | `simulator.py` `ind["ema21"]` 기반 default 필터, `config.py` V20_CFG `pullback_ema21_filter=0.015` |
| 6 | #85 보호 | BASE85/BASE85R `pullback_ema21_filter=None` (B0 무필터 유지) |

## 검증
- **시뮬 default(filter=0.015, mode=none) == B1 (+24.28%/N86/MDD24.99%) 정확 일치** → 차기 백테스트 B0 = production.
- #85 계열 재실행: B0 +20.25%/N95, B1 +24.28%/N86 불변 (보호 확인).
- py_compile + AST(상수·게이트·토큰) 통과. 무포지션 재시작 → v20.9.20 부팅 무에러.

## 적용 범위 (중요)
- **EMA path 신규 진입만**. Leading(O3)·E2 예외·피라미딩 추매·청산 로직은 **무변경** (시뮬 `path=="EMA"` 정합).

## 모니터링 / 롤백
- 1개월: 눌림목 차단 횟수 / 재진입율(목표 ~47%) / 대체진입가Δ
- 알려진 비용: 회복기 급반등 미탑승 (RECOVERY'23 -12.38%p 구간) — 발생 시 정상
- 롤백 트리거: 3개월 라이브가 B0 시뮬 대비 **-5%p 이상 열세** → `cp btc_bot_v290.py.bak.v20.9.19 …`
