"""共用分析函式：報酬計算、績效指標、進場特徵。"""
import numpy as np
import pandas as pd

import fcn_engine as E
from build_grid import BASKETS

TRAIN_END = pd.Timestamp("2012-12-31")   # 樣本內 2000-2012 / 樣本外 2013-2026
KEYS = ["tenor", "ko", "ki", "kitype", "strike"]


def features(df_prices: pd.DataFrame) -> pd.DataFrame:
    """每個籃子、每個日期可用的進場特徵（只用當日以前資料，無前視）。"""
    out = []
    spy = df_prices["SPY_c"]
    spy_ma = spy / spy.rolling(200).mean() - 1
    spy_dd = spy / spy.rolling(252, min_periods=60).max() - 1
    for name, tks in BASKETS.items():
        cols = [t + "_c" for t in tks]
        px = df_prices[cols].dropna()
        ma = px / px.rolling(200).mean() - 1
        dd = px / px.rolling(252, min_periods=60).max() - 1
        mom = px / px.shift(126) - 1
        lr = np.log(px).diff()
        v20 = lr.rolling(20).std() * np.sqrt(252)
        v250 = lr.rolling(250).std() * np.sqrt(252)
        f = pd.DataFrame({
            "basket": name,
            "ext": ma.max(1),                 # 最「過熱」那檔 vs 200 日均線
            "belowma": ma.min(1),             # 最弱那檔 vs 200 日均線
            "dd": dd.min(1),                  # 最弱那檔距 52 週高點
            "mom6": mom.min(1),               # 最弱那檔 6 個月報酬
            "volratio": (v20 / v250).mean(1),  # 短期波動 / 長期波動
            "spy_ma": spy_ma.reindex(px.index),
            "spy_dd": spy_dd.reindex(px.index),
        }, index=px.index)
        f.index.name = "date"
        out.append(f.reset_index())
    return pd.concat(out)


def add_returns(g: pd.DataFrame, alpha: float = 1.0, fee: float = 0.01,
                coupon_mult: float = 1.0) -> pd.DataFrame:
    """代入「報價」假設，算每張單的報酬。

    報價月配息 = max(0, c0(alpha) - fee/A) * coupon_mult
      alpha : 券商報價隱含波動 / 進場時歷史波動
      fee   : 券商/通路費（佔本金比例，每張單一次性）
    ret    = 本金回收比例 - 1 + 月配息 * 配息期數
    excess = ret - 同期現金報酬（無風險利率 * 存續年數）
    """
    g = g.copy()
    c = (g[f"c0_{alpha}"] - fee / g[f"A_{alpha}"]).clip(lower=0) * coupon_mult
    g["cpn_pa"] = 12 * c
    g["ret"] = g["princ"] - 1 + c * g["ncoup"]
    g["dur"] = g["end_day"] / 252
    g["excess"] = g["ret"] - g["rf"] * g["dur"]
    g["converted"] = g["princ"] < 1
    g["koed"] = g["end_day"] < g["tenor"] * E.MONTH
    return g


def metrics(x: pd.DataFrame) -> pd.Series:
    x = x.dropna(subset=["ret"])
    if len(x) == 0:
        return pd.Series(dtype=float)
    cap_time = x["dur"].sum()
    ann_ex = x["excess"].sum() / cap_time                 # 每「資金-年」超額報酬
    ann_ret = x["ret"].sum() / cap_time
    q = x["ret"].quantile(0.05)
    cvar = x.loc[x["ret"] <= q, "ret"].mean()
    return pd.Series({
        "n": len(x),
        "cpn_pa": x["cpn_pa"].mean(),
        "ann_ret": ann_ret,
        "ann_excess": ann_ex,
        "win": (x["ret"] > 0).mean(),
        "ko_rate": x["koed"].mean(),
        "loss_rate": (x["ret"] < 0).mean(),
        "conv_rate": x["converted"].mean(),
        "avg_dur_m": x["dur"].mean() * 12,
        "p5": q,
        "cvar5": cvar,
        "worst": x["ret"].min(),
        "mean_ret_note": x["ret"].mean(),
    })
