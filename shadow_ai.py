"""
shadow/shadow_ai.py — CatBoost + LSTM 쉐도우 AI 모델
봇 코드에 의존하지 않는 완전 독립 모듈.
자체 피처 빌더 포함. btc_status.json은 읽기 전용.
"""
import os, sys, time, logging, threading, json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

# pandas_ta 로드
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pandas_ta"))
try:
    import pandas_ta as ta
except ImportError:
    ta = None

logger = logging.getLogger("SHADOW")
KST = timezone(timedelta(hours=9))

# ── 경로 (shadow/ 기준) ──────────────────────────────────
SHADOW_DIR    = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR    = os.path.join(SHADOW_DIR, "models")
DATA_DIR      = os.path.join(SHADOW_DIR, "data")
RF_PATH     = os.path.join(MODELS_DIR, "rf_model.pkl")
ONLINE_PATH = os.path.join(MODELS_DIR, "online_model.pkl")
SHADOW_XGB_TB3_PATH      = os.path.join(MODELS_DIR, "shadow_xgb_tb3.pkl")
SHADOW_XGB_TB3_META_PATH = os.path.join(MODELS_DIR, "shadow_xgb_tb3_meta.json")
PREDICTIONS_CSV  = os.path.join(DATA_DIR, "shadow_predictions.csv")

# ── 라벨링 (XGBoost와 동일 기준) ─────────────────────────
LABEL_UP_THRESH   = 0.012
LABEL_DOWN_THRESH = -0.012
LABEL_FUTURE_BARS = 8
LABEL_MIN_SAMPLES = 400

# ── #80 Triple Barrier (TB3) 라벨링 ───────────────────────
TB_TP_BARRIER = 0.020   # +2.0%
TB_SL_BARRIER = -0.010  # -1.0%
TB_TIME_LIMIT = 16      # 16봉

# ── 외부 데이터 캐시 ─────────────────────────────────────
_fng_cache = {"value": None, "ts": 0.0}
_nasdaq_cache = {"value": None, "ts": 0.0}
_DAILY_CACHE_TTL = 14400  # 4시간


# ══════════════════════════════════════════════════════════
# 외부 데이터 API
# ══════════════════════════════════════════════════════════

def fetch_fng():
    """Fear & Greed Index (0~100). 4시간 캐싱."""
    now = time.time()
    if _fng_cache["value"] is not None and now - _fng_cache["ts"] < _DAILY_CACHE_TTL:
        return _fng_cache["value"]
    try:
        import requests
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        if r.status_code == 200:
            val = int(r.json()["data"][0]["value"])
            _fng_cache["value"] = val
            _fng_cache["ts"] = now
            return val
    except Exception as e:
        logger.debug(f"FNG API err: {e}")
    return _fng_cache["value"]


def calc_fng_extreme(fng_val):
    if fng_val is None: return 0.0
    if fng_val < 25: return 1.0
    if fng_val > 75: return -1.0
    return 0.0


def fetch_nasdaq_return():
    """나스닥 전일 수익률(%). 4시간 캐싱."""
    now = time.time()
    if _nasdaq_cache["value"] is not None and now - _nasdaq_cache["ts"] < _DAILY_CACHE_TTL:
        return _nasdaq_cache["value"]
    try:
        import requests
        end = int(now)
        start = end - 5 * 86400
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC"
               f"?period1={start}&period2={end}&interval=1d")
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data = r.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                ret = (closes[-1] - closes[-2]) / closes[-2] * 100
                _nasdaq_cache["value"] = ret
                _nasdaq_cache["ts"] = now
                return ret
    except Exception as e:
        logger.debug(f"NASDAQ API err: {e}")
    return _nasdaq_cache["value"]


_usdkrw_cache = {"rate": None, "ts": 0.0}


def fetch_usdkrw():
    now = time.time()
    if _usdkrw_cache["rate"] is not None and now - _usdkrw_cache["ts"] < 86400:
        return _usdkrw_cache["rate"]
    try:
        import requests
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if r.status_code == 200:
            rate = float(r.json()["rates"]["KRW"])
            _usdkrw_cache["rate"] = rate
            _usdkrw_cache["ts"] = now
            return rate
    except Exception:
        pass
    return _usdkrw_cache["rate"]


def fetch_binance_btc_usdt():
    try:
        import requests
        r = requests.get("https://api.binance.com/api/v3/ticker/price",
                         params={"symbol": "BTCUSDT"}, timeout=5)
        if r.status_code == 200:
            return float(r.json()["price"])
    except Exception:
        pass
    return None


