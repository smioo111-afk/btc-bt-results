# v20.8.1 시뮬레이터 정합성 점검

**작성일**: 2026-04-20
**대상**: `btc_bot_v281.py` (v20.8.1 프로덕션) ↔ `backtest/core/simulator.py` + `backtest/core/trainer.py`
**점검 범위**: AR1 (PerfDegrade OFF), AR2 (재시작 리셋), AR3 (롤백 가드), AR4 (CSV 영속화)

---

## 0) 결론 요약

| AR | 프로덕션 | 시뮬 | 정합 상태 | 영향 |
|----|----------|------|-----------|------|
| AR1 PerfDegrade OFF | `ENABLE_PERF_DEGRAD_TRIGGER=False` | **재학습 로직 자체 없음** | ⚪ 해당없음 | 없음 (AR1 취지와 일치) |
| AR2 재시작 리셋 | `_load_status` candles=0 | 영속 status 없음 | ⚪ 해당없음 | 없음 |
| AR3 롤백 가드 | `_do_train` PF -0.10 거부 | **재학습 로직 자체 없음** | ⚪ 해당없음 | 없음 (거부할 대상 없음) |
| AR4 CSV 영속화 | `btc_retrain_history.csv` | 학습 1회 → 로깅 불필요 | ⚪ 해당없음 | 없음 |

**판정**: 🟢 **재실행 불필요**. 시뮬레이터는 walk-forward 재학습 대신 `df[index < "2024-01-01"]`로 **1회 고정 학습**하는 설계이므로, AR1~AR4는 전부 재학습 정책 변경 → 시뮬에 적용 대상이 없음. 이미 수행된 E2a/E2b/E2c/E2d 결과는 그대로 유효.

**근거**: 11 케이스 모두 **동일한 frozen 모델** 공유 (`bt_e2_combined_exception.py:610` — `train_model()` 1회 호출 후 `simulate(model, ...)` 11회 반복) → 상대 순위 불변.

---

## 1) AR1: PerfDegrade Trigger OFF

### 프로덕션 코드
- `btc_bot_v281.py:398-399` — `ENABLE_PERF_DEGRAD_TRIGGER = False`
- `btc_bot_v281.py:3425-3446` — 트리거 조건문 (해당 플래그로 전체 차단)
- `btc_bot_v281.py:3307-3309` — PerfDegrade 설명 (`PF<{PERF_DEGRAD_PF_THRESH} + {PERF_DEGRAD_MIN_CANDLES}캔들 + ADX>{PERF_DEGRAD_MIN_ADX}`)

### 시뮬레이터 대응
- **없음** — `simulator.py`에 PerfDegrade 트리거뿐 아니라 **어떤 재학습 로직도 존재하지 않음**.
- `simulate()`는 사전 학습된 `model`을 인자로 받아 `model.predict_proba()` (line 325)만 호출.
- 재학습 트리거 3종 (Periodic 30캔들 / Regime전환 15캔들 / PerfDegrade 20캔들) 전부 시뮬 미구현.

### 정합 상태: ⚪ **해당없음**

### 영향 평가
- **절대값 편향**: 없음 (시뮬에 해당 트리거가 없음)
- **상대 순위 영향**: 없음
- **크기 추정**: 미미
- **AR1 취지와의 관계**: AR1은 "PerfDegrade 트리거를 끄는 것". 시뮬은 원래부터 이 트리거가 없으므로 사실상 AR1 목표와 이미 일치.
- **시뮬 설계 노트** (`simulator.py:22-28`): "AR1 (PerfDegrade trigger OFF): 시뮬레이터에 AI 재학습 트리거 로직 없음 → 영향 없음" — 이미 문서화됨.

---

## 2) AR2: 재시작 시 candles_since_retrain 리셋

### 프로덕션 코드
- `btc_bot_v281.py:1533-1540` — `_load_status` 직후 `candles_since_retrain` 강제 0 리셋
- `btc_bot_v281.py:1466-1476` — `needs_retrain(new_candles)` 판단

