"""FCN 回測引擎

做兩件事（兩者共用同一套條款結算規則 `settle`）：
  1. 模型定價：用「進場日當下已知的資訊」(波動率、相關性) 以風險中立蒙地卡羅算出
     這張 FCN 的公平月配息 c0 與年金係數 A（實際收到的配息 = c0 - fee/A）。
  2. 歷史實現：把同一組條款套到「進場日之後真實發生的價格路徑」，記錄
     配息期數、期末本金回收比例、存續天數。
實際報酬 = 本金回收比例 - 1 + 月配息 * 配息期數。
配息水準因此可事後任意代入（模型公平價 / 打折 / 券商實際報價），不必重跑。

所有條款以「期初價 = 1」標準化，籃子取 worst-of：
  W_t = min_i S_i,t / S_i,0
KO / KI / 轉股只依賴 W_t（籃子中最差的那檔），所以一條 W 路徑就夠結算。
"""
from __future__ import annotations

import itertools
import numpy as np
import pandas as pd

MONTH = 21                      # 一個月 = 21 個交易日
TENORS = (3, 6, 12)             # 月
KOS = (1.0, None)               # 提前贖回價（None = 無 KO）
KIS = (0.55, 0.60, 0.65, 0.70, 0.75)
STRIKES = (1.0, 0.90, 0.80)
KITYPES = ("A", "E")            # A = 美式(每日收盤觀察) / E = 歐式(僅到期日)
ALPHAS = (0.9, 1.0, 1.1, 1.2, 1.3)  # 報價隱含波動 / 進場時歷史波動

COMBOS = [
    (t, ko, ki, ty, k)
    for t in TENORS for ko in KOS for ki in KIS for ty in KITYPES for k in STRIKES
    if ki < k
]

# 美國 3M 國庫券年均殖利率（近似值，供折現/現金基準使用）
RF = {
    2000: 5.8, 2001: 3.4, 2002: 1.6, 2003: 1.0, 2004: 1.4, 2005: 3.2, 2006: 4.7,
    2007: 4.4, 2008: 1.4, 2009: 0.15, 2010: 0.14, 2011: 0.05, 2012: 0.09,
    2013: 0.06, 2014: 0.03, 2015: 0.05, 2016: 0.32, 2017: 0.93, 2018: 1.94,
    2019: 2.06, 2020: 0.37, 2021: 0.04, 2022: 2.0, 2023: 5.1, 2024: 5.0,
    2025: 4.2, 2026: 3.7,
}


def rf_at(ts: pd.Timestamp) -> float:
    return RF.get(ts.year, 3.7) / 100.0


def settle(W: np.ndarray, tenor: int, ko, ki: float, kitype: str, strike: float):
    """W: (P, >=D+1) 的 worst-of 標準化路徑 (W[:,0]=1)。回傳 (ncoup, princ, end_day)，皆為 (P,)。"""
    D = tenor * MONTH
    obs = W[:, MONTH:D + 1:MONTH]                      # (P, tenor) 月度觀察日
    P = W.shape[0]
    if ko is None:
        koed = np.zeros(P, bool)
        kk = np.full(P, tenor)
    else:
        hit = obs >= ko
        koed = hit.any(1)
        kk = np.where(koed, hit.argmax(1) + 1, tenor)
    if kitype == "A":
        breach = W[:, 1:D + 1].min(1) <= ki
    else:
        breach = W[:, D] <= ki
    wT = W[:, D]
    conv = (~koed) & breach & (wT < strike)
    princ = np.where(conv, wT / strike, 1.0)
    end_day = np.where(koed, kk * MONTH, D)
    return kk, princ, end_day


def corr_chol(rets: np.ndarray) -> np.ndarray:
    n = rets.shape[1]
    if n == 1:
        return np.ones((1, 1))
    C = np.corrcoef(rets, rowvar=False)
    C = 0.9 * C + 0.1 * np.eye(n)                      # 輕微收縮，保證正定
    return np.linalg.cholesky(C)


def mc_worst_paths(sig: np.ndarray, L: np.ndarray, r: float, days: int,
                   n_paths: int, rng: np.random.Generator) -> np.ndarray:
    """風險中立 GBM（單一波動率、無跳躍、無股息）產生 worst-of 路徑 (n_paths, days+1)。"""
    n = len(sig)
    half = n_paths // 2
    Z = rng.standard_normal((half, days, n)) @ L.T
    Z = np.concatenate([Z, -Z], 0)                     # 對偶變異數降低雜訊
    dt = 1 / 252
    inc = (r - 0.5 * sig ** 2) * dt + sig * np.sqrt(dt) * Z   # (P, days, n)
    X = np.concatenate([np.zeros((Z.shape[0], 1, n)), np.cumsum(inc, 1)], 1)
    return np.exp(X).min(2)


def price_entry(sig: np.ndarray, L: np.ndarray, r: float, n_paths: int, seed: int):
    """回傳 dict[alpha] -> dict[combo] -> (c0, A)。c0 = 公平月配息(未扣費)，A = 年金係數。"""
    out = {}
    maxD = max(TENORS) * MONTH
    for a in ALPHAS:
        rng = np.random.default_rng(seed)
        W = mc_worst_paths(sig * a, L, r, maxD, n_paths, rng)
        res = {}
        for combo in COMBOS:
            t, ko, ki, ty, k = combo
            kk, princ, end_day = settle(W, t, ko, ki, ty, k)
            disc_end = np.exp(-r * end_day / 252)
            pv_pr = float(np.mean(disc_end * princ))
            cd = np.concatenate([[0.0], np.cumsum(np.exp(-r * MONTH * np.arange(1, t + 1) / 252))])
            A = float(np.mean(cd[kk]))
            res[combo] = ((1 - pv_pr) / A, A)
        out[a] = res
    return out


def realize(Wreal: np.ndarray):
    """Wreal: (D+1,) 單一真實路徑 → dict[combo] -> (ncoup, princ, end_day)。路徑太短者回傳 None。"""
    out = {}
    for combo in COMBOS:
        t, ko, ki, ty, k = combo
        if len(Wreal) < t * MONTH + 1:
            out[combo] = None
            continue
        kk, princ, end_day = settle(Wreal[None, :], t, ko, ki, ty, k)
        out[combo] = (int(kk[0]), float(princ[0]), int(end_day[0]))
    return out


def vol_inputs(logret: np.ndarray):
    """進場日當下可得的波動率估計：sqrt(0.5*σ60² + 0.5*σ250²)。logret: (T, n)。"""
    s60 = logret[-60:].std(0, ddof=1) * np.sqrt(252)
    s250 = logret[-250:].std(0, ddof=1) * np.sqrt(252)
    return np.sqrt(0.5 * s60 ** 2 + 0.5 * s250 ** 2)
