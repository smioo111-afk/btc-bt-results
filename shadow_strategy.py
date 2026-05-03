"""
shadow/shadow_strategy.py — M3 가상 진입/청산 + TP 추가매수 추적 + 텔레그램 리포트
독립 모듈. 봇 코드에 의존하지 않음.
"""
import os, logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("SHADOW")
KST = timezone(timedelta(hours=9))

SHADOW_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SHADOW_DIR, "data")
M3_TRADES_CSV = os.path.join(DATA_DIR, "shadow_m3_trades.csv")
TP_ADDS_CSV   = os.path.join(DATA_DIR, "shadow_tp_adds.csv")

# ── M3 상수 ──────────────────────────────────────────────
M3_FNG_THRESH     = 25
M3_ENTRY_RATIO    = 0.30
M3_ATR_STOP_MULT  = 2.5
M3_ATR_TRAIL_MULT = 3.5
M3_MAX_HOLD_BARS  = 32

# ── TP 추가매수 상수 ──────────────────────────────────────
TP_ADD_RATIO = 0.10


class M3Shadow:
    """FNG<25 + Trend_Down 시 가상 진입 추적."""

    def __init__(self):
        self.open_trade = None
        self._load_open_trade()

    def _load_open_trade(self):
        try:
            if os.path.exists(M3_TRADES_CSV):
                df = pd.read_csv(M3_TRADES_CSV)
                open_trades = df[df["status"] == "open"]
                if len(open_trades) > 0:
                    row = open_trades.iloc[-1]
                    self.open_trade = {
                        "datetime": row["datetime"],
                        "entry_price": float(row["entry_price"]),
                        "fng": int(row["fng"]),
                        "regime": row["regime"],
                        "virtual_size": float(row["virtual_size"]),
                        "stop_loss": float(row["stop_loss"]),
                        "highest_price": float(row.get("highest_price", row["entry_price"])),
                        "hold_bars": int(row.get("hold_bars", 0)),
                    }
                    logger.info(f"M3 open trade restored: {self.open_trade['entry_price']:,.0f}")
        except Exception as e:
            logger.debug(f"M3 restore err: {e}")

    def check_entry(self, fng_value, market_state, price, equity, atr):
        if self.open_trade is not None: return None
        if fng_value is None or fng_value >= M3_FNG_THRESH: return None
        if market_state != "Trend_Down": return None

        stop_loss = price - atr * M3_ATR_STOP_MULT
        entry = {
            "datetime": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
            "entry_price": price, "fng": fng_value,
            "regime": market_state,
            "virtual_size": equity * M3_ENTRY_RATIO,
            "stop_loss": stop_loss,
            "highest_price": price, "hold_bars": 0,
            "status": "open",
            "exit_price": None, "exit_reason": None, "pnl_pct": None,
        }
        self.open_trade = entry
        self._append_trade(entry)
        logger.info(f"M3 virtual entry: {price:,.0f} FNG={fng_value}")
        return entry

    def check_exit(self, price, atr):
        if self.open_trade is None: return None
        self.open_trade["hold_bars"] += 1
        entry_price = self.open_trade["entry_price"]
        if price > self.open_trade["highest_price"]:
            self.open_trade["highest_price"] = price

        reason = None
        if price <= self.open_trade["stop_loss"]:
            reason = "stop_loss"
        trailing_stop = self.open_trade["highest_price"] - atr * M3_ATR_TRAIL_MULT
        if reason is None and price <= trailing_stop and price > entry_price:
            reason = "trailing_stop"
        if reason is None and self.open_trade["hold_bars"] >= M3_MAX_HOLD_BARS:
            reason = "timeout"
        if reason is None: return None

        pnl_pct = (price - entry_price) / entry_price * 100
        exit_info = {
            "entry_price": entry_price,
            "exit_price": price, "exit_reason": reason,
            "pnl_pct": round(pnl_pct, 2),
            "hold_bars": self.open_trade["hold_bars"],
        }
        self._update_trade_exit(exit_info)
        self.open_trade = None
        logger.info(f"M3 virtual exit: {price:,.0f} reason={reason} PnL={pnl_pct:+.2f}%")
        return exit_info

    def get_summary(self):
        try:
            if not os.path.exists(M3_TRADES_CSV):
                return {"count": 0, "avg_pnl": 0, "winrate": 0}
            df = pd.read_csv(M3_TRADES_CSV)
            closed = df[df["status"] == "closed"]
            if len(closed) == 0:
                return {"count": 0, "avg_pnl": 0, "winrate": 0}
            pnls = closed["pnl_pct"].dropna()
            return {
                "count": len(closed),
                "avg_pnl": float(pnls.mean()) if len(pnls) > 0 else 0,
                "winrate": float((pnls > 0).mean()) if len(pnls) > 0 else 0,
            }
        except Exception:
            return {"count": 0, "avg_pnl": 0, "winrate": 0}

    def _append_trade(self, entry):
        try:
            cols = ["datetime", "entry_price", "fng", "regime", "virtual_size",
                    "stop_loss", "highest_price", "hold_bars", "status",
                    "exit_price", "exit_reason", "pnl_pct"]
            if os.path.exists(M3_TRADES_CSV):
                df = pd.read_csv(M3_TRADES_CSV)
            else:
                df = pd.DataFrame(columns=cols)
            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
            df.to_csv(M3_TRADES_CSV, index=False)
        except Exception as e:
            logger.debug(f"M3 write err: {e}")

    def _update_trade_exit(self, exit_info):
        try:
            if not os.path.exists(M3_TRADES_CSV): return
            df = pd.read_csv(M3_TRADES_CSV)
            open_idx = df[df["status"] == "open"].index
            if len(open_idx) == 0: return
            idx = open_idx[-1]
            df.at[idx, "status"] = "closed"
            df.at[idx, "exit_price"] = exit_info["exit_price"]
            df.at[idx, "exit_reason"] = exit_info["exit_reason"]
            df.at[idx, "pnl_pct"] = exit_info["pnl_pct"]
            df.at[idx, "hold_bars"] = exit_info["hold_bars"]
            df.to_csv(M3_TRADES_CSV, index=False)
        except Exception as e:
            logger.debug(f"M3 update err: {e}")


