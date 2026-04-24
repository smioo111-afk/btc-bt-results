# AI Gate 실측 통과율 (프로덕션 로그 분석)

**작성일**: 2026-04-19
**출처**: `/root/tradingbot/btc_bot.log` + `btc_bot.log.1` (전체 운영 로그)
**총 AI Gate 평가**: 20,228회

## 전체 통과율

| 결과 | 횟수 | 비율 |
|---|---|---|
| 통과 | 19,656 | **97.17%** |
| 차단 | 572 | 2.83% |
| **합계** | **20,228** | 100% |

## Regime별 통과율

| Regime | 통과 | 차단 | 총계 | 통과율 |
|---|---|---|---|---|
| **Trend_Up** | 19,360 | 440 | 19,800 | **97.78%** |
| **Range** | 296 | 123 | 419 | **70.64%** |
| Trend_Down | 0 | 9 | 9 | 0.00% |
| Volatile | (샘플 없음) | - | - | - |

## 해석

1. **Trend_Up 시장에서 AI Gate는 거의 무효**: 97.78% 통과
   - XGB threshold가 Trend_Up 시 낮게 설정됨 (현재 regime=1 threshold)
   - 실전에서 대부분의 진입 신호가 AI Gate를 통과

2. **Range 시장에서는 AI Gate가 실질 필터**: 29.36% 차단
   - Range regime threshold가 더 엄격
   - 3건 중 1건 차단 → Range 진입 품질 관리 역할

3. **Trend_Down은 진입 금지 규칙으로 별도 차단**
   - AI Gate 검사도 거의 없음 (9건)
   - 실제 entry 차단은 regime 레벨에서 이미 완료

## 시뮬레이터 적용

backtest/core/simulator.py에 `ai_gate_pass_rates` cfg 추가:
```python
AI_EST_RATES = {
    "Trend_Up":   0.9778,
    "Range":      0.7064,
    "Trend_Down": 0.0,     # 실제론 regime 차단
    "Volatile":   1.0,     # 샘플 없음, 보수적 1.0
}
```

Seeded random sampling (seed=42) 으로 bar 단위 결정.

## 실측 기간

- 로그 크기: btc_bot.log.1 (10.5MB) + btc_bot.log (206KB)
- 운영 시작: 약 2026-04 초
- 수집 종료: 2026-04-19
- 약 17-19일간 데이터

샘플 크기 충분 (20,000+), 통계적 신뢰도 높음.

## 참고 — 시뮬 영향

28개월 재백테스트에서 AI Gate sampling 결과:
- Trend_Up 중심 거래 → AI 차단 50-90건 수준
- 최종 수익 영향 +95K~+1.7M KRW (전략별 차이)
- Trend_Up에서 거의 영향 없음, Range에서 일부 기회 차단
