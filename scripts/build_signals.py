#!/usr/bin/env python3
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "screener.json")
SIGNALS_PATH = os.path.join(ROOT, "data", "signals.json")
HISTORY_PATH = os.path.join(ROOT, "data", "signal-history.json")

P = {"rsi": 14, "sk": 14, "ss": 3, "sd": 3, "mf": 12, "ms": 26, "mg": 9, "vn": 20, "fw": 3}
W = {"stoch": 25, "macd": 30, "rsi": 25, "vol": 20}

def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)

def ema(values, period):
    if len(values) < period:
        return [float("nan")] * len(values)
    out = [float("nan")] * len(values)
    e = sum(values[:period]) / period
    out[period - 1] = e
    a = 2.0 / (period + 1)
    for i in range(period, len(values)):
        e = a * values[i] + (1 - a) * e
        out[i] = e
    return out

def rsi(values, period):
    n = len(values)
    out = [float("nan")] * n
    if n <= period:
        return out
    gain = loss = 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        if d > 0: gain += d
        else: loss -= d
    avg_gain, avg_loss = gain / period, loss / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, n):
        d = values[i] - values[i - 1]
        g, l = max(d, 0.0), max(-d, 0.0)
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out

def sma(values, period):
    out = [float("nan")] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if all(finite(x) for x in window):
            out[i] = sum(window) / period
    return out

def stochastic(high, low, close, k_period, k_smooth, d_smooth):
    raw = [float("nan")] * len(close)
    for i in range(k_period - 1, len(close)):
        lo = min(low[i-k_period+1:i+1])
        hi = max(high[i-k_period+1:i+1])
        raw[i] = 50.0 if hi == lo else (close[i] - lo) / (hi - lo) * 100
    k = sma(raw, k_smooth)
    d = sma(k, d_smooth)
    return k, d

def last_cross(k, d, window):
    diff = [a-b if finite(a) and finite(b) else float("nan") for a,b in zip(k,d)]
    n = len(diff)
    for ago in range(window):
        i = n - 1 - ago
        if i < 1 or not finite(diff[i]) or not finite(diff[i-1]):
            break
        if diff[i-1] <= 0 and diff[i] > 0:
            return 1, ago
        if diff[i-1] >= 0 and diff[i] < 0:
            return -1, ago
    return None

def last_cross_series(values, window):
    n = len(values)
    for ago in range(window):
        i = n - 1 - ago
        if i < 1 or not finite(values[i]) or not finite(values[i-1]):
            break
        if values[i-1] <= 0 and values[i] > 0:
            return 1, ago
        if values[i-1] >= 0 and values[i] < 0:
            return -1, ago
    return None

def clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))