def calc_kimchi_premium(upbit_price):
    btc_usdt = fetch_binance_btc_usdt()
    if btc_usdt is None: return None
    usdkrw = fetch_usdkrw()
    if usdkrw is None: return None
    binance_krw = btc_usdt * usdkrw
    if binance_krw <= 0: return None
    return (upbit_price - binance_krw) / binance_krw * 100


# ══════════════════════════════════════════════════════════
# 독립 피처 빌더 (봇의 _build_features 복제)
# ══════════════════════════════════════════════���═══════════

# XGB 모델이 사용하는 13피처 인덱스 (24컬럼 중)
_FEAT_COLS = [4, 6, 7, 8, 11, 12, 13, 14, 16, 17, 20, 22, 23]


def build_features_24(df):
    """df(OHLCV) → (n, 24) ���열. 봇의 _build_features()와 동일."""
    out = df[["open", "high", "low", "close", "volume"]].copy()
    out["volume"]     = df["volume"].shift(1).bfill()
    out["ema_diff"]   = (ta.ema(df["close"], 21) - ta.ema(df["close"], 55)).shift(1).fillna(0)
    out["rsi"]        = ta.rsi(df["close"], 14).shift(1).fillna(50)
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
    except Exception:
        atr_s = pd.Series(0.0, index=df.index)
        out["atr_ratio"] = 1.0
    try:
        adx_df   = ta.adx(df["high"], df["low"], df["close"], length=14)
        out["adx"] = adx_df["ADX_14"].shift(1).fillna(20)
        di_plus  = adx_df["DMP_14"].shift(1).fillna(20)
        di_minus = adx_df["DMN_14"].shift(1).fillna(20)
    except Exception:
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
    return out.values  # (n, 24)


def label_tb3(prices, i):
    """#80 Triple Barrier 라벨링.
    현재 봉 i부터 TB_TIME_LIMIT(16)봉 내:
      - +TP_BARRIER (+2.0%) 먼저 도달 → 1
      - -SL_BARRIER (-1.0%) 먼저 도달 → 0
      - 둘 다 미도달 → 16봉 후 ret > 0 기준
    경계: i + TB_TIME_LIMIT 가 시리즈 길이를 넘으면 None.
    """
    if i + TB_TIME_LIMIT >= len(prices):
        return None
    entry = prices[i]
    if entry <= 0:
        return None
    for j in range(1, TB_TIME_LIMIT + 1):
        future_price = prices[i + j]
        if future_price <= 0: continue
        ret = (future_price - entry) / entry
        if ret >= TB_TP_BARRIER: return 1
        if ret <= TB_SL_BARRIER: return 0
    final_ret = (prices[i + TB_TIME_LIMIT] - entry) / entry
    return 1 if final_ret > 0 else 0