### 시뮬레이터 대응
- **없음** — 시뮬은 `status.json` 같은 영속 상태가 없고, "재시작" 개념 자체 부재.
- 각 백테스트는 clean slate에서 시작 → AR2가 해결하려는 "재시작 후 즉시 학습 발동" 문제 자체가 발생하지 않음.

### 정합 상태: ⚪ **해당없음**

### 영향 평가
- **절대값 편향**: 없음
- **상대 순위 영향**: 없음
- **크기 추정**: 없음

---

## 3) AR3: 모델 롤백 가드 (PF 단독 -0.10)

### 프로덕션 코드
- `btc_bot_v281.py:1244` — `_do_train(self, df)` 메인 재학습 함수
- `btc_bot_v281.py:1305-1334` — AR3 핵심 로직 (`pf_drop > ROLLBACK_PF_THRESHOLD` 시 거부)
- `btc_bot_v281.py:398-402` — 상수 `ENABLE_ROLLBACK_GUARD=True`, `ROLLBACK_PF_THRESHOLD=0.10`, `MAX_CONSECUTIVE_REJECTS=5`
- `btc_bot_v281.py:1385-1399` — 거부 시 기존 모델 유지 + `_save_ai_meta` 미호출 (Shadow 자동 sync)

### 시뮬레이터 대응
- **없음** — `trainer.py:23-99` `train_model()`은 단발 학습.
  - `simulate()` 외부에서 1회 호출되고, 반환된 모델이 시뮬 전체 구간에 사용됨.
  - 기존 모델 ↔ 신 모델 비교 대상이 존재하지 않음.
- 시뮬 내부에 재학습 루프가 없으므로 "신모델 거부"라는 개념 자체가 성립하지 않음.

### 정합 상태: ⚪ **해당없음**

### 영향 평가
- **절대값 편향**: 없음 (학습 1회만 수행 → 거부 대상 부재)
- **상대 순위 영향**: 없음 (모든 케이스가 동일 frozen 모델 공유)
- **크기 추정**: 미미
- **이론적 고려**: AR3 부재 시 시뮬의 이론적 약점 — "production은 매 재학습마다 PF가 -0.10 이상 악화되면 거부하지만, 시뮬은 매 학습마다 무조건 수용" → **시뮬이 AR3 없음 = 프로덕션보다 비관적일 가능성**. 하지만 **시뮬은 학습을 1회만 수행**하므로 애초에 악화 누적 발생 구조가 없음. 결국 AR3가 필요한 전제(다회 재학습) 자체가 성립하지 않음.
- **docstring 주석** (`simulator.py:25-26`): "AR3 (모델 롤백 가드): 시뮬레이터는 학습 후 검증/롤백 없이 그대로 사용 → 필요 시 trainer.py에 별도 추가 (현재 미적용, 백테스트 결과 해석 시 주의)" — 단발 학습 구조에서는 비교 대상이 없으므로 "주의" 수준으로만 기재됨. 이번 점검 결과도 동일 판정.

---

## 4) AR4: CSV 영속화

### 프로덕션 코드
- `btc_bot_v281.py:1446` 및 관련 `btc_retrain_history.csv` 기록 루틴 (재학습 결과 영속 로그)

### 시뮬레이터 대응
- **불필요** — 시뮬은 학습 1회만 수행하므로 history 누적 무관.

### 정합 상태: ⚪ **해당없음**

### 영향 평가
- 없음 (로깅 목적 전용 기능)

---

## 5) 왜 재실행 불필요한가 — 3 가지 관점

### 5-A. 재학습 로직 자체 부재

시뮬은 `simulate(model, ...)` 외부에서 `train_model(df_train_slice)`을 1회 호출한 뒤, 반환된 모델로 28개월 전 구간을 평가. 재학습 트리거 3종 (Periodic/Regime/PerfDegrade) 전부 미구현. 따라서 "트리거 끄기 (AR1)" 또는 "재학습 후 검증 (AR3)"은 시뮬에 적용 대상이 없음.

### 5-B. 모든 케이스가 동일 frozen 모델 공유

