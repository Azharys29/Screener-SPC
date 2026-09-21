#!/usr/bin/env python3
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE_PATH=os.path.join(ROOT,"universe.csv")
OUTPUT_PATH=os.path.join(ROOT,"data","screener.json")
OUTPUT_BARS=300
BENCHMARK="^JKSE"

def read_universe():
    rows=[]
    with open(UNIVERSE_PATH,"r",encoding="utf-8-sig") as f:
        for line in f:
            line=line.strip()
            if line and not line.startswith("#"): rows.append(line)
    if not rows: raise RuntimeError("universe.csv kosong")
    header=[x.strip() for x in rows[0].split(",")]
    need={"ticker","name","sector","indices","board"}
    if not need.issubset(header): raise RuntimeError(f"Kolom kurang: {sorted(need-set(header))}")
    out=[]
    for line in rows[1:]:
        p=[x.strip() for x in line.split(",")]
        p += [""]*max(0,len(header)-len(p))
        d=dict(zip(header,p)); t=d.get("ticker","").upper().strip()
        if t:
            out.append({"ticker":t,"name":d.get("name","").strip(),"sector":d.get("sector","").strip(),
                        "indices":[x.strip().upper() for x in d.get("indices","").split("|") if x.strip()],"board":d.get("board","").strip()})
    return out

def get_close(frame,ticker):
    if isinstance(frame.columns,pd.MultiIndex):
        if ticker in frame.columns.get_level_values(0): frame=frame[ticker]
        elif ticker in frame.columns.get_level_values(-1): frame=frame.xs(ticker,axis=1,level=-1)
    return frame["Close"] if isinstance(frame,pd.DataFrame) else frame

def beta(stock,bench):
    a=pd.to_numeric(stock,errors="coerce").pct_change()
    b=pd.to_numeric(bench,errors="coerce").pct_change()
    x=pd.concat([a,b],axis=1).dropna().tail(252)
    if len(x)<60: return None
    var=float(x.iloc[:,1].var())
    if not math.isfinite(var) or var<=0: return None
    v=float(x.iloc[:,0].cov(x.iloc[:,1]))/var
    return round(v,4) if math.isfinite(v) else None

def mcap(symbol):
    try:
        v=yf.Ticker(symbol).fast_info.get("market_cap")
        if v is not None and math.isfinite(float(v)): return float(v)
    except Exception: pass
    try:
        v=yf.Ticker(symbol).get_info().get("marketCap")
        if v is not None and math.isfinite(float(v)): return float(v)
    except Exception: pass
    return None

def main():
    universe=read_universe()
    symbols=[f"{x['ticker']}.JK" for x in universe]
    benchdf=yf.download(BENCHMARK,period="2y",interval="1d",auto_adjust=False,progress=False,threads=False)
    if benchdf.empty: raise RuntimeError("Data IHSG tidak tersedia")
    bench=get_close(benchdf,BENCHMARK).dropna()
    data=yf.download(symbols,period="2y",interval="1d",auto_adjust=False,progress=False,threads=True,group_by="ticker")
    stocks=[]; skipped=[]
    for i,meta in enumerate(universe,1):
        symbol=f"{meta['ticker']}.JK"
        try:
            frame=data[symbol] if isinstance(data.columns,pd.MultiIndex) and symbol in data.columns.get_level_values(0) else data
            needed=["Open","High","Low","Close","Volume"]
            if not all(c in frame.columns for c in needed): raise ValueError("OHLCV tidak lengkap")
            frame=frame[needed].dropna(subset=["Close"]).tail(OUTPUT_BARS)
            if len(frame)<120: raise ValueError(f"data hanya {len(frame)} bar")
            stocks.append({
                "t":meta["ticker"],"n":meta["name"],"s":meta["sector"],"ix":meta["indices"],"board":meta["board"],
                "mc":mcap(symbol),"b":beta(frame["Close"],bench),
                "d":[x.strftime("%Y-%m-%d") for x in frame.index],
                "o":pd.to_numeric(frame["Open"],errors="coerce").round(4).tolist(),
                "h":pd.to_numeric(frame["High"],errors="coerce").round(4).tolist(),
                "l":pd.to_numeric(frame["Low"],errors="coerce").round(4).tolist(),
                "c":pd.to_numeric(frame["Close"],errors="coerce").round(4).tolist(),
                "v":pd.to_numeric(frame["Volume"],errors="coerce").fillna(0).round().astype(np.int64).tolist()
            })
            print(f"[{i}/{len(universe)}] {meta['ticker']}: OK")
        except Exception as e:
            skipped.append({"ticker":meta["ticker"],"reason":str(e)})
            print(f"[{i}/{len(universe)}] {meta['ticker']}: SKIP — {e}")
    if not stocks: raise RuntimeError("Tidak ada saham yang berhasil diambil")
    asof=max(s["d"][-1] for s in stocks)
    payload={"asof":asof,"generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
             "source":"Yahoo Finance via yfinance","benchmark":BENCHMARK,"bars":OUTPUT_BARS,
             "stocks":stocks,"skipped":skipped}
    os.makedirs(os.path.dirname(OUTPUT_PATH),exist_ok=True)
    with open(OUTPUT_PATH,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,separators=(",",":"))
    print(f"Selesai: {OUTPUT_PATH}; stocks={len(stocks)} skipped={len(skipped)} asof={asof}")

if __name__=="__main__": main()
