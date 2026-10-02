import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import glob
# 中文字型（若無則退回預設）
fm.fontManager.addfont('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'); plt.rcParams['font.sans-serif']=['WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus']=False
px=pd.read_csv('prices.csv',index_col=0,parse_dates=True)
import fcn_engine as E, analysis as A
from common import load
C={'ko':'#2a9d8f','ki':'#e76f51','nv':'#264653','ts':'#8d99ae'}
# 圖1：怎麼畫——兩個真實案例（NVDA+TSM, 6M, KO100, KI65 美式, 轉換價100）
g=load('asis'); b=g[(g.basket=='NVDA+TSM')&(g.tenor==6)&(g.ko==1.0)&(g.ki==0.65)&(g.kitype=='A')&(g.strike==1.0)]
b=A.add_returns(b,1.0,0.01).dropna(subset=['ret'])
ex_ko=b[(b.date>='2023-01-01')&b.koed].iloc[0]; ex_bad=b.loc[b.ret.idxmin()]
sub=px[['NVDA_c','TSM_c']].dropna()
fig,axs=plt.subplots(1,2,figsize=(13,4.6))
for ax,row,title in [(axs[0],ex_ko,'案例A：第 %d 個月被 KO，拿回本金+配息'),(axs[1],ex_bad,'案例B：觸及 KI 且期末低於轉換價 → 接股票')]:
    i=sub.index.get_loc(pd.Timestamp(row.date)); D=126
    seg=sub.iloc[i:i+D+1]/sub.iloc[i]
    for c,col,lab in [('NVDA_c',C['nv'],'NVDA'),('TSM_c',C['ts'],'TSM')]:
        ax.plot(range(len(seg)),seg[c]*100,color=col,lw=1.3,label=lab)
    ax.plot(range(len(seg)),seg.min(1)*100,color='k',lw=2,label='最差標的 (worst-of)')
    ax.axhline(100,color=C['ko'],ls='--',label='KO / 轉換價 100%'); ax.axhline(65,color=C['ki'],ls='--',label='KI 65%')
    for k in range(1,7): ax.axvline(21*k,color='#ddd',lw=.8); 
    ax.scatter([21*k for k in range(1,7) if 21*k<len(seg)],[seg.min(1).iloc[21*k]*100 for k in range(1,7) if 21*k<len(seg)],color='k',zorder=5,s=18)
    ax.set_title(f"{title % int(np.ceil(row.end_day/21)) if '%d' in title else title}\n進場 {pd.Timestamp(row.date).date()}｜報酬 {row.ret:+.0%}｜年化配息(模型) {row.cpn_pa:.0%}",fontsize=10)
    ax.set_xlabel('進場後交易日（灰線=月度觀察日）'); ax.set_ylabel('% of 期初價'); ax.grid(alpha=.2)
axs[0].legend(fontsize=8,loc='lower left')
plt.tight_layout(); plt.savefig('charts/01_how_to_read.png',dpi=140); plt.close()
# 圖2：到期損益圖（含懸崖）
w=np.linspace(0.3,1.3,500)
def payoff(w,ki,K,kind):
    conv=(w<ki) if kind=='E' else None
    return np.where(w<ki, w/K, 1.0)
