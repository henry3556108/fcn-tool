import pandas as pd, numpy as np
from common import *
pd.set_option('display.width',280); pd.set_option('display.max_rows',400); pd.set_option('display.max_columns',40)
STRUCT={'6M KO KI65A K100':(6,1.0,0.65,'A',1.0),'6M KO KI70E K90':(6,1.0,0.70,'E',0.9),
        '6M noKO KI65E K90':(6,0.0,0.65,'E',0.9),'12M noKO KI65E K90':(12,0.0,0.65,'E',0.9),
        '12M noKO KI70A K100':(12,0.0,0.70,'A',1.0),'12M noKO KI60E K80':(12,0.0,0.60,'E',0.8)}
rng=np.random.default_rng(7)
def ladder(x,L):
    x=x.sort_values('date').reset_index(drop=True)
    k0=np.arange(len(x)); settle=k0+np.ceil(x.end_day/21).astype(int)
    T=settle.max()+1; e=np.zeros(T)
    np.add.at(e,settle.values,x.excess.values/L)
    # 只取「梯隊已滿載」之後且最後一批已結算的區間
    return e[L:len(x)]
def boot_ci(x,n=2000):
    ys=x.groupby(x.date.dt.year).agg(e=('excess','sum'),d=('dur','sum'))
    E_,D_=ys.e.values,ys.d.values
    idx=rng.integers(0,len(ys),(n,len(ys)))
    v=E_[idx].sum(1)/D_[idx].sum(1)
    return np.percentile(v,[5,95])
rows=[]
for s in SCEN:
    g=load(s)
    for bk in ['TSM','NVDA','NVDA+TSM']:
        gb=g[g.basket==bk].dropna(subset=['princ'])
        for name,(t,ko,ki,ty,k) in STRUCT.items():
            b=gb[(gb.tenor==t)&(gb.ko==ko)&(gb.ki==ki)&(gb.kitype==ty)&(gb.strike==k)]
            for al in [1.0,1.1,1.2]:
                x=A.add_returns(b,al,0.01)
                m=A.metrics(x); e=ladder(x,t)
                cum=np.cumsum(e); dd=(cum-np.maximum.accumulate(cum)).min()
                r12=pd.Series(e).rolling(12).sum().dropna()
                lo,hi=boot_ci(x)
                rows.append(dict(scen=s,basket=bk,struct=name,alpha=al,n=int(m.n),cpn=m.cpn_pa,ann_ex=m.ann_excess,ci_lo=lo,ci_hi=hi,
                                 win=m.win,conv=m.conv_rate,p5=m.p5,worst=m.worst,ladder_maxdd=dd,pos12=(r12>0).mean(),worst12=r12.min()))
R=pd.DataFrame(rows); R.to_parquet('h7b.parquet')
for al in [1.0,1.2]:
    print('alpha',al); print(R[(R.alpha==al)&(R.basket=='NVDA+TSM')].pivot_table(index='struct',columns='scen',values=['ann_ex','pos12']).round(3))
