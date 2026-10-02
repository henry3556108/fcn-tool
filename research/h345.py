import pandas as pd, numpy as np
from common import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',300)
KIS=np.array([.55,.60,.65,.70,.75])
out=[]
def summarize(tag,x,**kw):
    for per,mask in [('train',x.date<=A.TRAIN_END),('test',x.date>A.TRAIN_END),('all',x.date>pd.Timestamp('1990-01-01'))]:
        d=x[mask]
        if len(d)<8: continue
        m=A.metrics(d); out.append(dict(tag=tag,per=per,**kw,n=len(d),cpn=m.cpn_pa,ann_ex=m.ann_excess,cvar5=m.cvar5,conv=m.conv_rate,ko=m.ko_rate,worst=m.worst))
for s in SCEN:
    g=load(s)
    for bk in ['NVDA','TSM','NVDA+TSM']:
        gb=g[g.basket==bk]
        # H3 vol-adaptive barrier vs fixed
        for ty in ['A','E']:
            for K in [1.0,0.9]:
                b=gb[(gb.tenor==6)&(gb.ko==1.0)&(gb.kitype==ty)&(gb.strike==K)]
                for ki in [0.60,0.65,0.70]:
                    summarize('H3 fixed',A.add_returns(b[b.ki==ki],1.0,0.01),scen=s,basket=bk,cfg=f'{ty} K{K} KI{ki}')
                for z in [1.0,1.5,2.0]:
                    b2=b.copy(); tgt=np.exp(-z*b2.sig*np.sqrt(0.5)); b2['near']=KIS[np.abs(tgt.values[:,None]-KIS[None,:]).argmin(1)]
                    b2=b2[b2.ki==b2.near]
                    summarize('H3 vol-adaptive',A.add_returns(b2,1.0,0.01),scen=s,basket=bk,cfg=f'{ty} K{K} z{z}')
        # H4 tenor & KO
        for t in [3,6,12]:
            for ko in [1.0,0.0]:
                b=gb[(gb.tenor==t)&(gb.ko==ko)&(gb.ki==0.65)&(gb.kitype=='A')&(gb.strike==0.9)]
                summarize('H4 tenor/KO',A.add_returns(b,1.0,0.01),scen=s,basket=bk,cfg=f'{t}M KO{"Y" if ko else "N"}')
R=pd.DataFrame(out); R.to_parquet('h345.parquet')
r=R[R.per!='all']
print('H3: mean ann_ex over baskets/types/K')
print(r[r.tag.str.startswith('H3')].assign(g=lambda d:d.cfg.str.split().str[-1]).groupby(['tag','g','scen','per']).ann_ex.mean().unstack(['scen','per']).round(3))
print(r[r.tag.str.startswith('H3')].assign(g=lambda d:d.cfg.str.split().str[-1]).groupby(['tag','g']).agg(cvar5=('cvar5','mean'),conv=('conv','mean'),cpn=('cpn','mean')).round(3))
print('H4'); print(R[(R.tag=='H4 tenor/KO')].pivot_table(index='cfg',columns=['scen','per'],values='ann_ex').round(3))
print(R[(R.tag=='H4 tenor/KO')&(R.per=='all')&(R.scen=='erp6')].pivot_table(index='cfg',columns='basket',values='cvar5').round(3))
