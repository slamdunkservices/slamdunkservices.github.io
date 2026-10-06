# Season statistics for a recap post: python season_stats.py nba|wnba. NBA reads the 2025-26 adhoc snapshot,
# WNBA the live 2026 ledger; change the paths in load() for another season.
import pandas as pd, glob, numpy as np, sys
pd.set_option('display.width',200); pd.set_option('display.max_rows',200)
def load(which):
    if which=='nba':
        d=pd.read_csv('/Users/jim/Code/adhoc/bet_tracking/NBA/2025-2026/bet_tracking_consolidated.csv',low_memory=False)
    else:
        d=pd.concat(pd.read_csv(f) for f in sorted(glob.glob('/Users/jim/Desktop/files/sdbs_wnba/02_curated/wnba_first_to_score/tracking/ledger/*.csv')))
    d['date']=pd.to_datetime(d.date)
    d['gtype']=d.game_id.astype(str).str.zfill(10).str[2].map({'1':'preseason','2':'regular','4':'playoffs','5':'play-in','6':'cup final'})
    d['uplay']=d.prop_type+'|'+d.play.astype(str)+'|'+d.date.dt.strftime('%Y-%m-%d')+'|'+d.game.astype(str)
    return d
def agg(g):
    g=g[g.result.isin(['Win','Loss'])]
    st=g.units_standardized_bet.sum(); net=g.units_standardized_net.sum()
    return pd.Series({'wagers':len(g),'plays':g.uplay.nunique(),'wins':(g.result=='Win').sum(),'staked':round(st,1),'net':round(net,1),'roi%':round(100*net/st,1) if st else np.nan})
for which in sys.argv[1:]:
    d=load(which); print('='*30, which.upper())
    gl=d[d.result.isin(['Win','Loss'])]
    print('dates',d.date.min().date(),d.date.max().date(),'games',d.game_id.nunique(),'results',d.result.value_counts().to_dict())
    print(agg(d).to_dict())
    print('win rate by wager %.1f%%'%(100*(gl.result=='Win').mean()))
    print('\n-- by game type'); print(d.groupby('gtype').apply(agg))
    print('game types dates', d.groupby('gtype').date.agg(['min','max']))
    print('\n-- by prop_type'); print(d.groupby('prop_type').apply(agg).sort_values('net',ascending=False))
    print('\n-- by month'); print(d.groupby(d.date.dt.to_period('M')).apply(agg))
    print('\n-- by book'); print(d.groupby('book').apply(agg).sort_values('staked',ascending=False))
    daily=gl.groupby('date').units_standardized_net.sum().sort_index(); cum=daily.cumsum()
    peak=cum.cummax(); dd=cum-peak; t=dd.idxmin(); p=cum[:t].idxmax()
    print('\nmax drawdown %.1f from %s (%.1f) to %s (%.1f)'%(dd.min(),p.date(),cum[p],t.date(),cum[t]))
    rec=cum[t:][cum[t:]>=cum[p]]; print('recovered on', rec.index[0].date() if len(rec) else 'not recovered')
    print('days with bets',len(daily),'winning days',(daily>0).sum(),'%.1f%%'%(100*(daily>0).mean()))
    print('best day',daily.idxmax().date(),round(daily.max(),1),' worst day',daily.idxmin().date(),round(daily.min(),1))
    # odds/edge per wager
    print('median book odds %+d'%gl.line_book.median(),' mean model prob %.3f mean book prob %.3f mean edge %.4f'%(gl.prob_model.mean(),gl.prob_book.mean(),gl.edge.mean()))
    # calibration on unique plays (first row each)
    u=gl.sort_values('run_timestamp_utc').groupby('uplay').first()
    print('unique plays',len(u),' expected wins (sum model prob) %.0f  book-implied %.0f  actual %d'%(u.prob_model.sum(),u.prob_book.sum(),(u.result=='Win').sum()))
    # players
    pl=gl.groupby('play').agg(wagers=('result','size'),plays=('uplay','nunique'),staked=('units_standardized_bet','sum'),net=('units_standardized_net','sum'))
    pl['roi%']=100*pl.net/pl.staked
    print('\n-- top players'); print(pl.sort_values('net',ascending=False).head(8).round(1))
    print('\n-- worst players'); print(pl.sort_values('net').head(5).round(1))
    # biggest hits by unique play
    hp=gl.groupby('uplay').agg(date=('date','first'),game=('game','first'),prop=('prop_type','first'),play=('play','first'),books=('book',lambda x:', '.join(sorted(set(x)))),best=('line_book','max'),staked=('units_standardized_bet','sum'),net=('units_standardized_net','sum'),res=('result','first'))
    print('\n-- biggest hits'); print(hp.sort_values('net',ascending=False).head(10).round(2).to_string(index=False))
    print('largest single-play loss', round(hp.net.min(),2))
