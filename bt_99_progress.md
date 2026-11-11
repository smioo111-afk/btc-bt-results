# bt #99 — 시뮬 production 정합 수리 + 운영 중 결정 4건 재확인 (진행 기록)

재개 방법: 이 파일을 읽고 "다음 단계"부터 이어서 진행.

## 범위 (사용자 승인 2026-11-11)
1. 시뮬 수리(opt-in 옵션, 기존 B0 회귀 보존): O3 끔 / 봉 내 손절(유예 없음) / 초기 손절 production 식 / 진행봉 EMA / 데이터 11월 연장
2. 새 기준에서 재확인: K4(#87) / P3(#95) / B1(#85) / B2(#82)
3. 기각 실험은 재실행하지 않음

## 사전 검토 결과 (2026-11-11)
- 회귀 5세계 PASS, 미래 정보 누수 없음(데이터 연장 시 과거 지표 불변)
- 2×2 (~05-31): O3on+K4 33.07M / O3on+K0 28.79M / O3off+K4 31.71M / O3off+K0 36.42M
- 6~10월 리플레이: 시뮬 단순합 -17% vs 실거래 +5.6% (8/19 진입 미재현, 손실 건당 ~1%p 과대)

## 진행 상황
- [x] 백업: core/simulator.py.bak.pre_99_parity
- [x] 시뮬 옵션 추가 (core/simulator.py: intrabar_stop / init_stop_prod, 기본 off) — 회귀 5세계 PASS 유지
- [x] 스크립트 bt_99_prod_parity.py (validate / matrix), 연장 데이터 btc_4h_ext_cache.csv (~2026-11-11)
- [x] validate: 실거래 6~10월 9건 대조 — 기존 시뮬 합 -14.33% → 새 기준 -4.31% (실거래 +5.56%), 진입 매칭 6/9
- [x] matrix 실행 → results/bt_99_matrix.csv
## 다음 단계
- verifier 로 matrix 수치 독립 검증 → 결과 해석·보고 → backtest_log.md / improvement_todo.md 기록 (production 변경은 사용자 승인 후)
- [x] 독립 검증 완료 (2026-11-12): 수치 전부 재현, 남은 불일치 3건(A 트레일 고점 / B 계단 TP 종가 판정 / C 청산 봉 자산 평가) 확인
- [x] 기록: bt_99_parity_full.md / backtest_log.md #99 / improvement_todo.md #V26_AUDIT / CLAUDE.md 시뮬 베이스라인
## 다음 단계 (사용자 결정 대기)
- 하위 봉 루프로 봉내 순서 모델링 후 P3/B2/K4 재판정 여부
