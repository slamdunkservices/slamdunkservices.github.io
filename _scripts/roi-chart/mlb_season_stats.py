# MLB season statistics for a recap post: python mlb_season_stats.py [daily.csv]. Reads every product's
# alerted_plays/*.csv under $MLB_DATA_ROOT/02_curated/bet_tracking (one row per alerted wager, deduplicated the
# same way roi_daily.csv is, so the totals match the ROI receipts) and the season schedule for game types.
# With a path argument it also writes the daily net CSV (date, period, units_standardized_net) that season.R draws.
import pandas as pd, numpy as np, glob, sys, os
pd.set_option('display.width', 220); pd.set_option('display.max_rows', 200)
ROOT = '/Users/jim/Desktop/files/sdbs_mlb/'
M = ROOT + '02_curated/bet_tracking/'
PRODUCTS = [('home_runs', 'Home runs'), ('nrfi_yrfi', 'NRFI / YRFI'), ('stolen_bases', 'Stolen bases'),
            ('rbi', 'RBI'), ('runs', 'Runs scored'), ('total_bases', 'Total bases')]
BOOKS = {'fanduel': 'FanDuel', 'draftkings': 'DraftKings', 'betmgm': 'BetMGM', 'betrivers': 'BetRivers', 'caesars': 'Caesars',
         'bet365': 'bet365', 'fanatics': 'Fanatics', 'hardrockbet': 'Hard Rock', 'thescore': 'theScore', 'circa': 'Circa', 'espnbet': 'ESPN'}
GTYPE = {'R': 'Regular season', 'F': 'Postseason', 'D': 'Postseason', 'L': 'Postseason', 'W': 'Postseason'}
parts = []
for prod, label in PRODUCTS:
    fs = sorted(glob.glob(M + prod + '/alerted_plays/*.csv'))
    d = pd.concat((pd.read_csv(f) for f in fs), ignore_index=True)
    d['product'] = label; parts.append(d)
d = pd.concat(parts, ignore_index=True)
d['date'] = pd.to_datetime(d.date)
sched = pd.read_csv(ROOT + '01_raw/schedules/%d.csv' % d.season.max(), usecols=['game_pk', 'game_type']).drop_duplicates('game_pk')
d = d.merge(sched, on='game_pk', how='left'); d['period'] = d.game_type.map(GTYPE).fillna('Regular season')
d['book'] = d.best_book.map(lambda b: BOOKS.get(str(b).lower(), str(b)))
d['pm'] = d['product'] + ' ' + d.market.astype(str)
d['uplay'] = d['product'] + '|' + d.market.astype(str) + '|' + d.player.astype(str) + '|' + d.game_pk.astype(str)
g = d[~d['void'].astype(bool)]
def agg(x):
    x = x[~x['void'].astype(bool)]
    st = x.staked_units_std.sum(); net = x.net_units_std.sum()
    return pd.Series({'wagers': len(x), 'plays': x.uplay.nunique(), 'wins': int(x.won.astype(bool).sum()), 'staked': round(st, 1),
                      'net': round(net, 1), 'roi%': round(100 * net / st, 1) if st else np.nan})
print('dates', d.date.min().date(), d.date.max().date(), 'rows', len(d), 'voids', int(d['void'].astype(bool).sum()), 'games', d.game_pk.nunique())
print('ALL', agg(d).to_dict())
print('\n-- by product'); print(d.groupby('product', sort=False).apply(agg))
print('\n-- by product and market'); print(d.groupby('pm', sort=False).apply(agg))
print('\n-- by period'); print(d.groupby('period').apply(agg))
print('\n-- by period, flagship (HR + NRFI/YRFI)'); print(d[d['product'].isin(['Home runs', 'NRFI / YRFI'])].groupby('period').apply(agg))
print('\n-- by month'); print(d.groupby(d.date.dt.strftime('%Y-%m')).apply(agg))
print('\n-- by month, flagship'); print(d[d['product'].isin(['Home runs', 'NRFI / YRFI'])].groupby(d.date.dt.strftime('%Y-%m')).apply(agg))
print('\n-- by book'); print(d.groupby('book').apply(agg).sort_values('staked', ascending=False))
print('\n-- by book, home runs'); print(d[d['product'] == 'Home runs'].groupby('book').apply(agg).sort_values('staked', ascending=False))
print('\n-- voids by product'); print(d.groupby('product', sort=False)['void'].apply(lambda v: int(v.astype(bool).sum())))
daily = g.groupby('date').net_units_std.sum().cumsum()
dd = daily.diff().fillna(daily); peak = daily.cummax(); dd_from = (daily - peak)
i = dd_from.idxmin(); j = daily[:i].idxmax(); rec = daily[i:][daily[i:] >= daily[j]]
print('\nmax drawdown %.1f from %s (%.1f) to %s (%.1f)' % (dd_from.min(), j.date(), daily[j], i.date(), daily[i]), 'recovered', rec.index[0].date() if len(rec) else 'never')
days = g.groupby('date').net_units_std.sum()
print('days with bets', len(days), 'winning days', int((days > 0).sum()), 'best', days.idxmax().date(), round(days.max(), 1), 'worst', days.idxmin().date(), round(days.min(), 1))
hr = g[g['product'] == 'Home runs']
print('home runs: median odds', hr.american_odds.median(), 'win rate by wager %.1f%%' % (100 * hr.won.astype(bool).mean()))
# projection accuracy per play at first alert
first = g.sort_values(['date', 'edge_run_timestamp' if 'edge_run_timestamp' in g else 'inference_run_timestamp']).drop_duplicates('uplay')
for lab, sub in [('all', first), ('home runs', first[first['product'] == 'Home runs']), ('NRFI/YRFI', first[first['product'] == 'NRFI / YRFI'])]:
    print('accuracy %-10s plays %5d  model %.0f  book %.0f  actual %d' % (lab, len(sub), sub.projection.sum(), sub.implied_probability.sum(), sub.won.astype(bool).sum()))
pl = g[g['product'] != 'NRFI / YRFI'].groupby('player').apply(agg)
print('\n-- top players'); print(pl.sort_values('net', ascending=False).head(8))
print('\n-- worst players'); print(pl.sort_values('net').head(5)); print('players bet', len(pl))
print('\n-- top players, home runs only'); print(hr.groupby('player').apply(agg).sort_values('net', ascending=False).head(6))
hp = g.groupby('uplay').agg(date=('date', 'min'), product=('product', 'first'), market=('market', 'first'), player=('player', 'first'), team=('team', 'first'),
                            books=('book', lambda b: ', '.join(sorted(set(b)))), best=('american_odds', 'max'), staked=('staked_units_std', 'sum'), net=('net_units_std', 'sum'))
print('\n-- biggest hits'); print(hp.sort_values('net', ascending=False).head(10).round(2).to_string(index=False))
print('ten largest total', round(hp.sort_values('net', ascending=False).head(10).net.sum(), 1), 'largest loss', round(hp.net.min(), 2))
print('\n-- 2+ home run hits'); print(hp[(hp['product'] == 'Home runs') & (hp.market == '2+') & (hp.net > 0)].sort_values('net', ascending=False).round(2).to_string(index=False))
if len(sys.argv) > 1:
    out = g.groupby(['date', 'period'], as_index=False).net_units_std.sum().rename(columns={'net_units_std': 'units_standardized_net'})
    out['date'] = out.date.dt.date; out.to_csv(sys.argv[1], index=False); print('wrote', sys.argv[1], len(out), 'rows')
