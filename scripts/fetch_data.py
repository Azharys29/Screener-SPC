#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, os, time
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE_PATH=os.path.join(ROOT,"universe.csv")
OUTPUT_PATH=os.path.join(ROOT,"data","screener.json")
OUTPUT_BARS=300
BENCHMARK="^JKSE"
CHUNK_SIZE=40
ALLOWED_BOARDS={"Utama","Pengembangan"}
ALLOWED_INDICES={"IDX30","LQ45","KOMPAS100"}

def read_universe():
    out=[]
    with open(UNIVERSE_PATH,"r",encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(line for line in f if not line.lstrip().startswith("#")):
            t=(row.get("ticker") or "").strip().upper()
            board=(row.get("board") or "").strip()
            indices=[x.strip().upper() for x in (row.get("indices") or "").split("|") if x.strip()]
            if not t or board not in ALLOWED_BOARDS or not set(indices).intersection(ALLOWED_INDICES): continue
            out.append({
                "ticker":t,
                "name":(row.get("name") or "").strip(),
                "sector":(row.get("sector") or "").strip(),
                "indices":indices,
                "board":board
            })
    if not out: raise RuntimeError("universe.csv kosong")
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

def main():
    universe=read_universe()
    symbols=[f"{x['ticker']}.JK" for x in universe]

    benchdf=yf.download(BENCHMARK,period="2y",interval="1d",auto_adjust=False,progress=False,threads=False)
    if benchdf.empty: raise RuntimeError("Data IHSG tidak tersedia")
    bench=get_close(benchdf,BENCHMARK).dropna()

    # Yahoo/yfinance can return empty data or trigger throttling when ~1,000
    # symbols are requested in one call. Download in small sequential chunks.
    frames={}
    for start in range(0,len(symbols),CHUNK_SIZE):
        chunk=symbols[start:start+CHUNK_SIZE]
        print(f"Download batch {start+1}-{start+len(chunk)} / {len(symbols)}")
        try:
            batch=yf.download(chunk,period="2y",interval="1d",auto_adjust=False,
                              progress=False,threads=False,group_by="ticker")
            if not batch.empty:
                if isinstance(batch.columns,pd.MultiIndex):
                    for symbol in chunk:
                        if symbol in batch.columns.get_level_values(0):
                            frames[symbol]=batch[symbol]
                        elif symbol in batch.columns.get_level_values(-1):
                            frames[symbol]=batch.xs(symbol,axis=1,level=-1)
                elif len(chunk)==1:
                    frames[chunk[0]]=batch
        except Exception as e:
            print(f"Batch gagal: {e}")
        if start + CHUNK_SIZE < len(symbols):
            time.sleep(1)

    stocks=[]; skipped=[]
    for i,meta in enumerate(universe,1):
        symbol=f"{meta['ticker']}.JK"
        try:
            frame=frames.get(symbol)
            if frame is None: raise ValueError("data tidak tersedia dari Yahoo")
            needed=["Open","High","Low","Close","Volume"]
            if not all(c in frame.columns for c in needed): raise ValueError("OHLCV tidak lengkap")
            frame=frame[needed].dropna(subset=["Close"]).tail(OUTPUT_BARS)
            if len(frame)<120: raise ValueError(f"data hanya {len(frame)} bar")
            stocks.append({
                "t":meta["ticker"],"n":meta["name"],"s":meta["sector"],"ix":meta["indices"],"board":meta["board"],
                "mc":None,"b":beta(frame["Close"],bench),
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
    with open(OUTPUT_PATH,"w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,separators=(",",":"))
    print(f"Selesai: {OUTPUT_PATH}; stocks={len(stocks)} skipped={len(skipped)} asof={asof}")

if __name__=="__main__": main()
