"""
BTC AI Trading Bot v20.9.10
5단계 진입 파이프라인:
  [1] AI Gate    — XGBoost (방향성)
  [2] Rule Score — 가중치 합산 (EMA / ATR / Volume / Breakout / 1D / RR / OBV)
  [3] 리스크     — 쿨다운 / Daily Loss / Kill Switch / MDD / VWAP / OBV DIV
  [4] 사이징     — Regime별 차등 (Trend_Up 피라미딩 / Range new / Volatile·TD 보수)
  [5] 청산       — ATR 손절 + 무한 계단 TP + TU 트레일링 + 자동 알림 (#75-B)

변경 이력은 btc_bot_improvement.md / improvement_todo.md / backtest_log.md 참조.
v20.9.10 (2026-05-02): #74 E2 OFF (데이터 누적 모드) + #75-B 자동 알림 + multi-EMA candle_log.
"""

import os, sys, time, uuid, hashlib, logging, requests, json, joblib, re
import signal as _signal
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import pyupbit
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score
from sklearn.model_selection import train_test_split
import jwt

sys.path.append(os.path.join(os.path.dirname(__file__), "pandas_ta"))
try:
    import pandas_ta as ta
except ImportError:
    print("pandas_ta 없음")

KST = ZoneInfo("Asia/Seoul")

def now_kst():
    return datetime.now(KST)

def fmt_kst(dt=None):
    if dt is None: dt = now_kst()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=KST)
    else: dt = dt.astimezone(KST)
    return dt.strftime("%Y-%m-%d %H:%M KST")

def fmt_kst_short(dt=None):
    if dt is None: dt = now_kst()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=KST)
    else: dt = dt.astimezone(KST)
    return dt.strftime("%m/%d %H:%M")

load_dotenv()
ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")
TG_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TICKER        = "KRW-BTC"
COIN          = "BTC"
TF_PRIMARY    = "minute240"
TF_DAILY      = "day"
MIN_ORDER_KRW = 6000
BOT_VERSION   = "20.9.10"

STATUS_FILE       = "btc_status.json"
TRADE_LOG         = "btc_trade.csv"
CONFIRMED_LOG     = "btc_confirmed_trades.csv"
SIGNAL_LOG        = "btc_signal.log"
XGB_PATH    = "btc_model_xgb.pkl"
LOG_FILE    = "btc_bot.log"

# ── v20.9.9 #68: 월간 리포트 보강 ──────────────────────────
MONTHLY_HISTORY_FILE = "btc_monthly_history.json"
MONTHLY_REPORT_DIR   = "/root/tradingbot/backtest/results"
MONTHLY_REPORT_RAW_BASE = "https://raw.githubusercontent.com/smioo111-afk/btc-bt-results/main"
MONTHLY_AUTO_PUSH_SH = "/root/tradingbot/backtest/auto_push.sh"
PRICE_4H_CACHE_FILE  = "btc_4h.csv"

# ── v19.4: EMA 대체 연구용 캔들 로그 ─────────────────────
CANDLE_LOG           = "btc_candle_log.csv"
CANDLE_LOG_MAX_ROWS  = 2000   # 약 333일분 (4H * 2000)
CANDLE_LOG_COLUMNS   = [
    "datetime", "price", "ema21", "ema55", "ema_ok", "ema_gap_pct",
    "o3_signal", "xgb_prob", "regime", "adx", "rsi", "obv", "obv_ema20",
    "atr_percentile", "volume_ratio", "funding_rate", "score",
    "entered", "entry_path",
    "price_after_4", "price_after_8", "pct_change_4", "pct_change_8",
    # v20.9.10: 사후 분석 / 가상 시나리오 비교용 추가 컬럼
    "ema100_d", "ema150_d", "ema200_d", "ema250_d", "ema300_d",
    "gap_e100_d", "gap_e150_d", "gap_e200_d", "gap_e250_d", "gap_e300_d",
    "virtual_e2_block_e200", "virtual_e2_block_e250", "virtual_e2_block_gap5",
    "actual_block_reason",
    "price_after_24", "pct_change_24",
]

FEE_RATE      = 0.001
SLIPPAGE_RATE = 0.002
COST_RATE     = FEE_RATE + SLIPPAGE_RATE

# ── [1단계] AI Gate ───────────────────────────────────────
AI_GATE_THRESHOLD  = 0.55           # 텔레그램 표시용 초기값
AI_UNRELIABLE_GATE = 0.62           # 텔레그램 표시용 (호환)
# ── XGB Dynamic Gate (실 사용) ───────────────────────────
XGB_ABS_THRESHOLD        = 0.58  # Cold Start fallback
XGB_DYNAMIC_PERCENTILE   = 60    # 최근 예측값 분포 상위 N%
XGB_DYNAMIC_MIN_SAMPLES  = 20

# ── Threshold 가드 (P2 사이징 + Phase4) ──────────────────
THRESHOLD_ADJUST_TRADES = 30    # calc_position_size P2 guard + phase4_min_trades

# ── [2단계] Rule Score 가중치 ─────────────────────────────
SCORE_EMA_4H    = 1.2
SCORE_ATR       = 1.0
SCORE_VOLUME    = 0.8
SCORE_BREAKOUT  = 0.8
SCORE_1D_TREND  = 0.7
SCORE_RR_FULL   = 1.3
SCORE_RR_HALF   = 0.7
SCORE_OBV       = 0.5    # v18.3: OBV>EMA20일 때 score 보너스
SCORE_THRESHOLD = 2.5    # Phase1: 3.0→2.5 (fallback)
SCORE_MAX       = (SCORE_EMA_4H + SCORE_ATR + SCORE_VOLUME +
                   SCORE_BREAKOUT + SCORE_1D_TREND + SCORE_RR_FULL + SCORE_OBV)

BREAKOUT_WINDOW    = 10
BREAKOUT_RATIO     = 0.95
VOLUME_FILTER_MULT = 1.0

# ── Regime별 Adaptive 설정 (백테스트 최적화, 2026-03-30) ─────
REGIME_CONFIG = {
    # v18.2 최적화: xgb_th 하향 (백테스트 216조합 그리드서치, PF 2.40→3.70)
    "Trend_Up":   {"xgb_th": 0.58, "score_th": 4.0, "size_mult": 0.5},
    "Range":      {"xgb_th": 0.55, "score_th": 3.0, "size_mult": 0.7},
    "Volatile":   {"xgb_th": 0.58, "score_th": 3.5, "size_mult": 0.5},
    "Trend_Down": {"xgb_th": 0.60, "score_th": 3.5, "size_mult": 0.4},
}

# ── Regime별 risk_pct 기준값 (백테스트 최적화 C안, 2026-03-30) ─
REGIME_RISK_PCT = {
    "Trend_Up":   0.020,
    "Range":      0.015,
    "Volatile":   0.010,
    "Trend_Down": 0.005,
}

# ── ATR ──────────────────────────────────────────────────
ATR_PERCENTILE_LOW    = 5
ATR_PERCENTILE_HIGH   = 95
ATR_PERCENTILE_WINDOW = 100
ATR_STOP_MULT         = 2.5   # v19.9: 2.2→2.5 (백테스트 #17)
ATR_TRAILING_MULT     = 3.5   # v19.9: 2.8→3.5 (백테스트 #17)
MIN_STOP_PCT          = 0.05
TRAILING_PCT_FROM_HIGH = 0.05

# v20.6 BD: TU 전용 트레일링 (진입 시 status.pos_trail_m에 저장, 없으면 전역값 fallback)
TU_ATR_TRAILING_MULT  = 4.5   # Trend_Up 포지션 전용 (백테스트 R3+BD+E2)

# ── [4단계] 포지션 사이징 ────────────────────────────────
RISK_PER_TRADE     = 0.01
MAX_POSITION_RATIO = 0.60
MIN_POSITION_RATIO = 0.05
MAX_RISK_PCT       = 0.025  # Trend_Up 2.0% base + AI/score 보너스 허용
CONF_HIGH_THRESH   = 0.70
CONF_LOW_THRESH    = 0.58

# ── [5단계] ATR 기반 부분 익절 ───────────────────────────
PARTIAL_TP1_ATR     = 1.8
PARTIAL_TP2_ATR     = 2.8
ADX_STRONG_THRESH   = 30.0
PARTIAL_TP_STRONG_1 = 0.25
PARTIAL_TP_STRONG_2 = 0.25
PARTIAL_TP_NORMAL_1 = 0.40
PARTIAL_TP_NORMAL_2 = 0.40

# ── v18.4: P5 피라미딩 설정 ─────────────────────────────
# v18.9 (X1): 초기 80% + TP1 +20% (95% 한도) — 사실상 풀 인베스트
PYRAMID_INITIAL_RATIO = 0.80   # Trend_Up 초기 진입 비율 (v18.9: 60%→80%)
PYRAMID_ADD_RATIOS    = [0.15]  # v19.9: 0.20→0.15 (백테스트 #17-B) TP1 추가매수 (TP2는 잔여 전부)
PYRAMID_MAX_RATIO     = 0.95   # 포지션 상한 (최소 5% 현금 유지)

# v20.1: 무한 계단손절 (#23 S3)
STEP_TP_INTERVAL_ATR  = 1.5    # TP 간격 = ATR × 1.5
STEP_LOOKBACK         = 1.5    # 손절 = (도달TP - 1.5칸) × 간격
# v20.6 BD: TU 전용 STEP_LOOKBACK (status.pos_step_lookback에 저장, 없으면 전역값 fallback)
TU_STEP_LOOKBACK      = 2.5    # Trend_Up 포지션 전용 (백테스트 R3+BD+E2)
# v20.7 C6: Range 전용 STEP_LOOKBACK (status.pos_step_lookback에 Range 진입 시 3.0 저장)
RANGE_STEP_LOOKBACK   = 3.0    # Range 포지션 전용 (백테스트 C6: +44.24%p 수익, -5.18%p MDD)
# v20.7 C6: Range 전용 초기 사이징 (TU는 PYRAMID_INITIAL_RATIO=80% 유지)
RANGE_INITIAL_RATIO   = 0.70   # Range 진입 시 70% 투입 (기본 80%에서 축소)
P1_TP1_SELL_RATIO     = 0.25   # Break-Even: TP1에서 25% 매도

# v19.3 O3: 선행신호(유동성흡수) 진입 시 안전장치 — 최대 40% / 피라미딩 OFF
LEADING_MAX_POS_RATIO = 0.40

# v20.0: 김치 프리미엄 Modifier (K2, 백테스트 #20 검증)
KIMCHI_PREMIUM_THRESHOLD = 3.0    # 김프 > 이 값이면 사이징 ×0.5
KIMCHI_PREMIUM_SIZING    = 0.5    # 축소 배수
KIMCHI_USDKRW_CACHE_TTL  = 86400  # 환율 캐시 TTL (24시간)

# ── 쿨다운 ───────────────────────────────────────────────
COOLDOWN_ENTRY     = 1800
COOLDOWN_STOPLOSS  = 14400
COOLDOWN_TRAILING  = 3600
COOLDOWN_SIGNAL    = 3600
COOLDOWN_MR        = 1800   # MR 청산 후 쿨다운

# ── 손실/수익 관리 ───────────────────────────────────────
MAX_CONSECUTIVE_LOSS  = 3
LOSS_MODE_POS_MULT    = 0.3
LOSS_MODE_GATE        = 0.65
WIN_STREAK_THRESHOLD  = 3
WIN_STREAK_MIN_WR     = 0.55
WIN_STREAK_MIN_PF     = 1.2
PERF_LOW_PF_THRESHOLD = 1.0
PERF_LOW_RISK_MULT    = 0.5

# ── Kill Switch ───────────────────────────────────────────
KILL_SWITCH_PF         = 0.7
KILL_SWITCH_MIN_TRADES = 20

# ── MDD / Daily Loss ──────────────────────────────────────
MDD_STOP_PCT     = 0.20   # v20.7 K1: 15%→20% (백테스트 C6 OOS MDD 20.92% 수용)
DAILY_LOSS_LIMIT = 0.05   # -5% (v16.3: -3%)

# ── AI 품질 ──────────────────────────────────────────────
MIN_PRECISION         = 0.42  # 현재 Prec=42.2%, 보수적 모드 해제 (0.45→0.42)
MIN_PROFIT_FACTOR     = 1.0

# ── Phase4 검토 알림 (실전 vs 백테스트 괴리 감지) ─────────
PHASE4_MIN_TRADES     = 20    # 최소 거래 수 이후 판단
PHASE4_BT_PF          = 2.76  # 백테스트 PF (Phase 1+2+3)
PHASE4_BT_WR          = 0.538 # 백테스트 승률
PHASE4_PF_THRESHOLD   = 1.5   # 실전 PF 이 미만이면 알림
PHASE4_WR_THRESHOLD   = 0.40  # 실전 승률 이 미만이면 알림
INIT_DATA_COUNT       = 3000
RETRAIN_DATA_COUNT    = 3000

# ── 학습 스케줄 (데이터 기반) ────────────────────────────
RETRAIN_MIN_DAYS     = 7    # 정기 재학습: 최소 경과일
RETRAIN_MIN_CANDLES  = 30   # 정기 재학습: 최소 누적 캔들 수

# ── Regime 변화 감지 트리거 ───────────────────────────────
REGIME_CHANGE_RETRAIN = True
REGIME_RETRAIN_MIN_CANDLES = 15   # Regime 전환 재학습: 최소 캔들 수
REGIME_RETRAIN_MIN_DAYS    = 3    # Regime 전환 재학습: 최소 경과일
PERF_DEGRAD_PF_THRESH      = 0.8  # 성능 저하 트리거: PF 기준
PERF_DEGRAD_MIN_CANDLES    = 20   # 성능 저하 트리거: 최소 캔들 수
PERF_DEGRAD_MIN_ADX        = 20   # 성능 저하 트리거: ADX 하한

# ── v20.8.1: AI 재학습 정책 개선 ──────────────────────────
# AR1: PerfDegrade trigger OFF (1/1 사례에서 PF 추가 악화 — bt_candle_count 분석)
ENABLE_PERF_DEGRAD_TRIGGER = False
# AR3: 학습 후 PF 단독 기준 롤백 가드 (PF가 -0.10 이상 악화 시 신모델 거부)
ENABLE_ROLLBACK_GUARD      = True
ROLLBACK_PF_THRESHOLD      = 0.10
MAX_CONSECUTIVE_REJECTS    = 5     # 5회 연속 거부 시 강제 채택 + 텔레그램 경고
# AR4: 재학습 결과 영속화
RETRAIN_HISTORY_CSV        = "btc_retrain_history.csv"

# ── Phase1: ADX 22~24 차단 + ADX 기반 score_th ──────────
ADX_BLOCK_LOW  = 0    # v18.2: ADX 차단 비활성화 (백테스트 TOP20 전부 차단 없음)
ADX_BLOCK_HIGH = 0    # v18.2: ADX 차단 비활성화
ADX_LOW_SCORE_TH  = 2.5  # ADX < 22 → score_th 완화 (Phase1: 4.3→2.5)
ADX_HIGH_SCORE_TH = 2.8  # ADX > 24 → score_th 완화 (Phase1: 3.5→2.8)

# v20.5 Range New: Range regime 진입 전용 타이트 Score 임계 + 플래그
RANGE_NEW_ENABLED    = True
RANGE_NEW_SCORE_TH   = 5.0    # Range 진입만 이 임계 적용 (TU/기타는 ADX 기반 유지)

# ── v18.5: Regime 히스테리시스 (Trend ↔ Range 전환 떨림 방지) ──
REGIME_HYS_ENTER = 27.0  # Trend로 진입: ADX >= 27
REGIME_HYS_EXIT  = 23.0  # Range로 해제: ADX <  23
                          # 23 ≤ ADX < 27 구간에서는 직전 Regime 유지

# ── 라벨링 ───────────────────────────────────────────────
LABEL_UP_THRESH   = 0.012   # Phase2: 0.004→0.012 (노이즈→의미있는 변동)
LABEL_DOWN_THRESH = -0.012  # Phase2: -0.004→-0.012
LABEL_FUTURE_BARS = 8       # Phase2: 3봉→8봉 (12h→32h 예측)
LABEL_MIN_SAMPLES = 400     # Phase2: 800→400 (라벨 기준 상향으로 샘플 감소 허용)

REPORT_HOURS_KST       = [0, 4, 8, 12, 16, 20]  # 4H 봉 마감 시점 6회/일

# v20.6 E2: 일봉 EMA200 기반 BEAR 모드 (신규 진입 전면 OFF)
# v20.9.10 (2026-05-02): #74 실로그 분석 기반 E2 OFF — BULL 후반 24건 차단 중 88.2%가 수익 신호 (실측).
#   BEAR 보호 가치는 BEAR 시기 도래 후 재평가 (롤백 트리거: 일손실 -3% / 누적 -5% / BTC -10% in 1주).
#   다른 7중 안전장치 (AI Gate / EMA 4H / Score / 일손실 한도 / Kill Switch / ATR / 김프) 그대로 작동.
E2_ENABLED           = False        # v20.9.10: OFF (데이터 누적 모드)
E2_DAILY_EMA_LEN     = 200
E2_DAILY_FETCH_COUNT = 300          # EMA200 여유분 확보 (200봉 + 버퍼)
E2_REFRESH_INTERVAL  = 4 * 3600     # 4H 봉 마감 주기로 갱신
E2_DATA_INSUFFICIENT_BEHAVIOR = "allow"  # 데이터 부족 시 진입 허용 (보수적이면 "block")

# v20.9.0 E2 차단 기준 F10 (F2 OR F5) + 예외 규칙 E2b + E2b+6mo
# 근거: backtest #43 (F10 도출), #42 (E2b+6mo), #44 (심층 검증 Option B)
# ─────────────────────────────────────────────────────────
# v20.9.8: E2 차단 기준 F10 → F2 (AY 채택, backtest #52)
# 근거: #52 ablation 4/4 통과 — F5 제거로 거짓 신호 손실 5건 회피
# 과거: #43 F10 채택은 예외 규칙 OFF 문맥이었음. E2b+6mo 도입 후 F5 과잉 차단됨.
E2_BLOCK_MODE           = "F2"    # "F2" | "F10" — F2 단독 채택 (v20.9.8)
E2_F5_ENABLED           = False   # v20.9.8: F5 비활성화 (AY 채택)

# E2b O3 유동성 흡수 예외
E2_O3_EXCEPTION_ENABLED = True
E2_O3_EXCEPTION_RATIO   = 0.40    # 예외 진입 사이즈 (40%)

# E2b+6mo gap+score 예외 (1080봉 = 180일 × 6봉/일)
E2_GAP_SCORE_EXCEPTION_ENABLED = True
E2_GAP_THRESHOLD        = -10.0   # 일봉 EMA200 gap 상한 (%)
E2_SCORE_THRESHOLD      = 4.0     # rule_score 하한
E2_REQUIRE_BARS_SINCE_E2 = 1080   # 180일 × 4H/일 = 1080봉
E2_GAP_EXCEPTION_RATIO  = 0.40    # 예외 진입 사이즈

# days_since_e2 flicker 정책: Option B (plain reset on OFF)
# 근거: bt_e2_longterm_52mo.py:232 precompute_days_since_e2 매 OFF 즉시 cnt=0 리셋
# 프로덕션/시뮬 동일 정책 유지. F5 flicker(52mo 143회)로 1080봉 도달 드묾 — improvement_todo 관찰 항목
API_FAIL_THRESHOLD     = 5
API_FAIL_SLEEP         = 60
API_FAIL_MAX_SLEEP     = 300
MANUAL_TRADE_THRESHOLD = 0.0001

# ── 진입 타이밍 필터 ──────────────────────────────────────
ENTRY_GAP_MAX   = 0.03

# ── v18.3: Range 평균회귀 (MR) ───────────────────────────
MR_RSI_THRESH   = 35    # RSI <= 이 값이면 과매도 (G1 최적)
MR_BB_THRESH    = 0.15  # BB position <= 이 값이면 하단 근접 (G1 최적)
MR_MAX_HOLD_BARS = 6    # MR 전용 타임아웃 (24h)

# ── 초기 손절 유예 ────────────────────────────────────────
STOP_GRACE_BARS = 3
STOP_GRACE_MULT = 1.5

# ══════════════════════════════════════════════════════════
# 로깅
# ══════════════════════════════════════════════════════════
logger = logging.getLogger("BTC_V202")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_fh  = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
_fh.setFormatter(_fmt)
if not logger.handlers:
    logger.addHandler(_fh)
    # StreamHandler 제거: systemd StandardOutput이 stdout→btc_bot.log 리다이렉트하므로
    # RotatingFileHandler + stdout 둘 다 같은 파일에 쓰면 중복됨

# 신호 전용 로거
signal_logger = logging.getLogger("BTC_SIGNAL")
signal_logger.setLevel(logging.INFO)
signal_logger.propagate = False
_sfh = RotatingFileHandler(SIGNAL_LOG, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
_sfh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
if not signal_logger.handlers:
    signal_logger.addHandler(_sfh)

# ══════════════════════════════════════════════════════════
# 텔레그램 3단계 알림
# ══════════════════════════════════════════════════════════
def send_telegram(msg, retries=3):
    if not TG_TOKEN: return False
    for attempt in range(retries):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=10)
            if resp.status_code == 200: return True
            if resp.status_code == 400:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                    json={"chat_id": TG_CHAT_ID, "text": msg}, timeout=10)
                return True
        except Exception as e:
            logger.warning(f"텔레그램 실패 ({attempt+1}/{retries}): {e}")
            if attempt < retries - 1: time.sleep(2 * (attempt + 1))
    return False

def tg_info(msg):
    """INFO 레벨 — 정기 리포트, 매매 체결 등"""
    return send_telegram(msg)

def tg_warn(msg):
    """WARN 레벨 — 임계값 근접, 연속 손실, 재학습 등"""
    return send_telegram(f"⚠️ *[WARN]* {msg}")

def tg_error(msg):
    """ERROR 레벨 — Kill Switch, MDD 초과, API 장애 등"""
    return send_telegram(f"🚨 *[ERROR]* {msg}")

# ══════════════════════════════════════════════════════════
# API 유틸
# ══════════════════════════════════════════════════════════
def _make_token(query_params=None):
    payload = {"access_key": ACCESS_KEY, "nonce": str(uuid.uuid4())}
    if query_params:
        qs = urlencode(query_params).encode("utf-8")
        m  = hashlib.sha512(); m.update(qs)
        payload["query_hash"]     = m.hexdigest()
        payload["query_hash_alg"] = "SHA512"
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def _auth_header(q=None):
    return {"Authorization": f"Bearer {_make_token(q)}"}

def api_retry(func, retries=3, delay=2):
    for i in range(retries):
        try:
            r = func()
            if r is not None: return r
        except Exception as e:
            wait = delay * (2 ** i)
            logger.warning(f"API 재시도 {i+1}/{retries}: {e} / {wait}s")
            time.sleep(wait)
    return None

def upbit_get_all_balances():
    def _call():
        resp = requests.get("https://api.upbit.com/v1/accounts",
                            headers=_auth_header(), timeout=10)
        if resp.status_code == 200:
            result = {"KRW": 0.0, "BTC": 0.0}
            for item in resp.json():
                cur = item.get("currency", "")
                if cur in result:
                    result[cur] = float(item.get("balance", 0))
            return result
        return None
    return api_retry(_call)

# ══════════════════════════════════════════════════════════
# 지표 함수
# ══════════════════════════════════════════════════════════
def get_daily_trend():
    try:
        df = api_retry(lambda: pyupbit.get_ohlcv(TICKER, interval=TF_DAILY, count=120))
        if df is None: return True, 0, 0
        ema20 = ta.ema(df["close"], 20).iloc[-1]
        ema60 = ta.ema(df["close"], 60).iloc[-1]
        up    = ema20 > ema60
        logger.info(f"1D: {'상승' if up else '하락'} EMA20:{ema20:,.0f}/EMA60:{ema60:,.0f}")
        return up, ema20, ema60
    except Exception as e:
        logger.error(f"일봉 오류: {e}"); return True, 0, 0

def compute_e2_bear_mode():
    """v20.6 E2 (F2): 일봉 종가 < 일봉 EMA200 → BEAR 모드 (F2 차단 조건).

    look-ahead 방지:
      - 일봉 데이터는 pyupbit.get_ohlcv로 가져옴. 마지막 봉은 '오늘 진행 중'일 수 있음.
      - 현재 4H 봉 시작 시점 기준, 확정된 전일까지의 데이터로 판정.
      - 즉, df.iloc[-2]의 종가와 EMA200 비교 (df.iloc[-1]은 미확정).

    반환:
      (bear_mode: bool, daily_close: float, daily_ema200: float, data_available: bool)
      bear_mode == F2 활성 여부 (F10에서는 F2 컴포넌트로 사용됨).
    """
    try:
        df = api_retry(lambda: pyupbit.get_ohlcv(
            TICKER, interval=TF_DAILY, count=E2_DAILY_FETCH_COUNT))
        if df is None or len(df) < E2_DAILY_EMA_LEN + 2:
            return False, 0.0, 0.0, False
        ema_sr = ta.ema(df["close"], E2_DAILY_EMA_LEN)
        if ema_sr is None or ema_sr.dropna().empty:
            return False, 0.0, 0.0, False
        # 확정된 전일 기준 (iloc[-2])
        daily_close  = float(df["close"].iloc[-2])
        daily_ema200 = float(ema_sr.iloc[-2])
        if np.isnan(daily_ema200) or daily_ema200 <= 0:
            return False, daily_close, 0.0, False
        bear = daily_close < daily_ema200
        return bear, daily_close, daily_ema200, True
    except Exception as e:
        logger.error(f"E2 일봉 EMA200 오류: {e}")
        return False, 0.0, 0.0, False


def compute_e2_f5(df4h):
    """v20.9.0 F5: 4H EMA21 < EMA55 (역배열) → 차단 조건 추가.
    기존 Rule Score 계산과 동일한 값을 재사용하도록 caller가 ema_s/ema_l을 전달해도 됨.
    여기서는 df4h만 받아 계산 (중복 연산 있지만 안전).

    반환:
      (f5_active: bool, ema21_4h: float, ema55_4h: float)
    """
    try:
        if df4h is None or len(df4h) < 56:
            return False, 0.0, 0.0
        ema21 = float(ta.ema(df4h["close"], 21).iloc[-1])
        ema55 = float(ta.ema(df4h["close"], 55).iloc[-1])
        if np.isnan(ema21) or np.isnan(ema55) or ema55 <= 0:
            return False, 0.0, 0.0
        return bool(ema21 < ema55), ema21, ema55
    except Exception as e:
        logger.debug(f"E2 F5 계산 오류: {e}")
        return False, 0.0, 0.0

def get_atr_regime(df4h):
    try:
        atr = ta.atr(df4h["high"], df4h["low"], df4h["close"], length=14)
        if atr is None or len(atr.dropna()) < ATR_PERCENTILE_WINDOW:
            return True, "데이터부족", 0, 0
        recent  = atr.dropna().iloc[-ATR_PERCENTILE_WINDOW:]
        cur_atr = atr.iloc[-1]
        cur_pct = float(np.mean(recent <= cur_atr) * 100)
        if cur_pct <= ATR_PERCENTILE_LOW:    regime, ok = "횡보장",     False
        elif cur_pct >= ATR_PERCENTILE_HIGH: regime, ok = "과열장",     False
        else:                                regime, ok = "적정변동성", True
        logger.debug(f"ATR: {regime} ({cur_pct:.0f}%ile / {cur_atr:,.0f})")
        return ok, regime, cur_atr, cur_pct
    except Exception as e:
        logger.error(f"ATR 오류: {e}"); return True, "오류", 0, 0

def get_adx_full(df4h):
    try:
        adx_df   = ta.adx(df4h["high"], df4h["low"], df4h["close"], length=14)
        adx_val  = float(adx_df["ADX_14"].iloc[-1])
        di_plus  = float(adx_df["DMP_14"].iloc[-1])
        di_minus = float(adx_df["DMN_14"].iloc[-1])
        bullish  = di_plus > di_minus
        logger.debug(f"ADX:{adx_val:.1f} DI+:{di_plus:.1f} DI-:{di_minus:.1f}")
        return {"adx": adx_val, "di_plus": di_plus,
                "di_minus": di_minus, "bullish": bullish}
    except Exception:
        return {"adx": 20.0, "di_plus": 20.0, "di_minus": 20.0, "bullish": True}

def classify_market(atr_ok, atr_regime, adx_info, prev_regime=None):
    """v18.5: ADX 히스테리시스 적용
      - Volatile: 기존 그대로 (ATR 과열장 우선)
      - Trend 진입: ADX >= REGIME_HYS_ENTER (27)
      - Range 해제: ADX <  REGIME_HYS_EXIT  (23)
      - 23 <= ADX < 27 회색지대: 직전 Regime(prev_regime) 유지
        (단, 직전이 Volatile이거나 None이면 fallback 으로 Range)
    """
    adx = adx_info["adx"]; bullish = adx_info["bullish"]
    if atr_regime == "과열장":
        return "Volatile"
    if adx >= REGIME_HYS_ENTER:
        return "Trend_Up" if bullish else "Trend_Down"
    if adx < REGIME_HYS_EXIT:
        return "Range"
    # 회색지대: 직전 Regime 유지
    if prev_regime in ("Trend_Up", "Trend_Down", "Range"):
        # Trend 유지 시 방향(bullish) 변동은 즉시 반영
        if prev_regime == "Trend_Up" and not bullish:
            return "Trend_Down"
        if prev_regime == "Trend_Down" and bullish:
            return "Trend_Up"
        return prev_regime
    return "Range"

def market_display(ms):
    return {"Trend_Up":"Trend 📈","Trend_Down":"Trend 📉",
            "Range":"Range 😴","Volatile":"Volatile ⚡"}.get(ms, ms)

# ══════════════════════════════════════════════════════════
# v20.9.9 #68: 월간 리포트 보강용 헬퍼
# ══════════════════════════════════════════════════════════
def _monthly_btc_change(ym):
    """해당 월의 첫/마지막 종가, 변동률 반환.
    1) btc_4h.csv 캐시 사용. 캐시가 해당 월을 커버 못하면
    2) pyupbit.get_ohlcv 일봉 fallback."""
    df_m = None
    if os.path.exists(PRICE_4H_CACHE_FILE):
        try:
            df = pd.read_csv(PRICE_4H_CACHE_FILE, index_col=0, parse_dates=True)
            df_m = df[df.index.strftime("%Y-%m") == ym]
            if df_m.empty:
                df_m = None
        except Exception as e:
            logger.debug(f"_monthly_btc_change 캐시 로드 실패: {e}")

    if df_m is None or len(df_m) < 2:
        # fallback: pyupbit 일봉 → 해당 월 필터
        try:
            year, month = int(ym[:4]), int(ym[5:7])
            month_start = datetime(year, month, 1, tzinfo=KST)
            if month == 12:
                month_end = datetime(year+1, 1, 1, tzinfo=KST)
            else:
                month_end = datetime(year, month+1, 1, tzinfo=KST)
            need_until = min(month_end, now_kst()) + timedelta(days=1)
            # 충분한 일봉 확보 (최대 200개)
            df_d = pyupbit.get_ohlcv(TICKER, interval="day", count=200,
                                     to=need_until.strftime("%Y-%m-%d %H:%M:%S"))
            if df_d is None or df_d.empty: return None
            if df_d.index.tz is None:
                df_d.index = df_d.index.tz_localize(KST)
            df_m = df_d[df_d.index.strftime("%Y-%m") == ym]
            if df_m.empty: return None
        except Exception as e:
            logger.debug(f"_monthly_btc_change pyupbit fallback 실패: {e}")
            return None

    try:
        start = float(df_m["close"].iloc[0])
        end   = float(df_m["close"].iloc[-1])
        if start <= 0: return None
        return {"start": start, "end": end,
                "change_pct": (end - start) / start * 100.0,
                "bars": len(df_m)}
    except Exception as e:
        logger.debug(f"_monthly_btc_change 계산 실패: {e}")
        return None