class TPAddShadow:

    def check_tp_add(self, tp_level, price, equity, trade_id):
        if tp_level < 2: return None
        try:
            record = {
                "datetime": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                "trade_id": trade_id, "tp_level": tp_level,
                "price": price, "virtual_add": equity * TP_ADD_RATIO,
                "exit_price": None, "pnl_pct": None,
            }
            cols = ["datetime", "trade_id", "tp_level", "price",
                    "virtual_add", "exit_price", "pnl_pct"]
            if os.path.exists(TP_ADDS_CSV):
                df = pd.read_csv(TP_ADDS_CSV)
            else:
                df = pd.DataFrame(columns=cols)
            dup = df[(df["trade_id"] == trade_id) & (df["tp_level"] == tp_level)]
            if len(dup) > 0: return None
            df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            df.to_csv(TP_ADDS_CSV, index=False)
            logger.info(f"TP{tp_level} virtual add: {price:,.0f}")
            return record
        except Exception as e:
            logger.debug(f"TP add err: {e}")
            return None

    def close_trade(self, trade_id, exit_price):
        try:
            if not os.path.exists(TP_ADDS_CSV): return
            df = pd.read_csv(TP_ADDS_CSV)
            mask = (df["trade_id"] == trade_id) & df["exit_price"].isna()
            for idx in df[mask].index:
                entry_p = df.at[idx, "price"]
                pnl = (exit_price - entry_p) / entry_p * 100
                df.at[idx, "exit_price"] = exit_price
                df.at[idx, "pnl_pct"] = round(pnl, 2)
            df.to_csv(TP_ADDS_CSV, index=False)
        except Exception as e:
            logger.debug(f"TP close err: {e}")

    def get_summary(self):
        try:
            if not os.path.exists(TP_ADDS_CSV):
                return {"count": 0, "avg_pnl": 0}
            df = pd.read_csv(TP_ADDS_CSV)
            closed = df[df["pnl_pct"].notna()]
            if len(closed) == 0:
                return {"count": 0, "avg_pnl": 0}
            return {"count": len(closed), "avg_pnl": float(closed["pnl_pct"].mean())}
        except Exception:
            return {"count": 0, "avg_pnl": 0}


# ══════════════════════════════════════════════════════════
# 텔레그램 리포트 빌더
# ══════════════════════════════════════════════════════════

