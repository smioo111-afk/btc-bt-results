# E2 BEAR 가상 거래 — 채택 후보 규칙 요약

**작성일**: 2026-04-20 21:37
**타겟**: `pnl_at_20bar`, **샘플 기준**: n ≥ 50

## 상위 5 후보 (평균 PnL 기준)

| 순위 | 규칙 | k | n | avg_pnl | wr | pf |
|---|---|---|---|---|---|---|
| 1 | d_ma5>ma10 AND score>4.0 AND gap<-10% | 3 | 66 | +0.89 | 77.27 | 2.69 |
| 2 | score>4.0 AND gap<-10% | 2 | 80 | +0.88 | 75.00 | 2.44 |
| 3 | o3=F AND score>4.0 AND gap<-10% | 3 | 80 | +0.88 | 75.00 | 2.44 |
| 4 | ema_ok=T AND score>4.0 AND gap<-10% | 3 | 80 | +0.88 | 75.00 | 2.44 |
| 5 | rsi4h>55 AND score>4.0 AND gap<-10% | 3 | 66 | +0.69 | 74.24 | 2.00 |


## 하위 5 (피해야 할 패턴)

| 순위 | 규칙 | k | n | avg_pnl | wr | pf |
|---|---|---|---|---|---|---|
| 1 | d_ma5>ma10 AND bnc30>10% AND adx4h>25 | 3 | 55 | -1.91 | 14.55 | 0.06 |
| 2 | o3=F AND bnc30>10% AND adx4h>25 | 3 | 66 | -1.89 | 15.15 | 0.08 |
| 3 | bnc30>10% AND adx4h>25 | 2 | 67 | -1.84 | 16.42 | 0.09 |
| 4 | ema_ok=T AND bnc30>10% AND adx4h>25 | 3 | 52 | -1.82 | 15.38 | 0.06 |
| 5 | d_ma5>ma10 AND bnc30>10% AND score>4.0 | 3 | 55 | -1.79 | 18.18 | 0.08 |


## Decision Tree 상위 leaf 3

| 순위 | 규칙 | samples | wr | avg_pnl |
|---|---|---|---|---|
| 1 | days_since_e2_start>141.417 AND adx_4h<=40.089 | 43 | 100.00 | +1.91 |
| 2 | days_since_e2_start<=141.417 AND bounce_from_low_30d_pct>8.679 AND kimp_pct>-0.440 AND adx_4h>15.811 | 149 | 0 | -1.68 |
| 3 | days_since_e2_start<=141.417 AND bounce_from_low_30d_pct<=8.679 AND nasdaq_ret_1d>0.001 AND days_since_e2_start>38.250 | 135 | 0 | -1.39 |


---

**후속 조치**:

- 상위 규칙을 프로덕션 `_update_e2_bear_mode` 에 조건부 bypass로 추가 검토
- E2b O3 예외와 교집합 영역 (o3_sweep=T AND 기타 조건) 주목
- 샘플 50 미만이면 재현성 낮음 → 다음 BEAR 사이클 추가 데이터 축적 권장