# ══════════════════════════════════════════════════════════
# #80 Shadow XGB TB3 — Triple Barrier 라벨링 별도 모델
# ══════════════════════════════════════════════════════════
class ShadowXGBTB3Wrapper:
    """별도 XGB 모델 + TB3 라벨링.
    피처 13개 (Main과 동일), 하이퍼파라미터 Main 동일, 학습 빈도 Main 동기화.
    """
    def __init__(self):
        self.model = None
        self.trained = False
        self.train_dt = None
        self.precision = 0.0
        self.recall = 0.0
        self.profit_factor = 0.0
        self.accuracy = 0.0
        self.n_train = 0
        self._training = False
        self._load()

    def _load(self):
        if os.path.exists(SHADOW_XGB_TB3_PATH):
            try:
                import joblib
                self.model = joblib.load(SHADOW_XGB_TB3_PATH)
                self.trained = True
                if os.path.exists(SHADOW_XGB_TB3_META_PATH):
                    with open(SHADOW_XGB_TB3_META_PATH) as f:
                        m = json.load(f)
                    self.train_dt = (datetime.fromisoformat(m["train_dt"])
                                     if m.get("train_dt") else None)
                    self.precision     = float(m.get("precision", 0.0))
                    self.recall        = float(m.get("recall", 0.0))
                    self.profit_factor = float(m.get("profit_factor", 0.0))
                    self.accuracy      = float(m.get("accuracy", 0.0))
                    self.n_train       = int(m.get("n_train", 0))
                logger.info(f"Shadow XGB TB3 loaded: Prec={self.precision:.1%} "
                            f"PF={self.profit_factor:.2f} n={self.n_train}")
            except Exception as e:
                logger.warning(f"Shadow XGB TB3 load err: {e}")
                self.model = None; self.trained = False

    def _save_meta(self):
        try:
            os.makedirs(MODELS_DIR, exist_ok=True)
            meta = {
                "train_dt": self.train_dt.isoformat() if self.train_dt else None,
                "precision": self.precision, "recall": self.recall,
                "profit_factor": self.profit_factor, "accuracy": self.accuracy,
                "n_train": self.n_train,
            }
            with open(SHADOW_XGB_TB3_META_PATH, "w") as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            logger.warning(f"TB3 meta save err: {e}")

    def train(self, df):
        if self._training: return
        self._training = True
        try:
            from xgboost import XGBClassifier
            import joblib
            feat24 = build_features_24(df)
            x13_full = feat24[:, _FEAT_COLS]
            prices = feat24[:, 3]

            X, y = [], []
            for i in range(len(prices) - TB_TIME_LIMIT):
                lbl = label_tb3(prices, i)
                if lbl is None: continue
                X.append(x13_full[i]); y.append(lbl)

            if len(X) < LABEL_MIN_SAMPLES:
                logger.info(f"TB3 data insufficient: {len(X)}/{LABEL_MIN_SAMPLES}")
                return
            X = np.array(X); y = np.array(y, dtype=int)
            split = int(len(X) * 0.8)
            X_tr, y_tr = X[:split], y[:split]
            X_te, y_te = X[split:], y[split:]

            n_pos = max(int((y_tr == 1).sum()), 1)
            n_neg = max(int((y_tr == 0).sum()), 1)
            spw = n_neg / n_pos

            model = XGBClassifier(
                n_estimators=500, max_depth=3, learning_rate=0.03,
                min_child_weight=15, subsample=0.7, colsample_bytree=0.7,
                gamma=0.5, reg_lambda=1.5, reg_alpha=0.1,
                scale_pos_weight=spw, eval_metric="auc", base_score=0.5,
                random_state=42, n_jobs=-1, verbosity=0)
            model.fit(X_tr, y_tr, verbose=False)

            probs = model.predict_proba(X_te)[:, 1]
            preds = (probs > 0.5).astype(int)
            acc = float(np.mean(preds == y_te))
            tp = int(((preds == 1) & (y_te == 1)).sum())
            fp = int(((preds == 1) & (y_te == 0)).sum())
            fn = int(((preds == 0) & (y_te == 1)).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            # PF — TB3 라벨 기준 (gain = 실제 +2% 도달, loss = -1% 도달)
            gains  = probs[y_te == 1].sum()
            losses = (1 - probs[y_te == 0]).sum()
            pf = float(gains / losses) if losses > 0 else 0.0

            self.model = model
            self.trained = True
            self.train_dt = datetime.now(KST)
            self.precision = prec; self.recall = rec
            self.profit_factor = pf; self.accuracy = acc
            self.n_train = len(X_tr)
            joblib.dump(model, SHADOW_XGB_TB3_PATH)
            self._save_meta()
            logger.info(f"Shadow XGB TB3 trained: Prec={prec:.1%} PF={pf:.2f} "
                        f"Acc={acc:.1%} (tr={len(X_tr)} te={len(X_te)})")
        except Exception as e:
            logger.error(f"TB3 train err: {e}", exc_info=True)
        finally:
            self._training = False

    def predict(self, df):
        if not self.trained or self.model is None: return None
        try:
            feat24 = build_features_24(df)
            if feat24 is None or len(feat24) == 0: return None
            x = feat24[-1:, _FEAT_COLS]
            return float(self.model.predict_proba(x)[0][1])
        except Exception as e:
            logger.debug(f"TB3 predict err: {e}")
            return None


# ══════════════════════════════════════════════════════════
# Random Forest 쉐도우 (v2.0 — CatBoost 대체)
# ══════════════════════════════════════════════════════════
class RandomForestShadow:
    """sklearn RandomForest 기반 Shadow. XGB와 직접 비교 목적.
    400 샘플 작동, 과적합 저항 강, Regime 전환 추적 빠름.
    """
    def __init__(self):
        self.model = None
        self.trained = False
        self.train_dt = None
        self.precision = 0.0
        self.recall = 0.0
        self.profit_factor = 0.0
        self.accuracy = 0.0
        self._training = False
        self._load_model()

    def _load_model(self):
        if os.path.exists(RF_PATH):
            try:
                import joblib
                self.model = joblib.load(RF_PATH)
                self.trained = True
                meta_path = os.path.join(MODELS_DIR, "rf_meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path) as f:
                        m = json.load(f)
                    self.train_dt = (datetime.fromisoformat(m["train_dt"])
                                     if m.get("train_dt") else None)
                    self.precision = m.get("precision", 0.0)
                    self.recall = m.get("recall", 0.0)
                    self.profit_factor = m.get("profit_factor", 0.0)
                    self.accuracy = m.get("accuracy", 0.0)
                logger.info(f"RF loaded (Prec={self.precision:.1%})")
            except Exception as e:
                logger.warning(f"RF load fail: {e}")

    def _build_features(self, feat24, kimchi_premium=None):
        """16 피처 = XGB 13 + 김프 + FNG + 나스닥 (CB와 동일 구성)"""
        x13 = feat24[:, _FEAT_COLS]
        n = len(x13)
        kp = kimchi_premium if kimchi_premium is not None else 0.0
        fng_ext = calc_fng_extreme(fetch_fng())
        nasdaq = fetch_nasdaq_return()
        nasdaq_val = nasdaq if nasdaq is not None else 0.0
        extra = np.column_stack([
            np.full(n, kp), np.full(n, fng_ext), np.full(n, nasdaq_val)])
        return np.hstack([x13, extra])

    def train(self, df, kimchi_premium=None):
        if self._training: return
        self._training = True
        try:
            from sklearn.ensemble import RandomForestClassifier
            import joblib
            feat24 = build_features_24(df)
            x16 = self._build_features(feat24, kimchi_premium)
            closes = feat24[:, 3]
            X, y = [], []
            for i in range(len(closes) - LABEL_FUTURE_BARS):
                ret = (closes[i + LABEL_FUTURE_BARS] - closes[i]) / closes[i]
                if ret > LABEL_UP_THRESH:
                    X.append(x16[i]); y.append(1)
                elif ret < LABEL_DOWN_THRESH:
                    X.append(x16[i]); y.append(0)
            if len(X) < LABEL_MIN_SAMPLES:
                logger.info(f"RF data insufficient: {len(X)}/{LABEL_MIN_SAMPLES}")
                return
            X, y = np.array(X), np.array(y)
            split = int(len(X) * 0.8)
            X_tr, y_tr = X[:split], y[:split]
            X_te, y_te = X[split:], y[split:]

            rf = RandomForestClassifier(
                n_estimators=300,
                max_depth=5,              # XGB와 유사 (과적합 방지)
                min_samples_leaf=5,
                max_features='sqrt',
                class_weight='balanced',
                random_state=42,
                n_jobs=-1)
            rf.fit(X_tr, y_tr)

            probs = rf.predict_proba(X_te)[:, 1]
            preds = (probs > 0.5).astype(int)
            acc = float(np.mean(preds == y_te))
            tp = int(((preds == 1) & (y_te == 1)).sum())
            fp = int(((preds == 1) & (y_te == 0)).sum())
            fn = int(((preds == 0) & (y_te == 1)).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            gains = probs[y_te == 1].sum()
            losses_v = (1 - probs[y_te == 0]).sum()
            pf = float(gains / losses_v) if losses_v > 0 else 0.0

            self.model = rf
            self.trained = True
            self.train_dt = datetime.now(KST)
            self.precision = prec; self.recall = rec
            self.profit_factor = pf; self.accuracy = acc
            joblib.dump(rf, RF_PATH)
            self._save_meta()
            logger.info(f"RF trained: Prec={prec:.1%} PF={pf:.2f} Acc={acc:.1%} "
                        f"(tr={len(X_tr)} te={len(X_te)})")
        except Exception as e:
            logger.error(f"RF train err: {e}", exc_info=True)
        finally:
            self._training = False

    def predict(self, feat24_last, kimchi_premium=None):
        if not self.trained or self.model is None: return None
        try:
            if feat24_last.ndim == 1:
                feat24_last = feat24_last.reshape(1, -1)
            x16 = self._build_features(feat24_last, kimchi_premium)
            return float(self.model.predict_proba(x16)[0][1])
        except Exception as e:
            logger.debug(f"RF predict err: {e}")
            return None

    def _save_meta(self):
        try:
            meta = {"train_dt": self.train_dt.isoformat() if self.train_dt else None,
                    "precision": self.precision, "recall": self.recall,
                    "profit_factor": self.profit_factor, "accuracy": self.accuracy}
            with open(os.path.join(MODELS_DIR, "rf_meta.json"), "w") as f:
                json.dump(meta, f, indent=2)
        except Exception: pass


# ══════════════════════════════════════════════════════════
# Online Learning 쉐도우 (v2.0 — LSTM 대체, River ARF)
# ══════════════════════════════════════════════════════════
# 16 피처 이름 (Online 모델용 dict key)
_ONLINE_FEAT_NAMES = [
    'volume', 'rsi', 'returns', 'volatility', 'atr_ratio',
    'adx', 'return_5', 'return_10', 'trend_strength',
    'ema_slope', 'volatility_expansion', 'price_vs_ema200', 'bb_position',
    'kimchi_premium', 'fng_extreme', 'nasdaq_return'
]


class OnlineLearningShadow:
    """River ARF(Adaptive Random Forest) 기반 증분 학습.
    매 캔들 예측 + actual_result 확정 시 learn_one() 호출.
    ADWIN 드리프트 감지 내장 → 시장 변화 추적 최적.
    """
    def __init__(self):
        self.model = None
        self.trained = False
        self.train_dt = None
        self.precision = 0.0
        self.recall = 0.0
        self.profit_factor = 0.0
        self.accuracy = 0.0
        self.n_learned = 0
        self._training = False
        self._load_model()

    def _load_model(self):
        if os.path.exists(ONLINE_PATH):
            try:
                import joblib
                self.model = joblib.load(ONLINE_PATH)
                self.trained = True
                meta_path = os.path.join(MODELS_DIR, "online_meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path) as f:
                        m = json.load(f)
                    self.train_dt = (datetime.fromisoformat(m["train_dt"])
                                     if m.get("train_dt") else None)
                    self.precision = m.get("precision", 0.0)
                    self.recall = m.get("recall", 0.0)
                    self.profit_factor = m.get("profit_factor", 0.0)
                    self.accuracy = m.get("accuracy", 0.0)
                    self.n_learned = m.get("n_learned", 0)
                logger.info(f"Online loaded (n_learned={self.n_learned})")
            except Exception as e:
                logger.warning(f"Online load fail: {e}")

    def _init_new_model(self):
        from river import forest, preprocessing, compose
        return compose.Pipeline(
            preprocessing.StandardScaler(),
            forest.ARFClassifier(
                n_models=10,
                max_features='sqrt',
                seed=42,
            )
        )

    def _features_to_dict(self, feat24_row, kimchi_premium=None):
        """피처 배열 → River용 dict.
        feat24_row: shape (24,) 단일 행
        """
        x13 = feat24_row[_FEAT_COLS]
        kp = kimchi_premium if kimchi_premium is not None else 0.0
        fng_ext = calc_fng_extreme(fetch_fng())
        nasdaq = fetch_nasdaq_return()
        nasdaq_val = nasdaq if nasdaq is not None else 0.0
        values = list(x13) + [kp, fng_ext, nasdaq_val]
        return {name: float(val) for name, val in zip(_ONLINE_FEAT_NAMES, values)}

    def train(self, df, kimchi_premium=None):
        """초기 warm-up: 과거 데이터 순차 주입 (시간순)"""
        if self._training: return
        self._training = True
        try:
            self.model = self._init_new_model()
            feat24 = build_features_24(df)
            closes = feat24[:, 3]

            n_trained = 0
            for i in range(len(closes) - LABEL_FUTURE_BARS):
                ret = (closes[i + LABEL_FUTURE_BARS] - closes[i]) / closes[i]
                if ret > LABEL_UP_THRESH:
                    y = 1
                elif ret < LABEL_DOWN_THRESH:
                    y = 0
                else:
                    continue
                x_dict = self._features_to_dict(feat24[i], kimchi_premium)
                self.model.learn_one(x_dict, y)
                n_trained += 1

            if n_trained < LABEL_MIN_SAMPLES:
                logger.info(f"Online warm-up insufficient: {n_trained}")
                self.model = None
                return

            self.trained = True
            self.train_dt = datetime.now(KST)
            self.n_learned = n_trained
            # 초기엔 Precision 측정 없음. 실전 누적 시 get_shadow_stats에서 산출.

            import joblib
            joblib.dump(self.model, ONLINE_PATH)
            self._save_meta()
            logger.info(f"Online warm-up done: n={n_trained}")
        except Exception as e:
            logger.error(f"Online train err: {e}", exc_info=True)
        finally:
            self._training = False

    def predict(self, feat24_last, kimchi_premium=None):
        if not self.trained or self.model is None: return None
        try:
            if feat24_last.ndim == 2:
                feat24_last = feat24_last[-1]
            x_dict = self._features_to_dict(feat24_last, kimchi_premium)
            proba = self.model.predict_proba_one(x_dict)
            return float(proba.get(1, 0.5))
        except Exception as e:
            logger.debug(f"Online predict err: {e}")
            return None

    def learn_one_with_result(self, feat24_row, y, kimchi_premium=None):
        """actual_result 확정 시 호출 — 증분 학습 (매매 후 결과 반영)"""
        if self.model is None: return
        try:
            x_dict = self._features_to_dict(feat24_row, kimchi_premium)
            self.model.learn_one(x_dict, int(y))
            self.n_learned += 1
            # 100회마다 저장 (I/O 절감)
            if self.n_learned % 100 == 0:
                import joblib
                joblib.dump(self.model, ONLINE_PATH)
                self._save_meta()
        except Exception as e:
            logger.debug(f"Online learn err: {e}")

    def _save_meta(self):
        try:
            meta = {"train_dt": self.train_dt.isoformat() if self.train_dt else None,
                    "precision": self.precision, "recall": self.recall,
                    "profit_factor": self.profit_factor, "accuracy": self.accuracy,
                    "n_learned": self.n_learned}
            with open(os.path.join(MODELS_DIR, "online_meta.json"), "w") as f:
                json.dump(meta, f, indent=2)
        except Exception: pass


# ═══════════════════════════════════════════════════��══════
# 예측 기록 / 역산
# ══════════════════════════════════════════════════════════
PRED_COLUMNS = [
    "datetime", "price",
    "xgb_prob", "rf_prob", "online_prob",
    "ensemble_xgb_rf", "ensemble_all",
    "xgb_version", "rf_version", "online_version",
    "regime",
    # market state (#67)
    "rsi14", "adx", "atr_pct",
    # operation flow (#67)
    "xgb_gate_pass", "rule_score", "rule_score_pass",
    "e2_blocked", "would_enter",
    # outcomes (multi-layered, #67)
    "actual_result", "actual_return",
    "mfe_8bar", "mae_8bar",
    "actual_return_16bar",
    # #79 Main PF 측정 비교
    "main_pf_holdout", "main_pf_oos_100",
    # #80 Shadow XGB TB3
    "shadow_xgb_tb3_prob", "shadow_xgb_tb3_label", "shadow_xgb_tb3_version",
    # #81 통합 시그널
    "main_signal", "shadow_xgb_tb3_signal",
    # #81 사후 결과 horizon별
    "ret_4bar", "ret_8bar", "ret_16bar",
]


def _ensure_columns(df):
    """기존 CSV에 새 컬럼이 없으면 추가."""
    for col in PRED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[PRED_COLUMNS]


def log_shadow_prediction(dt_str, price, xgb_prob, rf_prob, online_prob,
                          xgb_version, rf_version, online_version,
                          regime=None,
                          rsi14=None, adx=None, atr_pct=None,
                          xgb_gate_pass=None, rule_score=None,
                          rule_score_pass=None, e2_blocked=None,
                          would_enter=None,
                          main_pf_holdout=None, main_pf_oos_100=None,
                          shadow_xgb_tb3_prob=None, shadow_xgb_tb3_version=None,
                          main_signal=None, shadow_xgb_tb3_signal=None):
    try:
        ens_xr = ((xgb_prob + rf_prob) / 2
                  if xgb_prob is not None and rf_prob is not None else None)
        probs = [p for p in [xgb_prob, rf_prob, online_prob] if p is not None]
        ens_all = sum(probs) / len(probs) if len(probs) >= 2 else None

        row = {
            "datetime": dt_str, "price": price,
            "xgb_prob": round(xgb_prob, 4) if xgb_prob is not None else None,
            "rf_prob": round(rf_prob, 4) if rf_prob is not None else None,
            "online_prob": round(online_prob, 4) if online_prob is not None else None,
            "ensemble_xgb_rf": round(ens_xr, 4) if ens_xr is not None else None,
            "ensemble_all": round(ens_all, 4) if ens_all is not None else None,
            "xgb_version": xgb_version, "rf_version": rf_version,
            "online_version": online_version,
            "regime": regime,
            "rsi14": round(rsi14, 2) if rsi14 is not None else None,
            "adx": round(adx, 2) if adx is not None else None,
            "atr_pct": round(atr_pct, 2) if atr_pct is not None else None,
            "xgb_gate_pass": bool(xgb_gate_pass) if xgb_gate_pass is not None else None,
            "rule_score": round(rule_score, 2) if rule_score is not None else None,
            "rule_score_pass": bool(rule_score_pass) if rule_score_pass is not None else None,
            "e2_blocked": bool(e2_blocked) if e2_blocked is not None else None,
            "would_enter": bool(would_enter) if would_enter is not None else None,
            "actual_result": None, "actual_return": None,
            "mfe_8bar": None, "mae_8bar": None,
            "actual_return_16bar": None,
            # #79
            "main_pf_holdout": round(main_pf_holdout, 4) if main_pf_holdout is not None else None,
            "main_pf_oos_100": round(main_pf_oos_100, 4) if main_pf_oos_100 is not None else None,
            # #80
            "shadow_xgb_tb3_prob": round(shadow_xgb_tb3_prob, 4) if shadow_xgb_tb3_prob is not None else None,
            "shadow_xgb_tb3_label": None,
            "shadow_xgb_tb3_version": shadow_xgb_tb3_version,
            # #81
            "main_signal": main_signal,
            "shadow_xgb_tb3_signal": shadow_xgb_tb3_signal,
            "ret_4bar": None, "ret_8bar": None, "ret_16bar": None,
        }
        if os.path.exists(PREDICTIONS_CSV) and os.path.getsize(PREDICTIONS_CSV) > 0:
            df = pd.read_csv(PREDICTIONS_CSV)
            df = _ensure_columns(df)
        else:
            df = pd.DataFrame(columns=PRED_COLUMNS)
        if len(df) > 0 and str(df["datetime"].iloc[-1]) == str(dt_str):
            return
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(PREDICTIONS_CSV, index=False)
    except Exception as e:
        logger.debug(f"pred log err: {e}")


def _lookup_ohlcv_window(df4h, dt_str, n_bars):
    """df4h에서 dt_str에 해당하는 캔들 이후 n_bars개 캔들의 high/low/close를 반환.
    (n_bars개에 미치지 못하면 None)"""
    if df4h is None or len(df4h) == 0: return None
    try:
        target_dt = pd.to_datetime(dt_str)
        # df4h.index가 timezone-aware면 naive로 통일
        if df4h.index.tz is not None:
            idx = df4h.index.tz_localize(None)
        else:
            idx = df4h.index
        # 정확 매칭 (4H 캔들 시작시각)
        matches = np.where(idx == target_dt)[0]
        if len(matches) == 0: return None
        i = int(matches[0])
        end = i + n_bars
        if end >= len(df4h): return None
        # i+1 ~ i+n_bars (다음 n_bars 캔들)
        sub = df4h.iloc[i+1:end+1]
        return {
            "high": float(sub["high"].max()),
            "low": float(sub["low"].min()),
            "close_at_n": float(sub["close"].iloc[-1]),
        }
    except Exception:
        return None


def update_actual_results(current_price, online_model=None, df4h=None, kp=None):
    """actual_result 확정 시 Online 모델에 learn_one 호출.

    online_model: OnlineLearningShadow 인스턴스 (선택)
    df4h: 피처 재계산용 최근 OHLCV (선택)
    kp: 김치 프리미엄 (선택)

    #67: mfe_8bar, mae_8bar, actual_return_16bar도 함께 채움.
    """
    try:
        if not os.path.exists(PREDICTIONS_CSV): return
        df = pd.read_csv(PREDICTIONS_CSV)
        df = _ensure_columns(df)
        if len(df) < LABEL_FUTURE_BARS + 1: return

        # Online 학습용 피처 재계산 (있으면)
        feat24 = None
        if online_model is not None and df4h is not None:
            try:
                feat24 = build_features_24(df4h)
            except Exception:
                feat24 = None

        updated = False
        learned = 0
        for idx in range(len(df)):
            entry_price = df.at[idx, "price"]
            if entry_price is None or pd.isna(entry_price) or entry_price <= 0:
                continue
            dt_str = df.at[idx, "datetime"]

            # 8봉 actual_result/return
            if pd.isna(df.at[idx, "actual_result"]):
                target_idx = idx + LABEL_FUTURE_BARS
                if target_idx < len(df):
                    future_price = df.at[target_idx, "price"]
                    if pd.notna(future_price) and future_price > 0:
                        ret = (future_price - entry_price) / entry_price
                        df.at[idx, "actual_return"] = round(ret * 100, 4)
                        y = 1 if ret >= LABEL_UP_THRESH else 0
                        df.at[idx, "actual_result"] = y
                        updated = True

                        # Online 증분 학습
                        if online_model is not None and feat24 is not None:
                            offset_from_end = len(df) - idx - 1
                            feat_idx = len(feat24) - 1 - offset_from_end
                            if 0 <= feat_idx < len(feat24):
                                online_model.learn_one_with_result(feat24[feat_idx], y, kp)
                                learned += 1

            # 8봉 mfe/mae (high/low 데이터 필요)
            if pd.isna(df.at[idx, "mfe_8bar"]) and df4h is not None:
                w = _lookup_ohlcv_window(df4h, dt_str, LABEL_FUTURE_BARS)
                if w is not None:
                    df.at[idx, "mfe_8bar"] = round((w["high"] - entry_price) / entry_price * 100, 4)
                    df.at[idx, "mae_8bar"] = round((w["low"] - entry_price) / entry_price * 100, 4)
                    updated = True

            # 16봉 return
            if pd.isna(df.at[idx, "actual_return_16bar"]) and df4h is not None:
                w16 = _lookup_ohlcv_window(df4h, dt_str, 16)
                if w16 is not None:
                    df.at[idx, "actual_return_16bar"] = round(
                        (w16["close_at_n"] - entry_price) / entry_price * 100, 4)
                    updated = True

            # #81 horizon별 ret_4bar / ret_8bar / ret_16bar (price 컬럼 기반)
            for horizon, col in [(4, "ret_4bar"), (8, "ret_8bar"), (16, "ret_16bar")]:
                if pd.isna(df.at[idx, col]):
                    t_idx = idx + horizon
                    if t_idx < len(df):
                        fp = df.at[t_idx, "price"]
                        if pd.notna(fp) and fp > 0:
                            df.at[idx, col] = round((fp - entry_price) / entry_price * 100, 4)
                            updated = True

            # #80 TB3 label 사후 채움 (TB_TIME_LIMIT 봉 내 ±2%/-1% 도달 또는 16봉 후)
            if "shadow_xgb_tb3_label" in df.columns and pd.isna(df.at[idx, "shadow_xgb_tb3_label"]):
                if idx + TB_TIME_LIMIT < len(df):
                    # 향후 16봉 가격 시리즈 (price 컬럼 사용)
                    fp_seq = df.loc[idx:idx+TB_TIME_LIMIT, "price"].values
                    if not pd.isna(fp_seq).any():
                        try:
                            lbl = label_tb3(fp_seq.astype(float), 0)
                            if lbl is not None:
                                df.at[idx, "shadow_xgb_tb3_label"] = int(lbl)
                                updated = True
                        except Exception: pass

        if updated:
            df.to_csv(PREDICTIONS_CSV, index=False)
        if learned > 0:
            logger.info(f"Online learn_one: {learned} samples")
    except Exception as e:
        logger.debug(f"actual result err: {e}")


def get_shadow_stats():
    stats = {"xgb":    {"prec": None, "pf": None, "n": 0},
             "rf":     {"prec": None, "pf": None, "n": 0},
             "online": {"prec": None, "pf": None, "n": 0},
             "shadow_xgb_tb3": {"prec": None, "pf": None, "n": 0}}
    try:
        if not os.path.exists(PREDICTIONS_CSV): return stats
        df = pd.read_csv(PREDICTIONS_CSV)
        ev = df[df["actual_result"].notna()].copy()
        if len(ev) == 0: return stats
        for key, pc, vc in [("xgb","xgb_prob","xgb_version"),
                            ("rf","rf_prob","rf_version"),
                            ("online","online_prob","online_version")]:
            sub = ev[ev[pc].notna() & ev[vc].notna()].copy()
            if len(sub) == 0: continue
            try:
                sub["_ver_dt"] = pd.to_datetime(sub[vc])
                sub["_pred_dt"] = pd.to_datetime(sub["datetime"])
                sub = sub[sub["_pred_dt"] > sub["_ver_dt"]]
            except Exception: pass
            if len(sub) == 0: continue
            preds = (sub[pc] > 0.5).astype(int).values
            actual = sub["actual_result"].values.astype(int)
            returns = sub["actual_return"].values.astype(float)
            tp = int(((preds == 1) & (actual == 1)).sum())
            fp = int(((preds == 1) & (actual == 0)).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else None
            pred_mask = preds == 1
            if pred_mask.any():
                gains = returns[pred_mask & (actual == 1)].sum()
                loss_v = abs(returns[pred_mask & (actual == 0)].sum())
                pf = gains / loss_v if loss_v > 0 else (gains if gains > 0 else 0.0)
            else:
                pf = None
            stats[key] = {"prec": prec, "pf": pf, "n": int(pred_mask.sum())}

        # #80 Shadow XGB TB3 — TB3 라벨 기준 Prec + ret_8bar 기반 PF
        if "shadow_xgb_tb3_prob" in df.columns and "shadow_xgb_tb3_label" in df.columns:
            sub = df[df["shadow_xgb_tb3_prob"].notna() & df["shadow_xgb_tb3_label"].notna()].copy()
            if len(sub) > 0:
                preds = (sub["shadow_xgb_tb3_prob"] > 0.5).astype(int).values
                actual = sub["shadow_xgb_tb3_label"].values.astype(int)
                tp = int(((preds == 1) & (actual == 1)).sum())
                fp = int(((preds == 1) & (actual == 0)).sum())
                prec = tp / (tp + fp) if (tp + fp) > 0 else None
                pred_mask = preds == 1
                pf = None
                if pred_mask.any() and "ret_8bar" in sub.columns:
                    rets = sub["ret_8bar"].values.astype(float)
                    valid = ~np.isnan(rets)
                    rets_pred = rets[pred_mask & valid]
                    if len(rets_pred) > 0:
                        g = rets_pred[rets_pred > 0].sum()
                        l = abs(rets_pred[rets_pred <= 0].sum())
                        pf = float(g / l) if l > 0 else (float(g) if g > 0 else 0.0)
                stats["shadow_xgb_tb3"] = {"prec": prec, "pf": pf,
                                            "n": int(pred_mask.sum())}
    except Exception as e:
        logger.debug(f"stats err: {e}")
    return stats


def dt_to_str(dt):
    if dt is None: return None
    return dt.isoformat()
