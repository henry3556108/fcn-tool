"""用「去漂移」價格重算歷史實現結果（定價欄位 c0/A 沿用原網格：波動/相關不受影響）。
ERP = 預期超額報酬(算術)。ERP=0 → 風險中立世界，公平定價下期望損益≈-費用。
"""
import sys
import numpy as np, pandas as pd
import fcn_engine as E
from build_grid import BASKETS, STEP, MIN_HIST

def adjust(df, erp):
    out = df.copy()
    for t in ["NVDA", "TSM", "SPY", "ARM"]:
        c = df[t + "_c"].dropna()
        lr = np.log(c).diff().dropna()
        sig2 = lr.var() * 252
        rf = pd.Series([E.rf_at(d) for d in lr.index], index=lr.index)
        tgt = (rf + erp - 0.5 * sig2) / 252
        new = lr - lr.mean() + tgt.mean() * 0 + tgt          # 去掉樣本均值，換成目標漂移
        px = pd.concat([c.iloc[:1], c.iloc[0] * np.exp(new.cumsum())])
        out[t + "_c"] = px.reindex(df.index)
    return out

def main(erp, out):
    df = pd.read_csv("prices.csv", index_col=0, parse_dates=True)
    adj = adjust(df, erp)
    g = pd.read_parquet("grid_real.parquet")
    rows = []
    for name, tks in BASKETS.items():
        sub = adj[[t + "_c" for t in tks]].dropna()
        closes, dates = sub.values, sub.index
        for i in range(MIN_HIST, len(sub) - 1, STEP):
            Wr = (closes[i:] / closes[i]).min(1)
            real = E.realize(Wr)
            for combo, rr in real.items():
                t, ko, ki, ty, k = combo
                rows.append((name, dates[i], t, np.nan if ko is None else ko, ki, ty, k,
                             *(rr if rr else (np.nan,) * 3)))
    r = pd.DataFrame(rows, columns=["basket","date","tenor","ko","ki","kitype","strike","ncoup","princ","end_day"])
    keep = [c for c in g.columns if c not in ("ncoup","princ","end_day")]
    m = g[keep].merge(r, on=["basket","date","tenor","ko","ki","kitype","strike"], how="left")
    m.to_parquet(out); print(out, m.shape, m.princ.isna().mean())

if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])
