import pandas as pd, numpy as np
import analysis as A
SCEN={'asis':'grid_real.parquet','erp6':'grid_erp6.parquet','erp0':'grid_erp0.parquet'}
def load(s):
    g=pd.read_parquet(SCEN[s]); g['ko']=g['ko'].fillna(0); return g