`bt_e2_combined_exception.py:610`에서 `model = train_model(df_all[df_all.index < "2024-01-01"])` — **단 1번만 학습**. 이후 11 케이스가 이 `model`을 동일하게 사용. E2a의 XGB 확률 = E2d5의 XGB 확률 = ... 완전 동일. 따라서 AR1/AR3이 만약 "적용되었다면" 절대값은 변할 수 있으나 **상대 순위는 절대 불변**.

### 5-C. 11 케이스 비교는 AI Gate OFF 상태에서 수행

`bt_e2_combined_exception.py:500` `patch_ai_gate_off()` — 모든 케이스에서 XGB threshold를 0.0으로 강제. AI Gate의 영향을 제거하고 E2 예외 규칙의 순수 효과만 측정. AR3의 유무와 AI Gate 정책은 직접 연관됨 (모델 거부 시 Shadow sync로 AI threshold가 바뀜) — 시뮬에선 AI Gate OFF이므로 AR3 적용 여부에 무관.

---

## 6) 재실행 여부 판단

### 6-A. 재실행 필요 조건 (AND 전부)

- AR1 또는 AR3이 시뮬에 이미 구현되어 있고
- 프로덕션과 반대 방향으로 동작하고 있고
- 상대 순위에 영향을 주는 경우

### 6-B. 판정

위 조건 전부 미충족 → **재실행 불필요**.

기존 E2a/E2b/E2c/E2d (2026-04-20 #38, #40) 결과 그대로 유효. v21 제안 (`improvement_todo.md`) 방향 유지.

### 6-C. 단, 향후 고려 사항

- **장기 로드맵**: 시뮬에 walk-forward 재학습 로직을 추가하고 AR1/AR3을 정합시키면, 프로덕션 실전 성과를 더 정확히 재현 가능. 현재는 "단발 학습" 구조로 인한 일정한 편향이 존재 (direction indeterminate, but consistent across cases).
- **실전 영향 고려 시**: 프로덕션의 재학습이 시뮬 대비 "유리한 방향"으로 작동한다면 시뮬은 실전보다 보수적 추정일 가능성. 반대도 가능. 이는 별도 실험 (walk-forward backtest) 필요.
- **현 시점 처리**: CLAUDE.md 및 backtest_log.md에 "시뮬은 단발 학습 구조, 프로덕션 재학습 정책(AR1/AR3)은 재현하지 않음" 명시 유지.

---

## 7) 참고: 프로덕션 재학습 트리거 3종 (시뮬 미구현)

| 트리거 | 프로덕션 조건 | 시뮬 구현 |
|--------|---------------|-----------|
| Periodic | `candles_since_retrain >= RETRAIN_MIN_CANDLES (30)` | 없음 |
| Regime 전환 | Regime change + `candles >= REGIME_RETRAIN_MIN_CANDLES (15)` | 없음 |
| PerfDegrade (v20.8.1 OFF) | `PF<threshold + candles>=20 + ADX>min` AND `ENABLE_PERF_DEGRAD_TRIGGER` | 없음 |

모든 경우 `_do_train()` 호출 → AR3 롤백 가드 평가 → 채택/거부.

시뮬에서는 `train_model()` 1회만 호출되어 이 전체 체인 발생 안 함.

---

## 8) 산출물 정리

- 본 리포트: `backtest/results/sim_v208.1_audit.md`
- 패치: **없음** (불일치 없음 확인)
- 재실행 결과: **없음** (불필요 판정)
- 업데이트: `CLAUDE.md` 시뮬레이터 정합성 섹션, `backtest/results/backtest_log.md` "v20.8.1 시뮬 정합 점검" 항목 추가

---

**점검자 결론**: v20.8.1 AR1~AR4는 **전부 프로덕션 학습 정책 변경**이며, 시뮬레이터는 **walk-forward 학습 자체를 구현하지 않는 설계**이므로 정합 대상이 부재. 기존 E2 백테스트 결과 (E2b Soft 후보 / E2d5 수익 1순위 / 과적합 E2c3 경고) 판정 그대로 유지. v21 제안 방향 불변.
