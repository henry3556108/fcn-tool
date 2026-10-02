"""報價檢查器：輸入券商報價，反推「報價隱含的波動度 / 你自己看的歷史波動度」(α)，並對照損益兩平 α。

用法（範例）:
  python quote_check.py --tickers NVDA TSM --tenor 12 --ki 0.65 --kitype E --strike 0.9 --ko none --coupon-pa 0.18 --fee 0.01
資料取自 prices.csv（最後一個交易日當進場日）。ko: none 或 1.0。
"""
import argparse
import numpy as np, pandas as pd
import fcn_engine as E

ap = argparse.ArgumentParser()
ap.add_argument("--tickers", nargs="+", required=True)
ap.add_argument("--tenor", type=int, required=True)
ap.add_argument("--ki", type=float, required=True)
ap.add_argument("--kitype", choices=["A", "E"], required=True)
ap.add_argument("--strike", type=float, required=True)
ap.add_argument("--ko", default="none")
ap.add_argument("--coupon-pa", type=float, required=True, help="券商報價年化配息，例 0.18")
ap.add_argument("--fee", type=float, default=0.01)
ap.add_argument("--paths", type=int, default=20000)
a = ap.parse_args()

df = pd.read_csv("prices.csv", index_col=0, parse_dates=True)[[t + "_c" for t in a.tickers]].dropna()
lr = np.log(df).diff().dropna().values
sig = E.vol_inputs(lr)
L = E.corr_chol(lr[-120:])
r = E.rf_at(df.index[-1])
ko = None if a.ko == "none" else float(a.ko)
print(f"進場日(資料最後一日) {df.index[-1].date()}  進場用歷史波動 {np.round(sig,3)}  無風險利率 {r:.2%}")

def coupon_at(alpha):
    rng = np.random.default_rng(1)
    W = E.mc_worst_paths(sig * alpha, L, r, a.tenor * E.MONTH, a.paths, rng)
    kk, princ, end_day = E.settle(W, a.tenor, ko, a.ki, a.kitype, a.strike)
    pv = np.mean(np.exp(-r * end_day / 252) * princ)
    cd = np.concatenate([[0], np.cumsum(np.exp(-r * E.MONTH * np.arange(1, a.tenor + 1) / 252))])
    A_ = np.mean(cd[kk])
    return 12 * max(0.0, (1 - pv) / A_ - a.fee / A_), 12 * (1 - pv) / A_

lo, hi = 0.3, 2.5
for _ in range(40):
    mid = (lo + hi) / 2
    if coupon_at(mid)[0] < a.coupon_pa: lo = mid
    else: hi = mid
alpha = (lo + hi) / 2
print(f"報價 {a.coupon_pa:.1%}/年 ≈ 模型在『歷史波動 × {alpha:.2f}』下的公平配息(已扣費 {a.fee:.1%})")
print(f"  → 券商等於用 {alpha:.2f}× 的歷史波動在定價")
print(f"  → 損益兩平 α 參考(research/REPORT.md §6)：TSM≈0.85-0.95、NVDA+TSM≈1.0-1.1、NVDA≈1.1-1.2、SPY≈1.2-1.8")
print("  → 你需要『券商 α』明顯高於你對『未來波動/崩盤風險』的看法，才有正期望；否則配息只是在補你承擔的風險。")
