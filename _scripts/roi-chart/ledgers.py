# Per-season net units / ROI from the graded ledgers, plus a per-date, per-series daily net CSV (argv[1]).
# Called by _scripts/roi-chart/build.sh. Sources are documented in agents.md ("Update the ROI numbers").
import pandas as pd, glob, openpyxl, sys
A='/Users/jim/Code/adhoc/bet_tracking/'
W='/Users/jim/Desktop/files/sdbs_wnba/02_curated/wnba_first_to_score/tracking/ledger/'
M='/Users/jim/Desktop/files/sdbs_mlb/02_curated/bet_tracking/'
rows=[]; summ=[]
def old(path,label):
    ws=openpyxl.load_workbook(A+path,read_only=True,data_only=True).worksheets[0]
    r=list(ws.iter_rows(values_only=True)); h={k:i for i,k in enumerate(r[0])}
    d=[]
    for x in r[1:]:
        u,o,res=x[h['Units']],x[h['Odds']],x[h['Outcome']]
        if u is None or o is None or res not in('Win','Loss'): continue
        u=float(u);o=float(o)
        net=u*(o/100 if o>0 else 100/abs(o)) if res=='Win' else -u
        d.append((pd.Timestamp(x[h['Date']]).date(),net,u))
    df=pd.DataFrame(d,columns=['date','net','staked']); df['series']=label; return df
def std(path,label):
    df=pd.read_csv(path,low_memory=False)
    df=df[df['result'].isin(['Win','Loss'])] if 'result' in df else df
    out=pd.DataFrame({'date':pd.to_datetime(df['date']).dt.date,'net':df['units_standardized_net'],'staked':df['units_standardized_bet']}); out['series']=label; return out
parts=[old('NBA/2021-2022/prop_bets_21_22.xlsx','NBA 2021-22'),
       old('NBA/2022-2023/prop_bets_22_23.xlsx','NBA 2022-23'),
       std(A+'NBA/2023-2024/bet_tracking_consolidated.csv','NBA 2023-24'),
       std(A+'NBA/2024-2025/bet_tracking_consolidated.csv','NBA 2024-25'),
       std(A+'NBA/2025-2026/bet_tracking_consolidated.csv','NBA 2025-26'),
       std(A+'WNBA/2024/bet_tracking_consolidated.csv','WNBA 2024'),
       std(A+'WNBA/2025/bet_tracking_consolidated.csv','WNBA 2025'),
       pd.concat([std(f,'WNBA 2026') for f in sorted(glob.glob(W+'*.csv'))])]
for prod,label in [('home_runs','MLB 2026 home runs'),('nrfi_yrfi','MLB 2026 NRFI/YRFI')]:
    df=pd.read_csv(M+prod+'/roi_daily.csv'); df=df[df.market=='ALL']
    parts.append(pd.DataFrame({'date':pd.to_datetime(df.date).dt.date,'net':df.net_units_std,'staked':df.staked_units_std,'series':label}))
allp=pd.concat(parts)
for s,g in allp.groupby('series',sort=False):
    print(f"{s:22s} {g.date.min()} -> {g.date.max()}  net {g.net.sum():8.1f}  staked {g.staked.sum():9.1f}  roi {100*g.net.sum()/g.staked.sum():5.1f}%  n={len(g)}")
tot=allp.net.sum(); print(f"TOTAL net {tot:.1f}  (with 2022-23 at 1,610: {tot-allp[allp.series=='NBA 2022-23'].net.sum()+1610:.1f})")
daily=allp.groupby(["date","series"],as_index=False).net.sum().sort_values("date")
daily.to_csv(sys.argv[1],index=False); print("max date",daily.date.max(),"rows",len(daily))