def build_shadow_report(xgb_prob, rf_prob, online_prob,
                        shadow_stats, m3_status, m3_summary,
                        fng_value, market_state, tp_summary,
                        online_n_learned=0, tb3_prob=None):
    now = datetime.now(KST).strftime("%m/%d %H:%M")
    lines = [f"*Shadow Report v3.0* | {now}", "=" * 28]

    lines.append("*Model Compare* (현재 캔들 확률)")
    xgb_str = f"  Main XGB:   {xgb_prob:.1%}" if xgb_prob is not None else "  Main XGB:   N/A"
    lines.append(f"{xgb_str} (8봉/±1.2%)")
    if tb3_prob is not None:
        diff = tb3_prob - xgb_prob if xgb_prob is not None else 0
        lines.append(f"  Shadow TB3: {tb3_prob:.1%} ({diff:+.1%}) (16봉 +2/-1%)")
    else:
        lines.append("  Shadow TB3: training...")
    if rf_prob is not None:
        diff = rf_prob - xgb_prob if xgb_prob is not None else 0
        lines.append(f"  RF:         {rf_prob:.1%} ({diff:+.1%})")
    else:
        lines.append("  RF:         training...")
    if online_prob is not None:
        diff = online_prob - xgb_prob if xgb_prob is not None else 0
        lines.append(f"  Online:     {online_prob:.1%} ({diff:+.1%}) [n={online_n_learned}]")
    else:
        lines.append("  Online:     training...")
    probs = [p for p in [xgb_prob, tb3_prob, rf_prob, online_prob] if p is not None]
    if len(probs) >= 2:
        lines.append(f"  Ensemble:   {sum(probs)/len(probs):.1%}")

    lines.append("")
    lines.append("*Live OOS PF (post-train)*")
    label_map = [("xgb","Main XGB"), ("shadow_xgb_tb3","Shadow TB3"),
                 ("rf","RF"), ("online","Online")]
    for key, label in label_map:
        s = shadow_stats.get(key, {})
        prec, pf, n = s.get("prec"), s.get("pf"), s.get("n", 0)
        if prec is not None:
            lines.append(f"  {label}: Prec {prec:.1%} | PF {pf:.2f} (n={n})")
        else:
            lines.append(f"  {label}: collecting...")

    lines.append("")
    lines.append("*M3 Signal*")
    fng_str = str(fng_value) if fng_value is not None else "N/A"
    lines.append(f"  FNG: {fng_str} | {market_state}")
    if m3_status == "open":
        lines.append("  >> ACTIVE (virtual position)")
    elif fng_value is not None and fng_value < M3_FNG_THRESH:
        lines.append("  >> TRIGGERED" if market_state == "Trend_Down"
                      else f"  >> FNG<{M3_FNG_THRESH} but not TD")
    else:
        lines.append(f"  >> Inactive (FNG>={M3_FNG_THRESH})")
    mc = m3_summary.get("count", 0)
    if mc > 0:
        lines.append(f"  Trades: {mc} | Avg: {m3_summary['avg_pnl']:+.2f}%"
                      f" | WR: {m3_summary['winrate']:.0%}")
    else:
        lines.append("  Trades: 0 (waiting)")

    lines.append("")
    lines.append("*TP Add Shadow*")
    tc = tp_summary.get("count", 0)
    if tc > 0:
        lines.append(f"  Closed: {tc} | Avg: {tp_summary['avg_pnl']:+.2f}%")
    else:
        lines.append("  No TP2+ adds yet")

    return "\n".join(lines)


def build_m3_entry_msg(entry):
    return (
        f"*M3 Virtual Entry!*\n"
        f"{entry['datetime']} KST\n"
        f"FNG: {entry['fng']} (extreme fear)\n"
        f"Regime: {entry['regime']}\n"
        f"Entry: {entry['entry_price']:,.0f}\n"
        f"SL: {entry['stop_loss']:,.0f}\n"
        f"Size: 30% (P0)\n"
        f"{'=' * 28}\n"
        f"No real trade")


def build_m3_exit_msg(exit_info, m3_summary):
    mc = m3_summary.get("count", 0)
    return (
        f"*M3 Virtual Exit*\n"
        f"Entry: {exit_info['entry_price']:,.0f} -> Exit: {exit_info['exit_price']:,.0f}\n"
        f"PnL: {exit_info['pnl_pct']:+.2f}%\n"
        f"Reason: {exit_info['exit_reason']}\n"
        f"Hold: {exit_info['hold_bars']} bars\n"
        f"Cumul: {mc} trades | Avg: {m3_summary['avg_pnl']:+.2f}%"
        f" | WR: {m3_summary['winrate']:.0%}\n"
        f"{'=' * 28}\n"
        f"Eval: {'5+ trades needed' if mc < 5 else 'Ready for review'}")
