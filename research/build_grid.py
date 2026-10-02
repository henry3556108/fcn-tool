"""對每個「籃子 × 進場日 × 條款組合」同時算模型公平配息與歷史實現結果。

用法: python build_grid.py [真實資料 -> grid_real.parquet]
"""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

import fcn_engine as E

BASKETS = {
    "NVDA": ["NVDA"],
    "TSM": ["TSM"],
    "NVDA+TSM": ["NVDA", "TSM"],
    "SPY": ["SPY"],
    "ARM": ["ARM"],
    "NVDA+TSM+ARM": ["NVDA", "TSM", "ARM"],
}
STEP = 21          # 每月進場一次
N_PATHS = 2000
MIN_HIST = 250


def load():
    df = pd.read_csv("prices.csv", index_col=0, parse_dates=True)
    return df


def _job(args):
    name, dates, closes, i, seed = args          # closes: (T, n) 到 i+maxD 為止
    n = closes.shape[1]
    lr = np.diff(np.log(closes[: i + 1]), axis=0)
    sig = E.vol_inputs(lr)
    L = E.corr_chol(lr[-120:])
    r = E.rf_at(dates[i])
    px = E.price_entry(sig, L, r, N_PATHS, seed)
    fut = closes[i:] / closes[i]
    Wreal = fut.min(1)
    real = E.realize(Wreal)
    rows = []
    for combo in E.COMBOS:
        t, ko, ki, ty, k = combo
        rr = real[combo]
        row = dict(basket=name, date=dates[i], tenor=t, ko=(np.nan if ko is None else ko),
                   ki=ki, kitype=ty, strike=k, sig=float(sig.mean()), rf=r)
        if rr is None:
            row.update(ncoup=np.nan, princ=np.nan, end_day=np.nan)
        else:
            row.update(ncoup=rr[0], princ=rr[1], end_day=rr[2])
        for a in E.ALPHAS:
            c0, A = px[a][combo]
            row[f"c0_{a}"] = c0
            row[f"A_{a}"] = A
        rows.append(row)
    return rows


def main(out="grid_real.parquet"):
    df = load()
    jobs = []
    for name, tks in BASKETS.items():
        cols = [t + "_c" for t in tks]
        sub = df[cols].dropna()
        if len(sub) < MIN_HIST + 70:
            continue
        closes = sub.values
        dates = sub.index
        for i in range(MIN_HIST, len(sub) - 1, STEP):
            jobs.append((name, dates, closes, i, 1000 + i))
    print(len(jobs), "entries", flush=True)
    with Pool(4) as p:
        res = p.map(_job, jobs, chunksize=4)
    out_df = pd.DataFrame([r for rows in res for r in rows])
    out_df.to_parquet(out)
    print(out_df.shape)


if __name__ == "__main__":
    main(*sys.argv[1:])