def _monthly_regime_distribution(ym):
    """btc_candle_log.csv 의 regime 컬럼 기준 월간 분포 (4H봉 카운트)."""
    if not os.path.exists(CANDLE_LOG): return None
    try:
        df = pd.read_csv(CANDLE_LOG)
        df = df[df["datetime"].astype(str).str.startswith(ym)]
        if df.empty: return None
        counts = df["regime"].value_counts().to_dict()
        total  = sum(counts.values())
        return {"total": total, "counts": counts,
                "pct": {k: v/total*100.0 for k, v in counts.items()}}
    except Exception as e:
        logger.debug(f"_monthly_regime_distribution 오류: {e}")
        return None

def _monthly_ai_gate_pass_rate(ym):
    """btc_signal.log 의 gate_check 이벤트 중 BUY/SKIP 비율."""
    if not os.path.exists(SIGNAL_LOG): return None
    try:
        buy = skip = 0
        with open(SIGNAL_LOG, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith(ym): continue
                if "event=gate_check" not in line: continue
                if "signal=BUY"  in line: buy  += 1
                elif "signal=SKIP" in line: skip += 1
        total = buy + skip
        if total == 0: return None
        return {"buy": buy, "skip": skip, "total": total,
                "pass_pct": buy / total * 100.0}
    except Exception as e:
        logger.debug(f"_monthly_ai_gate_pass_rate 오류: {e}")
        return None

def _parse_holding_bars(note):
    m = re.search(r"보유:(\d+)봉", str(note))
    return int(m.group(1)) if m else None

def _classify_exit(note):
    """SELL note → 청산 사유 대분류."""
    s = str(note)
    if "수동매도" in s: return "수동"
    if "사유:" in s:
        if "ATR트레일링" in s: return "트레일링"
        if "ATR손절"     in s: return "ATR손절"
        if "계단"        in s: return "계단손절"
        return "하드스톱"
    return "기타"

def _classify_entry_regime(note):
    """BUY note 의 Mkt: 필드 → 표시용 라벨 (Trend/Range/Volat)."""
    m = re.search(r"Mkt:(\S+)", str(note))
    if not m: return "Unknown"
    raw = m.group(1)
    if raw.startswith("Trend"): return "Trend"
    if raw.startswith("Range"): return "Range"
    if raw.startswith("Volat"): return "Volatile"
    return raw

def _trade_decomposition(df_trade):
    """월간 거래 df → 진입 regime / 청산 사유 / 보유시간 / 피라미딩 분해."""
    buys      = df_trade[df_trade["action"] == "BUY"]
    sells     = df_trade[df_trade["action"] == "SELL"]
    partial   = df_trade[df_trade["action"] == "SELL_PARTIAL"]
    pyramid   = df_trade[df_trade["action"] == "BUY_PYRAMID"]

    entry_regime = {"Trend": 0, "Range": 0, "Volatile": 0, "Unknown": 0}
    for _, r in buys.iterrows():
        entry_regime[_classify_entry_regime(r.get("note", ""))] += 1

    exit_kind = {"수동": 0, "트레일링": 0, "ATR손절": 0, "계단손절": 0,
                 "하드스톱": 0, "기타": 0}
    for _, r in sells.iterrows():
        exit_kind[_classify_exit(r.get("note", ""))] += 1

    holds = []
    for _, r in sells.iterrows():
        h = _parse_holding_bars(r.get("note", ""))
        if h is not None: holds.append(h)
    hold_stats = None
    if holds:
        hold_stats = {"avg_bars": float(np.mean(holds)),
                      "min_bars": int(min(holds)),
                      "max_bars": int(max(holds)),
                      "n_samples": len(holds)}

    tp1 = sum(1 for _, r in partial.iterrows() if "1차익절" in str(r.get("note", "")))
    tp2 = sum(1 for _, r in partial.iterrows() if "2차익절" in str(r.get("note", "")))

    return {"entry_regime": entry_regime,
            "exit_kind":    exit_kind,
            "hold":         hold_stats,
            "pyramid_n":    int(len(pyramid)),
            "tp1":          tp1, "tp2": tp2,
            "n_buys":       int(len(buys)),
            "n_sells_full": int(len(sells)),
            "n_partial":    int(len(partial))}

def _load_monthly_history():
    if not os.path.exists(MONTHLY_HISTORY_FILE): return {"months": {}}
    try:
        with open(MONTHLY_HISTORY_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("months", {})
        return d
    except Exception as e:
        logger.warning(f"monthly_history 로드 실패: {e}")
        return {"months": {}}

def _save_monthly_history(hist):
    try:
        with open(MONTHLY_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"monthly_history 저장 실패: {e}")

def _killswitch_count_in_month(status, ym):
    """현 status snapshot 만으로 월간 KS 발동 횟수 추정.
    last_killswitch_at 가 해당 월 안이면 1+, 아니면 0. 정밀 추적은 다음 달부터."""
    try:
        ts = float(status.get("last_killswitch_at", 0) or 0)
        if ts <= 0: return 0
        kst_dt = datetime.fromtimestamp(ts, tz=KST)
        if kst_dt.strftime("%Y-%m") != ym: return 0
        return int(status.get("killswitch_count_24h", 1) or 1)
    except Exception:
        return 0

def _retrain_count_in_month(ym):
    if not os.path.exists(RETRAIN_HISTORY_CSV): return None
    try:
        df = pd.read_csv(RETRAIN_HISTORY_CSV)
        df = df[df["timestamp_kst"].astype(str).str.startswith(ym)]
        if df.empty: return {"total": 0, "accepted": 0, "rejected": 0}
        accepted = int((df["accepted"].astype(str).str.lower() == "true").sum())
        return {"total": int(len(df)), "accepted": accepted,
                "rejected": int(len(df)) - accepted}
    except Exception as e:
        logger.debug(f"_retrain_count_in_month 오류: {e}")
        return None

def _push_monthly_report_to_github(filename):
    """auto_push.sh 실행해 backtest/results 디렉토리 GitHub 동기화."""
    try:
        if not os.path.exists(MONTHLY_AUTO_PUSH_SH):
            return None
        import subprocess
        subprocess.run([MONTHLY_AUTO_PUSH_SH], check=False, timeout=30,
                       capture_output=True)
        return f"{MONTHLY_REPORT_RAW_BASE}/{filename}"
    except Exception as e:
        logger.warning(f"월간 리포트 push 실패: {e}")
        return None

def generate_monthly_report(ym, equity=None, status=None, push=True, send_tg=True):
    """월간 리포트 생성 + Telegram 발송 + GitHub push.
    - ym: 'YYYY-MM' 문자열 (예: '2026-04')
    - equity: 현재 자산 (None 이면 status['live_equity'] 또는 initial 사용)
    - status: status 딕셔너리 (None 이면 STATUS_FILE 에서 로드)
    - push: True 면 auto_push.sh 실행 + raw URL 생성
    - send_tg: True 면 Telegram 발송"""

    # ── status 로드 ──────────────────────────────────
    if status is None:
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status = json.load(f)
        except Exception:
            status = {}
    if equity is None:
        equity = float(status.get("live_equity", 0) or
                       status.get("initial_equity", 0) or 0)

    # ── 거래 데이터 ──────────────────────────────────
    if not os.path.exists(TRADE_LOG):
        if send_tg: tg_info(f"📅 *{ym} 월간 리포트*\n거래 로그 없음")
        return {"ok": False, "reason": "no_trade_log"}
    df_all = pd.read_csv(TRADE_LOG)
    df_m   = df_all[df_all["datetime"].astype(str).str.startswith(ym)].copy()
    sells  = df_m[df_m["action"] == "SELL"]

    pnls = []
    for _, row in sells.iterrows():
        m = re.search(r"실질:([+-]?[\d.]+)%", str(row.get("note","")))
        if m:
            try: pnls.append(float(m.group(1)))
            except ValueError: pass

    if not pnls:
        msg = f"📅 *{ym} 월간 리포트*\n청산 완료 매매 없음"
        if send_tg: tg_info(msg)
        return {"ok": False, "reason": "no_pnls", "telegram_msg": msg}

    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    wr     = len(wins) / len(pnls) * 100.0
    pf     = sum(wins) / abs(sum(losses)) if losses else 9.9
    total_ret = sum(pnls)
    eq = equity if equity > 0 else 1.0
    peak = eq; mdd = 0.0
    for p in pnls:
        eq *= (1 + p/100.0)
        if eq > peak: peak = eq
        dd = (peak-eq)/peak*100.0
        if dd > mdd: mdd = dd

    # ── 보강 섹션 ────────────────────────────────────
    btc      = _monthly_btc_change(ym)
    regime   = _monthly_regime_distribution(ym)
    gate     = _monthly_ai_gate_pass_rate(ym)
    decomp   = _trade_decomposition(df_m)
    retrain  = _retrain_count_in_month(ym)
    ks_count = _killswitch_count_in_month(status, ym)

    # 추이 (전월 대비 + 누적)
    hist = _load_monthly_history()
    months = hist.get("months", {})
    prev_keys = sorted([k for k in months.keys() if k < ym])
    prev_ym   = prev_keys[-1] if prev_keys else None
    prev      = months.get(prev_ym) if prev_ym else None

    cum_return = total_ret
    cum_trades = len(pnls)
    cum_max_mdd = mdd
    bnh_cum = (btc["change_pct"] if btc else 0.0)
    for k in prev_keys:
        m = months[k]
        cum_return += float(m.get("return_pct", 0) or 0)
        cum_trades += int(m.get("trades", 0) or 0)
        cum_max_mdd = max(cum_max_mdd, float(m.get("mdd", 0) or 0))
        bnh_cum += float(m.get("btc_change_pct", 0) or 0)

    # 시작 월 기록 (첫 호출에만)
    first_month = hist.get("first_month") or ym

    edge = total_ret - (btc["change_pct"] if btc else 0.0)

    # ── 표본 신뢰도 (regime 분포) ─────────────────────
    EXPECTED_BARS = 720 // 4   # 30일 * 6봉 = 180 (30일 월 가정 4H봉)
    REGIME_MIN_BARS = 600 // 4  # 사용자 명세 600행 → 4H봉 기준 150
    regime_n = regime["total"] if regime else 0
    regime_short = regime_n < REGIME_MIN_BARS

    # ── Edge 한 줄 평가 ─────────────────────────────
    def _edge_verdict(e):
        if e is None: return ""
        if e >  5.0: return "✅ 우수"
        if e >  0.0: return "🟢 양호"
        if e > -5.0: return "🟡 보통"
        return "🔴 시장 미달 (점검 필요)"
    verdict = _edge_verdict(edge if btc else None)

    e2_active = bool(status.get("live_e2_bear_mode", False))
    cum_mdd_snap = float(status.get("current_mdd", 0) or 0) * 100.0

    # ── 본문 빌드 (Telegram + Markdown 공용) ─────────
    L = []
    L.append(f"📅 *{ym} 월간 리포트*  (v{BOT_VERSION})")
    L.append("━━━━━━━━━━━━━━━━━━━━")
    L.append("")

    # 1. 봇 성과
    bot_emoji = "✅" if total_ret > 0 else "🔴"
    L.append("📊 *봇 성과*")
    L.append(f"  {bot_emoji} 월수익     : {total_ret:+7.2f}%")
    L.append(f"  📉 MDD       : {-mdd:7.2f}%")
    L.append(f"  🔢 거래수    : {len(pnls):>4d}건  (승 {len(wins)} / 패 {len(losses)})")
    L.append(f"  🎯 승률      : {wr:6.1f}%   PF {pf:.2f}")
    if wins:   L.append(f"  📈 평균수익  : {np.mean(wins):+6.2f}%")
    if losses: L.append(f"  📉 평균손실  : {np.mean(losses):+6.2f}%")
    L.append("")

    # 2. 시장 비교
    L.append("📈 *시장 비교 (B&H)*")
    if btc:
        L.append(f"  BTC 시작가   : {btc['start']:>13,.0f} KRW")
        L.append(f"  BTC 종가     : {btc['end']:>13,.0f} KRW")
        L.append(f"  변동률       : {btc['change_pct']:+7.2f}%")
        L.append(f"  봇 수익      : {total_ret:+7.2f}%")
        L.append(f"  Edge         : {edge:+7.2f}%p  {verdict}")
    else:
        L.append("  BTC 시세 부족 — B&H 비교 불가")
    L.append("")

    # 3. Regime 분포
    L.append("🌡️ *시장 Regime 분포*")
    if regime and regime["total"] > 0:
        warn = " ⚠️" if regime_short else ""
        for k in ("Range", "Trend_Up", "Trend_Down", "Volatile"):
            v = regime["counts"].get(k, 0)
            p = regime["pct"].get(k, 0.0)
            label = {"Range":"Range    ","Trend_Up":"Trend_Up ",
                     "Trend_Down":"Trend_Dn ","Volatile":"Volatile "}[k]
            L.append(f"  {label}: {p:5.1f}%  ({v:>3d}봉)")
        L.append(f"  합계         : {regime['total']:>3d}봉{warn}")
        if regime_short:
            L.append(f"  ⚠️ 데이터 부족 ({regime['total']}/{EXPECTED_BARS}봉) — 신뢰도 제한")
    else:
        L.append("  캔들 로그 없음 — regime 분포 미산출")
        L.append("  ⚠️ 데이터 부족 (0/180봉) — 신뢰도 제한")
    L.append("")

    # 4. 거래 분해
    L.append("🎯 *거래 분해*")
    er = decomp["entry_regime"]
    L.append(f"  진입 regime  : Trend {er['Trend']} / Range {er['Range']} / "
             f"Vol {er['Volatile']} / Unk {er['Unknown']}")
    ek = decomp["exit_kind"]
    L.append(f"  청산 사유    : 트레일링 {ek['트레일링']} / ATR {ek['ATR손절']} / "
             f"계단 {ek['계단손절']} / 하드 {ek['하드스톱']}")
    L.append(f"               수동 {ek['수동']} / 기타 {ek['기타']}")
    if decomp["hold"]:
        h = decomp["hold"]
        L.append(f"  평균 보유    : {h['avg_bars']:5.1f}봉  "
                 f"({h['avg_bars']*4:.1f}H, n={h['n_samples']})")
        L.append(f"  최단/최장    : {h['min_bars']}봉 / {h['max_bars']}봉")
    else:
        L.append("  평균 보유    : 기록 없음 (수동매도 위주)")
    L.append(f"  피라미딩     : {decomp['pyramid_n']:>3d}회")
    L.append(f"  부분익절     : TP1 {decomp['tp1']} / TP2 {decomp['tp2']}")
    L.append("")

    # 5. 시스템 상태
    L.append("🛡️ *시스템 상태*")
    if gate:
        L.append(f"  AI Gate 통과 : {gate['pass_pct']:5.1f}%  "
                 f"({gate['buy']}/{gate['total']} 캔들)")
    else:
        L.append("  AI Gate 통과 : signal 로그 부족")
    L.append(f"  Kill Switch  : {ks_count:>3d}회")
    if retrain is not None:
        L.append(f"  재학습       : 시도 {retrain['total']}회  "
                 f"(승인 {retrain['accepted']} / 거부 {retrain['rejected']})")
    L.append(f"  E2 BEAR(현재): {'ON' if e2_active else 'OFF'}"
             + (f"  (사유 {status.get('live_e2_block_reason','')})" if e2_active else ""))
    L.append(f"  current_mdd  : {-cum_mdd_snap:7.2f}%")
    L.append("")

    # 6. 전월 대비
    L.append("📊 *전월 대비*")
    if prev:
        d_ret = total_ret - float(prev.get("return_pct", 0) or 0)
        d_n   = len(pnls) - int(prev.get("trades", 0) or 0)
        d_wr  = wr - float(prev.get("win_rate", 0) or 0)
        L.append(f"  수익  : {prev_ym} {prev.get('return_pct', 0):+6.2f}% → "
                 f"{ym} {total_ret:+6.2f}%  (Δ {d_ret:+.2f}%p)")
        L.append(f"  거래  : {prev_ym} {prev.get('trades', 0):>3d} → "
                 f"{ym} {len(pnls):>3d}  (Δ {d_n:+d})")
        L.append(f"  승률  : {prev_ym} {prev.get('win_rate', 0):5.1f}% → "
                 f"{ym} {wr:5.1f}%  (Δ {d_wr:+.2f}%p)")
    else:
        L.append(f"  비교 데이터 없음 ({ym} 첫 리포트 — 다음 달부터 활성)")
    L.append("")

    # 7. 누적 성과
    L.append("📈 *누적 성과*")
    months_run = len(prev_keys) + 1
    if months_run >= 2:
        L.append(f"  시작 월      : {first_month}")
        L.append(f"  누적 거래    : {cum_trades:>4d}건")
        L.append(f"  누적 수익    : {cum_return:+7.2f}%")
        L.append(f"  누적 B&H     : {bnh_cum:+7.2f}%")
        L.append(f"  누적 MDD     : {-cum_max_mdd:7.2f}%")
    else:
        L.append(f"  시작 월      : {first_month}")
        L.append(f"  ({first_month}부터 활성 — 누적 비교는 다음 달부터)")
    L.append("")

    L.append("━━━━━━━━━━━━━━━━━━━━")
    L.append(f"_v{BOT_VERSION} #68 — {now_kst().strftime('%Y-%m-%d %H:%M KST')}_")

    body = "\n".join(L)

    # 마크다운은 Telegram body 그대로 + 헤더만 추가 (검색용 백업)
    markdown = f"# 📅 {ym} 월간 리포트\n\n```\n{body}\n```\n"

    # ── 마크다운 파일 저장 + GitHub push (백업, URL 텔레그램 노출 안 함) ─
    filename = f"monthly_report_{ym}.md"
    raw_url = None
    try:
        os.makedirs(MONTHLY_REPORT_DIR, exist_ok=True)
        path = os.path.join(MONTHLY_REPORT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(markdown)
        if push:
            raw_url = _push_monthly_report_to_github(filename)
    except Exception as e:
        logger.warning(f"월간 리포트 파일 저장 실패: {e}")

    # ── 히스토리 갱신 ─────────────────────────────────
    months[ym] = {
        "return_pct":     round(total_ret, 4),
        "mdd":            round(mdd, 4),
        "trades":         len(pnls),
        "win_rate":       round(wr, 2),
        "pf":             round(pf, 4),
        "btc_start":      round(btc["start"], 0) if btc else 0.0,
        "btc_end":        round(btc["end"], 0)   if btc else 0.0,
        "btc_change_pct": round(btc["change_pct"], 4) if btc else 0.0,
        "edge_pct":       round(edge, 4),
        "generated_at":   now_kst().strftime("%Y-%m-%d %H:%M KST"),
    }
    hist["months"] = months
    hist["first_month"] = first_month
    _save_monthly_history(hist)

    # ── Telegram 발송 (전체 본문) ────────────────────
    if send_tg:
        tg_info(body)

    return {"ok": True, "ym": ym, "telegram_msg": body,
            "markdown": markdown, "raw_url": raw_url,
            "summary": {"return_pct": total_ret, "wr": wr, "pf": pf,
                        "mdd": mdd, "trades": len(pnls),
                        "edge_pct": edge if btc else None,
                        "verdict": verdict}}

# ══════════════════════════════════════════════════════════
# [1단계] AI Gate
# ══════════════════════════════════════════════════════════
def check_ai_gate(xgb_prob, last_xgb_probs=None, market_state="Trend_Up"):
    # Regime별 절대 기준 OR 분포 상위 10% 둘 중 하나 통과 (백테스트와 통일)
    regime_th = REGIME_CONFIG.get(market_state, {}).get("xgb_th", XGB_ABS_THRESHOLD)
    if last_xgb_probs and len(last_xgb_probs) >= XGB_DYNAMIC_MIN_SAMPLES:
        dynamic_th = float(np.percentile(last_xgb_probs, XGB_DYNAMIC_PERCENTILE))
    else:
        dynamic_th = regime_th  # Cold Start: Regime 기준값 사용
    ok = (xgb_prob >= regime_th) or (xgb_prob >= dynamic_th)
    logger.info(f"AI Gate: {'통과' if ok else '차단'} "
                f"XGB:{xgb_prob:.3f}(regime≥{regime_th:.2f}|dyn≥{dynamic_th:.3f}) [{market_state}]")
    return ok

# ══════════════════════════════════════════════════════════
# [2단계] Rule Score
# ══════════════════════════════════════════════════════════
def calc_weighted_score(ema_s, ema_l, price, df4h,
                        is_1d_up, atr_result, cur_atr):
    score, details = 0.0, {}
    atr_ok, atr_regime, _, cur_pct = atr_result

    ema_ok  = ema_s > ema_l
    if ema_ok: score += SCORE_EMA_4H
    ema_gap = (ema_s - ema_l) / ema_l * 100
    details["EMA 4H"] = (ema_ok, SCORE_EMA_4H, f"갭{ema_gap:+.1f}%")

    if atr_ok: score += SCORE_ATR
    details[f"ATR({atr_regime})"] = (atr_ok, SCORE_ATR, f"{cur_pct:.0f}%ile")

    vol_ma  = df4h["volume"].iloc[:-1].rolling(20).mean().iloc[-1]
    vol_cur = df4h["volume"].iloc[-2]
    vol_ok  = vol_cur > vol_ma * VOLUME_FILTER_MULT
    vol_r   = vol_cur / vol_ma if vol_ma > 0 else 1.0
    if vol_ok: score += SCORE_VOLUME
    details["거래량"] = (vol_ok, SCORE_VOLUME, f"x{vol_r:.1f}")

    bl     = df4h["close"].iloc[:-1].rolling(BREAKOUT_WINDOW).max().iloc[-1]
    brk_ok = price > bl * BREAKOUT_RATIO
    if brk_ok: score += SCORE_BREAKOUT
    details["고점근접"] = (brk_ok, SCORE_BREAKOUT,
                          f"{price/bl*100:.1f}%" if bl > 0 else "N/A")

    if is_1d_up: score += SCORE_1D_TREND
    details["1D추세"] = (is_1d_up, SCORE_1D_TREND, "")

    if cur_atr > 0:
        rr = ATR_TRAILING_MULT / ATR_STOP_MULT
        if rr >= 1.8:
            rr_score = SCORE_RR_FULL
        elif rr >= 1.2:  # v18.0 수정: 1.3→1.2 (ATR_TRAILING/STOP=2.8/2.2=1.27, 기존 기준으론 항상 0점)
            rr_score = SCORE_RR_HALF + (rr-1.2)/0.6*(SCORE_RR_FULL-SCORE_RR_HALF)
        else:
            rr_score = 0.0
        score += rr_score
        details["R:R"] = (rr_score > 0, round(rr_score, 2), f"1:{rr:.2f}")
    else:
        details["R:R"] = (False, 0.0, "N/A")

    # v18.3: OBV Score 보너스 (OBV > OBV_EMA20이면 매집 중 → +0.5)
    try:
        obv = ta.obv(df4h["close"], df4h["volume"])
        obv_ema = ta.ema(obv, 20)
        if obv is not None and obv_ema is not None:
            obv_bullish = float(obv.iloc[-1]) > float(obv_ema.iloc[-1])
        else:
            obv_bullish = False
    except:
        obv_bullish = False
    if obv_bullish:
        score += SCORE_OBV
    details["OBV"] = (obv_bullish, SCORE_OBV, "매집" if obv_bullish else "분배")

    logger.info(f"Score: {score:.1f}/{SCORE_MAX:.1f} EMA:{'OK' if ema_ok else 'NG'} OBV:{'OK' if obv_bullish else 'NG'}")
    return score, details, ema_ok

# ══════════════════════════════════════════════════════════
# 최근 성과 통계
# ══════════════════════════════════════════════════════════
def calc_recent_stats(n=30):
    result = {"winrate": None, "win_streak": 0, "pf": 0.0, "trade_count": 0}
    if not os.path.exists(TRADE_LOG): return result
    try:
        df    = pd.read_csv(TRADE_LOG)
        sells = df[df["action"] == "SELL"].tail(n)
        result["trade_count"] = len(df[df["action"] == "SELL"])
        if len(sells) < 5: return result
        pnls  = [float(m.group(1))
                 for note in sells["note"]
                 for m in [re.search(r"실질:([+-][\d.]+)%", str(note))] if m]
        if not pnls: return result
        wins   = sum(1 for p in pnls if p > 0)
        gains  = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p <= 0]
        result["winrate"] = wins / len(pnls)
        result["pf"]      = sum(gains) / (sum(losses) if losses else 0.0001)
        streak = 0
        for p in reversed(pnls):
            if p > 0: streak += 1
            else: break
        result["win_streak"] = streak
    except Exception: pass
    return result

# ══════════════════════════════════════════════════════════
# [4단계] 포지션 사이징
# ══════════════════════════════════════════════════════════
def calc_position_size(account_krw, entry_price, cur_atr, ai_prob,
                       rule_score=3.0, adx_info=None,
                       market_state="Trend_Up", cons_loss=0,
                       win_streak=0, winrate=None, recent_pf=0.0,
                       trade_count=0):
    if adx_info is None: adx_info = {"adx": 20.0, "bullish": True}
    if cur_atr <= 0 or entry_price <= 0: return account_krw * 0.10
    stop_ratio = (cur_atr * ATR_STOP_MULT) / entry_price
    if stop_ratio <= 0: return account_krw * 0.10

    risk_pct = REGIME_RISK_PCT.get(market_state, RISK_PER_TRADE)

    if ai_prob >= CONF_HIGH_THRESH:
        risk_pct += 0.003
    elif ai_prob < CONF_LOW_THRESH:
        risk_pct -= 0.003
    else:
        r = (ai_prob - CONF_LOW_THRESH) / (CONF_HIGH_THRESH - CONF_LOW_THRESH)
        risk_pct += -0.003 + r * 0.006

    if rule_score >= 5.0:
        risk_pct += 0.002
    elif rule_score < 4.0:
        risk_pct -= 0.002

    if not adx_info.get("bullish", True):
        risk_pct -= 0.002

    if cons_loss >= MAX_CONSECUTIVE_LOSS:
        risk_pct *= LOSS_MODE_POS_MULT
    elif (win_streak >= WIN_STREAK_THRESHOLD and
          winrate is not None and winrate >= WIN_STREAK_MIN_WR and
          recent_pf >= WIN_STREAK_MIN_PF):
        risk_pct += 0.002

    # v20.9.5: n<30 통계 유효성 가드 (pf_investigation #47)
    if (trade_count >= THRESHOLD_ADJUST_TRADES and
            0 < recent_pf < PERF_LOW_PF_THRESHOLD):
        risk_pct *= PERF_LOW_RISK_MULT

    risk_pct = float(np.clip(risk_pct, 0.005, MAX_RISK_PCT))
    position_krw = float(np.clip(
        account_krw * risk_pct / stop_ratio,
        account_krw * MIN_POSITION_RATIO,
        account_krw * MAX_POSITION_RATIO))

    logger.info(
        f"포지션: {position_krw:,.0f} ({position_krw/account_krw:.1%}) "
        f"risk_pct:{risk_pct:.2%} stop_ratio:{stop_ratio:.2%} "
        f"AI:{ai_prob:.2f} Score:{rule_score:.1f}")
    return position_krw

def calc_atr_stop(entry_price, cur_atr):
    return entry_price - (cur_atr * ATR_STOP_MULT)

def calc_trailing_stop(highest_price, cur_atr, entry_price, trail_m=None):
    """v20.6 BD: trail_m 인자로 per-position 트레일링 배수를 받음.
    None/0이면 전역 ATR_TRAILING_MULT 사용 (하위호환)."""
    _tm = trail_m if (trail_m and trail_m > 0) else ATR_TRAILING_MULT
    atr_trail = highest_price - (cur_atr * _tm)
    pct_trail = highest_price * (1 - TRAILING_PCT_FROM_HIGH)
    return max(max(atr_trail, pct_trail), entry_price * (1 - MIN_STOP_PCT))

def determine_sell_type(s1, s3, raw_pnl):
    if s3 and raw_pnl < 0: return "ATR손절",          COOLDOWN_STOPLOSS
    elif s3:                return "ATR트레일링(익절)", COOLDOWN_TRAILING
    else:                   return "신호매도",         COOLDOWN_SIGNAL

def calc_sell_signal(ema_s, ema_l, xgb_prob, price, status):
    if not status["in_position"]: return False, False, False
    # v19.3 T3: EMA 역배열 매도 비활성화 (백테스트 #6 검증)
    # v19.9: AI 매도 비활성화 (백테스트 #17 검증)
    #   AI매도=0.38이 전체 청산의 ~80%를 차지하며 조기 청산 유발
    #   OFF 시 BULL +11%pp / BEAR +13.6%pp / 최종자산 +30.4% 개선
    return (False,
            False,
            status["stop_loss"] > 0 and price <= status["stop_loss"])

def calc_ai_metrics(y_true, y_pred_prob, features_test):
    y_pred    = (y_pred_prob > 0.5).astype(int)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall    = recall_score(y_true, y_pred, zero_division=0)
    gains, losses = [], []
    for i in range(len(y_pred)):
        if y_pred[i] == 1 and i + LABEL_FUTURE_BARS < len(features_test):
            ret = ((features_test[i + LABEL_FUTURE_BARS, 3]
                    - features_test[i, 3]) / features_test[i, 3])
            (gains if ret > 0 else losses).append(abs(ret))
    pf = sum(gains) / (sum(losses) if losses else 0.0001)
    return precision, recall, pf

def check_entry_timing(df4h, price):
    try:
        close = df4h["close"]
        if len(close) >= 2:
            gap = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
            if gap >= ENTRY_GAP_MAX:
                logger.info(f"⏸️ 진입 보류 — 갭업 ({gap:.1%})")
                return False, f"갭업({gap:.1%})"
        return True, ""
    except Exception as e:
        logger.warning(f"진입 타이밍 필터 오류: {e}")
        return True, ""


def check_liquidity_sweep(df4h, price):
    """v19.3 O3: 유동성 흡수 (Liquidity Sweep) 선행 신호.
    20봉 최저가를 0.2% 이상 하회 후 3봉 내 0.5% 이상 복귀 → 고래 매집 완료 신호.
    백테스트 #8 검증: 발동률 1.4%, T3 대비 +2.7% 자산 / MDD 불변.
    """
    try:
        if df4h is None or len(df4h) < 21: return False
        recent_low = float(df4h["low"].iloc[-21:-1].min())  # 직전 20봉 최저
        if recent_low <= 0: return False
        # 최근 3봉 중 저점 0.2% 이상 하회 여부
        swept = False
        for i in range(-3, 0):
            if float(df4h["low"].iloc[i]) < recent_low * 0.998:
                swept = True; break
        if not swept: return False
        # 현재가 저점 대비 0.5% 이상 복귀
        return price > recent_low * 1.005
    except Exception as e:
        logger.debug(f"유동성 흡수 체크 오류: {e}")
        return False

def log_trade(action, price, note=""):
    try:
        pd.DataFrame([{"datetime": fmt_kst(), "action": action,
                       "price": price, "note": note}]).to_csv(
            TRADE_LOG, mode="a", header=not os.path.exists(TRADE_LOG), index=False)
    except Exception as e:
        logger.error(f"거래 기록 오류: {e}")

CONFIRMED_COLUMNS = [
    "datetime", "action", "price", "amount", "krw",
    "pnl_pct", "sell_reason", "regime", "xgb_prob", "score",
    "ema_gap", "holding_bars", "entry_reason",
]

def log_confirmed_trade(**kwargs):
    # v20.6 H2: 예외 시 세부 로그 + 텔레그램 알림 (과거 누락 재발 방지)
    try:
        row = {c: kwargs.get(c) for c in CONFIRMED_COLUMNS}
        row["datetime"] = row.get("datetime") or fmt_kst()
        need_hdr = not os.path.exists(CONFIRMED_LOG)
        pd.DataFrame([row]).to_csv(
            CONFIRMED_LOG, mode="a", header=need_hdr, index=False)
    except Exception as e:
        logger.error(
            f"CONFIRMED 체결 로그 실패: {e} | action={kwargs.get('action')} "
            f"price={kwargs.get('price')} path={CONFIRMED_LOG}")
        try:
            tg_error(
                f"*CONFIRMED 로그 실패*\n"
                f"action={kwargs.get('action')} / price={kwargs.get('price')}\n"
                f"err={e}\n수동 확인 필요")
        except Exception:
            pass

# ══════════════════════════════════════════════════════════
# v19.4: EMA 대체 연구용 캔들 로그
# ══════════════════════════════════════════════════════════
def fetch_binance_funding_rate():
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/premiumIndex",
            params={"symbol": "BTCUSDT"}, timeout=5)
        if r.status_code != 200:
            return None
        return float(r.json().get("lastFundingRate"))
    except Exception:
        return None


# ── v20.0: 김치 프리미엄 계산 ──────────────────────────────
_usdkrw_cache = {"rate": None, "ts": 0.0}


def fetch_binance_btc_usdt():
    """Binance BTC/USDT 현재가 조회."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"}, timeout=5)
        if r.status_code == 200:
            return float(r.json()["price"])
    except Exception:
        pass
    return None


def fetch_usdkrw():
    """USD/KRW 환율 조회 (24시간 캐싱)."""
    now = time.time()
    if (_usdkrw_cache["rate"] is not None and
            now - _usdkrw_cache["ts"] < KIMCHI_USDKRW_CACHE_TTL):
        return _usdkrw_cache["rate"]
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if r.status_code == 200:
            rate = float(r.json()["rates"]["KRW"])
            _usdkrw_cache["rate"] = rate
            _usdkrw_cache["ts"] = now
            return rate
    except Exception:
        pass
    return _usdkrw_cache["rate"]  # 실패 시 직전 캐시값 (없으면 None)


def calc_kimchi_premium(upbit_price):
    """김치 프리미엄(%) 계산. 실패 시 None (fail-open)."""
    btc_usdt = fetch_binance_btc_usdt()
    if btc_usdt is None:
        return None
    usdkrw = fetch_usdkrw()
    if usdkrw is None:
        return None
    binance_krw = btc_usdt * usdkrw
    if binance_krw <= 0:
        return None
    return (upbit_price - binance_krw) / binance_krw * 100


def compute_multi_ema_daily(daily_close_series, periods=(100, 150, 200, 250, 300)):
    """v20.9.10: 일봉 종가 시계열 → 여러 EMA 동시 계산.
    Returns: dict {period: latest_ema_value}. EMA 계산 부족 시 NaN.
    """
    out = {}
    if daily_close_series is None or len(daily_close_series) == 0:
        return {p: float("nan") for p in periods}
    s = pd.Series(daily_close_series).astype(float)
    for p in periods:
        try:
            ema = ta.ema(s, p)
            v = float(ema.iloc[-1]) if ema is not None and len(ema) > 0 else float("nan")
            out[p] = v if not pd.isna(v) else float("nan")
        except Exception:
            out[p] = float("nan")
    return out


def log_candle_record(rec):
    """매 4H 캔들 평가 시 btc_candle_log.csv 에 기록.
    - 신규 행 append 후 4/8봉 이전 행의 price_after_*/pct_change_* 역산
    - 최근 CANDLE_LOG_MAX_ROWS 행만 유지
    - 실패 시 무시 (봇 동작 영향 없음)
    """
    try:
        if os.path.exists(CANDLE_LOG) and os.path.getsize(CANDLE_LOG) > 0:
            df = pd.read_csv(CANDLE_LOG)
            for col in CANDLE_LOG_COLUMNS:
                if col not in df.columns: df[col] = np.nan
            df = df[CANDLE_LOG_COLUMNS]
        else:
            df = pd.DataFrame(columns=CANDLE_LOG_COLUMNS)

        if len(df) > 0 and str(df["datetime"].iloc[-1]) == str(rec["datetime"]):
            return  # 동일 캔들 중복 기록 방지

        df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)

        cur_price = rec["price"]
        for lag, pa_col, pc_col in ((4, "price_after_4", "pct_change_4"),
                                    (8, "price_after_8", "pct_change_8"),
                                    (24, "price_after_24", "pct_change_24")):
            idx = len(df) - 1 - lag
            if idx >= 0:
                past_price = df.at[idx, "price"]
                if pd.notna(past_price) and past_price > 0:
                    df.at[idx, pa_col] = cur_price
                    df.at[idx, pc_col] = (cur_price - past_price) / past_price * 100

        if len(df) > CANDLE_LOG_MAX_ROWS:
            df = df.iloc[-CANDLE_LOG_MAX_ROWS:].reset_index(drop=True)

        df.to_csv(CANDLE_LOG, index=False)
    except Exception as e:
        logger.debug(f"candle_log 기록 오류: {e}")

def log_signal(price, xgb_prob, threshold, gate_pass, score, decision, regime=""):
    """신호 상세 로그 — btc_signal.log
    포맷: time|model|xgb_prob|threshold|signal|regime|score|event

    v20.9.4: decision 우선 처리 — block 이벤트는 "BLOCK", SELL은 "SELL" 정확 표기.
    """
    BLOCK_EVENTS = {"e2_bear_block", "vwap_block", "obv_div_block",
                    "trend_down_block", "adx_block"}
    if decision in BLOCK_EVENTS:
        signal = "BLOCK"
    elif decision in ("BUY", "BUY_REINVEST") or decision.startswith("BUY_"):
        signal = "BUY"
    elif decision.startswith("SELL"):
        signal = "SELL"
    elif gate_pass:
        signal = "BUY"
    else:
        signal = "SKIP"
    try:
        signal_logger.info(
            f"price={price:,.0f}"
            f"|model=XGB"
            f"|xgb={xgb_prob:.3f}"
            f"|thresh={threshold:.3f}"
            f"|signal={signal}"
            f"|regime={regime or '-'}"
            f"|score={score:.1f}"
            f"|event={decision}")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════
# XGBoost 신호 모델
# ══════════════════════════════════════════════════════════
class XGBCBSignalModel:
    def __init__(self):
        self.xgb_model     = None
        self.trained       = False
        self.xgb_prob_history = []
        self.last_train_dt = None
        self.test_accuracy = 0.0
        self.precision     = 0.0
        self.recall        = 0.0
        self.profit_factor = 0.0
        self._training     = False
        self._last_df      = None
        self._lock         = threading.Lock()
        self._retrain_reason = ""
        self._load()

    def _load(self):
        try:
            if os.path.exists(XGB_PATH):
                self.xgb_model = joblib.load(XGB_PATH)
                self.trained   = True
                logger.info("AI 모델 로드 완료 (XGBoost)")
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE) as f: s = json.load(f)
                dt_str = s.get("ai_last_train_dt")
                if dt_str: self.last_train_dt = datetime.fromisoformat(dt_str)
                self.precision     = float(s.get("ai_precision",     0.0))
                self.recall        = float(s.get("ai_recall",        0.0))
                self.test_accuracy = float(s.get("ai_accuracy",      0.0))
                self.profit_factor = float(s.get("ai_profit_factor", 0.0))
                with self._lock:
                    self.xgb_prob_history = s.get("ai_prob_history", [])
                logger.info(f"AI 복원 Prec={self.precision:.1%} PF={self.profit_factor:.2f}")
            except Exception as e:
                logger.warning(f"AI 메타 복원 실패: {e}")

    # v19.0: 피처 정리 24→13개 — OHLC 4 + 중복 7 제거
    # _build_features()는 라벨링용 OHLC 포함 24컬럼 반환
    # _FEAT_COLS로 모델에 투입할 13컬럼만 선택
    #   제거: open(0), high(1), low(2), close(3), ema_diff(5), vol_ratio(9),
    #         vwap_dist(10), volatility_10(15), price_momentum(18), rsi_slope(19),
    #         momentum_ratio(21)
    #   잔존: volume(4), rsi(6), returns(7), volatility(8), atr_ratio(11), adx(12),
    #         return_5(13), return_10(14), trend_strength(16), ema_slope(17),
    #         volatility_expansion(20), price_vs_ema200(22), bb_position(23)
    _FEAT_COLS = [4, 6, 7, 8, 11, 12, 13, 14, 16, 17, 20, 22, 23]
    _N_FEATURES = 13

    def _build_features(self, df):
        """24컬럼 (라벨링용 OHLC 포함). 모델 투입 시 _FEAT_COLS로 13개만 선택."""
        out = df[["open","high","low","close","volume"]].copy()
        out["volume"]     = df["volume"].shift(1).bfill()
        out["ema_diff"]   = (ta.ema(df["close"],21) - ta.ema(df["close"],55)).shift(1).fillna(0)
        out["rsi"]        = ta.rsi(df["close"],14).shift(1).fillna(50)
        out["returns"]    = df["close"].pct_change().shift(1).fillna(0)
        out["volatility"] = out["returns"].rolling(10).std().shift(1).fillna(0)
        vol_ma            = df["volume"].rolling(20).mean().shift(1)
        out["vol_ratio"]  = (df["volume"].shift(1) / vol_ma).fillna(1)
        typical           = (df["high"] + df["low"] + df["close"]) / 3
        vwap              = ((typical * df["volume"]).rolling(20).sum().shift(1)
                             / df["volume"].rolling(20).sum().shift(1))
        out["vwap_dist"]  = ((df["close"] - vwap) / vwap).fillna(0)
        try:
            atr_s = ta.atr(df["high"], df["low"], df["close"], length=14)
            out["atr_ratio"] = (atr_s / atr_s.rolling(20).mean()).shift(1).fillna(1)
        except:
            atr_s = pd.Series(0.0, index=df.index)
            out["atr_ratio"] = 1.0
        try:
            adx_df   = ta.adx(df["high"], df["low"], df["close"], length=14)
            out["adx"] = adx_df["ADX_14"].shift(1).fillna(20)
            di_plus  = adx_df["DMP_14"].shift(1).fillna(20)
            di_minus = adx_df["DMN_14"].shift(1).fillna(20)
        except:
            out["adx"] = 20.0
            di_plus  = pd.Series(20.0, index=df.index)
            di_minus = pd.Series(20.0, index=df.index)

        out["return_5"]      = df["close"].pct_change(5).shift(1).fillna(0)
        out["return_10"]     = df["close"].pct_change(10).shift(1).fillna(0)
        out["volatility_10"] = df["close"].pct_change().rolling(20).std().shift(1).fillna(0)
        denom = (di_plus + di_minus).replace(0, 1e-8)
        out["trend_strength"] = ((di_plus - di_minus) / denom).fillna(0)

        ema21 = ta.ema(df["close"], 21)
        rsi14 = ta.rsi(df["close"], 14)
        out["ema_slope"]            = (ema21 - ema21.shift(3)).shift(1).fillna(0)
        out["price_momentum"]       = (df["close"] - df["close"].shift(3)).shift(1).fillna(0)
        out["rsi_slope"]            = (rsi14 - rsi14.shift(3)).shift(1).fillna(0)
        out["volatility_expansion"] = (atr_s / atr_s.shift(5).replace(0, 1e-8)).shift(1).fillna(1)
        out["momentum_ratio"]       = (df["close"] / df["close"].shift(3).replace(0, 1e-8)).shift(1).fillna(1)

        ema200 = ta.ema(df["close"], 200)
        out["price_vs_ema200"] = (df["close"] / ema200.replace(0, 1e-8) - 1).shift(1).fillna(0)
        sma20  = df["close"].rolling(20).mean()
        std20  = df["close"].rolling(20).std()
        bb_upper = sma20 + 2.0 * std20
        bb_lower = sma20 - 2.0 * std20
        bb_range = (bb_upper - bb_lower).replace(0, 1e-9)
        out["bb_position"] = ((df["close"] - bb_lower) / bb_range).shift(1).fillna(0.5)

        return out.values  # shape: (n, 24) — 라벨링용

    def _prepare_data(self, df):
        feat  = self._build_features(df)
        split = int(len(feat) * 0.8)
        f_tr  = feat[:split]
        f_te  = feat[split:]

        def make_samples(raw, up_thresh, down_thresh, future_bars):
            """단순 라벨링 (폴백용)"""
            X, y = [], []
            for i in range(len(raw) - future_bars):
                ret = (raw[i + future_bars, 3] - raw[i, 3]) / raw[i, 3]
                if ret > up_thresh:     lbl = 1
                elif ret < down_thresh: lbl = 0
                else: continue
                X.append(raw[i])
                y.append(lbl)
            return np.array(X), np.array(y)

        def make_samples_clean(raw, future_bars=3,
                               up_thresh=0.004, dn_thresh=-0.004,
                               max_dd_limit=-0.002, max_rise_limit=0.002):
            """깔끔한 케이스만: 상승/하락 중 역방향 움직임 제거"""
            X, y = [], []
            for i in range(len(raw) - future_bars):
                future_ret   = (raw[i+future_bars, 3] - raw[i, 3]) / raw[i, 3]
                period_highs = [raw[i+k, 1] for k in range(1, future_bars+1)]
                period_lows  = [raw[i+k, 2] for k in range(1, future_bars+1)]
                ep           = raw[i, 3]
                max_drawdown = (min(period_lows)  - ep) / ep
                max_rise     = (max(period_highs) - ep) / ep
                if future_ret > up_thresh and max_drawdown > max_dd_limit:
                    lbl = 1
                elif future_ret < dn_thresh and max_rise < max_rise_limit:
                    lbl = 0
                else:
                    continue
                X.append(raw[i])
                y.append(lbl)
            return np.array(X), np.array(y)

        # Adaptive 라벨링: 단계적 완화 → 800 충족 시 멈춤, 모두 실패 시 단순 라벨링 폴백
        ADAPTIVE_STEPS = [(-0.002, 0.002), (-0.003, 0.003), (-0.004, 0.004)]
        X_tr = X_te = y_tr = y_te = None
        for dd_lim, rise_lim in ADAPTIVE_STEPS:
            _Xtr, _ytr = make_samples_clean(f_tr, max_dd_limit=dd_lim, max_rise_limit=rise_lim)
            _Xte, _yte = make_samples_clean(f_te, max_dd_limit=dd_lim, max_rise_limit=rise_lim)
            total = len(_Xtr) + len(_Xte)
            logger.info(f"Adaptive dd>{dd_lim:.3f}/rise<{rise_lim:.3f}: 샘플 {total}")
            if total >= LABEL_MIN_SAMPLES:
                X_tr, y_tr, X_te, y_te = _Xtr, _ytr, _Xte, _yte
                raw_total  = len(f_tr) + len(f_te) - LABEL_FUTURE_BARS * 2
                drop_ratio = 1.0 - total / max(raw_total, 1)
                logger.info(
                    f"✅ Adaptive 라벨링 확정: dd>{dd_lim:.3f}/rise<{rise_lim:.3f} "
                    f"샘플:{total} drop:{drop_ratio:.0%}")
                break
        if X_tr is None:
            logger.warning("⚠️ Adaptive 전 단계 미달 → 단순 라벨링(8봉/±1.2%) 폴백")
            X_tr, y_tr = make_samples(f_tr, LABEL_UP_THRESH, LABEL_DOWN_THRESH, LABEL_FUTURE_BARS)
            X_te, y_te = make_samples(f_te, LABEL_UP_THRESH, LABEL_DOWN_THRESH, LABEL_FUTURE_BARS)
            fallback_total = len(X_tr) + len(X_te)
            logger.info(f"폴백 샘플: {fallback_total}")
            # v20.2 C-3: 폴백 샘플도 최소 기준 미달이면 학습 스킵 (기존 모델 유지)
            if fallback_total < LABEL_MIN_SAMPLES:
                logger.warning(
                    f"⚠️ 폴백 샘플 부족 {fallback_total}<{LABEL_MIN_SAMPLES} — 학습 스킵")
                tg_warn(
                    f"*AI 학습 스킵 — 샘플 부족* (v{BOT_VERSION})\n"
                    f"Adaptive 3단계 전부 미달 + 폴백 {fallback_total}<{LABEL_MIN_SAMPLES}\n"
                    f"기존 모델 유지 (Prec={self.precision:.1%} PF={self.profit_factor:.2f})\n"
                    f"다음 재학습 시 재시도")
                return None, None, None, None, None

        # v19.0: 24→13 피처 축소 (OHLC+중복 제거, 라벨링 후 모델 투입용)
        if len(X_tr) > 0: X_tr = X_tr[:, self._FEAT_COLS]
        if len(X_te) > 0: X_te = X_te[:, self._FEAT_COLS]
        return X_tr, y_tr, X_te, y_te, f_te

    def _do_train(self, df):
        try:
            self._training = True
            # 재학습 전 기존 성능 기록 (비교용)
            old_prec = self.precision
            old_pf   = self.profit_factor
            old_acc  = self.test_accuracy
            logger.info(f"학습 시작 | {len(df)}개 | {fmt_kst()} | 기존 Prec={old_prec:.1%} PF={old_pf:.2f}")
            X_tr, y_tr, X_te, y_te, f_te = self._prepare_data(df)

            # v20.2 C-3: _prepare_data가 폴백 샘플 부족으로 스킵 시그널 반환
            if X_tr is None:
                logger.warning("학습 스킵 — 기존 모델 유지 [v20.2 C-3]")
                return

            if len(X_tr) == 0 or len(X_te) == 0:
                logger.error("학습 데이터 부족"); return

            n_pos = int(np.sum(y_tr == 1)); n_neg = int(np.sum(y_tr == 0))
            total = n_pos + n_neg
            pos_ratio = n_pos / total * 100 if total > 0 else 0
            logger.info(f"학습:{len(X_tr)}/테스트:{len(X_te)} "
                        f"↑{n_pos}({pos_ratio:.0f}%)↓{n_neg}({100-pos_ratio:.0f}%)")

            # STEP5: 실전용 XGB — class-balance + isotonic calibration (cv=3)
            neg_count = int((y_tr == 0).sum())
            pos_count = int((y_tr == 1).sum())
            scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
            logger.info(f"scale_pos_weight: {scale_pos_weight:.3f} "
                        f"(neg={neg_count}, pos={pos_count})")

            xgb_base = XGBClassifier(
                n_estimators=500,       # Phase2: 700→500
                max_depth=3,            # Phase2: 5→3 (과적합 방지)
                learning_rate=0.03,
                min_child_weight=15,    # Phase2: 5→15 (Precision 최적화)
                subsample=0.7,
                colsample_bytree=0.7,
                gamma=0.5,              # Phase2: 0.1→0.5 (분기 최소 이득 상향)
                reg_lambda=1.5,
                reg_alpha=0.1,
                scale_pos_weight=scale_pos_weight,
                eval_metric="auc",
                base_score=0.5,
                random_state=42,
                n_jobs=-1,
                verbosity=0)
            xgb_base.fit(X_tr, y_tr, verbose=False)
            xgb_new = xgb_base  # Calibration 제거 — Raw XGB 확률 사용

            _preds_log = xgb_new.predict_proba(X_te)[:, 1]
            xgb_stats_str = (f"min={_preds_log.min():.3f} "
                             f"max={_preds_log.max():.3f} "
                             f"mean={_preds_log.mean():.3f}")
            logger.info(f"XGB stats: {xgb_stats_str}")

            # 평가
            xgb_prob = xgb_new.predict_proba(X_te)[:, 1]
            new_acc  = float(np.mean((xgb_prob > 0.5).astype(int) == y_te))
            new_prec, new_rec, new_pf = calc_ai_metrics(y_te, xgb_prob, f_te)

            # ── v20.8.1 AR3: 롤백 가드 ──────────────────────────────
            # PF 단독 기준: post_pf < pre_pf - 0.10 시 신모델 거부, 5회 연속 시 강제 채택.
            # 거부 시 디스크 모델/메타 미변경 → Shadow도 ai_last_train_dt 변화 없어 자동 sync.
            consec_rejects = 0
            try:
                with open(STATUS_FILE) as _f: _s = json.load(_f)
                consec_rejects = int(_s.get("consecutive_train_rejects", 0))
            except Exception: pass
            accepted = True
            reject_reason = ""
            forced = False
            has_old = (old_pf > 0)  # 초기 학습은 비교 불가 → 무조건 채택
            if ENABLE_ROLLBACK_GUARD and has_old:
                pf_drop = old_pf - new_pf
                if pf_drop > ROLLBACK_PF_THRESHOLD:
                    consec_rejects += 1
                    if consec_rejects >= MAX_CONSECUTIVE_REJECTS:
                        # 강제 채택
                        accepted = True
                        forced = True
                        reject_reason = (f"PF {old_pf:.2f}→{new_pf:.2f} (-{pf_drop:.2f}) "
                                         f"→ {MAX_CONSECUTIVE_REJECTS}회 연속, 강제 채택")
                        consec_rejects = 0
                    else:
                        accepted = False
                        reject_reason = (f"PF {old_pf:.2f}→{new_pf:.2f} (-{pf_drop:.2f}) "
                                         f"> 임계 -{ROLLBACK_PF_THRESHOLD:.2f} "
                                         f"[연속거부 {consec_rejects}/{MAX_CONSECUTIVE_REJECTS}]")
                else:
                    consec_rejects = 0  # 정상 채택 → 카운터 리셋

            reason_str = getattr(self, '_retrain_reason', '정기')

            if accepted:
                self.xgb_model     = xgb_new
                self.trained       = True
                self.last_train_dt = now_kst()
                self.test_accuracy = new_acc
                self.precision     = new_prec
                self.recall        = new_rec
                self.profit_factor = new_pf

                joblib.dump(xgb_new, XGB_PATH)
                with self._lock:
                    self.xgb_prob_history.clear()   # 신 모델 확률 분포로 리셋
                self._save_ai_meta()
                if self._last_df is not None: self.predict(self._last_df)

                # v20.9.7 결함A: accepted 경로에서만 candles_since_retrain 리셋
                # Bot 인스턴스와 분리되어 있으므로 플래그 기반 동기화
                self._counter_reset_pending = True

                pr_ic = "✅" if new_prec >= MIN_PRECISION else "⚠️"
                pf_ic = "✅" if new_pf   >= MIN_PROFIT_FACTOR else "⚠️"
                # 전후 비교
                prec_delta = new_prec - old_prec if old_prec > 0 else 0
                pf_delta   = new_pf - old_pf if old_pf > 0 else 0
                acc_delta  = new_acc - old_acc if old_acc > 0 else 0
                comp_str = ""
                if old_prec > 0:
                    comp_str = (f"\n📊 *전후 비교*\n"
                                f"Prec: {old_prec:.1%}→{new_prec:.1%} ({prec_delta:+.1%}pp)\n"
                                f"PF: {old_pf:.2f}→{new_pf:.2f} ({pf_delta:+.2f})\n"
                                f"Acc: {old_acc:.1%}→{new_acc:.1%} ({acc_delta:+.1%}pp)")
                forced_str = "\n🚨 *강제 채택* (5회 연속 거부 한도 도달)" if forced else ""
                logger.info(f"학습 완료 | Prec:{old_prec:.1%}→{new_prec:.1%} "
                            f"PF:{old_pf:.2f}→{new_pf:.2f} Acc:{old_acc:.1%}→{new_acc:.1%}"
                            f"{' [FORCED]' if forced else ''}")
                tg_info(
                    f"🤖 *AI 재학습 완료* (v{BOT_VERSION})\n"
                    f"🕐 {fmt_kst()}\n"
                    f"📌 트리거: {reason_str}\n"
                    f"──────────────────\n"
                    f"📊 학습:{len(X_tr)} / 테스트:{len(X_te)} | Feature:{self._N_FEATURES}개\n"
                    f"📋 라벨: ↑{n_pos}({pos_ratio:.0f}%) ↓{n_neg}({100-pos_ratio:.0f}%) | XGB\n"
                    f"📈 XGB stats: {xgb_stats_str}\n"
                    f"🎯 정확도: {new_acc:.1%}\n"
                    f"{pr_ic} Precision: {new_prec:.1%}\n"
                    f"📡 Recall: {new_rec:.1%}\n"
                    f"{pf_ic} PF: {new_pf:.2f}"
                    f"{comp_str}{forced_str}\n"
                    f"──────────────────\n"
                    f"{'✅ 정상 운영' if self.is_reliable() else '⚠️ 보수적 운영'}"
                )
            else:
                # 거부: old 메트릭 유지, 디스크 모델 미변경, _save_ai_meta 미호출
                # #FIX: 거부 시에도 candles_since_retrain 리셋 — 무한 재시도 루프 방지
                self._counter_reset_pending = True
                logger.info("거부 후 candles_since_retrain 리셋 — 다음 30캔들까지 대기")
                logger.error(f"❌ 신모델 거부 [v20.8.1 AR3]: {reject_reason}")
                # #FIX: 텔레그램 dedup 24h (같은 PF 거부 반복 알림 방지)
                _now_ts = time.time()
                _send_tg_alert = True
                try:
                    with open(STATUS_FILE) as _f: _st_a = json.load(_f)
                    _last_alert = float(_st_a.get("last_alert_train_reject", 0) or 0)
                    _last_pf_pair = _st_a.get("last_alert_train_reject_pf", "")
                    _cur_pair = f"{old_pf:.2f}->{new_pf:.2f}"
                    if (_now_ts - _last_alert) < 86400 and _last_pf_pair == _cur_pair:
                        _send_tg_alert = False
                        logger.info(f"텔레그램 거부 알림 skip (24h dedup, 같은 PF {_cur_pair})")
                except Exception: pass
                if _send_tg_alert:
                    tg_error(
                        f"⚠️ *AI 신모델 거부* (v{BOT_VERSION})\n"
                        f"🕐 {fmt_kst()}\n"
                        f"📌 트리거: {reason_str}\n"
                        f"──────────────────\n"
                        f"PF: {old_pf:.2f}→{new_pf:.2f} (-{old_pf - new_pf:.2f})\n"
                        f"Prec: {old_prec:.1%}→{new_prec:.1%}\n"
                        f"임계: PF -{ROLLBACK_PF_THRESHOLD:.2f}\n"
                        f"연속거부: {consec_rejects}/{MAX_CONSECUTIVE_REJECTS}\n"
                        f"──────────────────\n"
                        f"기존 모델 유지 (Prec={old_prec:.1%} PF={old_pf:.2f})"
                    )
                    try:
                        with open(STATUS_FILE) as _f: _st_a = json.load(_f)
                        _st_a["last_alert_train_reject"] = _now_ts
                        _st_a["last_alert_train_reject_pf"] = f"{old_pf:.2f}->{new_pf:.2f}"
                        with open(STATUS_FILE, "w") as _f: json.dump(_st_a, _f, indent=2)
                    except Exception: pass

            # ── v20.8.1 AR3 후처리: status 필드 갱신 ─────────────────
            try:
                with open(STATUS_FILE) as _f: _st = json.load(_f)
                _st["consecutive_train_rejects"] = consec_rejects
                _st["last_retrain_accepted"] = accepted
                with open(STATUS_FILE, "w") as _f: json.dump(_st, _f, indent=2)
            except Exception as e:
                logger.warning(f"AR3 status 저장 실패: {e}")

            # ── v20.8.1 AR4: 재학습 결과 CSV 영속화 ─────────────────
            try:
                _regime = ""
                _adx = 0.0
                try:
                    with open(STATUS_FILE) as _f: _st2 = json.load(_f)
                    _regime = _st2.get("last_regime", "") or ""
                    _adx = float(_st2.get("live_adx", 0.0))
                except Exception: pass
                _need_header = not os.path.exists(RETRAIN_HISTORY_CSV)
                with open(RETRAIN_HISTORY_CSV, "a") as _cf:
                    if _need_header:
                        _cf.write("timestamp_kst,trigger_type,pre_pf,post_pf,"
                                  "pre_prec,post_prec,pre_acc,post_acc,"
                                  "samples_train,samples_test,regime,adx,"
                                  "accepted,reject_reason,consecutive_rejects\n")
                    _rs = (reject_reason or "").replace(",", ";").replace("\n", " ")
                    _ts = getattr(self, '_retrain_reason', '정기').replace(",", ";")
                    _cf.write(
                        f"{fmt_kst()},{_ts},{old_pf:.4f},{new_pf:.4f},"
                        f"{old_prec:.4f},{new_prec:.4f},{old_acc:.4f},{new_acc:.4f},"
                        f"{len(X_tr)},{len(X_te)},{_regime},{_adx:.1f},"
                        f"{accepted},{_rs},{consec_rejects}\n")
            except Exception as e:
                logger.warning(f"AR4 CSV 저장 실패: {e}")
        except Exception as e:
            logger.error(f"학습 오류: {e}", exc_info=True)
        finally:
            self._training = False

    def train_async(self, df):
        with self._lock:
            if self._training: logger.info("학습 중 스킵"); return
            self._training = True
        threading.Thread(target=self._do_train, args=(df,), daemon=True).start()

    def train(self, df): self._do_train(df)

    def predict(self, df):
        self._last_df = df
        if not self.trained or self._training:
            with self._lock:
                last = self.xgb_prob_history[-1] if self.xgb_prob_history else 0.5
            return last
        try:
            feat     = self._build_features(df)
            x        = feat[-1:, self._FEAT_COLS].reshape(1, -1)
            xgb_prob = float(self.xgb_model.predict_proba(x)[0][1])
            with self._lock:
                self.xgb_prob_history.append(xgb_prob)
                if len(self.xgb_prob_history) > 30:
                    self.xgb_prob_history.pop(0)
            return xgb_prob
        except Exception as e:
            logger.error(f"예측 오류: {e}"); return 0.5

    def needs_retrain(self, new_candles: int = 0) -> bool:
        """
        재학습 판단: 30캔들 누적 시 정기 재학습.
        v19.8: 7일 경과 조건 삭제 — 캔들 수 자체가 자연 쿨다운 (30캔들 ≈ 5일).
        Regime 전환 / 성능 저하 트리거는 메인 루프에서 직접 처리.
        """
        if not self.trained or self.last_train_dt is None:
            self._retrain_reason = "초기 학습"
            return True

        if new_candles >= RETRAIN_MIN_CANDLES:
            last = self.last_train_dt
            if last.tzinfo is None: last = last.replace(tzinfo=KST)
            days_since = (now_kst() - last).total_seconds() / 86400
            self._retrain_reason = f"정기({days_since:.1f}일+{new_candles}캔들)"
            logger.info(f"🕐 {self._retrain_reason} → 재학습")
            return True

        return False

    def is_reliable(self):
        if not self.trained: return True
        return self.precision >= MIN_PRECISION and self.profit_factor >= MIN_PROFIT_FACTOR

    def _save_ai_meta(self):
        if not os.path.exists(STATUS_FILE): return
        try:
            with open(STATUS_FILE) as f: s = json.load(f)
            with self._lock: snap = list(self.xgb_prob_history[-30:])
            s.update({
                "ai_last_train_dt": self.last_train_dt.isoformat() if self.last_train_dt else None,
                "ai_precision":     self.precision,
                "ai_recall":        self.recall,
                "ai_accuracy":      self.test_accuracy,
                "ai_profit_factor": self.profit_factor,
                "ai_prob_history":  snap
            })
            with open(STATUS_FILE, "w") as f: json.dump(s, f, indent=2)
        except Exception as e:
            logger.warning(f"AI 메타 저장 실패: {e}")


ai_engine = XGBCBSignalModel()

# ══════════════════════════════════════════════════════════
# 메인 봇
# ══════════════════════════════════════════════════════════
class BitcoinBot:
    def __init__(self):
        self.upbit              = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
        self.status             = self._load_status()
        self.last_report_dt     = None
        # v20.9.7 결함B: last_candle_time 영속화 — status.json 복원
        _lct_str = self.status.get("last_candle_time")
        try:
            self.last_candle_time = pd.Timestamp(_lct_str) if _lct_str else None
        except Exception:
            self.last_candle_time = None
        if self.last_candle_time is not None:
            logger.info(f"last_candle_time 복원: {self.last_candle_time}")
        self.daily_trend        = (True, 0, 0)
        self.last_trend_check   = None
        self._api_fail_count    = 0
        self._api_fail_alerted  = False
        self._last_known_btc    = 0.0
        self._last_known_krw    = -1.0  # 센티넬: 첫 루프에서 초기화
        self._partial_selling   = False
        self._last_buy_time     = 0.0   # v20.1: 매수 체결 시각 (외부출금 오인 방지)
        # v20.2 H-2: 동일 캔들 내 추가매수 중복 차단 플래그
        # (_check_partial_tp 피라미딩과 _auto_reinvest 간 배타 제어)
        # 재시작 시 None 시작 (last_candle_time도 None으로 시작하므로 영속화 불필요)
        self._last_pyr_add_candle = None
        # v18.5: 재시작 시 직전 Regime 복원 (히스테리시스 회색지대 유지용)
        self._last_market_state = self.status.get("last_regime")
        # v20.9.6 AR2 개선: 조건부 리셋 — ≥50 일 때만 리셋 (폭주 방지 본래 의도 유지)
        # 근거: restart_root_cause.md — 131회 재시작에서 매번 0 리셋 시
        #       30캔들 누적 불가, 5일간 정기 재학습 0회. 임계 50으로 완화.
        saved_candles = self.status.get("candles_since_retrain", 0)
        AR2_FORCE_RESET_THRESHOLD = 50
        if ai_engine.trained and saved_candles >= AR2_FORCE_RESET_THRESHOLD:
            logger.info(f"AR2: candles_since_retrain {saved_candles}→0 리셋 "
                        f"(≥{AR2_FORCE_RESET_THRESHOLD})")
            self.status["candles_since_retrain"] = 0
            self._candles_since_retrain = 0
        else:
            self._candles_since_retrain = int(saved_candles)
            logger.info(f"AR2: candles_since_retrain {saved_candles} 유지 "
                        f"(<{AR2_FORCE_RESET_THRESHOLD})")
        if self._last_market_state:
            logger.info(f"Regime 복원: last_regime={self._last_market_state}")
        self._sync_balance()
        self._cmd_thread = threading.Thread(
            target=self._telegram_command_listener, daemon=True)
        self._cmd_thread.start()
        self._last_monthly_report = None
        # v20.6 E2: 일봉 EMA200 BEAR 모드
        self._e2_bear_mode      = False       # 현재 F10 BEAR 모드 여부 (v20.9: F10 기준)
        self._e2_last_refresh   = 0.0         # 마지막 갱신 시각 (epoch)
        self._e2_daily_close    = None        # 최근 일봉 종가
        self._e2_daily_ema200   = None        # 최근 일봉 EMA200
        self._e2_blocks_today   = 0           # 금일 차단 건수 (카운터)
        self._e2_data_available = False       # 200일 데이터 확보 여부
        # v20.9.0 E2 F10 + 예외 상태
        self._e2_f2_active          = False   # F2 컴포넌트 상태 (일봉<EMA200)
        self._e2_f5_active          = False   # F5 컴포넌트 상태 (4H EMA21<EMA55)
        self._e2_block_reason       = "NONE"  # "F2" | "F5" | "BOTH" | "NONE"
        self._e2_daily_gap_pct      = 0.0     # (daily_close-EMA200)/EMA200 * 100
        self._e2_ema21_4h           = 0.0
        self._e2_ema55_4h           = 0.0
        self._e2_o3_exceptions_today  = 0     # 금일 O3 예외 진입 카운터
        self._e2_gap_exceptions_today = 0     # 금일 gap+score 예외 진입 카운터
        # bars_since_e2 및 pending_off_bars는 status에서 복원
        # (Option B 정책: F10 OFF 시 즉시 bars_since_e2=0 리셋)
        # v20.9.4: 자정 경과 감지 → 일일 카운터 자동 리셋
        self._e2_counters_date        = None  # YYYY-MM-DD (마지막 리셋 날짜)

    def _load_status(self):
        default = {
            "version": BOT_VERSION,
            "e2_enabled_config": E2_ENABLED,  # v20.9.10: 대시보드 표시용 (config-OFF 구분)
            "in_position": False, "entry": 0.0,
            "stop_loss": 0.0, "highest_price": 0.0, "hold_bars": 0,
            "buy_count": 0, "initial_equity": 0.0,
            "partial_tp1_done": False, "partial_tp2_done": False,
            "last_sell_reason": "", "last_trade_time": 0,
            "cooldown_seconds": COOLDOWN_ENTRY, "consecutive_losses": 0,
            # v18.4: P5 피라미딩/Break-Even 상태
            "pyramid_level": 0,           # 0=초기, 1=TP1후, 2=TP2후, ...
            "step_tp_level": 0,           # v20.1: 무한 계단손절 도달 TP 레벨
            "first_entry_price": 0.0,     # 첫 진입가 (TP 레벨 기준)
            "avg_entry_price": 0.0,       # v19.1: 평균 매수가 (추가매수 시 재계산)
            "entry_type": "trend",        # trend / mean_reversion / pyramid
            "range_new_mode": False,      # v20.5: Range New 진입 플래그
            # v20.6 BD + v20.7 C6: per-position 파라미터 (진입 시 set)
            "pos_trail_m":      0.0,      # 0 또는 없으면 ATR_TRAILING_MULT (전역) 사용
            "pos_step_lookback": 0.0,     # 0 또는 없으면 STEP_LOOKBACK (전역) 사용
            "pos_init_ratio":   0.0,      # 정보용 — 진입 시 사용된 초기 사이징 비율
            "ai_last_train_dt": None, "ai_precision": 0.0, "ai_recall": 0.0,
            "ai_accuracy": 0.0, "ai_profit_factor": 0.0, "ai_prob_history": [],
            "prev_price": 0.0, "prev_rsi": 0.0, "prev_prob": 0.0,
            "prev_adx": 0.0, "prev_score": 0.0, "prev_atr_pct": 0.0,
            # v18.0 신규 필드
            "kill_switch": False,
            "kill_switch_reason": "",
            # v20.8 KR1~KR3: 자동복구 + 재발동 방지 이력
            "last_killswitch_at":           0.0,   # 마지막 발동 epoch
            "last_killswitch_recovered_at": 0.0,   # 마지막 자동복구 epoch
            "killswitch_count_24h":         0,     # 24h 내 발동 횟수 (>=2 시 영구 중단)
            # v20.8.1 AR3: 모델 롤백 가드 — 연속 거부 카운터
            "consecutive_train_rejects":    0,     # 5회 연속 거부 시 강제 채택
            "last_retrain_accepted":        True,  # 대시보드 표시용 (직전 학습 채택 여부)
            # v20.8.1 DASH3: E2 BEAR 모드 대시보드 표시용
            "live_e2_bear_mode":   False,
            "live_daily_close":    0.0,
            "live_daily_ema200":   0.0,
            "live_e2_blocks_today": 0,
            # v20.9.0 E2 F10 + 예외 + 대시보드 신규 필드
            "live_e2_f2_active":       False,
            "live_e2_f5_active":       False,
            "live_e2_block_reason":    "NONE",
            "live_e2_activation_date": None,      # ISO8601 or null (F10 첫 ON 시각)
            "bars_since_e2":           0,         # F10 연속 ON 봉 수 (Option B)
            "pending_off_bars":        0,         # (미사용, Option C 확장 여지)
            "live_daily_ema200_gap_pct": 0.0,
            "live_ema21_4h":           0.0,
            "live_ema55_4h":           0.0,
            "live_e2_o3_exceptions_today":  0,
            "live_e2_gap_exceptions_today": 0,
            # 예외 진입 포지션 속성
            "pyramid_locked":          False,     # E2 예외 진입 포지션은 True
            "mdd_peak_equity": 0.0,
            "current_mdd": 0.0,
            "dynamic_threshold": AI_GATE_THRESHOLD,
            "threshold_calibrated_at": 0,   # 마지막 보정 시 trade_count
            "candles_since_retrain": 0,     # 재학습 이후 캔들 수 (재시작 복원용)
            "last_candle_time":      None,  # v20.9.7 결함B: 재시작 시 캔들 중복 카운트 방지
            "phase4_alerted": False,        # 4단계 알림 발송 여부
            "bot_state": None,              # running / stopped_signal / stopped_clean
            # v18.5: Regime 히스테리시스 — 재시작 후에도 직전 Regime 복원
            "last_regime": None,
        }
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE) as f: saved = json.load(f)
                saved_ver = saved.get("version", "unknown")
                if saved_ver != BOT_VERSION:
                    logger.info(f"버전 변경: {saved_ver} → {BOT_VERSION}")
                    for k in default:
                        if k in saved and k != "version": default[k] = saved[k]
                    # v20.9.8: F10 → F2 전환 시 bars_since_e2 리셋 (기준 변경)
                    # 기존 F10 기반 카운터는 F2 기준과 다를 수 있음 → 0 리셋이 안전
                    if (saved_ver in ("20.9.0","20.9.1","20.9.2","20.9.3","20.9.4",
                                        "20.9.5","20.9.6","20.9.7")
                            and BOT_VERSION >= "20.9.8"):
                        _bars_old = default.get("bars_since_e2", 0)
                        logger.info(
                            f"v20.9.8: bars_since_e2 F10→F2 기준 전환으로 "
                            f"{_bars_old}→0 리셋 (E2b+6mo 예외 180일 재시작)")
                        default["bars_since_e2"] = 0
                        default["live_e2_activation_date"] = None
                    default["version"] = BOT_VERSION
                    with open(STATUS_FILE, "w") as f: json.dump(default, f, indent=2)
                    tg_info(f"🔄 *버전 업그레이드* v{saved_ver}→v{BOT_VERSION} ✅")
                else:
                    default.update(saved)
            except Exception as e:
                logger.error(f"상태 로드 오류: {e}")
        # v18.4 안전장치: 포지션 보유 중 first_entry_price=0 → entry로 보정
        if default.get("in_position") and not default.get("first_entry_price"):
            default["first_entry_price"] = default.get("entry", 0.0)
            logger.info(f"first_entry_price 보정: {default['first_entry_price']:,.0f}")
        # v20.9.6: consecutive_train_rejects CSV 영속화 복원 (AR3 가드 정확성)
        # 근거: 4/24 사례 — status=0 vs csv=1 불일치 확인. CSV 가 authoritative source.
        try:
            if os.path.exists(RETRAIN_HISTORY_CSV):
                _df_rh = pd.read_csv(RETRAIN_HISTORY_CSV)
                if len(_df_rh) > 0:
                    _last = _df_rh.iloc[-1]
                    _csv_accepted = str(_last.get("accepted", "True")).lower() == "true"
                    _csv_rejects  = int(_last.get("consecutive_rejects", 0) or 0)
                    # CSV 에 최근 거부 기록이 있고 status 값이 더 낮으면 CSV 복원
                    if (not _csv_accepted) and _csv_rejects > int(default.get("consecutive_train_rejects", 0) or 0):
                        logger.info(
                            f"consecutive_train_rejects CSV 복원: "
                            f"status={default.get('consecutive_train_rejects',0)} → csv={_csv_rejects}")
                        default["consecutive_train_rejects"] = _csv_rejects
                        default["last_retrain_accepted"]     = _csv_accepted
        except Exception as e:
            logger.warning(f"consecutive_train_rejects CSV 복원 실패: {e}")
        return default

    def _save_status(self):
        with ai_engine._lock:
            self.status["ai_prob_history"] = list(ai_engine.xgb_prob_history[-30:])
        # ai_engine이 AI 메타의 진실의 원천 — stale 메모리 값이 _save_ai_meta()가
        # 디스크에 쓴 최신 재학습 결과를 덮어쓰지 않도록 매 저장 시 동기화
        self.status["ai_last_train_dt"] = (
            ai_engine.last_train_dt.isoformat() if ai_engine.last_train_dt else None
        )
        self.status["ai_precision"]     = ai_engine.precision
        self.status["ai_recall"]        = ai_engine.recall
        self.status["ai_accuracy"]      = ai_engine.test_accuracy
        self.status["ai_profit_factor"] = ai_engine.profit_factor
        # v20.9.10: 매 저장 시 config 동기화 (대시보드 표시용)
        self.status["e2_enabled_config"] = E2_ENABLED
        tmp = STATUS_FILE + ".tmp"
        try:
            with open(tmp, "w") as f: json.dump(self.status, f, indent=2)
            os.replace(tmp, STATUS_FILE)
        except Exception as e:
            logger.error(f"상태 저장 오류: {e}")

    def _check_phantom_position(self, balances):
        """v19.6: status.in_position=True 인데 실제 BTC 잔고가 없으면 팬텀으로 간주.
        포지션 상태를 초기화하고 텔레그램으로 알림. Returns True if reset."""
        if not self.status.get("in_position"): return False
        if balances is None: return False
        btc = balances.get(COIN, 0.0)
        if btc >= MANUAL_TRADE_THRESHOLD: return False

        old_entry = self.status.get("entry", 0.0)
        old_stop  = self.status.get("stop_loss", 0.0)
        old_pyr   = self.status.get("pyramid_level", 0)
        logger.warning(f"🔧 팬텀 포지션 감지: status.in_position=True 이지만 "
                       f"BTC={btc:.8f} < {MANUAL_TRADE_THRESHOLD}")
        self.status.update({
            "in_position": False, "entry": 0.0, "stop_loss": 0.0,
            "highest_price": 0.0, "hold_bars": 0, "buy_count": 0,
            "partial_tp1_done": False, "partial_tp2_done": False,
            "entry_type": "trend", "pyramid_level": 0, "step_tp_level": 0,
            "first_entry_price": 0.0, "avg_entry_price": 0.0,
            "range_new_mode": False,
            "pos_trail_m": 0.0, "pos_step_lookback": 0.0, "pos_init_ratio": 0.0,  # v20.6 BD + v20.7 C6
            "pyramid_locked": False, "e2_exception_type": "",  # v20.9.0 E2 예외 진입 속성 리셋
            "last_sell_reason": "팬텀자동리셋",
            "last_trade_time": time.time(),
            "cooldown_seconds": COOLDOWN_SIGNAL,
        })
        self._last_known_btc = 0.0
        self._save_status()
        tg_warn(
            f"🔧 *팬텀 포지션 자동 리셋* (v{BOT_VERSION})\n"
            f"status: in_position=True / 실제 BTC=0\n"
            f"이전 entry:{old_entry:,.0f} stop:{old_stop:,.0f} pyr_lv:{old_pyr}\n"
            f"→ 포지션 상태 초기화 완료")
        return True

    def _sync_balance(self):
        balances = upbit_get_all_balances()
        if balances is None: return
        self._last_known_btc = balances[COIN]
        # v20.6 H1: 매도 진행 중 (_partial_selling) 에는 phantom 감지 SKIP
        # 하드스톱 fallback이 _sync_balance를 호출할 때 status.entry가 조기 0화되어
        # 이후 sell_type 판정(raw=0)에서 "ATR트레일링(익절)" 오분류되는 버그 방지.
        # _detect_manual_trade에도 이미 동일 가드 존재 (대칭).
        if self._partial_selling:
            return
        if self._check_phantom_position(balances):
            return
        if balances[COIN] > 0.0001 and not self.status["in_position"]:
            price = api_retry(lambda: pyupbit.get_current_price(TICKER))
            self.status.update({
                "in_position": True, "entry": price,
                "stop_loss": price*(1-MIN_STOP_PCT), "highest_price": price,
                "hold_bars": 0, "partial_tp1_done": False, "partial_tp2_done": False})
            self._save_status()
            logger.info(f"잔고 동기화: {balances[COIN]:.6f} BTC")

    def _update_initial_equity(self, equity):
        if self.status["in_position"]: return
        ie = self.status.get("initial_equity", 0.0)
        if ie <= 0:
            self.status["initial_equity"] = equity
            # MDD 피크도 초기화
            if self.status.get("mdd_peak_equity", 0.0) <= 0:
                self.status["mdd_peak_equity"] = equity
            self._save_status(); return
        if abs(equity - ie) / ie > 0.20:
            tg_warn(f"*자금 변동 감지*\n{ie:,.0f}→{equity:,.0f} KRW | 기준점 재설정")
            self.status["initial_equity"]  = equity
            self.status["mdd_peak_equity"] = equity
            self._save_status()

    def _update_mdd(self, equity):
        """MDD 업데이트. MDD >= MDD_STOP_PCT 이면 True 반환."""
        peak = self.status.get("mdd_peak_equity", 0.0)
        if equity > peak or peak <= 0:
            self.status["mdd_peak_equity"] = equity
            self.status["current_mdd"] = 0.0
            return False, 0.0
        mdd = (peak - equity) / peak
        self.status["current_mdd"] = mdd
        if mdd >= MDD_STOP_PCT:
            return True, mdd
        return False, mdd

    def _check_kill_switch(self):
        """Kill Switch: PF < 0.7, 최소 20 거래 후"""
        if self.status.get("kill_switch", False):
            return True, self.status.get("kill_switch_reason", "이미 발동")
        stats = calc_recent_stats(n=KILL_SWITCH_MIN_TRADES)
        if stats["trade_count"] < KILL_SWITCH_MIN_TRADES:
            return False, ""
        if stats["pf"] < KILL_SWITCH_PF and stats["winrate"] is not None:
            reason = f"PF={stats['pf']:.2f}<{KILL_SWITCH_PF} ({stats['trade_count']}거래)"
            return True, reason
        return False, ""

    # v20.8 KR1: Kill Switch 자동복구 조건
    KS_RECOVER_MDD_PCT   = 0.10      # MDD < 10% 회복 시 자동 해제 고려
    KS_RECOVER_MIN_HOURS = 24        # 발동 후 최소 24h 경과
    KS_MAX_24H_COUNT     = 2         # 24h 내 재발동 한도 (>=2 시 영구 중단)

    def _trigger_kill_switch(self, reason, reason_type="MDD"):
        """v20.8 KR2: 통합 Kill Switch 발동 + 24h 재발동 추적.

        - status 상태 업데이트 (kill_switch, kill_switch_reason)
        - last_killswitch_at 갱신
        - killswitch_count_24h 누적 (24h 내 이전 발동 있으면 +1, 없으면 1로 리셋)
        - 텔레그램 경고 (24h 내 재발동이면 tg_error + 영구 중단 경고)
        """
        now_ts = time.time()
        last_ks_at = float(self.status.get("last_killswitch_at", 0.0) or 0.0)
        # 24h 윈도우 재발동 카운트 누적
        if last_ks_at > 0 and (now_ts - last_ks_at) < self.KS_RECOVER_MIN_HOURS * 3600:
            self.status["killswitch_count_24h"] = int(self.status.get("killswitch_count_24h", 0) or 0) + 1
        else:
            self.status["killswitch_count_24h"] = 1
        self.status["kill_switch"]        = True
        self.status["kill_switch_reason"] = reason
        self.status["last_killswitch_at"] = now_ts
        self._save_status()
        logger.error(f"🛑 Kill Switch 발동 [{reason_type}]: {reason}")
        count_24h = self.status["killswitch_count_24h"]
        if count_24h >= self.KS_MAX_24H_COUNT:
            tg_error(
                f"*⚠️ Kill Switch 영구 중단*\n"
                f"사유: {reason}\n"
                f"24h 내 {count_24h}회 발동 → 자동복구 비활성\n"
                f"수동 확인 후 `/killswitch reset` (카운터 초기화) 또는 `/killswitch off` 필요")
        else:
            tg_error(
                f"*Kill Switch 발동 ({reason_type})*\n"
                f"사유: {reason}\n"
                f"자동복구 조건: MDD<10% AND 24h 경과\n"
                f"수동 해제: /killswitch off")

    def _check_killswitch_auto_recover(self):
        """v20.8 KR1: Kill Switch 자동복구.

        조건 (AND):
          1. status["kill_switch"] == True
          2. 현재 MDD < KS_RECOVER_MDD_PCT (10%)
          3. 발동 후 24h 이상 경과
          4. 24h 내 재발동 한도(killswitch_count_24h) 미달
        """
        if not self.status.get("kill_switch", False):
            return
        cur_mdd = float(self.status.get("current_mdd", 0.0) or 0.0)
        if cur_mdd >= self.KS_RECOVER_MDD_PCT:
            return
        last_ks_at = float(self.status.get("last_killswitch_at", 0.0) or 0.0)
        if last_ks_at <= 0:
            # 이력 없음 (v20.7 이전 발동) — 24h 체크 생략, 즉시 복구 허용
            pass
        elif (time.time() - last_ks_at) < self.KS_RECOVER_MIN_HOURS * 3600:
            return
        # 24h 내 재발동 한도 체크
        count_24h = int(self.status.get("killswitch_count_24h", 0) or 0)
        if count_24h >= self.KS_MAX_24H_COUNT:
            logger.warning(
                f"Kill Switch 자동복구 보류: 24h 내 {count_24h}회 발동 (수동 /killswitch reset 필요)")
            return
        # 조건 만족 — 자동 해제
        prev_reason = self.status.get("kill_switch_reason", "")
        self.status["kill_switch"]               = False
        self.status["kill_switch_reason"]        = ""
        self.status["last_killswitch_recovered_at"] = time.time()
        self._save_status()
        logger.info(
            f"🟢 Kill Switch 자동복구: MDD {cur_mdd*100:.2f}% < "
            f"{self.KS_RECOVER_MDD_PCT*100:.0f}%, 발동 후 24h 경과")
        tg_info(
            f"🟢 *Kill Switch 자동 해제*\n"
            f"MDD 회복: {cur_mdd*100:.2f}% (< {self.KS_RECOVER_MDD_PCT*100:.0f}%)\n"
            f"발동 이후 24h 이상 경과\n"
            f"이전 사유: {prev_reason}\n"
            f"거래 재개 — 다음 신호부터 정상 동작")

    def _check_phase4_alert(self):
        """실전 성과가 백테스트 대비 크게 떨어지면 4단계(피처 정리) 검토 알림"""
        if self.status.get("phase4_alerted", False):
            return
        stats = calc_recent_stats(n=30)
        if stats["trade_count"] < PHASE4_MIN_TRADES:
            return
        wr = stats["winrate"]
        pf = stats["pf"]
        if wr is None:
            return
        reasons = []
        if pf < PHASE4_PF_THRESHOLD:
            reasons.append(f"PF {pf:.2f} < {PHASE4_PF_THRESHOLD} (백테스트:{PHASE4_BT_PF})")
        if wr < PHASE4_WR_THRESHOLD:
            reasons.append(f"승률 {wr:.1%} < {PHASE4_WR_THRESHOLD:.0%} (백테스트:{PHASE4_BT_WR:.1%})")
        if not reasons:
            return
        self.status["phase4_alerted"] = True
        self._save_status()
        tg_warn(
            f"📋 *4단계(피처 정리) 검토 시점*\n"
            f"실거래 {stats['trade_count']}건 기준:\n"
            f"{'  /  '.join(reasons)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"백테스트 대비 괴리 발생\n"
            f"→ 24개 피처 → 상위 12~15개 선별 권장\n"
            f"Claude Code에서 4단계 실행 요청")

    def _detect_manual_trade(self, balances, price):
        if self._partial_selling:
            self._last_known_btc = balances[COIN]; return
        cur = balances[COIN]; prev = self._last_known_btc; diff = cur - prev
        if abs(diff) < MANUAL_TRADE_THRESHOLD:
            self._last_known_btc = cur; return
        if not self.status["in_position"] and cur > MANUAL_TRADE_THRESHOLD:
            # v18.4: 현재 Regime으로 entry_type 결정
            _ms = self._last_market_state or "Range"
            if _ms == "Trend_Up":     _et = "pyramid"
            elif _ms == "Range":      _et = "breakeven"
            else:                     _et = "trend"
            self.status.update({
                "in_position": True, "entry": price,
                "stop_loss": price*(1-MIN_STOP_PCT), "highest_price": price,
                "hold_bars": 0, "partial_tp1_done": False, "partial_tp2_done": False,
                "entry_type": _et, "pyramid_level": 0, "step_tp_level": 0, "first_entry_price": price})
            self._save_status()
            # v20.6 H2: 수동 매수도 CONFIRMED CSV 페어링
            log_trade("BUY", price, f"수동매수감지 모드:{_et} regime:{_ms}")
            log_confirmed_trade(
                action="BUY", price=price,
                amount=cur, krw=cur*price, regime=_ms,
                entry_reason="manual")
            tg_warn(f"*수동 매수 감지*\n감지가:{price:,.0f} | 손절:{price*(1-MIN_STOP_PCT):,.0f} | 모드:{_et}")
        elif self.status["in_position"] and cur < MANUAL_TRADE_THRESHOLD:
            entry = self.status["entry"]
            raw   = ((price-entry)/entry)*100; real = raw - (COST_RATE*100)
            _hb   = self.status.get("hold_bars", 0)  # v20.3: 리셋 전 스냅샷
            self.status.update({
                "in_position": False, "entry": 0.0, "stop_loss": 0.0,
                "highest_price": 0.0, "hold_bars": 0,
                "partial_tp1_done": False, "partial_tp2_done": False,
                "entry_type": "trend", "pyramid_level": 0, "step_tp_level": 0,
                "first_entry_price": 0.0,
                "range_new_mode": False,
                "pos_trail_m": 0.0, "pos_step_lookback": 0.0, "pos_init_ratio": 0.0,  # v20.6 BD + v20.7 C6
                "pyramid_locked": False, "e2_exception_type": "",  # v20.9.0 E2 예외 진입 속성 리셋
                "last_sell_reason": "수동매도", "last_trade_time": time.time(),
                "cooldown_seconds": COOLDOWN_SIGNAL})
            self._save_status()
            log_trade("SELL", price, f"수동매도(전량) 표면:{raw:+.2f}% 실질:{real:+.2f}%")
            log_confirmed_trade(
                action="SELL", price=price,
                amount=prev, krw=prev * price,
                pnl_pct=round(real, 2), sell_reason="수동매도",
                regime=self._last_market_state, holding_bars=_hb)
            tg_warn(f"*수동 전량 매도 감지*\n감지가:{price:,.0f} | 표면:{raw:+.2f}% 실질:{real:+.2f}%")
        elif self.status["in_position"] and diff < -MANUAL_TRADE_THRESHOLD:
            tg_warn(f"*수동 일부 매도 감지*\n변화:{diff:+.6f} BTC | 현재:{cur:.6f}")
        self._last_known_btc = cur

    def _detect_external_transfer(self, balances, price):
        """매매 없이 KRW 잔고가 1% 초과 변동 → 외부 입출금으로 간주.
        initial_equity에 delta 직접 반영, mdd_peak도 보정."""
        cur_krw = balances["KRW"]
        cur_btc = balances[COIN]
        equity  = cur_krw + cur_btc * price

        if self._last_known_krw < 0:
            self._last_known_krw = cur_krw
            return

        krw_delta = cur_krw - self._last_known_krw
        threshold = max(equity * 0.01, 10000.0)
        if abs(krw_delta) < threshold:
            self._last_known_krw = cur_krw
            return

        if time.time() - float(self.status.get("last_trade_time", 0)) < 60:
            self._last_known_krw = cur_krw
            return
        # v20.1: 피라미딩 매수 후 2분 이내 KRW 감소 → 외부출금이 아닌 자체 매수
        if self._last_buy_time > 0 and time.time() - self._last_buy_time < 120:
            self._last_known_krw = cur_krw
            return

        old_ie = self.status.get("initial_equity", 0.0)
        self.status["initial_equity"] = old_ie + krw_delta
        peak = self.status.get("mdd_peak_equity", 0.0)
        if peak > 0:
            self.status["mdd_peak_equity"] = max(peak + krw_delta, equity)
        self._save_status()

        sign  = "입금" if krw_delta > 0 else "출금"
        emoji = "💰" if krw_delta > 0 else "💸"
        new_ie = self.status["initial_equity"]
        pct = ((equity / new_ie) - 1) * 100 if new_ie > 0 else 0
        tg_info(f"{emoji} *외부 {sign} 감지*\n"
                f"금액: {krw_delta:+,.0f} KRW\n"
                f"💰 {equity:,.0f} KRW ({krw_delta:+,.0f} | {pct:+.1f}%)")
        logger.info(f"외부 {sign} 감지: {krw_delta:+,.0f} / "
                    f"initial_equity: {old_ie:,.0f}→{new_ie:,.0f}")
        self._last_known_krw = cur_krw

    def _update_trailing_stop(self, price, cur_atr):
        if not self.status["in_position"]: return
        # v20.5 Range New: range_new_mode 포지션은 트레일링 스킵 (step_stop 전용)
        if self.status.get("range_new_mode", False):
            if price > self.status["highest_price"]:
                self.status["highest_price"] = price
            return
        if price > self.status["highest_price"]:
            self.status["highest_price"] = price
        hold_bars = self.status.get("hold_bars", 0)
        if hold_bars < STOP_GRACE_BARS:
            grace_stop = self.status["entry"] - cur_atr * STOP_GRACE_MULT
            min_stop   = self.status["entry"] * (1 - MIN_STOP_PCT * 2)
            new_stop   = max(grace_stop, min_stop)
            if self.status["stop_loss"] <= 0 or new_stop < self.status["stop_loss"]:
                self.status["stop_loss"] = new_stop
                self._save_status()
            logger.info(f"🛡️ 손절유예({hold_bars+1}/{STOP_GRACE_BARS}봉): "
                        f"{self.status['stop_loss']:,.0f} KRW")
            return
        # v20.6 BD: per-position 트레일링 배수 (TU 진입 시 4.5, 기본 None → 전역 3.5)
        _trail_m = self.status.get("pos_trail_m") or None
        new_stop = calc_trailing_stop(
            self.status["highest_price"], cur_atr, self.status["entry"],
            trail_m=_trail_m)
        if new_stop > self.status["stop_loss"]:
            self.status["stop_loss"] = new_stop
            logger.info(f"트레일링: {new_stop:,.0f} KRW")
            self._save_status()

    def _check_hard_stop(self, price, balances):
        """v19.6: 인트라캔들 하드스톱 — 30초 폴링마다 price <= stop_loss 체크.
        True면 4H 캔들 종가를 기다리지 않고 즉시 전량 매도. Returns True if sold."""
        if not self.status["in_position"]: return False
        if self._partial_selling: return False
        stop = self.status.get("stop_loss", 0.0)
        if stop <= 0 or price > stop: return False
        btc = balances.get(COIN, 0.0)
        if btc < 0.0001: return False

        logger.warning(f"🚨 인트라캔들 하드스톱 발동: price={price:,.0f} <= stop={stop:,.0f}")
        self._partial_selling = True
        try:
            order = self.upbit.sell_market_order(TICKER, btc)
            if not order:
                # v20.5 L1: btc_bot.log 침묵 방지 (tg_error는 유지)
                logger.error(
                    f"하드스톱 매도 주문 실패: sell_market_order None 응답 "
                    f"btc={btc:.8f} price={price:,.0f} stop={stop:,.0f}")
                tg_error(f"*하드스톱 매도 주문 실패*\n다음 루프 재시도")
                return False
            order_uuid = order.get("uuid")
            time.sleep(1.0)
            sf, asp = self._verify_sell_filled(order_uuid)
            if not sf:
                # v20.6 H1: 분할 체결 인식 실패 시 직접 잔고 조회 (이전엔 _sync_balance 호출 →
                # phantom 감지가 status.entry를 0화하여 아래 sell_type 판정이 오분류되었음).
                # 이제 _sync_balance는 _partial_selling 가드가 있어 안전하지만, 여기서는
                # 반환값을 받아야 하므로 upbit_get_all_balances() 직접 호출.
                _bal = upbit_get_all_balances()
                remaining = _bal.get(COIN, 0.0) if _bal else 0.0
                if remaining < 0.00001:
                    asp = api_retry(lambda: pyupbit.get_current_price(TICKER)) or price
                    sf = True
                    logger.warning(f"하드스톱 잔고 fallback: BTC={remaining:.8f} → 매도 완료 판정 (asp={asp:,.0f})")
                else:
                    # v20.5 L1: btc_bot.log 침묵 방지 (tg_error는 유지)
                    logger.error(
                        f"하드스톱 체결 실패 UUID={order_uuid} "
                        f"잔고={remaining:.8f} BTC — 수동 확인 필요")
                    tg_error(f"*하드스톱 체결 실패* UUID:{order_uuid}\n잔고:{remaining:.6f} BTC\n수동 확인 필요")
                    return False

            # v20.6 H1: entry<=0 방어 — status.entry가 외부 리셋 등으로 0이면 stop_loss 기반 추정.
            # 하드스톱 발동 조건 (price <= stop)이므로 손실 가능성 높음 → 기본 "ATR손절" 분류.
            entry = self.status["entry"]
            if entry is None or entry <= 0:
                _fallback_entry = self.status.get("avg_entry_price") or self.status.get("first_entry_price") or 0.0
                if _fallback_entry > 0:
                    logger.warning(
                        f"하드스톱 sell_type 계산: status.entry=0 → fallback "
                        f"avg/first_entry={_fallback_entry:,.0f} 사용")
                    entry = _fallback_entry
            raw   = ((asp - entry) / entry) * 100 if entry > 0 else 0.0
            real  = raw - (COST_RATE * 100)
            hold_bars = self.status.get("hold_bars", 0)
            # v20.6 H1: raw 계산이 신뢰 불가 시(entry=0 → raw=0) 하드스톱은 손실로 간주.
            # price <= stop → 진행 중 하락이 stop을 찍었다는 뜻이므로 ATR손절/STOPLOSS 쿨다운 안전.
            if entry <= 0:
                sell_type = "인트라캔들하드스톱"
                new_cd    = COOLDOWN_STOPLOSS
                logger.error(
                    f"하드스톱 sell_type UNKNOWN: entry=0, raw 계산 무효. "
                    f"보수적으로 STOPLOSS 쿨다운 적용. 수동 확인 권고.")
                tg_warn(
                    f"*하드스톱 sell_type 불확실*\nentry=0으로 raw 계산 불가\n"
                    f"STOPLOSS 쿨다운 ({COOLDOWN_STOPLOSS}s) 적용. 수동 점검 권고.")
            else:
                sell_type = "ATR손절" if raw < 0 else "ATR트레일링(익절)"
                new_cd    = COOLDOWN_STOPLOSS if raw < 0 else COOLDOWN_TRAILING

            self._update_consecutive_loss(real)
            self.status.update({
                "in_position": False, "entry": 0.0, "stop_loss": 0.0,
                "highest_price": 0.0, "hold_bars": 0,
                "partial_tp1_done": False, "partial_tp2_done": False,
                "entry_type": "trend", "pyramid_level": 0, "step_tp_level": 0,
                "first_entry_price": 0.0, "avg_entry_price": 0.0,
                "range_new_mode": False,
                "pos_trail_m": 0.0, "pos_step_lookback": 0.0, "pos_init_ratio": 0.0,  # v20.6 BD + v20.7 C6
                "pyramid_locked": False, "e2_exception_type": "",  # v20.9.0 E2 예외 진입 속성 리셋
                "last_sell_reason": sell_type,
                "last_trade_time": time.time(), "cooldown_seconds": new_cd,
            })
            self._last_known_btc = 0.0
            self._save_status()
            log_trade("SELL", asp,
                      f"사유:인트라캔들하드스톱 표면:{raw:+.2f}% 실질:{real:+.2f}% "
                      f"유형:{sell_type} 보유:{hold_bars}봉")
            log_confirmed_trade(
                action="SELL", price=asp, amount=btc, krw=btc*asp,
                pnl_pct=round(real, 2), sell_reason="인트라캔들하드스톱",
                holding_bars=hold_bars)
            tg_info(
                f"🚨 *하드스톱 매도 체결* (인트라캔들 v{BOT_VERSION})\n"
                f"🕐 {fmt_kst()}\n"
                f"가격:{asp:,.0f} KRW (stop:{stop:,.0f})\n"
                f"수익: 표면{raw:+.2f}% 실질{real:+.2f}%\n"
                f"유형:{sell_type} | 보유:{hold_bars}봉\n"
                f"※ 4H 캔들 종가 대기 없이 즉시 매도")
            return True
        finally:
            self._partial_selling = False

    def _check_partial_tp(self, price, balances, cur_atr, df4h=None):
        if not self.status["in_position"]: return
        entry = self.status["entry"]; btc = balances[COIN]
        first_entry = self.status.get("first_entry_price", 0.0) or entry
        if btc < 0.0001 or cur_atr <= 0: return
        pnl  = (price - entry) / entry
        entry_type = self.status.get("entry_type", "trend")

        # MR 진입은 TP 없음 (별도 MR 청산 로직이 처리)
        if entry_type == "mean_reversion":
            return

        # TP 레벨은 항상 첫 진입가 기준
        tp1 = first_entry + cur_atr * PARTIAL_TP1_ATR
        tp2 = first_entry + cur_atr * PARTIAL_TP2_ATR

        # ── P0: Volatile / Trend_Down — 기존 부분 익절 ──
        if entry_type == "trend":
            adx_val = 20.0
            if df4h is not None:
                try: adx_val = get_adx_full(df4h)["adx"]
                except: pass
            if adx_val >= ADX_STRONG_THRESH:
                tp1_ratio, tp2_ratio = PARTIAL_TP_STRONG_1, PARTIAL_TP_STRONG_2
                mode_str = f"강한추세(ADX:{adx_val:.0f})"
            else:
                tp1_ratio, tp2_ratio = PARTIAL_TP_NORMAL_1, PARTIAL_TP_NORMAL_2
                mode_str = f"보통추세(ADX:{adx_val:.0f})"

            if price >= tp1 and not self.status.get("partial_tp1_done", False):
                qty = btc * tp1_ratio
                if qty * price < MIN_ORDER_KRW: return
                self._partial_selling = True
                order = self.upbit.sell_market_order(TICKER, qty)
                if order:
                    self.status["partial_tp1_done"] = True; self._save_status()
                    self._last_known_btc = btc - qty
                    log_trade("SELL_PARTIAL", price,
                              f"1차익절(ATRx{PARTIAL_TP1_ATR},{mode_str}) 실질:{pnl:+.2%}")
                    log_confirmed_trade(
                        action="SELL_PARTIAL", price=price,
                        amount=qty, krw=qty * price,
                        pnl_pct=round(pnl * 100, 2),
                        sell_reason=f"1차익절(ATRx{PARTIAL_TP1_ATR},{mode_str})",
                        regime=self._last_market_state,
                        holding_bars=self.status.get("hold_bars", 0))
                    tg_info(
                        f"💛 *1차 부분 익절* ({mode_str})\n"
                        f"가격:{price:,.0f} +{pnl:.2%}\n"
                        f"매도:{tp1_ratio:.0%} | 나머지{1-tp1_ratio:.0%} 트레일링")
                self._partial_selling = False

            elif (price >= tp2 and self.status.get("partial_tp1_done", False) and
                  not self.status.get("partial_tp2_done", False)):
                qty = btc * tp2_ratio / (1.0 - tp1_ratio)
                qty = min(qty, btc)
                if qty * price < MIN_ORDER_KRW: return
                self._partial_selling = True
                order = self.upbit.sell_market_order(TICKER, qty)
                if order:
                    self.status["partial_tp2_done"] = True; self._save_status()
                    self._last_known_btc = btc - qty
                    log_trade("SELL_PARTIAL", price,
                              f"2차익절(ATRx{PARTIAL_TP2_ATR},{mode_str}) 실질:{pnl:+.2%}")
                    log_confirmed_trade(
                        action="SELL_PARTIAL", price=price,
                        amount=qty, krw=qty * price,
                        pnl_pct=round(pnl * 100, 2),
                        sell_reason=f"2차익절(ATRx{PARTIAL_TP2_ATR},{mode_str})",
                        regime=self._last_market_state,
                        holding_bars=self.status.get("hold_bars", 0))
                    remaining = 1.0 - tp1_ratio - tp2_ratio
                    tg_info(
                        f"💚 *2차 부분 익절* ({mode_str})\n"
                        f"가격:{price:,.0f} +{pnl:.2%}\n"
                        f"매도:{tp2_ratio:.0%} | 나머지{max(0,remaining):.0%} 트레일링")
                self._partial_selling = False

        # ── Break-Even (Range): TP1에서 25% 매도 + 손절→본전 ──
        elif entry_type == "breakeven":
            if price >= tp1 and not self.status.get("partial_tp1_done", False):
                qty = btc * P1_TP1_SELL_RATIO  # 25%
                if qty * price < MIN_ORDER_KRW: return
                self._partial_selling = True
                order = self.upbit.sell_market_order(TICKER, qty)
                if order:
                    self.status["partial_tp1_done"] = True
                    self.status["stop_loss"] = first_entry  # 손절→본전
                    self._save_status()
                    self._last_known_btc = btc - qty
                    log_trade("SELL_PARTIAL", price,
                              f"BE익절(25%매도,손절→본전) 실질:{pnl:+.2%}")
                    log_confirmed_trade(
                        action="SELL_PARTIAL", price=price,
                        amount=qty, krw=qty * price,
                        pnl_pct=round(pnl * 100, 2),
                        sell_reason="BE익절(25%매도,손절→본전)",
                        regime="Range",
                        holding_bars=self.status.get("hold_bars", 0))
                    tg_info(
                        f"💛 *Break-Even 익절* (Range P1)\n"
                        f"가격:{price:,.0f} +{pnl:.2%}\n"
                        f"매도:25% | 손절→본전({first_entry:,.0f})\n"
                        f"나머지 75% 트레일링")
                self._partial_selling = False
            # TP2 없음 — 나머지는 순수 트레일링

        # ── 피라미딩 (Trend_Up): 무한 계단손절 + 추가매수 ──
        # v20.1 (#23 S3): TP간격=ATR×1.5, 손절=1.5칸 아래, 무한 TP
        # v20.9.0: e2_exception 포지션도 여기 Step TP 갱신 경로 재사용 (TP 허용, 추가매수만 금지)
        elif entry_type == "pyramid" or entry_type == "e2_exception":
            step_lv = self.status.get("step_tp_level", 0)
            interval = cur_atr * STEP_TP_INTERVAL_ATR
            krw_avail = balances["KRW"]
            # v20.9.0: pyramid_locked=True면 추가매수 강제 스킵 (Step TP 갱신만 허용)
            _pyramid_locked = bool(self.status.get("pyramid_locked", False)
                                   or entry_type == "e2_exception")

            # 추가매수 조건 사전 체크 (v19.1)
            _pyr_ema_ok = False
            if df4h is not None:
                _pyr_ema_s = ta.ema(df4h["close"], 21).iloc[-1]
                _pyr_ema_l = ta.ema(df4h["close"], 55).iloc[-1]
                _pyr_ema_ok = _pyr_ema_s > _pyr_ema_l

            _pyr_xgb = ai_engine.predict(df4h) if df4h is not None else 0.0
            _pyr_stats = calc_recent_stats()
            _pyr_gate_pass = check_ai_gate(_pyr_xgb,
                                           last_xgb_probs=list(ai_engine.xgb_prob_history),
                                           market_state="Trend_Up")

            _pyr_ks = self.status.get("kill_switch", False)
            _pyr_mdd = self.status.get("current_mdd", 0.0)
            _pyr_dl_ok, _ = self._check_daily_loss(krw_avail + btc * price)

            changed = False
            for lv in range(step_lv, 20):  # 무한 TP (실질 상한 20)
                tp_price = first_entry + (lv + 1) * interval
                if price < tp_price:
                    break

                # 추가매수 조건 체크
                _skip_reason = None
                # v20.9.0: E2 예외 포지션은 추가매수 완전 금지
                if _pyramid_locked:
                    _skip_reason = "E2 예외 포지션 — 피라미딩 차단 (pyramid_locked)"
                elif not _pyr_gate_pass:
                    _skip_reason = f"AI Gate 미통과 XGB={_pyr_xgb:.3f}"
                elif not _pyr_ema_ok:
                    _skip_reason = "EMA 역배열"
                elif _pyr_ks:
                    _skip_reason = "Kill Switch"
                elif _pyr_mdd >= MDD_STOP_PCT:
                    _skip_reason = f"MDD {_pyr_mdd:.2%}"
                elif not _pyr_dl_ok:
                    _skip_reason = "Daily Loss"

                if _skip_reason:
                    logger.info(f"피라미딩 Lv{lv+1} 추가매수 스킵: {_skip_reason} (TP{lv+1} 도달)")
                else:
                    total_assets = krw_avail + btc * price
                    if lv == 0:
                        add_krw = total_assets * PYRAMID_ADD_RATIOS[0]
                    else:
                        max_add = total_assets * PYRAMID_MAX_RATIO - btc * price
                        add_krw = min(krw_avail * 0.95, max(max_add, 0))
                    add_krw = min(add_krw, krw_avail * 0.95)

                    if add_krw >= MIN_ORDER_KRW:
                        order = self.upbit.buy_market_order(TICKER, add_krw)
                        if order:
                            _uuid = order.get("uuid"); time.sleep(1.0)
                            _filled, _avg = self._verify_order_filled(_uuid)
                            if _filled:
                                old_btc = btc
                                new_btc_bought = add_krw / _avg if _avg > 0 else 0
                                avg_entry = self.status.get("avg_entry_price", 0.0) or entry
                                old_cost = avg_entry * old_btc
                                new_avg = (old_cost + add_krw) / (old_btc + new_btc_bought) if (old_btc + new_btc_bought) > 0 else _avg
                                self.status["avg_entry_price"] = new_avg
                                self._last_buy_time = time.time()
                                # v20.2 H-2: 동일 캔들 _auto_reinvest 중복 차단 플래그
                                if df4h is not None and len(df4h) > 0:
                                    self._last_pyr_add_candle = df4h.index[-1]

                                self._sync_balance()
                                log_trade("BUY_PYRAMID", _avg,
                                          f"피라미딩Lv{lv+1} 추가:{add_krw:,.0f}KRW 평균가:{new_avg:,.0f}")
                                log_confirmed_trade(
                                    action="BUY_PYRAMID", price=_avg,
                                    amount=new_btc_bought, krw=add_krw,
                                    regime="Trend_Up",
                                    xgb_prob=round(_pyr_xgb, 4),
                                    entry_reason=f"피라미딩Lv{lv+1}")
                                tg_info(
                                    f"📈 *피라미딩 추가매수* Lv{lv+1}\n"
                                    f"TP{lv+1} 도달:{tp_price:,.0f}\n"
                                    f"추가:{add_krw:,.0f} KRW\n"
                                    f"체결가:{_avg:,.0f} | 평균매수가:{new_avg:,.0f}\n"
                                    f"AI:{_pyr_xgb:.1%} EMA:OK")
                                btc = self._last_known_btc or balances[COIN]
                                krw_avail = balances.get("KRW", krw_avail - add_krw)
                                # v20.6 U1: 이벤트 리포트 제거 (정기 리포트만 유지)
                                # 과거 코드: TP 도달 시 event_type="tp_reached" 리포트 발송 → 현재 비활성화

                # v20.1: 무한 계단손절 (S3 — 1.5칸 아래)
                # v20.6 BD: TU 포지션은 status["pos_step_lookback"]=2.5 사용 → 더 느슨한 계단
                new_lv = lv + 1
                _step_lb = self.status.get("pos_step_lookback") or 0
                _step_lb = _step_lb if _step_lb > 0 else STEP_LOOKBACK
                if new_lv == 1:
                    new_stop = first_entry                                    # TP1: 본전
                else:
                    new_stop = first_entry + (new_lv - _step_lb) * interval
                new_stop = max(new_stop, first_entry * (1 - MIN_STOP_PCT))    # -5% 하한
                self.status["stop_loss"] = max(self.status.get("stop_loss", 0), new_stop)
                self.status["step_tp_level"] = new_lv
                self.status["pyramid_level"] = new_lv
                changed = True
                logger.info(f"피라미딩 Lv{new_lv}/inf: 손절→{self.status['stop_loss']:,.0f}")

            if changed:
                self._save_status()

    # v19.0: 1회 추가매수 상한 = 현재 총 자산의 20%
    REINVEST_MAX_RATIO = 0.20

    def _auto_reinvest(self, price, balances, market_state, df4h=None, xgb_prob=0.0):
        """v19.1: 피라미딩+TU 유지 시 매 4H 캔들마다 여유자금 자동 추가매수.
        5단계 파이프라인 조건 적용: AI Gate + Trend_Up + EMA 정배열 + 수익+2% + 리스크 필터.
        Returns True if a buy was executed.

        v20.2 H-2: 동일 캔들에 _check_partial_tp 피라미딩 추가매수가 이미 발생했다면 스킵.
        연쇄 진입(피라미딩 15% + 자동투입 20% = 35%)으로 인한 반전 손실 집중을 방지.
        """
        if not self.status["in_position"]:
            return False
        if self.status.get("entry_type") != "pyramid":
            return False
        # v20.9.0: E2 예외 포지션은 pyramid_locked=True → 잔액 투입 금지
        if self.status.get("pyramid_locked", False):
            logger.debug("잔액 투입 스킵: pyramid_locked=True (E2 예외 포지션)")
            return False

        # v20.2 H-2: 동일 캔들 피라미딩 추가매수 선행 발생 시 스킵
        if (df4h is not None and len(df4h) > 0 and
                self._last_pyr_add_candle is not None and
                self._last_pyr_add_candle == df4h.index[-1]):
            logger.info("잔액 투입 스킵: 동일 캔들 피라미딩 추가매수 완료 [v20.2 H-2]")
            return False

        # (0) TP1 완료 후에만 잔액 투입 (pyramid_level >= 1)
        if self.status.get("pyramid_level", 0) < 1:
            return False

        # (1) Trend_Up 유지
        if market_state != "Trend_Up":
            logger.info(f"잔액 투입 스킵: Regime={market_state} (Trend_Up 아님)")
            return False

        # (2) AI Gate — XGB >= REGIME_CONFIG 기준 OR 분포 상위 10%
        stats = calc_recent_stats()
        gate_pass = check_ai_gate(xgb_prob,
                                  last_xgb_probs=list(ai_engine.xgb_prob_history),
                                  market_state=market_state)
        if not gate_pass:
            logger.info(f"잔액 투입 스킵: AI Gate 미통과 XGB={xgb_prob:.3f}")
            return False

        # (3) EMA 정배열
        if df4h is not None:
            ema_s = ta.ema(df4h["close"], 21).iloc[-1]
            ema_l = ta.ema(df4h["close"], 55).iloc[-1]
            if ema_s <= ema_l:
                logger.info(f"잔액 투입 스킵: EMA 역배열 (21={ema_s:,.0f} <= 55={ema_l:,.0f})")
                return False
        else:
            logger.info("잔액 투입 스킵: df4h 없음")
            return False

        # (4) 현재가 >= 평균 매수가 × 1.02 (수익 +2% 이상)
        avg_entry = self.status.get("avg_entry_price", 0.0) or self.status.get("entry", 0.0)
        if avg_entry > 0 and price < avg_entry * 1.02:
            logger.info(f"잔액 투입 스킵: 수익 부족 (현재:{price:,.0f} < 평균매수가×1.02={avg_entry*1.02:,.0f})")
            return False

        # (5) 리스크 필터 — Daily Loss / MDD / Kill Switch
        ks_active = self.status.get("kill_switch", False)
        if ks_active:
            logger.info("잔액 투입 스킵: Kill Switch 발동 중")
            return False
        current_mdd = self.status.get("current_mdd", 0.0)
        if current_mdd >= MDD_STOP_PCT:
            logger.info(f"잔액 투입 스킵: MDD {current_mdd:.2%} >= {MDD_STOP_PCT:.2%}")
            return False
        btc = balances.get(COIN, 0)
        krw = balances.get("KRW", 0)
        total_assets = krw + btc * price
        dl_ok, dl_pct = self._check_daily_loss(total_assets)
        if not dl_ok:
            logger.info(f"잔액 투입 스킵: Daily Loss {dl_pct:.2%}")
            return False

        # (6) 금액 계산 — 1회 상한 20%, MIN_ORDER_KRW 이상
        max_add = total_assets * self.REINVEST_MAX_RATIO  # 20% 상한
        add_krw = min(krw * 0.95, max_add)

        if add_krw < MIN_ORDER_KRW:
            logger.info(f"잔액 투입 스킵: 금액 부족 ({add_krw:,.0f} < {MIN_ORDER_KRW:,.0f})")
            return False

        order = self.upbit.buy_market_order(TICKER, add_krw)
        if order:
            _uuid = order.get("uuid"); time.sleep(1.0)
            _filled, _avg = self._verify_order_filled(_uuid)
            if _filled:
                # 평균 매수가 재계산
                old_btc = btc
                new_btc_bought = add_krw / _avg if _avg > 0 else 0
                old_cost = avg_entry * old_btc if avg_entry > 0 else self.status.get("entry", 0.0) * old_btc
                new_avg = (old_cost + add_krw) / (old_btc + new_btc_bought) if (old_btc + new_btc_bought) > 0 else _avg
                self.status["avg_entry_price"] = new_avg
                self._last_buy_time = time.time()
                # v20.2 H-2: 대칭 플래그 세팅 (_check_partial_tp 중복 방지)
                if df4h is not None and len(df4h) > 0:
                    self._last_pyr_add_candle = df4h.index[-1]

                self._sync_balance()
                self._save_status()
                log_trade("BUY_REINVEST", _avg,
                          f"자동투입:{add_krw:,.0f}KRW 총자산:{total_assets:,.0f} 평균가:{new_avg:,.0f}")
                log_confirmed_trade(
                    action="BUY_REINVEST", price=_avg,
                    amount=new_btc_bought, krw=add_krw,
                    regime=market_state,
                    xgb_prob=round(xgb_prob, 4),
                    entry_reason="자동투입(Reinvest)")
                tg_info(
                    f"📈 *잔액 자동 투입* (v{BOT_VERSION})\n"
                    f"체결가:{_avg:,.0f}\n"
                    f"추가:{add_krw:,.0f} KRW\n"
                    f"총자산:{total_assets:,.0f} | 평균매수가:{new_avg:,.0f}\n"
                    f"AI:{xgb_prob:.1%} EMA:OK 수익:{(price/avg_entry-1)*100:+.1f}%")
                logger.info(f"v19.1 잔액 자동 투입: {add_krw:,.0f} KRW @ {_avg:,.0f} 평균가:{new_avg:,.0f}")
                return True
        return False

    def _check_regime_switch(self, prev_regime, cur_regime, balances, price):
        """v18.4: 포지션 보유 중 Regime 전환 시 entry_type 자동 전환."""
        if not self.status["in_position"]:
            return
        # v20.5 Range New: Range 진입 포지션은 Regime 전환 시에도 유지 (regime 이탈 청산 없음)
        if self.status.get("range_new_mode", False):
            return
        old_et = self.status.get("entry_type", "trend")
        if old_et == "mean_reversion":
            return  # MR은 전환 없이 MR 청산 로직으로 처리

        # 새 Regime → 새 entry_type 결정
        if cur_regime == "Trend_Up":
            new_et = "pyramid"
        elif cur_regime == "Range":
            new_et = "breakeven"
        else:
            new_et = "trend"

        if new_et == old_et:
            return

        _mode_names = {"pyramid": "피라미딩", "breakeven": "Break-Even",
                       "trend": "P0", "mean_reversion": "평균회귀"}

        # 포지션 비율 기반 pyramid_level 산정
        new_pyr_lv = 0
        if new_et == "pyramid":
            btc_val = balances.get(COIN, 0) * price
            total   = balances.get("KRW", 0) + btc_val
            pos_pct = btc_val / total if total > 0 else 0
            # v18.8 (T1): 60%=Lv0, 80%=Lv1 (TP1후), 95%=Lv2 (TP2후)
            if   pos_pct >= 0.88: new_pyr_lv = 2
            elif pos_pct >= 0.70: new_pyr_lv = 1
            else:                 new_pyr_lv = 0

        self.status["entry_type"] = new_et
        self.status["pyramid_level"] = new_pyr_lv
        self._save_status()

        logger.info(f"Regime 전환 entry_type: {old_et}→{new_et} "
                    f"(pyr_lv={new_pyr_lv}) [{prev_regime}→{cur_regime}]")
        tg_info(
            f"🔄 *포지션 모드 전환* (v{BOT_VERSION})\n"
            f"시장: {prev_regime} → {cur_regime}\n"
            f"모드: {_mode_names.get(old_et, old_et)} → {_mode_names.get(new_et, new_et)}\n"
            f"{'피라미딩 Lv' + str(new_pyr_lv) if new_et == 'pyramid' else ''}"
            f"{'추가매수 중단' if old_et == 'pyramid' and new_et != 'pyramid' else ''}")

    def _update_consecutive_loss(self, real_pnl):
        if real_pnl < 0:
            self.status["consecutive_losses"] = self.status.get("consecutive_losses", 0) + 1
            cons = self.status["consecutive_losses"]
            if cons >= MAX_CONSECUTIVE_LOSS:
                tg_warn(f"*{cons}연패 손실 모드*\n포지션 {LOSS_MODE_POS_MULT:.0%}배 + Gate {LOSS_MODE_GATE:.0%}")
        else:
            old = self.status.get("consecutive_losses", 0)
            self.status["consecutive_losses"] = 0
            if old >= MAX_CONSECUTIVE_LOSS:
                tg_info("✅ *손실 모드 해제* — 정상 운영 복귀")
        self._save_status()

    def _verify_order_filled(self, order_uuid, retries=5, delay=2.0):
        """v18.4: 2초 간격 5회(최대 10초) + 잔고 직접 확인 fallback"""
        for i in range(retries):
            try:
                params = {"uuid": order_uuid}
                resp   = requests.get("https://api.upbit.com/v1/order", params=params,
                                      headers=_auth_header(params), timeout=10)
                if resp.status_code == 200:
                    data  = resp.json(); state = data.get("state", "")
                    avg   = float(data.get("avg_buy_price") or 0)
                    if state == "done" and avg > 0: return True, avg
                    elif state in ("cancel", "cancelled"): return False, 0.0
                    logger.info(f"체결 대기 ({state},{i+1}/{retries})")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"체결 조회: {e}"); time.sleep(delay)
        # fallback: 잔고에서 BTC 보유 여부 직접 확인
        try:
            self._sync_balance()
            bal = self.upbit.get_balance(COIN)
            if bal and float(bal) > 0.0001:
                avg_price = self.upbit.get_avg_buy_price(COIN)
                logger.info(f"체결 확인(잔고 fallback): {float(bal):.6f} BTC @ {avg_price:,.0f}")
                return True, float(avg_price) if avg_price else 0.0
        except Exception as e:
            logger.error(f"잔고 fallback 실패: {e}")
        return False, 0.0

    def _verify_sell_filled(self, order_uuid, retries=5, delay=1.0):
        for i in range(retries):
            try:
                params = {"uuid": order_uuid}
                resp   = requests.get("https://api.upbit.com/v1/order", params=params,
                                      headers=_auth_header(params), timeout=10)
                if resp.status_code == 200:
                    data   = resp.json(); state = data.get("state", "")
                    ev     = float(data.get("executed_volume") or 0)
                    trades = data.get("trades", [])
                    if state == "done" and ev > 0:
                        sp = (sum(float(t["price"])*float(t["volume"]) for t in trades)/ev
                              if trades else
                              api_retry(lambda: pyupbit.get_current_price(TICKER)) or 0)
                        return True, sp
                    elif state in ("cancel", "cancelled"): return False, 0.0
                    logger.info(f"매도 대기 ({state},{i+1}/{retries})")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"매도 체결 조회: {e}"); time.sleep(delay)
        # v20.1: retries 소진 → 잔고 fallback (_check_hard_stop과 동일)
        try:
            bal = self._sync_balance()
            remaining = bal.get(COIN, 0.0) if bal else 0.0
            if remaining < 0.00001:
                asp = api_retry(lambda: pyupbit.get_current_price(TICKER)) or 0.0
                logger.warning(f"매도 체결 잔고 fallback: BTC={remaining:.8f} → 매도 완료 판정 (asp={asp:,.0f})")
                return True, asp
        except Exception as e:
            logger.error(f"매도 잔고 fallback 조회 실패: {e}")
        return False, 0.0

    def _handle_api_failure(self):
        self._api_fail_count += 1
        wait = min(API_FAIL_SLEEP * self._api_fail_count, API_FAIL_MAX_SLEEP)
        if self._api_fail_count >= API_FAIL_THRESHOLD and not self._api_fail_alerted:
            self._api_fail_alerted = True
            pos = ""
            if self.status["in_position"]:
                pos = (f"\n⚠️ 포지션 보유 "
                       f"매수:{self.status['entry']:,.0f}/"
                       f"손절:{self.status['stop_loss']:,.0f}")
            tg_error(f"*API 장애* {self._api_fail_count}회/{wait}s{pos}")
        time.sleep(wait)

    def _reset_api_fail(self):
        if self._api_fail_count > 0:
            if self._api_fail_alerted: tg_info(f"✅ *API 복구* | {fmt_kst()}")
            self._api_fail_count = 0; self._api_fail_alerted = False

    def _check_daily_loss(self, equity):
        try:
            if not os.path.exists(TRADE_LOG): return True, 0.0
            df_log = pd.read_csv(TRADE_LOG)
            today  = now_kst().strftime("%Y-%m-%d")
            sells  = df_log[(df_log["action"] == "SELL") &
                            (df_log["datetime"].str.startswith(today))]
            if sells.empty: return True, 0.0
            total  = sum(float(m.group(1)) for note in sells["note"]
                         for m in [re.search(r"실질:([+-][\d.]+)%", str(note))] if m) / 100.0
            ok = total > -DAILY_LOSS_LIMIT
            if not ok: logger.info(f"Daily Loss: {total:.2%}")
            return ok, total
        except: return True, 0.0

    def _should_send_report(self, force=False):
        if force: return True
        now = now_kst()
        if now.hour not in REPORT_HOURS_KST: return False
        if self.last_report_dt is None: return True
        last = self.last_report_dt
        if last.tzinfo is None: last = last.replace(tzinfo=KST)
        return last.hour != now.hour or last.date() != now.date()

    def _check_rollback_triggers(self, equity, price):
        """v20.9.10 #75-B: E2 OFF 모드 롤백 트리거 자동 알림.
        조건:
          1) 일손실 -3% (24h 1회) — 기존 -5% 한도 도달 전 경고
          2) 누적 손실 -5% (24h 1회)
          3) BTC -10% in 1주 (24h 1회)
        각 알림은 status.json 의 last_alert_* 필드로 24h dedup.
        """
        try:
            now_ts = time.time()
            DEDUP_SECS = 24 * 3600

            # 1) 일손실 -3%
            try:
                dl_ok, dl_pct = self._check_daily_loss(equity)
                if dl_pct is not None and dl_pct <= -0.03:
                    last = float(self.status.get("last_alert_daily_loss", 0) or 0)
                    if now_ts - last >= DEDUP_SECS:
                        tg_error(
                            f"⚠️ *일손실 -3% 도달* (v{BOT_VERSION})\n\n"
                            f"오늘 손익: {dl_pct*100:+.2f}%\n"
                            f"한도: -{DAILY_LOSS_LIMIT*100:.0f}% (자동 차단)\n\n"
                            f"거래 신중 검토 권장. E2 OFF 모드 진행 중 — 시장 상황 확인 필요.")
                        self.status["last_alert_daily_loss"] = now_ts
                        self._save_status()
            except Exception as _e1:
                logger.debug(f"일손실 알림 체크 오류: {_e1}")

            # 2) 누적 손실 -5%
            try:
                init_eq = float(self.status.get("initial_equity", 0) or 0)
                if init_eq > 0:
                    cum_pct = (equity - init_eq) / init_eq * 100
                    if cum_pct <= -5.0:
                        last = float(self.status.get("last_alert_cumulative_loss", 0) or 0)
                        if now_ts - last >= DEDUP_SECS:
                            tg_error(
                                f"🚨 *롤백 트리거: 누적 손실* (v{BOT_VERSION})\n\n"
                                f"누적: {cum_pct:+.2f}%\n"
                                f"시작 자산: {init_eq:,.0f} KRW\n"
                                f"현재 자산: {equity:,.0f} KRW\n\n"
                                f"권장 액션:\n"
                                f"  1. 시장 상황 확인\n"
                                f"  2. 롤백 검토:\n"
                                f"     `cp btc_bot_v290.py.bak.pre_20.9.10 btc_bot_v290.py`\n"
                                f"     `systemctl restart btc_bot.service`")
                            self.status["last_alert_cumulative_loss"] = now_ts
                            self._save_status()
            except Exception as _e2:
                logger.debug(f"누적 손실 알림 체크 오류: {_e2}")

            # 3) BTC -10% in 1주
            try:
                df_d = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=10)
                if df_d is not None and len(df_d) >= 8:
                    p_now = float(df_d["close"].iloc[-1])
                    p_7d  = float(df_d["close"].iloc[-8])
                    if p_7d > 0:
                        wk_chg = (p_now - p_7d) / p_7d * 100
                        if wk_chg <= -10.0:
                            last = float(self.status.get("last_alert_btc_weekly", 0) or 0)
                            if now_ts - last >= DEDUP_SECS:
                                init_eq = float(self.status.get("initial_equity", 0) or 0)
                                cum_pct = ((equity - init_eq) / init_eq * 100) if init_eq > 0 else 0
                                tg_error(
                                    f"🚨 *롤백 트리거: BTC 1주 {wk_chg:+.2f}%* (v{BOT_VERSION})\n\n"
                                    f"BTC 7일 전: {p_7d:,.0f} KRW\n"
                                    f"BTC 현재:   {p_now:,.0f} KRW\n"
                                    f"변화: {wk_chg:+.2f}%\n\n"
                                    f"BEAR 도래 가능성 — 롤백 검토 권장.\n"
                                    f"봇 누적: {cum_pct:+.2f}%\n\n"
                                    f"롤백 명령:\n"
                                    f"  `cp btc_bot_v290.py.bak.pre_20.9.10 btc_bot_v290.py && systemctl restart btc_bot.service`")
                                self.status["last_alert_btc_weekly"] = now_ts
                                self._save_status()
            except Exception as _e3:
                logger.debug(f"BTC 주간 알림 체크 오류: {_e3}")
        except Exception as e:
            logger.debug(f"_check_rollback_triggers 오류: {e}")

    def _update_daily_trend(self, df4h=None):
        now = now_kst()
        if (self.last_trend_check is None or
                (now - self.last_trend_check) > timedelta(hours=4)):
            self.daily_trend    = get_daily_trend()
            self.last_trend_check = now
            # v20.6 E2: 일봉 EMA200 기반 BEAR 모드 갱신 (4H 주기로 함께 수행)
            # v20.9.0: F5 (4H EMA21<EMA55) 포함을 위해 df4h 전달
            if E2_ENABLED:
                self._update_e2_bear_mode(df4h=df4h)

    def _update_e2_bear_mode(self, df4h=None):
        """v20.9.0 E2: F2 + F5 → F10 BEAR 모드 판정.
        F2 = 일봉 종가 < EMA200 (4H 주기 갱신)
        F5 = 4H EMA21 < EMA55 (df4h 전달 시 갱신)
        F10 = F2 OR F5 (E2_BLOCK_MODE == "F10")
        bars_since_e2: Option B — F10 ON 시 +1, OFF 시 즉시 0 리셋.

        v20.9.4: 자정 경과 시 일일 카운터 자동 리셋
        """
        # v20.9.4: 자정 경과 감지 → 일일 카운터 리셋
        today_str = datetime.now(KST).strftime("%Y-%m-%d")
        if self._e2_counters_date != today_str:
            if self._e2_counters_date is not None:
                logger.info(
                    f"E2 일일 카운터 리셋: {self._e2_counters_date} → {today_str} "
                    f"(전일 차단 {self._e2_blocks_today}, "
                    f"O3예외 {self._e2_o3_exceptions_today}, "
                    f"gap예외 {self._e2_gap_exceptions_today})")
            self._e2_blocks_today         = 0
            self._e2_o3_exceptions_today  = 0
            self._e2_gap_exceptions_today = 0
            self._e2_counters_date        = today_str
            # status 동기화 (자정 직후 대시보드·리포트 표시 0 초기화)
            self.status["live_e2_blocks_today"]         = 0
            self.status["live_e2_o3_exceptions_today"]  = 0
            self.status["live_e2_gap_exceptions_today"] = 0

        prev_bear = self._e2_bear_mode
        # F2 갱신 (일봉 데이터)
        bear_f2, d_close, d_ema200, available = compute_e2_bear_mode()
        self._e2_data_available = available
        if available:
            self._e2_f2_active    = bool(bear_f2)
            self._e2_daily_close  = d_close
            self._e2_daily_ema200 = d_ema200
            if d_ema200 > 0:
                self._e2_daily_gap_pct = (d_close - d_ema200) / d_ema200 * 100
        else:
            # 데이터 부족 처리
            if E2_DATA_INSUFFICIENT_BEHAVIOR == "block":
                logger.warning("E2 일봉 EMA200 데이터 부족 → F2 차단 유지 (보수)")
                self._e2_f2_active = True
            else:
                logger.info("E2 일봉 EMA200 데이터 부족 → F2 허용 (관대)")
                self._e2_f2_active = False
        # F5 갱신 (4H 데이터, df4h 제공 시만)
        if E2_F5_ENABLED and df4h is not None:
            f5_active, ema21_4h, ema55_4h = compute_e2_f5(df4h)
            self._e2_f5_active = f5_active
            self._e2_ema21_4h  = ema21_4h
            self._e2_ema55_4h  = ema55_4h
        # F10 = F2 OR F5 (E2_BLOCK_MODE 기준)
        if E2_BLOCK_MODE == "F10":
            self._e2_bear_mode = bool(self._e2_f2_active or self._e2_f5_active)
        else:
            self._e2_bear_mode = bool(self._e2_f2_active)
        # 차단 이유 분류
        if self._e2_f2_active and self._e2_f5_active:
            self._e2_block_reason = "BOTH"
        elif self._e2_f2_active:
            self._e2_block_reason = "F2"
        elif self._e2_f5_active:
            self._e2_block_reason = "F5"
        else:
            self._e2_block_reason = "NONE"
        # bars_since_e2 추적 (Option B: ON→+1, OFF→즉시 0)
        bars_prev = int(self.status.get("bars_since_e2", 0))
        if self._e2_bear_mode:
            bars_now = bars_prev + 1
            if not prev_bear:  # OFF → ON 전환
                self.status["live_e2_activation_date"] = fmt_kst()
        else:
            bars_now = 0
            if prev_bear:  # ON → OFF 전환
                self.status["live_e2_activation_date"] = None
        self.status["bars_since_e2"] = bars_now
        self._e2_last_refresh = time.time()
        # 대시보드/리포트 status 동기화
        self.status["live_e2_bear_mode"]    = bool(self._e2_bear_mode)
        self.status["live_e2_f2_active"]    = bool(self._e2_f2_active)
        self.status["live_e2_f5_active"]    = bool(self._e2_f5_active)
        self.status["live_e2_block_reason"] = str(self._e2_block_reason)
        self.status["live_daily_close"]     = float(self._e2_daily_close or 0.0)
        self.status["live_daily_ema200"]    = float(self._e2_daily_ema200 or 0.0)
        self.status["live_daily_ema200_gap_pct"] = float(self._e2_daily_gap_pct)
        self.status["live_ema21_4h"]        = float(self._e2_ema21_4h)
        self.status["live_ema55_4h"]        = float(self._e2_ema55_4h)
        self.status["live_e2_blocks_today"] = int(self._e2_blocks_today)
        self.status["live_e2_o3_exceptions_today"]  = int(self._e2_o3_exceptions_today)
        self.status["live_e2_gap_exceptions_today"] = int(self._e2_gap_exceptions_today)
        self._save_status()
        days_eq = bars_now / 6.0
        logger.info(
            f"E2: F2={'ON' if self._e2_f2_active else 'OFF'} "
            f"F5={'ON' if self._e2_f5_active else 'OFF'} "
            f"F10={'ON' if self._e2_bear_mode else 'OFF'} "
            f"(reason={self._e2_block_reason}) "
            f"| 일봉 {self._e2_daily_close or 0:,.0f} gap {self._e2_daily_gap_pct:+.2f}% "
            f"| bars {bars_now}/1080 (≈{days_eq:.1f}일/180일)")
        # 모드 전환 시에만 텔레그램 알림
        if prev_bear != self._e2_bear_mode:
            if self._e2_bear_mode:
                tg_info(
                    f"🐻 *E2 BEAR 모드 진입* ({self._e2_block_reason})\n"
                    f"일봉 `{self._e2_daily_close or 0:,.0f}` vs EMA200 `{self._e2_daily_ema200 or 0:,.0f}` "
                    f"({self._e2_daily_gap_pct:+.2f}%)\n"
                    f"4H EMA21 {'<' if self._e2_f5_active else '≥'} EMA55\n"
                    f"→ 신규 진입 차단. O3 예외 ON / 180일+gap 예외 ON.")
            else:
                tg_info(
                    f"☀️ *E2 BEAR 모드 해제*\n"
                    f"F2=OFF, F5=OFF\n"
                    f"→ 신규 진입 재개. bars_since_e2=0 리셋.")

    # ── 텔레그램 명령어 수신 ─────────────────────────────
    def _telegram_command_listener(self):
        logger.info("텔레그램 명령어 리스너 시작")
        last_update_id = 0
        while True:
            try:
                resp = requests.get(
                    f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                    params={"offset": last_update_id + 1, "timeout": 30},
                    timeout=35)
                if resp.status_code != 200:
                    time.sleep(5); continue
                for update in resp.json().get("result", []):
                    last_update_id = update["update_id"]
                    msg     = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text    = msg.get("text", "").strip()
                    if chat_id != str(TG_CHAT_ID): continue
                    if text.startswith("/"): self._handle_command(text)
            except requests.exceptions.ReadTimeout:
                # v20.9.6: getUpdates long-poll 자연 타임아웃 — WARN 소거 (노이즈)
                continue
            except requests.exceptions.ConnectTimeout:
                # v20.9.6: 연결 타임아웃 — WARN 소거 (자동 재시도)
                time.sleep(10); continue
            except Exception as e:
                logger.warning(f"명령어 리스너 오류: {e}")
                time.sleep(10)

    def _handle_command(self, text):
        parts = text.strip().split()
        cmd   = parts[0].lower()
        now   = fmt_kst()
        try:
            if cmd == "/status":
                ks  = self.status.get("kill_switch", False)
                mdd = self.status.get("current_mdd", 0.0)
                dth = self.status.get("dynamic_threshold", AI_GATE_THRESHOLD)
                msg  = f"⚙️ *현재 파라미터* (v{BOT_VERSION})\n🕐 {now}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"AI Gate (기본): {AI_GATE_THRESHOLD:.0%}\n"
                msg += f"AI Gate (동적): {dth:.0%}\n"
                msg += f"AI Gate (보수적): {AI_UNRELIABLE_GATE:.0%}\n"
                msg += f"Rule Score 기준: {SCORE_THRESHOLD}점\n"
                msg += f"일손실 한도: -{DAILY_LOSS_LIMIT:.0%}\n"
                msg += f"MDD 한도: -{MDD_STOP_PCT:.0%} (현재:{mdd:.1%})\n"
                msg += f"Kill Switch: {'🛑 발동' if ks else '✅ 정상'}\n"
                if ks: msg += f"사유: {self.status.get('kill_switch_reason','')}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"포지션: {'보유 중' if self.status['in_position'] else '없음'}\n"
                tg_info(msg)

            elif cmd == "/pause":
                self.status["paused"] = True; self._save_status()
                tg_info(f"⏸️ *봇 진입 일시 중단*\n🕐 {now}\n재개: /resume")

            elif cmd == "/resume":
                self.status["paused"] = False; self._save_status()
                tg_info(f"▶️ *봇 진입 재개*\n🕐 {now}")

            elif cmd == "/killswitch":
                # Kill Switch 해제/조회/리셋 (v20.8 확장)
                sub = parts[1].lower() if len(parts) > 1 else ""
                if sub == "off":
                    # 수동 해제 (이력 유지, 24h 카운터는 그대로)
                    self.status["kill_switch"]        = False
                    self.status["kill_switch_reason"] = ""
                    self._save_status()
                    tg_info(f"✅ *Kill Switch 수동 해제* | {now}")
                elif sub == "status":
                    # 현재 상태 + 이력 조회
                    ks = self.status.get("kill_switch", False)
                    reason = self.status.get("kill_switch_reason", "")
                    last_at = float(self.status.get("last_killswitch_at", 0.0) or 0.0)
                    last_rec = float(self.status.get("last_killswitch_recovered_at", 0.0) or 0.0)
                    cnt24 = int(self.status.get("killswitch_count_24h", 0) or 0)
                    cur_mdd = float(self.status.get("current_mdd", 0.0) or 0.0)
                    last_at_str = datetime.fromtimestamp(last_at, tz=KST).strftime("%m-%d %H:%M") if last_at else "없음"
                    last_rec_str = datetime.fromtimestamp(last_rec, tz=KST).strftime("%m-%d %H:%M") if last_rec else "없음"
                    tg_info(
                        f"🛡️ *Kill Switch 상태*\n"
                        f"현재: {'🛑 발동' if ks else '✅ 정상'}\n"
                        f"사유: {reason or '-'}\n"
                        f"현재 MDD: {cur_mdd*100:.2f}%\n"
                        f"마지막 발동: {last_at_str}\n"
                        f"마지막 자동복구: {last_rec_str}\n"
                        f"24h 발동 카운트: {cnt24} (한도 {self.KS_MAX_24H_COUNT})")
                elif sub == "reset":
                    # 24h 카운터 리셋 + 해제 (비상 재시작)
                    self.status["kill_switch"]          = False
                    self.status["kill_switch_reason"]   = ""
                    self.status["killswitch_count_24h"] = 0
                    self.status["last_killswitch_at"]   = 0.0
                    self._save_status()
                    tg_info(f"🔄 *Kill Switch 완전 리셋* | 24h 카운터 초기화 | {now}")
                else:
                    tg_info(
                        f"ℹ️ Kill Switch 명령:\n"
                        f"/killswitch off — 수동 해제\n"
                        f"/killswitch status — 상태 조회\n"
                        f"/killswitch reset — 24h 카운터 리셋 (비상 재시작)")

            elif cmd == "/report":
                tg_info("📊 리포트 요청 수신 — 다음 루프에서 전송")
                self.last_report_dt = None

            elif cmd == "/log":
                keyword = parts[1] if len(parts) > 1 else ""
                n = int(parts[2]) if len(parts) > 2 else 20
                try:
                    with open(LOG_FILE, encoding="utf-8") as f:
                        lines = f.readlines()
                    if keyword: lines = [l for l in lines if keyword in l]
                    lines = lines[-n:]
                    if lines:
                        tg_info(f"📋 *로그* ({keyword or '전체'} {len(lines)}건)\n"
                                f"```\n{''.join(lines[-15:])[-1500:]}\n```")
                    else:
                        tg_info(f"📋 '{keyword}' 로그 없음")
                except Exception as e:
                    tg_error(f"로그 조회 오류: {e}")

            elif cmd == "/retrain":
                tg_info("🔄 수동 재학습 요청 — 다음 루프에서 실행")
                ai_engine.last_train_dt = None  # 강제 재학습 트리거

        except Exception as e:
            logger.error(f"명령어 처리 오류: {e}")

    # ── 월간 리포트 ──────────────────────────────────────
    def _check_monthly_report(self, equity):
        now = now_kst()
        if now.day != 1 or now.hour != 0: return
        if self._last_monthly_report and self._last_monthly_report.month == now.month: return
        self._last_monthly_report = now
        self._send_monthly_report(equity)

    def _send_monthly_report(self, equity, ym=None):
        """v20.9.9 #68: 월간 리포트 보강.
        ym 미지정 시 직전 달 (자동 매월 1일 호출용). 지정 시 백필."""
        try:
            now = now_kst()
            if ym is None:
                last_m = (now.replace(day=1) - timedelta(days=1))
                ym     = last_m.strftime("%Y-%m")
            generate_monthly_report(ym=ym, equity=equity,
                                    status=self.status, push=True, send_tg=True)
        except Exception as e:
            logger.error(f"월간 리포트 오류: {e}", exc_info=True)

    # ── 시간당 리포트 ─────────────────────────────────────
    def _send_report(self, df4h, price, balances, atr_result, force=False):
        if not self._should_send_report(force=force): return
        try:
            kst_now = now_kst()
            equity  = balances["KRW"] + balances[COIN] * price
            if self.status["initial_equity"] == 0:
                self.status["initial_equity"] = equity
            else:
                self._update_initial_equity(equity)

            xgb_prob = ai_engine.predict(df4h)
            ema_s    = ta.ema(df4h["close"], 21).iloc[-1]
            ema_l    = ta.ema(df4h["close"], 55).iloc[-1]
            rsi      = ta.rsi(df4h["close"]).iloc[-1]
            adx_info = get_adx_full(df4h)

            is_1d_up, _, _     = self.daily_trend
            atr_ok, atr_regime, cur_atr, cur_pct = atr_result
            # v18.5: 리포트 단계에서는 회색지대 떨림을 막기 위해 직전 Regime 전달만,
            # 실제 Regime 갱신/저장은 캔들 확정 후 한 번만 수행한다.
            market_state = classify_market(atr_ok, atr_regime, adx_info,
                                           prev_regime=self._last_market_state)
            mkt_disp     = market_display(market_state)

            stats      = calc_recent_stats()
            winrate    = stats["winrate"]
            win_streak = stats["win_streak"]
            recent_pf  = stats["pf"]
            cons_loss  = self.status.get("consecutive_losses", 0)

            # v20.9.5: 실거래 PF 대시보드/외부 노출 (#47)
            self.status["live_real_pf"]              = float(stats["pf"] or 0.0)
            self.status["live_real_pf_n"]            = int(stats["trade_count"] or 0)
            self.status["live_real_penalty_active"]  = bool(
                stats["trade_count"] >= THRESHOLD_ADJUST_TRADES and
                0 < stats["pf"] < PERF_LOW_PF_THRESHOLD
            )

            gate_pass  = check_ai_gate(xgb_prob,
                                       last_xgb_probs=list(ai_engine.xgb_prob_history),
                                       market_state=market_state)

            rule_score, rule_details, ema_ok = calc_weighted_score(
                ema_s, ema_l, price, df4h, is_1d_up, atr_result, cur_atr)

            # vA: ADX 기반 score_th 분기 (리포트용)
            rpt_adx = adx_info["adx"]
            rpt_adx_blocked = ADX_BLOCK_LOW <= rpt_adx <= ADX_BLOCK_HIGH
            if rpt_adx < ADX_BLOCK_LOW:
                rpt_score_th = ADX_LOW_SCORE_TH
            elif rpt_adx > ADX_BLOCK_HIGH:
                rpt_score_th = ADX_HIGH_SCORE_TH
            else:
                rpt_score_th = SCORE_THRESHOLD  # 차단 구간이므로 표시용
            score_pass = ema_ok and rule_score >= rpt_score_th and not rpt_adx_blocked

            last_t    = float(self.status.get("last_trade_time", 0))
            cd_secs   = int(self.status.get("cooldown_seconds", COOLDOWN_ENTRY))
            cd_remain = max(0.0, cd_secs - (time.time() - last_t))
            dl_ok, dl_pct = self._check_daily_loss(equity)

            timing_ok_r, timing_reason_r = check_entry_timing(df4h, price)
            # v19.0 D8: 1H RSI 필터 삭제
            ks_active  = self.status.get("kill_switch", False)
            mdd_val    = self.status.get("current_mdd", 0.0)
            paused     = self.status.get("paused", False)
            # v18.9 (X1-C): Trend_Down 진입 완전 차단
            td_blocked = (market_state == "Trend_Down")
            # v19.6: VWAP 필터 사전 계산 (리포트 표시 + can_enter 반영)
            try:
                _rpt_typ = (df4h["high"] + df4h["low"] + df4h["close"]) / 3
                _rpt_vwap = float((_rpt_typ * df4h["volume"]).rolling(20).sum().iloc[-1]
                                  / df4h["volume"].rolling(20).sum().iloc[-1])
            except Exception:
                _rpt_vwap = 0.0
            _vwap_applies = market_state not in ("Range", "Trend_Down")
            _vwap_ok = (not _vwap_applies) or (_rpt_vwap <= 0) or (price > _rpt_vwap)
            # v20.9.1: E2 활성 시 can_enter=False (예외 평가는 실전 진입 경로에서만)
            # → 리포트 최종 판정에 "차단: E2 BEAR" 정확 표시
            _e2_report_blocks = bool(E2_ENABLED and self._e2_bear_mode)
            can_enter  = (gate_pass and score_pass and cd_remain == 0 and
                          dl_ok and timing_ok_r and not paused and
                          not ks_active and mdd_val < MDD_STOP_PCT and
                          not td_blocked and _vwap_ok and
                          not _e2_report_blocks)

            # v18.4: Regime별 실제 진입 금액 계산 (리포트용)
            if market_state == "Trend_Up":
                pos_prev = equity * PYRAMID_INITIAL_RATIO  # v18.9: 80% 피라미딩 초기
            else:
                pos_prev = calc_position_size(equity, price, cur_atr, xgb_prob,
                                              rule_score, adx_info, market_state,
                                              cons_loss, win_streak, winrate, recent_pf,
                                              trade_count=stats["trade_count"])

            if cons_loss >= MAX_CONSECUTIVE_LOSS: mode_str = f"🛑{cons_loss}연패손실모드"
            elif win_streak >= WIN_STREAK_THRESHOLD: mode_str = f"🔥{win_streak}연승공격모드"
            else: mode_str = mkt_disp

            ai_mode = "정상" if ai_engine.is_reliable() else "⚠️보수적"
            def mk(c): return "✅" if c else "❌"

            prev_price   = float(self.status.get("prev_price",   0.0))
            prev_rsi     = float(self.status.get("prev_rsi",     0.0))
            prev_prob    = float(self.status.get("prev_prob",    0.0))
            prev_adx     = float(self.status.get("prev_adx",     0.0))
            prev_score   = float(self.status.get("prev_score",   0.0))
            prev_atr_pct = float(self.status.get("prev_atr_pct", 0.0))

            def chg(cur, prev, threshold=0.01):
                if prev == 0.0 or abs(cur - prev) < threshold: return ""
                return f" {'▲' if cur > prev else '▼'}{abs(cur-prev):.1f}"
            def chg_price(cur, prev):
                if prev == 0.0 or abs(cur-prev) < 100: return ""
                return f" {'▲' if cur>prev else '▼'}{abs(cur-prev):,.0f}"

            msg  = f"📊 *BTC AI Bot v{BOT_VERSION}* | {fmt_kst_short(kst_now)}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"

            ie  = self.status["initial_equity"]
            pct = ((equity / ie) - 1) * 100 if ie > 0 else 0
            diff_krw = equity - ie
            msg += f"💰 *{equity:,.0f} KRW* ({diff_krw:+,.0f} | {pct:+.1f}%)"
            if mdd_val > 0.05: msg += f" | MDD:{mdd_val:.1%}"
            msg += "\n"

            adx_val_r = adx_info["adx"]; adx_dir_r = '↑' if adx_info["bullish"] else '↓'
            msg += (f"현재가:{price:,.0f}{chg_price(price,prev_price)} | "
                    f"RSI:{rsi:.0f}{chg(rsi,prev_rsi,0.5)} | "
                    f"{mkt_disp} ADX:{adx_val_r:.0f}{chg(adx_val_r,prev_adx,0.5)}({adx_dir_r})\n")
            msg += (f"ATR:{atr_regime}({cur_pct:.0f}%ile{chg(cur_pct,prev_atr_pct,1.0)}) | "
                    f"모드:{mode_str}\n")

            # Kill Switch / MDD 경고
            if ks_active:
                msg += f"🛑 *Kill Switch 발동* — {self.status.get('kill_switch_reason','')}\n"
            if mdd_val >= MDD_STOP_PCT * 0.8:
                msg += f"⚠️ MDD:{mdd_val:.1%} / 한도:{MDD_STOP_PCT:.0%}\n"
            msg += "\n"

            pr_ic = "✅" if ai_engine.precision >= MIN_PRECISION else "⚠️"
            pf_ic = "✅" if ai_engine.profit_factor >= MIN_PROFIT_FACTOR else "⚠️"
            rpt_regime_th = REGIME_CONFIG.get(market_state, {}).get("xgb_th", XGB_ABS_THRESHOLD)
            msg += f"🚪 *[1] AI Gate [{ai_mode}]* (XGB)\n"
            msg += (f"XGB:{xgb_prob:.1%}{chg(xgb_prob*100,prev_prob*100,0.5)} "
                    f"/ 임계:{rpt_regime_th:.0%}({market_state[:5]}) {mk(gate_pass)}\n")
            # v20.9.5: PF_AI (학습) vs PF_실거래 (calc_recent_stats) 이중 표시
            msg += (f"{pr_ic}Prec:{ai_engine.precision:.1%} "
                    f"{pf_ic}PF_AI:{ai_engine.profit_factor:.2f} (학습)\n")
            # 실거래 PF + 사이징감점 상태
            _live_n  = stats["trade_count"]
            _live_pf = stats["pf"]
            if _live_n < 5:
                _live_pf_s   = "N/A"
                _live_pf_ic  = "⚠️"
                _penalty_s   = "N/A (n<5)"
            else:
                _live_pf_s   = f"{_live_pf:.2f}"
                _live_pf_ic  = "✅" if _live_pf >= PERF_LOW_PF_THRESHOLD else "⚠️"
                if _live_n < THRESHOLD_ADJUST_TRADES:
                    _penalty_s = f"N/A (n<{THRESHOLD_ADJUST_TRADES})"
                elif 0 < _live_pf < PERF_LOW_PF_THRESHOLD:
                    _penalty_s = f"적용 (×{PERF_LOW_RISK_MULT})"
                else:
                    _penalty_s = "미적용"
            msg += (f"{_live_pf_ic}PF_실거래:{_live_pf_s} (n={_live_n}) "
                    f"⚙️사이징감점:{_penalty_s}")
            if winrate is not None: msg += f" WR:{winrate:.0%}"
            if cons_loss > 0: msg += f" {cons_loss}연패🛑"
            if win_streak >= 2: msg += f" {win_streak}연승{'🔥' if win_streak>=WIN_STREAK_THRESHOLD else ''}"
            msg += "\n"
            # v20.9.6: Threshold(동적) 라인 제거 (#49 dead code)
            if ai_engine.last_train_dt:
                msg += f"마지막학습:{fmt_kst_short(ai_engine.last_train_dt)}"
                if ai_engine._training: msg += " ⏳학습중"
                else:
                    last_t = ai_engine.last_train_dt
                    if last_t.tzinfo is None: last_t = last_t.replace(tzinfo=KST)
                    days_el = (now_kst() - last_t).total_seconds() / 86400
                    msg += f" | {days_el:.1f}일경과 {self._candles_since_retrain}캔들/{RETRAIN_MIN_CANDLES}"
            msg += "\n\n"

            score_chg = chg(rule_score, prev_score, 0.1)
            msg += f"🎯 *[2] Rule Score: {rule_score:.1f}/{SCORE_MAX:.1f}점{score_chg}*"
            msg += f" {mk(score_pass)} (기준:{rpt_score_th}점"
            if rpt_adx_blocked:
                msg += f"|ADX{rpt_adx:.0f} 차단"
            msg += ")\n"
            for name, (ok, weight, extra) in rule_details.items():
                earned = weight if ok else 0.0
                msg += f"  {mk(ok)} {name}:{earned:.1f}/{weight:.1f}"
                if extra: msg += f"({extra})"
                msg += "\n"
            # v19.3 O3: 유동성 흡수 선행 신호 표시
            _liq_now = check_liquidity_sweep(df4h, price)
            msg += f"  {'⚡' if _liq_now else '⚪'} 유동성흡수: {'발동' if _liq_now else '없음'}"
            if _liq_now and not ema_ok:
                msg += " (EMA 우회 진입 가능)"
            msg += "\n\n"

            # v19.6: VWAP 리포트 표시 (_rpt_vwap, _vwap_ok는 위에서 계산됨)
            if _vwap_applies and _rpt_vwap > 0:
                _vwap_ic = "✅" if _vwap_ok else "❌"
                _vwap_str = f"{_vwap_ic} VWAP: {price/1e6:,.1f}M {'>' if _vwap_ok else '<'} {_rpt_vwap/1e6:,.1f}M"
            else:
                _vwap_str = f"⚪ VWAP: 미적용({market_state})"

            # v20.0: 김프 리포트
            _rpt_kp = calc_kimchi_premium(price)
            if _rpt_kp is not None:
                if _rpt_kp > KIMCHI_PREMIUM_THRESHOLD:
                    _kp_str = f"⚠️ 김프: {_rpt_kp:.1f}% (사이징x{KIMCHI_PREMIUM_SIZING})"
                else:
                    _kp_str = f"✅ 김프: {_rpt_kp:.1f}% (정상)"
            else:
                _kp_str = "⚪ 김프: 조회실패 (무시)"

            msg += f"🛡️ *[3] 리스크 필터*\n"
            msg += f"  {'❌' if cd_remain>0 else '✅'} 쿨다운:{f'{cd_remain/60:.0f}분 남음' if cd_remain>0 else '없음'}\n"
            msg += f"  {'❌' if not dl_ok else '✅'} 일손실:{dl_pct:.1%}/한도-{DAILY_LOSS_LIMIT:.0%}\n"
            msg += f"  {'🛑' if ks_active else '✅'} Kill Switch\n"
            msg += f"  {'⚠️' if mdd_val>=MDD_STOP_PCT else '✅'} MDD:{mdd_val:.1%}/한도-{MDD_STOP_PCT:.0%}\n"
            msg += f"  {_vwap_str}\n"
            msg += f"  {_kp_str}\n"
            # v20.9.10: E2 OFF — 한 줄만 표시 (차단 조건/예외/EMA 비교는 대시보드에서 확인)
            if not E2_ENABLED:
                msg += f"  ⚠️ E2: OFF (v{BOT_VERSION})\n"
            # v20.9.1 E2 BEAR 섹션 — OR/AND 트리 + 개별 조건 색상
            elif E2_ENABLED:
                if self._e2_bear_mode:
                    _bars = int(self.status.get("bars_since_e2", 0))
                    _gap  = float(self._e2_daily_gap_pct)
                    _dc   = float(self._e2_daily_close or 0) / 1e6
                    _de   = float(self._e2_daily_ema200 or 0) / 1e6
                    _e21  = float(self._e2_ema21_4h or 0) / 1e6
                    _e55  = float(self._e2_ema55_4h or 0) / 1e6
                    _f2_badge = "🔴 ON " if self._e2_f2_active else "🟢 OFF"
                    _f5_badge = "🔴 ON " if self._e2_f5_active else "🟢 OFF"
                    _f5_arrow = "<" if self._e2_f5_active else "≥"
                    _o3_on = check_liquidity_sweep(df4h, price)
                    _o3_badge = "🟢 발동" if _o3_on else "🔴 미발동"
                    # gap+score 개별 조건
                    _bars_ok  = _bars >= E2_REQUIRE_BARS_SINCE_E2
                    _gap_ok   = _gap <= E2_GAP_THRESHOLD
                    _score_ok = rule_score > E2_SCORE_THRESHOLD
                    _bars_icon  = "🟢" if _bars_ok else "🔴"
                    _gap_icon   = "🟢" if _gap_ok else "🔴"
                    _score_icon = "🟢" if _score_ok else "🔴"
                    _gap_overall_ok = _bars_ok and _gap_ok and _score_ok
                    _gap_overall_icon = "🟢 활성" if _gap_overall_ok else "🔴 차단"
                    _activation_dt = self.status.get("live_e2_activation_date") or "-"
                    # v20.9.8: F5 표시 제거, F2 단독 차단 기준으로 간소화
                    msg += f"  🐻 *E2 BEAR: ON* (F2 — 일봉 < EMA200)\n"
                    msg += f"    차단 기준:\n"
                    msg += f"     └─ F2 (일봉): {_f2_badge}· {_dc:,.1f}M {'<' if self._e2_f2_active else '≥'} EMA200 {_de:,.1f}M ({_gap:+.2f}%)\n"
                    msg += f"    예외 (OR 중 하나 충족 시 진입 허용):\n"
                    msg += f"     ├─ {_o3_badge} O3 유동성 흡수\n"
                    msg += f"     └─ {_gap_overall_icon} gap 완화 (AND 3조건):\n"
                    msg += f"        {_bars_icon} bars {_bars}/{E2_REQUIRE_BARS_SINCE_E2}\n"
                    msg += f"        {_gap_icon} gap {_gap:+.2f}% (≤{E2_GAP_THRESHOLD}%)\n"
                    msg += f"        {_score_icon} score {rule_score:.1f} (>{E2_SCORE_THRESHOLD})\n"
                    msg += f"    경과: 시작 {_activation_dt} / bars {_bars}/{E2_REQUIRE_BARS_SINCE_E2} (Day {_bars/6:.1f}/180)\n"
                    msg += f"    오늘: 차단 {self._e2_blocks_today}건 · O3예외 {self._e2_o3_exceptions_today} · gap예외 {self._e2_gap_exceptions_today}\n"
                else:
                    msg += f"  ✅ E2 BEAR: OFF\n"

            if self.status["in_position"]:
                msg += f"\n👉 *포지션 보유 중 🟢*\n"
            elif can_enter:
                _mode_label = {
                    "Trend_Up": f"피라미딩{PYRAMID_INITIAL_RATIO:.0%}",
                    "Range":    "BE60%",
                }.get(market_state, "P0")
                msg += f"\n👉 *매수 대기 🟢* — 예상 {pos_prev:,.0f} KRW ({_mode_label})\n"
            else:
                # v20.9.1: E2 활성 시 "차단: E2 BEAR 🐻" 전용 라인 + 해제 조건 명시
                if E2_ENABLED and self._e2_bear_mode:
                    msg += (f"\n👉 *차단: E2 BEAR 🐻* (F2) — 예외 대기 중\n"
                            f"   해제 조건: F2 OFF (일봉>EMA200) "
                            f"OR O3 발동 OR (bars≥{E2_REQUIRE_BARS_SINCE_E2} & gap≤{E2_GAP_THRESHOLD}% & score>{E2_SCORE_THRESHOLD})\n")
                else:
                    reasons = []
                    if ks_active:          reasons.append("Kill Switch")
                    elif mdd_val >= MDD_STOP_PCT: reasons.append(f"MDD {mdd_val:.1%}")
                    elif td_blocked:       reasons.append("📉 Trend_Down 차단(v18.9 X1)")
                    elif not gate_pass:    reasons.append("AI Gate 차단")
                    elif not ema_ok:       reasons.append("EMA4H 역배열")
                    elif rpt_adx_blocked:  reasons.append(f"ADX {rpt_adx:.0f} ({ADX_BLOCK_LOW}~{ADX_BLOCK_HIGH} 차단)")
                    elif not score_pass:   reasons.append(f"Score {rule_score:.1f}<{rpt_score_th}")
                    if not _vwap_ok:       reasons.append(f"VWAP {price/1e6:,.1f}M<{_rpt_vwap/1e6:,.1f}M")
                    if not timing_ok_r:    reasons.append(f"타이밍({timing_reason_r})")
                    if cd_remain > 0:      reasons.append(f"쿨다운 {cd_remain/60:.0f}분")
                    if not dl_ok:          reasons.append("일손실한도")
                    msg += f"\n👉 *대기 ⚪* — {', '.join(reasons)}\n"
            msg += "\n"

            if self.status["in_position"]:
                entry     = self.status["entry"]
                stop      = self.status["stop_loss"]
                highest   = self.status["highest_price"]
                hold_bars = self.status.get("hold_bars", 0)
                _et       = self.status.get("entry_type", "trend")
                _pyr_lv   = self.status.get("pyramid_level", 0)
                _fe       = self.status.get("first_entry_price", 0.0) or entry
                unreal    = (price - entry) / entry * 100
                real_p    = unreal - (COST_RATE*100)
                stop_dist = (price - stop) / price * 100
                tp1_done  = self.status.get("partial_tp1_done", False)
                tp2_done  = self.status.get("partial_tp2_done", False)
                # TP 레벨은 첫 진입가 기준
                tp1_price = _fe + cur_atr*PARTIAL_TP1_ATR if cur_atr > 0 else 0
                tp2_price = _fe + cur_atr*PARTIAL_TP2_ATR if cur_atr > 0 else 0

                _mode_names = {"pyramid": "피라미딩", "breakeven": "Break-Even", "trend": "P0",
                               "mean_reversion": "평균회귀"}
                _btc_amt    = balances.get(COIN, 0.0)
                _avg_ep     = self.status.get("avg_entry_price", 0.0) or entry
                _invested   = _btc_amt * _avg_ep      # 평균 매수가 × 보유량 = 총 투입 원금
                _pos_value  = _btc_amt * price         # 현재 평가액
                _pos_pct    = (_pos_value / equity * 100) if equity > 0 else 0
                msg += "━━━━━━━━━━━━━━━━━━━━\n📌 *포지션*\n"
                msg += f"진입가:{entry:,.0f}"
                if _avg_ep != entry and _avg_ep > 0:
                    msg += f" | 평균:{_avg_ep:,.0f}"
                msg += f" | 최고:{highest:,.0f}\n"
                msg += f"손절선:{stop:,.0f} (-{stop_dist:.1f}%)\n"
                msg += f"투입:{_invested:,.0f} KRW ({_pos_pct:.0f}%)\n"
                msg += f"보유:{hold_bars}봉 | 표면:{unreal:+.1f}% 실질:{real_p:+.1f}%\n"
                msg += f"📋 모드:{_mode_names.get(_et, _et)}"
                if _et == "pyramid":
                    _step_lv = self.status.get("step_tp_level", _pyr_lv)
                    msg += f" Lv{_step_lv}/inf"
                msg += "\n"

                # Regime별 TP 정보
                if _et == "pyramid":
                    _krw_avail = balances.get("KRW", 0)
                    _step_lv = self.status.get("step_tp_level", 0)
                    _interval = cur_atr * STEP_TP_INTERVAL_ATR if cur_atr > 0 else 0
                    # 완료된 TP (최대 3개 표시)
                    _show_done = min(_step_lv, 3)
                    for _k in range(_show_done):
                        _tp = _fe + (_k + 1) * _interval
                        msg += f"  ✅ TP{_k+1}:{_tp:,.0f}\n"
                    if _step_lv > 3:
                        msg += f"  ✅ ...+{_step_lv-3}단계 더\n"
                    # 다음 TP
                    _next_tp = _fe + (_step_lv + 1) * _interval
                    if _next_tp > 0:
                        _dist = (_next_tp - price) / price * 100
                        msg += f"  ⬜ TP{_step_lv+1}:{_next_tp:,.0f}({_dist:+.1f}%)\n"
                    msg += f"  💵 여유자금:{_krw_avail:,.0f} KRW\n"

                elif _et == "breakeven":
                    if tp1_done:
                        msg += f"  ✅ TP1:{tp1_price:,.0f} 25%매도완료 | 손절→본전\n"
                        msg += f"  나머지 75% 트레일링 중\n"
                    else:
                        _dist = (tp1_price - price) / price * 100 if tp1_price > 0 else 0
                        msg += f"  ⬜ TP1:{tp1_price:,.0f}({_dist:+.1f}%) → 25%매도+손절→본전\n"

                else:  # trend (P0) / mean_reversion
                    _adx_r = adx_info.get("adx", 20.0)
                    _tp1_r = PARTIAL_TP_STRONG_1 if _adx_r >= ADX_STRONG_THRESH else PARTIAL_TP_NORMAL_1
                    _tp2_r = PARTIAL_TP_STRONG_2 if _adx_r >= ADX_STRONG_THRESH else PARTIAL_TP_NORMAL_2
                    tp1_str = '✅완료' if tp1_done else f'⬜{tp1_price:,.0f}({_tp1_r:.0%}매도)'
                    tp2_str = '✅완료' if tp2_done else f'⬜{tp2_price:,.0f}({_tp2_r:.0%}매도)'
                    msg += f"  익절1:{tp1_str}\n  익절2:{tp2_str}\n"

                s1, _, s3 = calc_sell_signal(ema_s, ema_l, xgb_prob, price, self.status)
                cur_pnl = (price - self.status["entry"]) / self.status["entry"] if self.status["entry"] > 0 else 0.0
                sell_any  = s1 or s3
                sell_type, _ = determine_sell_type(s1, s3, cur_pnl*100)
                cur_pnl_pct = cur_pnl * 100
                hard_stop_pnl = -MIN_STOP_PCT * 100
                trail_stop_pnl = (
                    (self.status["stop_loss"] - self.status["entry"])
                    / self.status["entry"] * 100
                ) if self.status["entry"] > 0 else 0.0
                # v19.3 T3: EMA 역배열 매도 비활성화 → 표시 제거
                msg += "\n🔸 *매도 조건*\n"
                msg += f"손절: {cur_pnl_pct:+.1f}%/{hard_stop_pnl:+.1f}%\n"
                msg += f"트레일링: {cur_pnl_pct:+.1f}%/{trail_stop_pnl:+.1f}%{' 🔴' if s3 else ''}\n"
                if sell_any:
                    msg += f"👉 *매도 예정 🔴 [{sell_type}]*\n"
                else:
                    msg += "👉 *홀딩 유지 🟢*\n"

            msg += "\n━━━━━━━━━━━━━━━━━━━━\n📜 *최근 매매*\n"
            if os.path.exists(TRADE_LOG):
                df_tr = pd.read_csv(TRADE_LOG)
                df_tr = df_tr[df_tr["action"].isin(["BUY","BUY_PYRAMID","BUY_REINVEST","SELL","SELL_PARTIAL"])].tail(4)
                for _, r in df_tr.iterrows():
                    dt = str(r["datetime"])[5:16]
                    m  = re.search(r"실질:([+-][\d.]+)%", str(r["note"]))
                    pstr = m.group(0) if m else ""
                    icon = ("✅" if "SELL" in r["action"] and m and float(m.group(1)) > 0
                            else "🔴" if "SELL" in r["action"] else "📥")
                    msg += f"{icon} {dt} {r['action']} {pstr}\n"
            else:
                msg += "없음\n"

            _ema_gap_rpt = (float(ema_s) - float(ema_l)) / float(ema_l) * 100 if float(ema_l) > 0 else 0
            # Score 컴포넌트별 상세값 추출
            _vol_detail = rule_details.get("거래량", (False, 0, ""))
            _brk_detail = rule_details.get("고점근접", (False, 0, ""))
            _rr_detail  = rule_details.get("R:R", (False, 0, ""))
            _obv_detail = rule_details.get("OBV", (False, 0, ""))
            self.status.update({
                "prev_price": float(price), "prev_rsi": float(rsi),
                "prev_prob": float(xgb_prob), "prev_adx": float(adx_info["adx"]),
                "prev_score": float(rule_score), "prev_atr_pct": float(cur_pct),
                "live_ema_ok": bool(ema_ok), "live_ema_gap": round(_ema_gap_rpt, 2),
                "live_vwap": round(_rpt_vwap, 0) if _rpt_vwap > 0 else 0,
                "live_vwap_ok": bool(_vwap_ok),
                "live_obv_ok": bool(_obv_detail[0]),
                "live_o3": bool(_liq_now),
                "live_xgb": round(float(xgb_prob), 4),
                "live_score": round(float(rule_score), 1),
                "live_vol_ok": bool(_vol_detail[0]),
                "live_vol_extra": str(_vol_detail[2]),
                "live_brk_ok": bool(_brk_detail[0]),
                "live_brk_extra": str(_brk_detail[2]),
                "live_rr_earned": round(float(_rr_detail[1]), 2),
                "live_rr_extra": str(_rr_detail[2]),
                "live_1d_up": bool(is_1d_up),
            })
            sent = tg_info(msg)
            if sent:
                self.last_report_dt = now_kst()
                logger.info(f"리포트 전송 ({fmt_kst()})")
            else:
                logger.warning("리포트 실패 재시도 예정")
            self._save_status()
        except Exception as e:
            logger.error(f"리포트 에러: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════
    # 메인 루프
    # ══════════════════════════════════════════════════════
    def run(self):
        # ── 재시작 사유 로깅 ──
        prev_state = self.status.get("bot_state")
        if prev_state == "running":
            reason = "비정상 종료 (크래시/OOM/강제중단)"
        elif prev_state == "stopped_signal":
            reason = "시그널 종료 (SIGTERM/SIGINT)"
        elif prev_state is None:
            reason = "첫 실행 또는 상태 초기화"
        else:
            reason = f"알 수 없음 ({prev_state})"
        logger.info(f"[시작] 이전 종료 사유: {reason}")
        self.status["bot_state"] = "running"
        self._save_status()

        # ── 시그널 핸들러 등록 (SIGTERM/SIGINT) ──
        def _shutdown_handler(signum, frame):
            sig_name = _signal.Signals(signum).name
            logger.info(f"[종료] {sig_name} 수신 — 상태 저장 후 종료")
            self.status["bot_state"] = "stopped_signal"
            self._save_status()
            tg_info(f"🛑 *Bot 종료* ({sig_name})\n🕐 {fmt_kst()}")
            sys.exit(0)
        _signal.signal(_signal.SIGTERM, _shutdown_handler)
        _signal.signal(_signal.SIGINT, _shutdown_handler)

        logger.info(f"BTC AI Bot v{BOT_VERSION} | {fmt_kst()}")
        tg_info(
            f"🚀 *BTC AI Bot v{BOT_VERSION} 시작*\n"
            f"🕐 {fmt_kst()}\n━━━━━━━━━━━━━━━━━━━━\n"
            f"*[1] AI Gate*: XGBoost(방향성)\n"
            f"  정상{AI_GATE_THRESHOLD:.0%}/보수적{AI_UNRELIABLE_GATE:.0%}\n"
            f"*[2] Rule Score*: ADX<20→{ADX_LOW_SCORE_TH} / ADX>25→{ADX_HIGH_SCORE_TH}\n"
            f"  ADX {ADX_BLOCK_LOW}~{ADX_BLOCK_HIGH} 진입 차단\n"
            f"*[3] 리스크*: 쿨다운{COOLDOWN_ENTRY//60}분 / "
            f"일손실-{DAILY_LOSS_LIMIT:.0%} / MDD-{MDD_STOP_PCT:.0%} / "
            f"KillSwitch PF<{KILL_SWITCH_PF}\n"
            f"*[4] E2 차단*: {E2_BLOCK_MODE} 모드 "
            f"({'F2 OR F5' if E2_BLOCK_MODE == 'F10' else 'F2 단독'})\n"
            f"  O3 예외: {'ON' if E2_O3_EXCEPTION_ENABLED else 'OFF'} ({E2_O3_EXCEPTION_RATIO:.0%} 사이즈)\n"
            f"  180일 gap 예외: {'ON' if E2_GAP_SCORE_EXCEPTION_ENABLED else 'OFF'} "
            f"(gap<{E2_GAP_THRESHOLD}%, score>{E2_SCORE_THRESHOLD})\n"
            f"  피라미딩: 예외 진입 시 OFF (pyramid_locked)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"*사이징 감점 가드*: n≥{THRESHOLD_ADJUST_TRADES} 시 PF<1.0 → risk×0.5\n"
            f"*🤖 AI 재학습 트리거*\n"
            f"• 정기: {RETRAIN_MIN_CANDLES}캔들 누적\n"
            f"• Regime전환: {REGIME_RETRAIN_MIN_CANDLES}캔들 누적 시\n"
            f"• 성능저하: PF<{PERF_DEGRAD_PF_THRESH} + {PERF_DEGRAD_MIN_CANDLES}캔들 + ADX>{PERF_DEGRAD_MIN_ADX}\n"
            f"• Feature: 24개 (기존17 + 모멘텀5 + 위치2)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ 초기 학습 시작..."
        )

        remaining = (self.status.get("cooldown_seconds", COOLDOWN_ENTRY)
                     - (time.time() - self.status.get("last_trade_time", 0)))
        if remaining > 0: logger.info(f"쿨다운 잔여:{remaining/60:.1f}분")

        df4h_init = api_retry(lambda: pyupbit.get_ohlcv(
            TICKER, interval=TF_PRIMARY, count=INIT_DATA_COUNT))
        if df4h_init is not None:
            if ai_engine.needs_retrain(): ai_engine.train(df4h_init)
            else: logger.info("기존 모델 사용")
            # v20.9.0: df4h 전달하여 F5 포함 F10 초기 계산
            self._update_daily_trend(df4h=df4h_init)
            init_price = api_retry(lambda: pyupbit.get_current_price(TICKER))
            init_bal   = upbit_get_all_balances()
            if init_price and init_bal:
                atr_result = get_atr_regime(df4h_init)
                self._send_report(df4h_init, init_price, init_bal, atr_result, force=True)

        while True:
            try:
                # 재학습 트리거 (정기: 7일+30캔들 / Regime전환 / 성능저하)
                if ai_engine.needs_retrain(self._candles_since_retrain) and not ai_engine._training:
                    df_rt = api_retry(lambda: pyupbit.get_ohlcv(
                        TICKER, interval=TF_PRIMARY, count=RETRAIN_DATA_COUNT))
                    if df_rt is not None:
                        ai_engine.train_async(df_rt)
                        # v20.9.7: 카운터 리셋은 _do_train accepted 경로로 이전 (결함 A)

                # v20.9.0: df4h를 먼저 fetch → _update_daily_trend에 전달 (F5 포함 F10 갱신)
                df4h     = api_retry(lambda: pyupbit.get_ohlcv(
                    TICKER, interval=TF_PRIMARY, count=300))
                price    = api_retry(lambda: pyupbit.get_current_price(TICKER))
                balances = upbit_get_all_balances()

                if df4h is None or price is None or balances is None:
                    self._handle_api_failure(); continue

                self._update_daily_trend(df4h=df4h)

                self._reset_api_fail()
                self._detect_manual_trade(balances, price)
                self._detect_external_transfer(balances, price)
                # v19.6: 매 루프마다 팬텀 포지션 감지
                self._check_phantom_position(balances)

                equity = balances["KRW"] + balances[COIN] * price
                if not self.status["in_position"]:
                    self._update_initial_equity(equity)

                atr_result = get_atr_regime(df4h)
                atr_ok, atr_regime, cur_atr, cur_pct = atr_result

                # MDD 업데이트
                mdd_exceeded, mdd_val = self._update_mdd(equity)
                if mdd_exceeded and not self.status.get("kill_switch", False):
                    self._trigger_kill_switch(
                        reason=f"MDD {mdd_val:.1%} >= {MDD_STOP_PCT:.0%}",
                        reason_type="MDD")

                # Kill Switch 체크 (PF 기반)
                if not self.status.get("kill_switch", False):
                    ks_triggered, ks_reason = self._check_kill_switch()
                    if ks_triggered:
                        self._trigger_kill_switch(reason=ks_reason, reason_type="PF")

                # v20.8 KR1: Kill Switch 자동복구 체크 (발동 후 조건 충족 시 해제)
                self._check_killswitch_auto_recover()

                # Regime 변화 감지 (vA: candles>=15 AND days>=3 조건)
                if REGIME_CHANGE_RETRAIN and not ai_engine._training:
                    adx_info_chk = get_adx_full(df4h)
                    # v18.5: 히스테리시스 — 직전 Regime 기준으로 판정
                    cur_market   = classify_market(
                        atr_ok, atr_regime, adx_info_chk,
                        prev_regime=self._last_market_state)
                    cur_adx_chk  = adx_info_chk["adx"]
                    regime_changed = (self._last_market_state is not None and
                                      self._last_market_state != cur_market)
                    if regime_changed:
                        # v20.1: 이중 카운트 버그 수정 — L2839에서 매 봉마다 +1 하므로 여기서 추가 금지
                        if self._candles_since_retrain >= REGIME_RETRAIN_MIN_CANDLES:
                            days_since = 0.0
                            if ai_engine.last_train_dt is not None:
                                last = ai_engine.last_train_dt
                                if last.tzinfo is None: last = last.replace(tzinfo=KST)
                                days_since = (now_kst() - last).total_seconds() / 86400
                            logger.info(f"🔄 Regime 전환: {self._last_market_state} → {cur_market}"
                                        f" ADX={cur_adx_chk:.1f}"
                                        f" (candles={self._candles_since_retrain}, days={days_since:.1f})")
                            tg_warn(
                                f"*시장 Regime 전환* (v{BOT_VERSION})\n"
                                f"🕐 {fmt_kst()}\n"
                                f"{self._last_market_state} → {cur_market}\n"
                                f"ADX={cur_adx_chk:.1f} "
                                f"(진입≥{REGIME_HYS_ENTER:.0f} / 해제<{REGIME_HYS_EXIT:.0f})\n"
                                f"캔들={self._candles_since_retrain} 일={days_since:.1f}\n"
                                f"AI 재학습 시작...")
                            df_rt = api_retry(lambda: pyupbit.get_ohlcv(
                                TICKER, interval=TF_PRIMARY, count=RETRAIN_DATA_COUNT))
                            if df_rt is not None:
                                ai_engine._retrain_reason = (
                                    f"Regime 전환({self._last_market_state}→{cur_market})")
                                ai_engine.train_async(df_rt)
                                # v20.9.7: 카운터 리셋은 _do_train accepted 경로로 (결함 A)
                        else:
                            logger.info(f"🔄 Regime 전환 감지: {self._last_market_state} → {cur_market}"
                                        f" ADX={cur_adx_chk:.1f}"
                                        f" — ��들 미���족 (candles={self._candles_since_retrain}"
                                        f"/{REGIME_RETRAIN_MIN_CANDLES})")

                    # 성능 저하 트리거: PF < 0.8 AND candles >= 20 AND ADX > 20
                    # v19.8: 3일 경과 조건 삭제
                    # v20.8.1 AR1: ENABLE_PERF_DEGRAD_TRIGGER=False로 비활성화
                    # (1/1 케이스 PF 추가 악화 — backtest_results/ai_retrain_analysis.md)
                    if (ENABLE_PERF_DEGRAD_TRIGGER and
                            not regime_changed and
                            ai_engine.profit_factor < PERF_DEGRAD_PF_THRESH and
                            self._candles_since_retrain >= PERF_DEGRAD_MIN_CANDLES and
                            adx_info_chk["adx"] > PERF_DEGRAD_MIN_ADX):
                        logger.info(f"📉 성능 저하 트리거: PF={ai_engine.profit_factor:.2f}"
                                    f" ADX={adx_info_chk['adx']:.0f}"
                                    f" candles={self._candles_since_retrain}")
                        tg_warn(
                            f"*성능 저하 재학습* (v{BOT_VERSION})\n"
                            f"PF={ai_engine.profit_factor:.2f} ADX={adx_info_chk['adx']:.0f}\n"
                            f"AI 재학습 시작...")
                        df_rt = api_retry(lambda: pyupbit.get_ohlcv(
                            TICKER, interval=TF_PRIMARY, count=RETRAIN_DATA_COUNT))
                        if df_rt is not None:
                            ai_engine._retrain_reason = (
                                f"성능저하(PF={ai_engine.profit_factor:.2f})")
                            ai_engine.train_async(df_rt)
                            # v20.9.7: 카운터 리셋은 _do_train accepted 경로로 (결함 A)

                    # v18.4: 포지션 보유 중 Regime 전환 → entry_type 자동 전환
                    if regime_changed and self.status["in_position"]:
                        self._check_regime_switch(
                            self._last_market_state, cur_market, balances, price)

                    self._last_market_state = cur_market
                    # v18.5: 재시작 후 복원용으로 last_regime 영속화
                    if self.status.get("last_regime") != cur_market:
                        self.status["last_regime"] = cur_market
                        self._save_status()

                self._update_trailing_stop(price, cur_atr)
                # v19.6: 인트라캔들 하드스톱 — 4H 캔들 종가 대기 없이 즉시 매도
                if self._check_hard_stop(price, balances):
                    time.sleep(30); continue
                self._check_partial_tp(price, balances, cur_atr, df4h)
                self._send_report(df4h, price, balances, atr_result)
                self._check_monthly_report(equity)

                # ── 30초 실시간 스냅샷 (대시보드용) ──
                try:
                    _s_ema_s = float(ta.ema(df4h["close"], 21).iloc[-1])
                    _s_ema_l = float(ta.ema(df4h["close"], 55).iloc[-1])
                    _s_rsi   = float(ta.rsi(df4h["close"]).iloc[-1])
                    _s_adx   = get_adx_full(df4h)
                    try:
                        _s_typ  = (df4h["high"]+df4h["low"]+df4h["close"])/3
                        _s_vwap = float((_s_typ*df4h["volume"]).rolling(20).sum().iloc[-1]
                                        / df4h["volume"].rolling(20).sum().iloc[-1])
                    except Exception:
                        _s_vwap = 0
                    self.status.update({
                        "live_price":    float(price),
                        "live_equity":   round(equity, 0),
                        "live_rsi":      round(_s_rsi, 1),
                        "live_adx":      round(float(_s_adx["adx"]), 1),
                        "live_adx_bull": _s_adx["bullish"],
                        "live_ema_ok":   _s_ema_s > _s_ema_l,
                        "live_ema_gap":  round((_s_ema_s-_s_ema_l)/_s_ema_l*100, 2) if _s_ema_l>0 else 0,
                        "live_vwap":     round(_s_vwap, 0),
                        "live_vwap_ok":  price > _s_vwap if _s_vwap > 0 else True,
                        "live_o3":       bool(check_liquidity_sweep(df4h, price)),
                        "live_atr_regime": atr_regime,
                        "live_atr_pct":  round(float(cur_pct), 0),
                        "live_ts":       int(time.time()),
                    })
                    self._save_status()
                except Exception:
                    pass

                # v20.9.7 결함A: _do_train accepted 시 카운터 리셋 동기화
                if getattr(ai_engine, '_counter_reset_pending', False):
                    logger.info(
                        f"v20.9.7: _do_train accepted → candles_since_retrain "
                        f"{self._candles_since_retrain}→0 리셋")
                    self._candles_since_retrain = 0
                    self.status["candles_since_retrain"] = 0
                    self._save_status()
                    ai_engine._counter_reset_pending = False

                latest_candle = df4h.index[-1]
                if self.last_candle_time == latest_candle:
                    time.sleep(30); continue
                self.last_candle_time = latest_candle
                self._candles_since_retrain += 1
                self.status["candles_since_retrain"] = self._candles_since_retrain
                # v20.9.7 결함B: last_candle_time 영속화 (재시작 시 같은 캔들 중복 카운트 방지)
                self.status["last_candle_time"] = str(latest_candle)
                self._save_status()

                xgb_prob = ai_engine.predict(df4h)
                ema_s    = ta.ema(df4h["close"], 21).iloc[-1]
                ema_l    = ta.ema(df4h["close"], 55).iloc[-1]
                adx_info = get_adx_full(df4h)
                logger.info(f"[새 캔들] ATR:{atr_regime}({cur_pct:.0f}%ile/{cur_atr:,.0f}) "
                            f"ADX:{adx_info['adx']:.1f} DI+:{adx_info['di_plus']:.1f} DI-:{adx_info['di_minus']:.1f}")
                is_1d_up = self.daily_trend[0]

                # v19.4: 캔들 로그용 진입 상태 스냅샷
                _cl_initial_buy_count = self.status.get("buy_count", 0)
                _cl_entry_path        = "none"

                last_t  = float(self.status.get("last_trade_time", 0))
                cd_secs = int(self.status.get("cooldown_seconds", COOLDOWN_ENTRY))
                cd_ok   = (time.time() - last_t) > cd_secs
                ai_rel  = ai_engine.is_reliable()

                # ── 시장 상태 (회색지대 prev_regime 유지) ──────
                market_state = classify_market(
                    atr_ok, atr_regime, adx_info,
                    prev_regime=self._last_market_state)

                # v19.1: 잔액 자동 투입 (매 새 캔들, 피라미딩+TU 유지 시 — 5단계 조건 적용)
                if self.status["in_position"] and self.status.get("entry_type") == "pyramid":
                    if self._auto_reinvest(price, balances, market_state, df4h=df4h, xgb_prob=xgb_prob):
                        balances = self._sync_balance()

                # ── 매수 ──────────────────────────────────
                ks_active = self.status.get("kill_switch", False)
                current_mdd = self.status.get("current_mdd", 0.0)

                # Phase1: ADX 22~24 차단
                cur_adx = adx_info["adx"]
                adx_blocked = ADX_BLOCK_LOW <= cur_adx <= ADX_BLOCK_HIGH

                if (not self.status["in_position"] and cd_ok and
                        not ks_active and current_mdd < MDD_STOP_PCT):

                    # v18.9 (X1-C): Trend_Down regime 진입 완전 차단
                    if market_state == "Trend_Down":
                        logger.info(f"⛔ Trend_Down 진입 차단 [v18.9 X1] ADX:{cur_adx:.1f}")
                        log_signal(price, xgb_prob, 0.0, False, 0.0, "trend_down_block", market_state)
                    elif adx_blocked:
                        logger.info(f"ADX {cur_adx:.1f} — {ADX_BLOCK_LOW}~{ADX_BLOCK_HIGH} 구간 진입 차단 [{market_state}]")
                        log_signal(price, xgb_prob, 0.0, False, 0.0, "adx_block", market_state)
                    # v20.9.0: E2 차단 체크는 gate_pass 브랜치 내부에서 rule_score 계산 후 수행
                    # (O3 예외 + bars+gap+score 예외 평가를 위해 rule_score 필요)
                    else:
                        gate_pass = check_ai_gate(xgb_prob,
                                                  last_xgb_probs=list(ai_engine.xgb_prob_history),
                                                  market_state=market_state)

                        # 신호 로그 — gate_thresh 인자 제거 후 regime_th 로 표기
                        _log_rth = REGIME_CONFIG.get(market_state, {}).get("xgb_th", XGB_ABS_THRESHOLD)
                        log_signal(price, xgb_prob, _log_rth, gate_pass, 0.0, "gate_check", market_state)

                        # vA: ADX 기반 score_th 분기
                        if cur_adx < ADX_BLOCK_LOW:
                            score_th = ADX_LOW_SCORE_TH    # 2.5
                        else:  # cur_adx > ADX_BLOCK_HIGH
                            score_th = ADX_HIGH_SCORE_TH   # 2.8
                        # v20.5 Range New: Range 진입만 타이트 Score 임계 적용
                        if RANGE_NEW_ENABLED and market_state == "Range":
                            score_th = RANGE_NEW_SCORE_TH  # 5.0

                        if self.status.get("paused", False):
                            logger.info("⏸️ 일시 중단 중 — 진입 차단")
                        elif gate_pass:
                            rule_score, rule_details, ema_ok = calc_weighted_score(
                                ema_s, ema_l, price, df4h, is_1d_up, atr_result, cur_atr)
                            log_signal(price, xgb_prob, _log_rth,
                                       gate_pass, rule_score, "score_check", market_state)
                            # v19.3 O3: 유동성 흡수 선행 신호 — EMA 우회 진입 허용
                            _liq_sweep = check_liquidity_sweep(df4h, price)
                            _via_leading = (not ema_ok) and _liq_sweep

                            # v20.9.0: E2 차단 체크 + 예외 평가 (rule_score 계산 후)
                            # F10 차단 활성 시: O3 예외 → gap+score 예외 순 체크
                            # 예외 통과 시 _via_leading=True로 40% 사이징 강제
                            _e2_exception = None    # "o3" | "gap_score" | None
                            if E2_ENABLED and self._e2_bear_mode:
                                _bars_since = int(self.status.get("bars_since_e2", 0))
                                _gap_pct    = float(self._e2_daily_gap_pct)
                                # 예외 1: O3 유동성 흡수
                                if E2_O3_EXCEPTION_ENABLED and _liq_sweep:
                                    _e2_exception = "o3"
                                # 예외 2: bars+gap+score (E2b+6mo)
                                elif (E2_GAP_SCORE_EXCEPTION_ENABLED
                                      and _bars_since >= E2_REQUIRE_BARS_SINCE_E2
                                      and _gap_pct <= E2_GAP_THRESHOLD
                                      and rule_score > E2_SCORE_THRESHOLD):
                                    _e2_exception = "gap_score"
                                if _e2_exception is None:
                                    # 차단 유지
                                    self._e2_blocks_today += 1
                                    self.status["live_e2_blocks_today"] = int(self._e2_blocks_today)
                                    logger.info(
                                        f"🐻 E2 BEAR 차단 (reason={self._e2_block_reason}) "
                                        f"| bars {_bars_since}/1080 "
                                        f"| gap {_gap_pct:+.2f}% "
                                        f"| score {rule_score:.1f} "
                                        f"| O3 {'Y' if _liq_sweep else 'N'} "
                                        f"| 차단 누적 {self._e2_blocks_today}건")
                                    log_signal(price, xgb_prob, _log_rth,
                                               gate_pass, rule_score, "e2_bear_block", market_state)
                                    continue
                                else:
                                    # 예외 경로 — leading signal 강제 + 카운터 증가
                                    _via_leading = True
                                    if _e2_exception == "o3":
                                        self._e2_o3_exceptions_today += 1
                                        self.status["live_e2_o3_exceptions_today"] = int(self._e2_o3_exceptions_today)
                                    else:
                                        self._e2_gap_exceptions_today += 1
                                        self.status["live_e2_gap_exceptions_today"] = int(self._e2_gap_exceptions_today)
                                    logger.info(
                                        f"🔓 E2 예외 경로 ({_e2_exception}): "
                                        f"bars {_bars_since}/1080, gap {_gap_pct:+.2f}%, score {rule_score:.1f} "
                                        f"→ 40% 사이징, 피라미딩 OFF")

                            # E2 예외 진입 시 ema_ok/score 미달 체크 우회 (O3 예외의 leading 우회 로직과 동일)
                            if not ema_ok and not _liq_sweep and _e2_exception is None:
                                logger.info("EMA 4H 역배열 — 필수 조건 미충족")
                            elif rule_score < score_th and _e2_exception is None:
                                logger.info(f"Score 미달 {rule_score:.1f}/{score_th} (ADX={cur_adx:.1f})")
                            else:
                                if _via_leading and _e2_exception is None:
                                    logger.info("⚡ 선행신호(유동성흡수) 진입 — EMA 역배열 우회")
                                elif _e2_exception is not None:
                                    logger.info(f"⚡ E2 예외 진입 ({_e2_exception}) — 40% 사이징")
                                timing_ok, timing_reason = check_entry_timing(df4h, price)
                                if not timing_ok:
                                    logger.info(f"⏸️ 타이밍 필터 차단: {timing_reason}")
                                    continue
                                # v19.0 D8: 1H RSI 필터 삭제

                                # v18.3: VWAP 진입 필터 (Range 제외)
                                if market_state != "Range":
                                    try:
                                        _typ = (df4h["high"] + df4h["low"] + df4h["close"]) / 3
                                        _vwap20 = ((_typ * df4h["volume"]).rolling(20).sum()
                                                   / df4h["volume"].rolling(20).sum())
                                        vwap_val = float(_vwap20.iloc[-1])
                                        if price <= vwap_val:
                                            logger.info(f"VWAP 필터 차단: 가격{price:,.0f} <= VWAP{vwap_val:,.0f} [{market_state}]")
                                            log_signal(price, xgb_prob, _log_rth,
                                                       gate_pass, rule_score, "vwap_block", market_state)
                                            continue
                                    except Exception as _ve:
                                        logger.debug(f"VWAP 계산 오류: {_ve}")

                                # v18.3: OBV 다이버전스 차단 (가격↑3봉 + OBV↓3봉 → 거짓 상승)
                                try:
                                    _obv = ta.obv(df4h["close"], df4h["volume"])
                                    if _obv is not None and len(_obv) >= 4:
                                        _price_up_3 = float(df4h["close"].iloc[-1]) > float(df4h["close"].iloc[-4])
                                        _obv_down_3 = float(_obv.iloc[-1]) < float(_obv.iloc[-4])
                                        if _price_up_3 and _obv_down_3:
                                            logger.info("OBV 다이버전스 차단: 가격↑ + OBV↓ (거래량 미확인 상승)")
                                            log_signal(price, xgb_prob, _log_rth,
                                                       gate_pass, rule_score, "obv_div_block", market_state)
                                            continue
                                except Exception as _oe:
                                    logger.debug(f"OBV DIV ��산 오류: {_oe}")

                                dl_ok, dl_pct = self._check_daily_loss(equity)
                                if not dl_ok:
                                    logger.info(f"Daily Loss ({dl_pct:.2%})")
                                    continue
                                # v18.4: P5 Regime별 포지션 사이징
                                # v19.3 O3: 선행신호 진입 시 안전장치 — 40% / P0 (피라미딩 OFF)
                                # v20.9.0: E2 예외 진입은 전용 ratio 사용 (O3=40% / gap=40%)
                                if _via_leading:
                                    if _e2_exception == "o3":
                                        _exc_ratio = E2_O3_EXCEPTION_RATIO
                                    elif _e2_exception == "gap_score":
                                        _exc_ratio = E2_GAP_EXCEPTION_RATIO
                                    else:
                                        _exc_ratio = LEADING_MAX_POS_RATIO
                                    buy_amount = equity * _exc_ratio
                                    _entry_mode = "trend"  # P0 (피라미딩 OFF)
                                elif market_state == "Trend_Up":
                                    buy_amount = equity * PYRAMID_INITIAL_RATIO  # v18.9: 80%
                                    _entry_mode = "pyramid"
                                elif market_state == "Range":
                                    if RANGE_NEW_ENABLED:
                                        # v20.5 Range New + v20.7 C6: Range 진입 70% (기존 80%)
                                        buy_amount = equity * RANGE_INITIAL_RATIO  # 70%
                                        _entry_mode = "pyramid"
                                    else:
                                        # 레거시 (RANGE_NEW_ENABLED=False일 때 롤백용)
                                        buy_amount = calc_position_size(
                                            equity, price, cur_atr, xgb_prob,
                                            rule_score, adx_info, market_state,
                                            cons_loss, stats["win_streak"],
                                            stats["winrate"], stats["pf"],
                                            trade_count=stats["trade_count"])
                                        _entry_mode = "breakeven"
                                else:
                                    buy_amount = calc_position_size(
                                        equity, price, cur_atr, xgb_prob,
                                        rule_score, adx_info, market_state,
                                        cons_loss, stats["win_streak"],
                                        stats["winrate"], stats["pf"],
                                        trade_count=stats["trade_count"])
                                    _entry_mode = "trend"

                                # v20.0: 김치 프리미엄 사이징 (K2)
                                _kp_val = calc_kimchi_premium(price)
                                _kp_applied = False
                                if (_kp_val is not None and
                                        _kp_val > KIMCHI_PREMIUM_THRESHOLD and
                                        not _via_leading):
                                    buy_amount *= KIMCHI_PREMIUM_SIZING
                                    _kp_applied = True
                                    logger.info(f"김프 {_kp_val:.1f}% > {KIMCHI_PREMIUM_THRESHOLD}% → 사이징×{KIMCHI_PREMIUM_SIZING}")
                                order = None
                                if buy_amount > MIN_ORDER_KRW:
                                    order = self.upbit.buy_market_order(
                                        TICKER, buy_amount)
                                if order:
                                    order_uuid = order.get("uuid")
                                    time.sleep(1.0)
                                    filled, actual_price = self._verify_order_filled(
                                        order_uuid)
                                    if filled:
                                        _cl_entry_path = "O3" if _via_leading else "EMA"
                                        a_stop = min(calc_atr_stop(actual_price, cur_atr),
                                                     actual_price*(1-MIN_STOP_PCT))
                                        pos_ratio = buy_amount / equity
                                        tp1p = actual_price + cur_atr*PARTIAL_TP1_ATR
                                        tp2p = actual_price + cur_atr*PARTIAL_TP2_ATR
                                        # v20.5 Range New: Range+RANGE_NEW 진입 시 플래그 설정
                                        _is_range_new = (RANGE_NEW_ENABLED
                                                          and market_state == "Range"
                                                          and _entry_mode == "pyramid"
                                                          and not _via_leading)
                                        # v20.6 BD: TU 피라미딩 진입(Range New 아님)에만 TU 전용 파라미터
                                        _is_tu_pyramid = (_entry_mode == "pyramid"
                                                            and market_state == "Trend_Up"
                                                            and not _via_leading)
                                        _pos_trail_m = TU_ATR_TRAILING_MULT if _is_tu_pyramid else 0.0
                                        # v20.7 C6: Range 진입 시 RANGE_STEP_LOOKBACK=3.0, TU는 2.5, 기타 0(전역 fallback)
                                        if _is_tu_pyramid:
                                            _pos_step_lb = TU_STEP_LOOKBACK
                                        elif _is_range_new:
                                            _pos_step_lb = RANGE_STEP_LOOKBACK
                                        else:
                                            _pos_step_lb = 0.0
                                        # v20.7 C6: 참고용 사이징 비율 (실제 결정은 buy_amount에서)
                                        _pos_init_ratio = (RANGE_INITIAL_RATIO if _is_range_new
                                                            else PYRAMID_INITIAL_RATIO if _is_tu_pyramid
                                                            else 0.0)
                                        # v20.9.0: E2 예외 진입은 entry_type="e2_exception" + pyramid_locked=True
                                        _final_entry_type = "e2_exception" if _e2_exception else _entry_mode
                                        _pyramid_locked   = bool(_e2_exception is not None)
                                        self.status.update({
                                            "in_position": True,
                                            "entry": actual_price,
                                            "stop_loss": a_stop,
                                            "highest_price": actual_price,
                                            "hold_bars": 0,
                                            "partial_tp1_done": False,
                                            "partial_tp2_done": False,
                                            "entry_type": _final_entry_type,
                                            "pyramid_level": 0, "step_tp_level": 0,
                                            "first_entry_price": actual_price,
                                            "avg_entry_price": actual_price,
                                            "entry_via_leading": _via_leading,
                                            "range_new_mode": _is_range_new,
                                            # v20.6 BD + v20.7 C6: per-position 파라미터
                                            "pos_trail_m":       _pos_trail_m,
                                            "pos_step_lookback": _pos_step_lb,
                                            "pos_init_ratio":    _pos_init_ratio,
                                            # v20.9.0 E2 예외 진입 속성
                                            "pyramid_locked":     _pyramid_locked,
                                            "e2_exception_type":  _e2_exception or "",

                                            "buy_count": self.status["buy_count"]+1,
                                            "last_trade_time": time.time(),
                                            "cooldown_seconds": COOLDOWN_ENTRY})
                                        self._last_known_btc = balances[COIN]
                                        self._last_buy_time = time.time()
                                        self._save_status()
                                        log_trade("BUY", actual_price,
                                            f"Gate:{xgb_prob:.1%}/{_log_rth:.1%} "
                                            f"Score:{rule_score:.1f}/{score_th} "
                                            f"Mkt:{market_state[:5]} Mode:{_entry_mode}"
                                            f"{'/Leading' if _via_leading else ''} "
                                            f"Pos:{pos_ratio:.1%} 손절:{a_stop:,.0f}")
                                        _ema_gap_v = (float(ema_s)-float(ema_l))/float(ema_l)*100 if float(ema_l)>0 else 0
                                        log_confirmed_trade(
                                            action="BUY", price=actual_price,
                                            amount=buy_amount/actual_price if actual_price>0 else 0,
                                            krw=buy_amount, regime=market_state,
                                            xgb_prob=round(xgb_prob,4), score=round(rule_score,1),
                                            ema_gap=round(_ema_gap_v,2),
                                            entry_reason="O3" if _via_leading else "EMA")
                                        log_signal(actual_price, xgb_prob,
                                                   _log_rth, True, rule_score, "BUY", market_state)
                                        _score_lines = ""
                                        for _n, (_ok, _w, _ex) in rule_details.items():
                                            _earned = _w if _ok else 0.0
                                            _score_lines += f"  {'✅' if _ok else '❌'}{_n}:{_earned:.1f}/{_w:.1f}"
                                            if _ex: _score_lines += f"({_ex})"
                                            _score_lines += "\n"
                                        _entry_path_label = ("⚡ 선행신호 진입(유동성흡수)"
                                                             if _via_leading else "EMA 정배열 진입")
                                        # #76: entry_type별 TP 라벨 분기
                                        if _entry_mode == "pyramid":
                                            if _e2_exception:
                                                _tp_lines = (
                                                    f"⚠️ TP1:{tp1p:,.0f} (피라미딩 차단 — Step만 갱신)\n"
                                                    f"⚠️ TP2:{tp2p:,.0f} (피라미딩 차단)")
                                            else:
                                                _tp_lines = (
                                                    f"📈 추매1:{tp1p:,.0f} (TP1 도달 시)\n"
                                                    f"📈 추매2:{tp2p:,.0f} (TP2 도달 시)")
                                        elif _entry_mode == "breakeven":
                                            _tp_lines = f"💛 BE익절:{tp1p:,.0f} (25%매도+본전이동)"
                                        else:  # trend / mean_reversion
                                            _tp_lines = (
                                                f"💛 익절1:{tp1p:,.0f} (부분매도)\n"
                                                f"💚 익절2:{tp2p:,.0f} (부분매도)")
                                        tg_info(
                                            f"✅ *매수 체결* (v{BOT_VERSION})\n"
                                            f"🕐 {fmt_kst()}\n"
                                            f"체결가:{actual_price:,.0f} KRW\n"
                                            f"진입경로: {_entry_path_label}\n"
                                            f"━━━━━━━━━━━━━━━━━━━━\n"
                                            f"[1] XGB:{xgb_prob:.1%}/{REGIME_CONFIG.get(market_state,{}).get('xgb_th',0.85):.0%}({market_state[:5]}) ✅\n"
                                            f"[2] Score:{rule_score:.1f}/{score_th} ✅\n"
                                            f"{_score_lines}"
                                            f"시장:{market_display(market_state)} "
                                            f"ADX:{adx_info['adx']:.0f}\n"
                                            f"━━━━━━━━━━━━━━━━━━━━\n"
                                            f"💰 {buy_amount:,.0f} KRW ({pos_ratio:.1%})"
                                            f"{f' (김프{_kp_val:.1f}%→x{KIMCHI_PREMIUM_SIZING})' if _kp_applied else ''}\n"
                                            f"📋 모드:{_entry_mode}"
                                            f"{' (40% 안전장치)' if _via_leading else ''}\n"
                                            f"🛡️ 손절:{a_stop:,.0f}\n"
                                            f"{_tp_lines}")
                                    else:
                                        try:
                                            self.upbit.cancel_order(order_uuid)
                                            cm = "취소 완료"
                                        except Exception as ce:
                                            logger.error(f"취소 실패:{ce}"); cm = "취소 실패"
                                        tg_warn(f"*체결 미확인* | {cm}")

                    # ── v18.3: 평균회귀 진입 (Range only, 추세추종 미진입 시) ──
                    # v20.6 E2: BEAR 모드에서는 MR 진입도 차단
                    if (not self.status["in_position"] and
                            market_state == "Range" and gate_pass
                            and not (E2_ENABLED and self._e2_bear_mode)):
                        try:
                            _rsi_4h = ta.rsi(df4h["close"], 14)
                            _rsi_val = float(_rsi_4h.iloc[-1]) if _rsi_4h is not None else 50
                            _sma20 = float(df4h["close"].rolling(20).mean().iloc[-1])
                            _std20 = float(df4h["close"].rolling(20).std().iloc[-1])
                            _bb_lo = _sma20 - 2 * _std20
                            _bb_hi = _sma20 + 2 * _std20
                            _bb_rng = _bb_hi - _bb_lo
                            _bb_pos = (price - _bb_lo) / _bb_rng if _bb_rng > 0 else 0.5

                            if _rsi_val <= MR_RSI_THRESH and _bb_pos <= MR_BB_THRESH:
                                dl_ok, dl_pct = self._check_daily_loss(equity)
                                if dl_ok:
                                    mr_amount = calc_position_size(
                                        equity, price, cur_atr, xgb_prob,
                                        0.0, adx_info, market_state,
                                        cons_loss, stats["win_streak"],
                                        stats["winrate"], stats["pf"],
                                        trade_count=stats["trade_count"])
                                    if mr_amount > MIN_ORDER_KRW:
                                        order = self.upbit.buy_market_order(TICKER, mr_amount)
                                        if order:
                                            order_uuid = order.get("uuid")
                                            time.sleep(1.0)
                                            filled, actual_price = self._verify_order_filled(order_uuid)
                                            if filled:
                                                _cl_entry_path = "MR"
                                                a_stop = min(calc_atr_stop(actual_price, cur_atr),
                                                             actual_price * (1 - MIN_STOP_PCT))
                                                pos_ratio = mr_amount / equity
                                                self.status.update({
                                                    "in_position": True,
                                                    "entry": actual_price,
                                                    "stop_loss": a_stop,
                                                    "highest_price": actual_price,
                                                    "hold_bars": 0,
                                                    "partial_tp1_done": False,
                                                    "partial_tp2_done": False,
                                                    "entry_type": "mean_reversion",
                                                    "pyramid_level": 0, "step_tp_level": 0,
                                                    "first_entry_price": actual_price,
                                                    "avg_entry_price": actual_price,
                                                    # v20.9.4: 다른 진입 경로와 일관성 — 신규 필드 명시 초기화
                                                    "range_new_mode":    False,
                                                    "pos_trail_m":       0.0,
                                                    "pos_step_lookback": 0.0,
                                                    "pos_init_ratio":    0.0,
                                                    # v20.9.0 E2 예외 진입 속성 (MR은 E2 예외 아님)
                                                    "pyramid_locked":    False,
                                                    "e2_exception_type": "",

                                                    "buy_count": self.status["buy_count"] + 1,
                                                    "last_trade_time": time.time(),
                                                    "cooldown_seconds": COOLDOWN_ENTRY})
                                                self._last_known_btc = balances[COIN]
                                                self._last_buy_time = time.time()
                                                self._save_status()
                                                log_trade("BUY", actual_price,
                                                    f"MR진입 RSI:{_rsi_val:.0f} BB:{_bb_pos:.2f} "
                                                    f"XGB:{xgb_prob:.1%} 손절:{a_stop:,.0f}")
                                                log_confirmed_trade(
                                                    action="BUY", price=actual_price,
                                                    amount=mr_amount/actual_price if actual_price>0 else 0,
                                                    krw=mr_amount, regime=market_state,
                                                    xgb_prob=round(xgb_prob,4), score=0,
                                                    entry_reason="MR")
                                                log_signal(actual_price, xgb_prob,
                                                           _log_rth, True, 0.0, "BUY_MR", market_state)
                                                tg_info(
                                                    f"🔵 *평균회귀 매수* (v{BOT_VERSION})\n"
                                                    f"🕐 {fmt_kst()}\n"
                                                    f"체결가:{actual_price:,.0f} KRW\n"
                                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                                    f"RSI:{_rsi_val:.0f}(<={MR_RSI_THRESH}) "
                                                    f"BB:{_bb_pos:.2f}(<={MR_BB_THRESH})\n"
                                                    f"XGB:{xgb_prob:.1%} | 시장:Range\n"
                                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                                    f"💰 {mr_amount:,.0f} KRW ({pos_ratio:.1%})\n"
                                                    f"🛡️ 손절:{a_stop:,.0f}\n"
                                                    f"🎯 목표:RSI50 or SMA20({_sma20:,.0f})\n"
                                                    f"⏰ 타임아웃:{MR_MAX_HOLD_BARS}봉({MR_MAX_HOLD_BARS*4}h)")
                                            else:
                                                try: self.upbit.cancel_order(order_uuid)
                                                except: pass
                        except Exception as _mr_e:
                            logger.debug(f"MR 진입 체크 오류: {_mr_e}")

                # ── 매도 ──────────────────────────────────
                elif self.status["in_position"] and cd_ok:
                    entry_type = self.status.get("entry_type", "trend")
                    s1, _, s3 = calc_sell_signal(ema_s, ema_l, xgb_prob, price, self.status)
                    hold_bars  = self.status.get("hold_bars", 0)

                    # v18.3: MR 전용 청산 — RSI>=50 or price>=SMA20, 6봉 타임아웃
                    mr_exit = False
                    if entry_type == "mean_reversion" and hold_bars >= 1:
                        try:
                            _mr_rsi = ta.rsi(df4h["close"], 14)
                            _mr_rsi_val = float(_mr_rsi.iloc[-1]) if _mr_rsi is not None else 50
                            _mr_sma20 = float(df4h["close"].rolling(20).mean().iloc[-1])
                            if _mr_rsi_val >= 50 or price >= _mr_sma20:
                                mr_exit = True
                                reason = ["MR익절"]
                            elif hold_bars >= MR_MAX_HOLD_BARS:
                                mr_exit = True
                                reason = ["MR시간초과"]
                        except:
                            pass

                    if mr_exit:
                        should_sell = True
                    elif s1 or s3:
                        should_sell = True
                        reason = (["EMA역배열"] if s1 else []) + \
                                 (["ATR트레일링"] if s3 else [])
                    else:
                        should_sell = False

                    if should_sell:
                        # v19.7: 하드스톱이 같은 루프에서 이미 청산한 경우 이중 매도 방지
                        if not self.status["in_position"]:
                            logger.info("매도 스킵: 하드스톱이 이미 처리함")
                            should_sell = False
                    if should_sell:
                        order = self.upbit.sell_market_order(TICKER, balances[COIN])
                        if order:
                            order_uuid = order.get("uuid"); time.sleep(1.0)
                            sf, asp = self._verify_sell_filled(order_uuid)
                            if not sf:
                                tg_error(f"*매도 체결 실패* UUID:{order_uuid}\n수동 확인 필요")
                                time.sleep(30); continue
                            raw  = ((asp - self.status["entry"]) / self.status["entry"]) * 100
                            real = raw - (COST_RATE * 100)
                            if mr_exit:
                                sell_type = reason[0]  # "MR익절" or "MR시간초과"
                                new_cd = COOLDOWN_MR
                            else:
                                sell_type, new_cd = determine_sell_type(s1, s3, raw)

                            # v18.9 (X1-B): Trend_Up + 피라미딩 진입 시 쿨다운 제거
                            #   추세 지속 중이면 즉시 재진입 → 추세 캡처 극대화
                            _prev_entry_type = self.status.get("entry_type", "trend")
                            if (_prev_entry_type == "pyramid" and
                                    market_state == "Trend_Up" and new_cd > 0):
                                logger.info(f"⚡ v18.9 X1: TU 피라미딩 쿨다운 제거 ({new_cd}→0)")
                                new_cd = 0

                            self._update_consecutive_loss(real)
                            self.status.update({
                                "in_position": False, "entry": 0.0, "stop_loss": 0.0,
                                "highest_price": 0.0, "hold_bars": 0,
                                "partial_tp1_done": False, "partial_tp2_done": False,
                                "entry_type": "trend",
                                "pyramid_level": 0, "step_tp_level": 0,
                                "first_entry_price": 0.0, "avg_entry_price": 0.0,
                                "range_new_mode": False,
                                "pos_trail_m": 0.0, "pos_step_lookback": 0.0, "pos_init_ratio": 0.0,  # v20.6 BD + v20.7 C6
                                "pyramid_locked": False, "e2_exception_type": "",  # v20.9.0 E2 예외 진입 속성 리셋
                                "last_sell_reason": sell_type,
                                "last_trade_time": time.time(), "cooldown_seconds": new_cd})
                            self._last_known_btc = 0.0
                            self._save_status()
                            log_trade("SELL", asp,
                                f"사유:{','.join(reason)} 표면:{raw:+.2f}% 실질:{real:+.2f}% "
                                f"유형:{sell_type} 보유:{hold_bars}봉")
                            log_confirmed_trade(
                                action="SELL", price=asp,
                                amount=balances[COIN], krw=balances[COIN]*asp,
                                pnl_pct=round(real, 2),
                                sell_reason=','.join(reason),
                                regime=market_state, xgb_prob=round(xgb_prob,4),
                                holding_bars=hold_bars)
                            log_signal(asp, xgb_prob, 0.0, False, 0.0,
                                       f"SELL({sell_type})", market_state)
                            tg_info(
                                f"🔴 *매도 체결* (v{BOT_VERSION})\n"
                                f"🕐 {fmt_kst()}\n"
                                f"가격:{asp:,.0f} KRW\n"
                                f"수익: 표면{raw:+.2f}% 실질{real:+.2f}%\n"
                                f"유형:{sell_type} | 사유:{', '.join(reason)}\n"
                                f"보유:{hold_bars}봉({hold_bars*4}h) | 대기:{new_cd//60}분")
                            self._check_phase4_alert()
                        else:
                            logger.error(f"매도 주문 실패 — 사유:{','.join(reason)}")
                            tg_error(
                                f"*매도 주문 실패* (v{BOT_VERSION})\n"
                                f"사유: {', '.join(reason)}\n"
                                f"다음 루프에서 재시도")
                    else:
                        self.status["hold_bars"] = hold_bars + 1
                        self._save_status()
                        logger.info(f"보유:{self.status['hold_bars']}봉")

                # ── v19.4: EMA 대체 연구용 캔들 로그 ──────────
                try:
                    _cl_rule_score, _, _cl_ema_ok = calc_weighted_score(
                        ema_s, ema_l, price, df4h, is_1d_up, atr_result, cur_atr)
                    _cl_rsi = float(ta.rsi(df4h["close"], 14).iloc[-1])
                    _cl_obv_series = ta.obv(df4h["close"], df4h["volume"])
                    _cl_obv     = float(_cl_obv_series.iloc[-1])
                    _cl_obv_e20 = float(ta.ema(_cl_obv_series, 20).iloc[-1])
                    _cl_vol_ma20 = float(df4h["volume"].iloc[-21:-1].mean())
                    _cl_vol_cur  = float(df4h["volume"].iloc[-1])
                    _cl_vol_ratio = (_cl_vol_cur / _cl_vol_ma20) if _cl_vol_ma20 > 0 else np.nan
                    _cl_o3 = bool(check_liquidity_sweep(df4h, price))
                    _cl_ema_gap = (float(ema_s) - float(ema_l)) / float(ema_l) * 100 if float(ema_l) > 0 else np.nan
                    _cl_funding = fetch_binance_funding_rate()
                    _cl_entered = self.status.get("buy_count", 0) > _cl_initial_buy_count
                    _cl_close   = float(df4h["close"].iloc[-1])
                    _cl_dt      = df4h.index[-1]
                    _cl_dt_str  = _cl_dt.strftime("%Y-%m-%d %H:%M") if hasattr(_cl_dt, "strftime") else str(_cl_dt)
                    # v20.9.10: 다중 EMA 일봉 + 가상 E2 차단 시나리오 (사후 분석용)
                    _cl_emas_d = {}
                    _cl_gaps_d = {}
                    _cl_v_e200 = _cl_v_e250 = _cl_v_gap5 = None
                    try:
                        _cl_df_daily = pyupbit.get_ohlcv("KRW-BTC", interval="day",
                                                         count=E2_DAILY_FETCH_COUNT)
                        if _cl_df_daily is not None and len(_cl_df_daily) > 0:
                            _cl_daily_close = _cl_df_daily["close"].iloc[-1]
                            _cl_emas_d = compute_multi_ema_daily(_cl_df_daily["close"])
                            for p in (100, 150, 200, 250, 300):
                                ev = _cl_emas_d.get(p, float("nan"))
                                if pd.notna(ev) and ev > 0:
                                    _cl_gaps_d[p] = (_cl_daily_close - ev) / ev * 100
                                else:
                                    _cl_gaps_d[p] = float("nan")
                            # 가상 E2 차단 시나리오 (사후 비교용)
                            g200 = _cl_gaps_d.get(200, float("nan"))
                            e250 = _cl_emas_d.get(250, float("nan"))
                            _cl_v_e200 = bool(_cl_daily_close < _cl_emas_d.get(200, _cl_daily_close)) if pd.notna(_cl_emas_d.get(200, float("nan"))) else None
                            _cl_v_e250 = bool(_cl_daily_close < e250) if pd.notna(e250) else None
                            _cl_v_gap5 = bool(g200 < -5.0) if pd.notna(g200) else None
                    except Exception as _cl_emas_e:
                        logger.debug(f"multi-EMA 계산 오류: {_cl_emas_e}")

                    # 차단 사유 (E2 OFF 시에도 기록 — actual_block_reason)
                    _cl_block_reason = "none"
                    if not gate_pass:
                        _cl_block_reason = "ai_gate"
                    elif not _cl_ema_ok:
                        _cl_block_reason = "ema_4h"
                    elif float(_cl_rule_score) < 2.5:
                        _cl_block_reason = "score"
                    elif self.status.get("paused", False):
                        _cl_block_reason = "paused"
                    elif self.status.get("kill_switch", False):
                        _cl_block_reason = "kill_switch"

                    log_candle_record({
                        "datetime":       _cl_dt_str,
                        "price":          _cl_close,
                        "ema21":          float(ema_s),
                        "ema55":          float(ema_l),
                        "ema_ok":         bool(_cl_ema_ok),
                        "ema_gap_pct":    _cl_ema_gap,
                        "o3_signal":      _cl_o3,
                        "xgb_prob":       float(xgb_prob),
                        "regime":         market_state,
                        "adx":            float(adx_info["adx"]),
                        "rsi":            _cl_rsi,
                        "obv":            _cl_obv,
                        "obv_ema20":      _cl_obv_e20,
                        "atr_percentile": float(cur_pct),
                        "volume_ratio":   _cl_vol_ratio,
                        "funding_rate":   _cl_funding if _cl_funding is not None else np.nan,
                        "score":          float(_cl_rule_score),
                        "entered":        bool(_cl_entered),
                        "entry_path":     _cl_entry_path,
                        "price_after_4":  np.nan,
                        "price_after_8":  np.nan,
                        "pct_change_4":   np.nan,
                        "pct_change_8":   np.nan,
                        # v20.9.10 추가
                        "ema100_d":       _cl_emas_d.get(100, np.nan),
                        "ema150_d":       _cl_emas_d.get(150, np.nan),
                        "ema200_d":       _cl_emas_d.get(200, np.nan),
                        "ema250_d":       _cl_emas_d.get(250, np.nan),
                        "ema300_d":       _cl_emas_d.get(300, np.nan),
                        "gap_e100_d":     _cl_gaps_d.get(100, np.nan),
                        "gap_e150_d":     _cl_gaps_d.get(150, np.nan),
                        "gap_e200_d":     _cl_gaps_d.get(200, np.nan),
                        "gap_e250_d":     _cl_gaps_d.get(250, np.nan),
                        "gap_e300_d":     _cl_gaps_d.get(300, np.nan),
                        "virtual_e2_block_e200": _cl_v_e200,
                        "virtual_e2_block_e250": _cl_v_e250,
                        "virtual_e2_block_gap5": _cl_v_gap5,
                        "actual_block_reason":   _cl_block_reason,
                        "price_after_24": np.nan,
                        "pct_change_24":  np.nan,
                    })
                except Exception as _cl_e:
                    logger.debug(f"candle_log 생성 오류: {_cl_e}")

                # v20.9.10 #75-B: 롤백 트리거 체크 (E2 OFF 모드 안전망)
                try:
                    self._check_rollback_triggers(equity, price)
                except Exception as _rb_e:
                    logger.debug(f"롤백 트리거 체크 오류: {_rb_e}")

            except Exception as e:
                logger.error(f"루프 에러: {e}", exc_info=True)
                time.sleep(30); continue
            time.sleep(30)


if __name__ == "__main__":
    # v20.9.9 #68: 월간 리포트 백필 CLI
    #   python btc_bot_v290.py --monthly-report YYYY-MM [--no-push] [--no-telegram]
    if len(sys.argv) >= 2 and sys.argv[1] == "--monthly-report":
        if len(sys.argv) < 3:
            print("usage: --monthly-report YYYY-MM [--no-push] [--no-telegram]")
            sys.exit(2)
        _ym = sys.argv[2]
        _push  = "--no-push"     not in sys.argv
        _send  = "--no-telegram" not in sys.argv
        _res = generate_monthly_report(ym=_ym, push=_push, send_tg=_send)
        if _res.get("ok"):
            print(f"[monthly-report] OK ym={_ym}")
            if _res.get("raw_url"): print(f"  raw_url: {_res['raw_url']}")
            print("---telegram---")
            print(_res.get("telegram_msg", ""))
            sys.exit(0)
        print(f"[monthly-report] FAIL reason={_res.get('reason')}")
        sys.exit(1)

    BitcoinBot().run()
