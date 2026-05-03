#!/usr/bin/env python3
"""
shadow/shadow_bot.py — 독립 쉐도우 AI 프로세스 (v2.0)
봇 코드에 의존하지 않음. btc_status.json 읽기 전용.

기능:
  1. RandomForest + Online(River ARF) 학습/예측 (XGB 재학습 감지 시 동기화)
  2. M3 가상 진입/청산 (FNG<25 + Trend_Down)
  3. TP 추가매수 가상 추적
  4. 정각(00,04,08,12,16,20 KST) 텔레그램 리포트

v1.0 → v2.0 (2026-04-17): CatBoost → RandomForest, LSTM → Online Learning
  - 4H 환경에서 3000+ 샘플 요구하는 CB/LSTM 구조적 한계 해소
  - RF: 400 샘플 작동, XGB와 직접 비교
  - Online: 증분 학습 + ADWIN 드리프트 감지 내장

사용:
  systemctl start shadow_bot.service
  또는
  /root/tradingbot/venv/bin/python shadow/shadow_bot.py
"""
import os, sys, time, json, logging, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# ── 경로 설정 ─────────────────────────────────────────────
SHADOW_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SHADOW_DIR)
os.chdir(PROJECT_DIR)

# pandas_ta는 로컬 폴더(pip 미설치). 반드시 sys.path 최상단에 삽입.
_pandas_ta_path = os.path.join(PROJECT_DIR, "pandas_ta")
if _pandas_ta_path not in sys.path:
    sys.path.insert(0, _pandas_ta_path)
if SHADOW_DIR not in sys.path:
    sys.path.insert(0, SHADOW_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import pandas_ta as ta
import pyupbit
from shadow_ai import (
    RandomForestShadow, OnlineLearningShadow, ShadowXGBTB3Wrapper,
    build_features_24,
    calc_kimchi_premium, fetch_fng, dt_to_str,
    log_shadow_prediction, update_actual_results, get_shadow_stats,
)
from shadow_strategy import (
    M3Shadow, TPAddShadow,
    build_shadow_report, build_m3_entry_msg, build_m3_exit_msg,
)

# ── 환경 변수 ─────────────────────────────────────────────
load_dotenv(os.path.join(PROJECT_DIR, ".env"))
TG_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── 상수 ──────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
TICKER     = "KRW-BTC"
TF_PRIMARY = "minute240"
STATUS_FILE = os.path.join(PROJECT_DIR, "btc_status.json")
LOG_FILE    = os.path.join(PROJECT_DIR, "shadow_bot.log")
DATA_COUNT  = 3000

# 리포트 발송 정각 (KST)
REPORT_HOURS = [0, 4, 8, 12, 16, 20]

# Regime 판정 상수 (봇과 동일)
REGIME_HYS_ENTER = 27.0
REGIME_HYS_EXIT  = 23.0

# Regime별 임계값 (btc_bot_v290.py REGIME_CONFIG와 동기화, #67 분석용)
REGIME_THRESHOLDS = {
    "Trend_Up":   {"xgb_th": 0.58, "score_th": 4.0},
    "Range":      {"xgb_th": 0.55, "score_th": 3.0},
    "Volatile":   {"xgb_th": 0.58, "score_th": 3.5},
    "Trend_Down": {"xgb_th": 0.60, "score_th": 3.5},
}

# ── 로깅 ──────────────────────────────────────────────────
logger = logging.getLogger("SHADOW")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
if not logger.handlers:
    logger.addHandler(_fh)
    logger.addHandler(_sh)


# ── 텔레그램 ──────────────────────────────────────────────
def send_telegram(msg, retries=3):
    if not TG_TOKEN:
        return False
    for attempt in range(retries):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=10)
            if resp.status_code == 200:
                return True
            if resp.status_code == 400:
                # Markdown 파싱 실패 시 plain text 재시도
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                    json={"chat_id": TG_CHAT_ID, "text": msg}, timeout=10)
                return True
        except Exception as e:
            logger.warning(f"TG fail ({attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    return False


# ── btc_status.json 읽기 (읽기 전용) ─────────────────────
def read_bot_status():
    """봇의 btc_status.json을 읽기 전용으로 조회."""
    try:
        if not os.path.exists(STATUS_FILE):
            return {}
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"status read err: {e}")
        return {}