fig,ax=plt.subplots(figsize=(7.5,4.3))
ax.plot(w*100,(np.where(w<0.65,w/0.9,1)-1)*100,color=C['ki'],lw=2,label='KI 65%(歐式) 轉換價 90%')
ax.plot(w*100,(np.where(w<0.65,w/1.0,1)-1)*100,color=C['nv'],lw=2,label='KI 65%(歐式) 轉換價 100%')
ax.plot(w*100,(np.where(w<0.70,w/0.8,1)-1)*100,color=C['ts'],lw=2,label='KI 70%(歐式) 轉換價 80%')
ax.axvline(65,color='#bbb',ls=':'); ax.set_xlabel('期末最差標的 / 期初價 (%)'); ax.set_ylabel('本金損益（未含配息）%'); ax.set_title('到期本金損益：KI 是「懸崖」不是緩坡'); ax.legend(fontsize=8); ax.grid(alpha=.2)
plt.tight_layout(); plt.savefig('charts/02_payoff_cliff.png',dpi=140); plt.close()
# 圖3：損益兩平 α
H=pd.read_parquet('h6.parquet'); H=H[(H.per=='all')]
S=[(6,1.0,0.65,'A',1.0,'6M KO KI65A K100'),(6,1.0,0.70,'E',0.9,'6M KO KI70E K90'),(12,0.0,0.65,'E',0.9,'12M 無KO KI65E K90'),(12,0.0,0.70,'A',1.0,'12M 無KO KI70A K100'),(12,0.0,0.60,'E',0.8,'12M 無KO KI60E K80')]
rows=[]
for bk in ['TSM','NVDA+TSM','NVDA','SPY']:
    for sc in ['erp0','erp6','asis']:
        r={'basket':bk,'scen':sc}
        for t,ko,ki,ty,k,n in S:
            x=H[(H.basket==bk)&(H.scen==sc)&(H.tenor==t)&(H.ko.fillna(0)==ko)&(H.ki==ki)&(H.kitype==ty)&(H.strike==k)]
            r[n]=x.be_alpha.iloc[0]
        rows.append(r)
T=pd.DataFrame(rows); T.to_csv('breakeven_alpha.csv',index=False)
fig,ax=plt.subplots(figsize=(9,4.8))
lab=[f"{r.basket}\n{ {'erp0':'去漂移 ERP0','erp6':'去漂移 ERP6%','asis':'原始路徑'}[r.scen]}" for r in T.itertuples()]
M=T[[s[-1] for s in S]].values
im=ax.imshow(M,cmap='RdYlGn_r',vmin=0.6,vmax=1.6,aspect='auto')
ax.set_xticks(range(len(S))); ax.set_xticklabels([s[-1] for s in S],fontsize=8,rotation=15); ax.set_yticks(range(len(T))); ax.set_yticklabels(lab,fontsize=7)
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j,i,f"{M[i,j]:.2f}",ha='center',va='center',fontsize=8)
ax.set_title('損益兩平所需「報價波動 ÷ 歷史波動」α（越低越容易賺；費用1%）'); plt.colorbar(im); plt.tight_layout(); plt.savefig('charts/03_breakeven_alpha.png',dpi=140); plt.close()
# 圖4：梯隊累計超額（去漂移 ERP6, α=1.1）
fig,axs=plt.subplots(1,2,figsize=(13,4.3),sharey=True)
for ax,bk in zip(axs,['NVDA+TSM','TSM']):
    gg=load('erp6'); gg=gg[gg.basket==bk].dropna(subset=['princ'])
    for (t,ko,ki,ty,k,n),col in zip([S[0],S[2],S[3]],[C['ki'],C['nv'],C['ko']]):
        x=A.add_returns(gg[(gg.tenor==t)&(gg.ko==ko)&(gg.ki==ki)&(gg.kitype==ty)&(gg.strike==k)],1.1,0.01).sort_values('date').reset_index(drop=True)
        settle=np.arange(len(x))+np.ceil(x.end_day/21).astype(int).values; e=np.zeros(settle.max()+1); np.add.at(e,settle,x.excess.values/t)
        e=e[t:len(x)]; dates=x.date.iloc[t:t+len(e)]
        ax.plot(dates.values[:len(e)],np.cumsum(e)*100,label=n,color=col)
    ax.axhline(0,color='k',lw=.6); ax.set_title(f'{bk}：梯隊累計「超額現金」報酬 (去漂移ERP6%, α=1.1, 費1%)',fontsize=9); ax.grid(alpha=.2); ax.legend(fontsize=7)
axs[0].set_ylabel('累計超額報酬 (% of 資金)')
plt.tight_layout(); plt.savefig('charts/04_ladder_curves.png',dpi=140); plt.close()
print(T.round(2)); print(ex_ko[['date','ret']].to_dict(),ex_bad[['date','ret']].to_dict())
