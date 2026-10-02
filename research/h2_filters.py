import pandas as pd, numpy as np
from common import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',300)
px=pd.read_csv('prices.csv',index_col=0,parse_dates=True)
F=A.features(px)
REF=[(6,1.0,0.65,'A',1.0),(6,1.0,0.70,'E',0.9),(6,1.0,0.60,'E',0.8),(3,1.0,0.65,'A',0.9)]
FILT={
 'none':lambda f:np.ones(len(f),bool),
 'spy>MA200':lambda f:f.spy_ma>0,
 'not extended(<+30% vs MA200)':lambda f:f.ext<0.30,
 'not extended(<+60%)':lambda f:f.ext<0.60,
 'dd>-25%':lambda f:f.dd>-0.25,
 'pullback -10..-35%':lambda f:(f.dd<=-0.10)&(f.dd>-0.35),
 'mom6>0':lambda f:f.mom6>0,
 'vol spike(ratio>1.2) & spy_dd>-10%':lambda f:(f.volratio>1.2)&(f.spy_dd>-0.10),
 'low vol(ratio<0.9)':lambda f:f.volratio<0.9,
 'spy>MA & dd>-25%':lambda f:(f.spy_ma>0)&(f.dd>-0.25),
}
res=[]
for s in SCEN:
    g=load(s)
    for bk in ['NVDA','TSM','NVDA+TSM']:
        gb=g[g.basket==bk].merge(F[F.basket==bk],on=['basket','date'],how='left')
        for (t,ko,ki,ty,k) in REF:
            b=gb[(gb.tenor==t)&(gb.ko==ko)&(gb.ki==ki)&(gb.kitype==ty)&(gb.strike==k)]
            x=A.add_returns(b,1.0,0.01).dropna(subset=['ret','dd','ext','spy_ma'])
            for fn,f in FILT.items():
                m=f(x); 
                for per,mask in [('train',x.date<=A.TRAIN_END),('test',x.date>A.TRAIN_END),('all',x.date>pd.Timestamp('1990-01-01'))]:
                    d=x[m&mask]
                    if len(d)<8: continue
                    mt=A.metrics(d); 
                    res.append(dict(scen=s,basket=bk,struct=f'{t}M KI{ki}{ty} K{k}',filt=fn,per=per,n=len(d),keep=len(d)/mask.sum(),ann_ex=mt.ann_excess,cvar5=mt.cvar5,conv=mt.conv_rate))
R=pd.DataFrame(res); R.to_parquet('h2.parquet')
base=R[R.filt=='none'].set_index(['scen','basket','struct','per']).ann_ex.rename('base')
R=R.join(base,on=['scen','basket','struct','per']); R['d']=R.ann_ex-R.base
t=R[R.per!='all'].groupby(['filt','scen','per']).agg(d=('d','mean'),keep=('keep','mean'),ann_ex=('ann_ex','mean')).reset_index()
print(t.pivot_table(index='filt',columns=['scen','per'],values='d').round(3))
print(R[R.per=='all'].groupby(['filt','scen']).ann_ex.mean().unstack().round(3))
