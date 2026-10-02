import pandas as pd, numpy as np
from common import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',400)
AL=[0.9,1.0,1.1,1.2,1.3]
def be_alpha(b,fee=0.01,per=None):
    ex=[A.add_returns(b,a,fee) for a in AL]
    v=[ (e.excess.sum()/e.dur.sum()) for e in ex]
    for i in range(len(AL)-1):
        if v[i]<0<=v[i+1]: return AL[i]+(AL[i+1]-AL[i])*(-v[i])/(v[i+1]-v[i])
    return AL[0]-0.0 if v[0]>=0 else np.nan if v[-1]<0 else AL[0]
rows=[]
for s in SCEN:
    g=load(s)
    for bk in ['NVDA','TSM','NVDA+TSM','SPY']:
        gb=g[g.basket==bk].dropna(subset=['princ'])
        for (t,ko,ki,ty,k),b in gb.groupby(['tenor','ko','ki','kitype','strike']):
            for per,mask in [('train',b.date<=A.TRAIN_END),('test',b.date>A.TRAIN_END),('all',b.date>pd.Timestamp('1990-01-01'))]:
                d=b[mask]
                if len(d)<20: continue
                v=[(A.add_returns(d,a,0.01).pipe(lambda e:e.excess.sum()/e.dur.sum())) for a in AL]
                # linear extrapolate crossing
                import numpy.polynomial.polynomial as P
                co=np.polyfit(AL,v,1); a0=-co[1]/co[0]
                rows.append(dict(scen=s,basket=bk,tenor=t,ko=ko,ki=ki,kitype=ty,strike=k,per=per,be_alpha=a0,
                                 cpn_at1=A.add_returns(d,1.0,0.01).cpn_pa.mean()))
R=pd.DataFrame(rows); R.to_parquet('h6.parquet')
a=R[(R.per=='all')]
print(a.groupby(['basket','scen']).be_alpha.describe()[['min','25%','50%','75%','max']].round(2))
# by structure feature, NVDA+TSM
x=a[a.basket=='NVDA+TSM']
for col in ['tenor','ko','ki','kitype','strike']:
    print(col); print(x.pivot_table(index=col,columns='scen',values='be_alpha').round(2))
