# #66 — E100 + B3 조합 — Verdict

**판정**: 🔴 RED (0/5 case 통과)
**B0 회귀**: 27,542,773 (expected 27,542,773, Δ=-0) ✅
**결과**: 모든 조합 case FAIL → 현행 v20.9.4 유지 권고 (단독·조합 모두 net-edge 부족)
**핵심 트레이드오프**: E100 조기 진입 vs rng 축소 사이즈 — 사이즈 축소가 회복기 수익도 동시 잠식
**다음 단계**: rejected_experiments.md 추가 + Phase 3 AI 교체 우선