def analyze(s):
    c, h, l, v = s["c"], s["h"], s["l"], s["v"]
    n = len(c)
    need = max(P["ms"] + P["mg"], P["rsi"] + 2, P["sk"] + P["ss"] + P["sd"], P["vn"] + 1, 55) + 3
    if n < need:
        return None
    ra = rsi(c, P["rsi"])
    k, d = stochastic(h, l, c, P["sk"], P["ss"], P["sd"])
    fast, slow = ema(c, P["mf"]), ema(c, P["ms"])
    mac_line = [a-b if finite(a) and finite(b) else float("nan") for a,b in zip(fast,slow)]
    sig = ema(mac_line, P["mg"])
    hist = [a-b if finite(a) and finite(b) else float("nan") for a,b in zip(mac_line,sig)]
    i = n-1
    vals = [ra[i], ra[i-1], k[i], d[i], hist[i], hist[i-1]]
    if not all(finite(x) for x in vals):
        return None
    price = c[i]
    chg = (c[i]/c[i-1]-1)*100 if c[i-1] else 0
    rvol = None
    base = v[i-P["vn"]:i]
    if len(base) == P["vn"] and sum(base) > 0:
        rvol = v[i] / (sum(base)/P["vn"])

    orient = 1
    rz = clamp((50-ra[i])/20) * orient
    rs = 1 if ra[i] > ra[i-1] else -1 if ra[i] < ra[i-1] else 0
    rsi_s = clamp(0.7*rz + 0.3*rs)

    xs = last_cross(k, d, P["fw"])
    sz = clamp((50-k[i])/30) * orient * 0.5
    sp = 0.25 if k[i] > d[i] else -0.25
    sx = xs[0]*0.25 if xs else 0
    stoch_s = clamp(sz + sp + sx)

    xm = last_cross_series(hist, P["fw"])
    md = 1 if hist[i] > 0 else -1
    msl = 1 if hist[i] > hist[i-1] else -1 if hist[i] < hist[i-1] else 0
    macd_s = clamp(0.4*md + 0.2*msl + (0.4*xm[0] if xm else 0))

    pdir = 1 if chg > 0 else -1 if chg < 0 else 0
    vol_s = 0 if rvol is None or rvol < 1 else pdir*clamp(rvol-1)

    comps = [(rsi_s,W["rsi"]),(stoch_s,W["stoch"]),(macd_s,W["macd"]),(vol_s,W["vol"])]
    sw = sum(w for _,w in comps)
    score = sum(s*w for s,w in comps)/sw*100 if sw else 0
    direction = "Bullish" if score >= 15 else "Bearish" if score <= -15 else "Neutral"
    strength = "Sangat kuat" if abs(score) >= 60 else "Kuat" if abs(score) >= 35 else "Moderat" if abs(score) >= 15 else "Netral"
    sign = 1 if score >= 0 else -1
    agree = sum(1 for s,_ in comps if s*sign >= 0.2)
    return {
        "price": round(price,4), "change_pct": round(chg,4),
        "rsi": round(ra[i],2), "stoch_k": round(k[i],2), "stoch_d": round(d[i],2),
        "macd_hist_pct": round(hist[i]/price*100,4) if price else None,
        "volume_ratio": round(rvol,3) if rvol is not None else None,
        "score": round(score,2), "signal": direction, "strength": strength,
        "agree": agree, "total": len(comps),
        "stoch_cross": {"direction": xs[0], "ago": xs[1]} if xs else None,
        "macd_cross": {"direction": xm[0], "ago": xm[1]} if xm else None
    }

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def main():
    data = load_json(DATA_PATH, {})
    stocks = data.get("stocks", [])
    if not stocks:
        raise RuntimeError("data/screener.json tidak berisi stocks")

    previous = load_json(SIGNALS_PATH, {}).get("signals", {})
    history_doc = load_json(HISTORY_PATH, {"version":1,"events":[]})
    events = history_doc.get("events", [])
    now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    asof = data.get("asof")
    signals = {}
    new_bullish = []

    for s in stocks:
        a = analyze(s)
        if not a:
            continue
        t = s["t"]
        prev = previous.get(t)
        changed = bool(prev and prev.get("signal") != a["signal"])
        score_delta = round(a["score"] - prev.get("score", a["score"]), 2) if prev else 0
        is_new_bullish = bool(
            prev and a["signal"] == "Bullish" and
            (prev.get("signal") != "Bullish" or score_delta >= 15)
        )
        ai_candidate = bool(is_new_bullish and a["score"] >= 50 and a["agree"] >= 3)
        row = {
            "ticker": t, "name": s.get("n",""), "sector": s.get("s",""),
            "indices": s.get("ix",[]), "board": s.get("board",""),
            "asof": asof, "scanned_at": now, **a,
            "previous_signal": prev.get("signal") if prev else None,
            "previous_score": prev.get("score") if prev else None,
            "score_delta": score_delta,
            "signal_changed": changed,
            "new_bullish": is_new_bullish,
            "ai_candidate": ai_candidate
        }
        signals[t] = row
        if is_new_bullish:
            event = {
                "timestamp": now, "asof": asof, "ticker": t,
                "name": s.get("n",""), "previous_signal": prev.get("signal"),
                "signal": a["signal"], "previous_score": prev.get("score"),
                "score": a["score"], "score_delta": score_delta,
                "new_bullish": True, "ai_candidate": ai_candidate
            }
            events.append(event)
        if ai_candidate:
            new_bullish.append(row)

    # Keep only signal-change events; cap history to avoid unbounded JSON growth.
    events = events[-1000:]
    payload = {
        "version": 1, "generated_at": now, "asof": asof,
        "universe_count": len(stocks), "signals_count": len(signals),
        "new_bullish_count": sum(1 for x in signals.values() if x["new_bullish"]),
        "ai_queue_count": len(new_bullish),
        "ai_queue": new_bullish, "signals": signals
    }
    history = {"version":1, "updated_at":now, "events":events}

    os.makedirs(os.path.dirname(SIGNALS_PATH), exist_ok=True)
    with open(SIGNALS_PATH,"w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,separators=(",",":"))
    with open(HISTORY_PATH,"w",encoding="utf-8") as f:
        json.dump(history,f,ensure_ascii=False,separators=(",",":"))

    print(f"Signals: {len(signals)} | NEW BULLISH: {payload['new_bullish_count']} | AI queue: {len(new_bullish)} | asof={asof}")

if __name__ == "__main__":
    main()