# ── Regime 판정 (봇과 동일 로직) ──────────────────────────
def classify_market_from_df(df4h, prev_regime=None):
    """df4h에서 ATR/ADX 계산 후 Regime 판정."""
    try:
        atr_s = ta.atr(df4h["high"], df4h["low"], df4h["close"], length=14)
        atr_pcts = atr_s.rolling(100).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False)
        cur_pct = float(atr_pcts.iloc[-1]) if pd.notna(atr_pcts.iloc[-1]) else 50.0
        atr_volatile = cur_pct > 95

        adx_df = ta.adx(df4h["high"], df4h["low"], df4h["close"], length=14)
        adx_val = float(adx_df["ADX_14"].iloc[-1])
        di_plus = float(adx_df["DMP_14"].iloc[-1])
        di_minus = float(adx_df["DMN_14"].iloc[-1])
        cur_atr = float(atr_s.iloc[-1]) if pd.notna(atr_s.iloc[-1]) else 0

        if atr_volatile:
            return "Volatile", adx_val, cur_atr

        if adx_val >= REGIME_HYS_ENTER:
            regime = "Trend_Up" if di_plus > di_minus else "Trend_Down"
        elif adx_val < REGIME_HYS_EXIT:
            regime = "Range"
        else:
            # 회색지대 23~27: 직전 유지
            regime = prev_regime if prev_regime else "Range"

        return regime, adx_val, cur_atr
    except Exception as e:
        logger.debug(f"classify err: {e}")
        return prev_regime or "Range", 20.0, 0.0


