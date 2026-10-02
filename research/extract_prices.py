"""從 repo 根目錄 index.html 內嵌的 DATA 抽出日線價格 → prices.csv（Yahoo 快照）。"""
import json, datetime, pandas as pd
s = open('../index.html').read()
i = s.index('const DATA =') + len('const DATA =')
D, _ = json.JSONDecoder().raw_decode(s[i:].lstrip())
fr = {}
for k, v in D['series'].items():
    idx = pd.to_datetime([datetime.date(1970, 1, 1) + datetime.timedelta(x) for x in v['d']])
    fr[k + '_c'] = pd.Series(v['c'], idx); fr[k + '_l'] = pd.Series(v['l'], idx)
df = pd.DataFrame(fr).sort_index(); df.index.name = 'date'
df.to_csv('prices.csv')