# ══════════════════════════════════════════════════════════
# 메인 봇 클래스
# ══════════════════════════════════════════════════════════
class ShadowBot:

    def __init__(self):
        self.rf = RandomForestShadow()
        self.online = OnlineLearningShadow()
        self.tb3 = ShadowXGBTB3Wrapper()        # #80
        self.m3 = M3Shadow()
        self.tp = TPAddShadow()

        self.last_xgb_train_dt = None   # XGB 재학습 감지용
        self.last_candle_time = None     # 새 캔들 감지용
        self.last_report_hour = None     # 정각 발송 중복 방지
        self.prev_regime = None          # Regime 히스테리시스

        self.last_rf_prob = None
        self.last_online_prob = None
        self.last_tb3_prob = None              # #80

        # 봇 상태에서 초기값 로드
        status = read_bot_status()
        self.last_xgb_train_dt = status.get("ai_last_train_dt")
        self.prev_regime = status.get("last_regime")
        logger.info(f"ShadowBot init: regime={self.prev_regime} "
                     f"xgb_train={self.last_xgb_train_dt}")

    def run(self):
        logger.info("=" * 40)
        logger.info("Shadow Bot started")
        send_telegram("*Shadow Bot started*\nIndependent process — no trade impact")

        # 초기 학습
        self._initial_train()

        while True:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"tick err: {e}", exc_info=True)
            time.sleep(30)

    def _initial_train(self):
        """시작 시 RF + Online + TB3 학습 (모델 파일 없을 때만)."""
        if self.rf.trained and self.online.trained and self.tb3.trained:
            logger.info("Models already trained, skip initial training")
            return
        logger.info("Initial training...")
        df = self._fetch_ohlcv(DATA_COUNT)
        if df is None:
            logger.warning("Initial train: data fetch failed")
            return
        price = float(df["close"].iloc[-1])
        kp = calc_kimchi_premium(price)
        if not self.rf.trained:
            self.rf.train(df, kp)
        if not self.online.trained:
            self.online.train(df, kp)
        if not self.tb3.trained:
            self.tb3.train(df)

    def _tick(self):
        """30초마다 실행되는 메인 루프 틱."""
        now_kst = datetime.now(KST)

        # 1) XGB 재학습 감지 → 쉐도우 동기화 학습
        self._check_xgb_retrain()

        # 2) 새 캔들 감지 → 예측 기록 + M3 체크
        self._check_new_candle()

        # 3) 정각 리포트 발송
        self._check_report_time(now_kst)

    def _check_xgb_retrain(self):
        """봇의 ai_last_train_dt가 변경되면 쉐도우도 재학습."""
        status = read_bot_status()
        current_dt = status.get("ai_last_train_dt")
        if current_dt and current_dt != self.last_xgb_train_dt:
            logger.info(f"XGB retrain detected: {self.last_xgb_train_dt} -> {current_dt}")
            self.last_xgb_train_dt = current_dt

            df = self._fetch_ohlcv(DATA_COUNT)
            if df is not None:
                price = float(df["close"].iloc[-1])
                kp = calc_kimchi_premium(price)
                import threading
                # RF는 재학습 (배치 모델 — XGB와 동일 타이밍)
                threading.Thread(target=self.rf.train, args=(df, kp), daemon=True).start()
                # Online은 재학습 불필요 (증분 학습 중) — 단, 초기 warm-up 미완이면 재시도
                if not self.online.trained:
                    threading.Thread(target=self.online.train, args=(df, kp), daemon=True).start()
                # #80 TB3는 매 XGB 재학습마다 재학습 (배치 모델, Main 동기)
                threading.Thread(target=self.tb3.train, args=(df,), daemon=True).start()
                logger.info("Shadow retrain started (background)")

    def _check_new_candle(self):
        """새 4H 캔들 감지 시 예측 기록 + M3/TP 체크."""
        df4h = self._fetch_ohlcv(300)
        if df4h is None:
            return

        latest_candle = df4h.index[-1]
        if self.last_candle_time == latest_candle:
            return  # 같은 캔들

        self.last_candle_time = latest_candle
        price = float(df4h["close"].iloc[-1])
        logger.info(f"New candle: {latest_candle} price={price:,.0f}")

        # 봇 상태 읽기
        status = read_bot_status()
        xgb_prob = status.get("live_xgb")
        market_state = status.get("last_regime", "Range")
        self.prev_regime = market_state

        # Regime/ATR 독립 계산
        regime, adx_val, cur_atr = classify_market_from_df(df4h, self.prev_regime)

        # 쉐도우 예측
        rf_prob, online_prob, tb3_prob = None, None, None
        kp = None
        try:
            feat24 = build_features_24(df4h)
            kp = calc_kimchi_premium(price)
            if feat24 is not None and len(feat24) > 0:
                rf_prob = self.rf.predict(feat24[-1:], kp)
                online_prob = self.online.predict(feat24[-1], kp)
            tb3_prob = self.tb3.predict(df4h)             # #80
        except Exception as e:
            logger.debug(f"predict err: {e}")
        self.last_rf_prob = rf_prob
        self.last_online_prob = online_prob
        self.last_tb3_prob = tb3_prob

        # #67: 시장 상태 컬럼 (rsi14, atr_pct percentile) — adx는 위에서 계산됨
        rsi14_val, atr_pct_val = None, None
        try:
            rsi_s = ta.rsi(df4h["close"], 14)
            rsi14_val = float(rsi_s.iloc[-1]) if pd.notna(rsi_s.iloc[-1]) else None
            atr_s = ta.atr(df4h["high"], df4h["low"], df4h["close"], length=14)
            atr_pcts = atr_s.rolling(100).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False)
            atr_pct_val = float(atr_pcts.iloc[-1]) if pd.notna(atr_pcts.iloc[-1]) else None
        except Exception as e:
            logger.debug(f"market state calc err: {e}")

        # #67: 운영 흐름 컬럼 (xgb_gate / rule_score / e2 / would_enter)
        regime_th = REGIME_THRESHOLDS.get(regime, REGIME_THRESHOLDS["Range"])
        xgb_gate_pass = (xgb_prob > regime_th["xgb_th"]) if xgb_prob is not None else None
        rule_score = status.get("live_score")
        rule_score_pass = (rule_score > regime_th["score_th"]) if rule_score is not None else None
        e2_blocked = bool(status.get("live_e2_f2_active") or status.get("live_e2_f5_active"))
        if xgb_gate_pass is not None and rule_score_pass is not None:
            would_enter = bool(xgb_gate_pass and rule_score_pass and not e2_blocked)
        else:
            would_enter = None

        # 예측 CSV 기록
        dt_str = latest_candle.strftime("%Y-%m-%d %H:%M") if hasattr(latest_candle, "strftime") else str(latest_candle)
        xgb_ver = self.last_xgb_train_dt
        rf_ver = dt_to_str(self.rf.train_dt)
        online_ver = dt_to_str(self.online.train_dt)
        tb3_ver = dt_to_str(self.tb3.train_dt)
        # #79 Main PF 측정값
        main_pf_holdout = status.get("ai_pf_holdout")
        main_pf_oos_100 = status.get("ai_pf_oos_100")
        # #81 시그널
        main_signal = "BUY" if (xgb_prob is not None and xgb_prob > 0.55) else "SKIP"
        tb3_signal  = ("BUY" if (tb3_prob is not None and tb3_prob > 0.5)
                       else ("SKIP" if tb3_prob is not None else None))
        log_shadow_prediction(
            dt_str, price, xgb_prob, rf_prob, online_prob,
            xgb_ver, rf_ver, online_ver, regime=regime,
            rsi14=rsi14_val, adx=adx_val, atr_pct=atr_pct_val,
            xgb_gate_pass=xgb_gate_pass, rule_score=rule_score,
            rule_score_pass=rule_score_pass, e2_blocked=e2_blocked,
            would_enter=would_enter,
            main_pf_holdout=main_pf_holdout, main_pf_oos_100=main_pf_oos_100,
            shadow_xgb_tb3_prob=tb3_prob, shadow_xgb_tb3_version=tb3_ver,
            main_signal=main_signal, shadow_xgb_tb3_signal=tb3_signal)
        # v2.0: Online 증분 학습 — actual_result 확정 시점마다 learn_one
        update_actual_results(price, online_model=self.online, df4h=df4h, kp=kp)

        # M3 체크 (FNG<25 + Trend_Down)
        fng_val = fetch_fng()
        equity = status.get("live_equity", 0) or 10_000_000  # fallback
        m3_entry = self.m3.check_entry(fng_val, market_state, price, equity, cur_atr)
        if m3_entry:
            send_telegram(build_m3_entry_msg(m3_entry))

        m3_exit = self.m3.check_exit(price, cur_atr)
        if m3_exit:
            send_telegram(build_m3_exit_msg(m3_exit, self.m3.get_summary()))

        # TP 추가매수 쉐도우
        if status.get("in_position"):
            stp_lv = status.get("step_tp_level", 0)
            if stp_lv >= 2:
                trade_id = status.get("last_trade_time", 0)
                self.tp.check_tp_add(stp_lv, price, equity, trade_id)

        # TP 청산 감지 (이전 포지션 → 청산)
        if not status.get("in_position") and hasattr(self, '_prev_in_position') and self._prev_in_position:
            trade_id = status.get("last_trade_time", 0)
            self.tp.close_trade(trade_id, price)

        self._prev_in_position = status.get("in_position", False)

    def _check_report_time(self, now_kst):
        """정각(00,04,08,12,16,20 KST) 텔레그램 발송."""
        hour = now_kst.hour
        minute = now_kst.minute

        if hour not in REPORT_HOURS:
            return
        if minute > 5:
            return  # 정각 후 5분 이내만
        if self.last_report_hour == (now_kst.date(), hour):
            return  # 이미 발송

        self.last_report_hour = (now_kst.date(), hour)
        logger.info(f"Report time: {hour:02d}:00 KST")

        # 봇 상태
        status = read_bot_status()
        xgb_prob = status.get("live_xgb")
        market_state = status.get("last_regime", "Range")
        fng_val = fetch_fng()

        shadow_stats = get_shadow_stats()
        m3_status = "open" if self.m3.open_trade else "inactive"
        m3_summary = self.m3.get_summary()
        tp_summary = self.tp.get_summary()

        msg = build_shadow_report(
            xgb_prob, self.last_rf_prob, self.last_online_prob,
            shadow_stats, m3_status, m3_summary,
            fng_val, market_state, tp_summary,
            online_n_learned=self.online.n_learned,
            tb3_prob=self.last_tb3_prob)
        send_telegram(msg)

    @staticmethod
    def _fetch_ohlcv(count):
        """pyupbit OHLCV 조회. 실패 시 None."""
        for attempt in range(3):
            try:
                df = pyupbit.get_ohlcv(TICKER, interval=TF_PRIMARY, count=count)
                if df is not None and len(df) > 50:
                    return df
            except Exception as e:
                logger.debug(f"OHLCV fetch err ({attempt+1}): {e}")
            time.sleep(2)
        return None


if __name__ == "__main__":
    ShadowBot().run()
