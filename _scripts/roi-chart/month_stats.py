# Monthly results for a results post: python month_stats.py YYYY-MM
# Prints, for each league with wagers in that month, the month's totals, season-to-date totals, results by
# market and by book, the top and bottom players, and the largest single-play wins. NBA and WNBA come from the
# graded ledgers (same sources as season_stats.py; the NBA season folder is the newest one under the adhoc tree),
# MLB from the daily ROI files (per-product totals only; there is no per-play detail there).
# Paste the numbers into a copy of _drafts/monthly-results-template.qmd (see agents.md, "Monthly results post").
import glob, os, sys
import numpy as np, pandas as pd

pd.set_option('display.width', 200); pd.set_option('display.max_rows', 200)
A = '/Users/jim/Code/adhoc/bet_tracking/'
W = '/Users/jim/Desktop/files/sdbs_wnba/02_curated/wnba_first_to_score/tracking/ledger/'
M = '/Users/jim/Desktop/files/sdbs_mlb/02_curated/bet_tracking/'


def ledger(which):
    if which == 'nba':
        seasons = sorted(d for d in os.listdir(A + 'NBA') if d[:4].isdigit())
        path = A + 'NBA/%s/bet_tracking_consolidated.csv' % seasons[-1]
        d = pd.read_csv(path, low_memory=False); label = 'NBA %s' % seasons[-1]
    else:
        d = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(W + '*.csv'))); label = 'WNBA'
    d['date'] = pd.to_datetime(d.date)
    d['uplay'] = d.prop_type + '|' + d.play.astype(str) + '|' + d.date.dt.strftime('%Y-%m-%d') + '|' + d.game.astype(str)
    return d[d.result.isin(['Win', 'Loss'])], label


def agg(g):
    st = g.units_standardized_bet.sum(); net = g.units_standardized_net.sum()
    return pd.Series({'wagers': len(g), 'plays': g.uplay.nunique(), 'wins': int((g.result == 'Win').sum()),
                      'staked': round(st, 1), 'net': round(net, 1), 'roi%': round(100 * net / st, 1) if st else np.nan})


def main(month):
    period = pd.Period(month, 'M')
    for which in ('nba', 'wnba'):
        try:
            d, label = ledger(which)
        except FileNotFoundError as e:
            print('skip', which, e); continue
        m = d[d.date.dt.to_period('M') == period]
        if m.empty:
            print('%s: no wagers in %s' % (label, month)); continue
        print('=' * 30, label, month)
        print('month', agg(m).to_dict())
        std = d[d.date <= m.date.max()]
        print('season to date through %s' % m.date.max().date(), agg(std).to_dict())
        print('\n-- by market'); print(m.groupby('prop_type').apply(agg).sort_values('net', ascending=False))
        print('\n-- by book'); print(m.groupby('book').apply(agg).sort_values('staked', ascending=False))
        daily = m.groupby('date').units_standardized_net.sum()
        print('\ndays with bets', len(daily), 'winning days', int((daily > 0).sum()),
              'best day', daily.idxmax().date(), round(daily.max(), 1), 'worst day', daily.idxmin().date(), round(daily.min(), 1))
        pl = m.groupby('play').agg(wagers=('result', 'size'), wins=('result', lambda x: int((x == 'Win').sum())),
                                   staked=('units_standardized_bet', 'sum'), net=('units_standardized_net', 'sum'))
        pl['roi%'] = 100 * pl.net / pl.staked
        print('\n-- top players'); print(pl.sort_values('net', ascending=False).head(5).round(1))
        print('\n-- worst players'); print(pl.sort_values('net').head(3).round(1))
        hp = m.groupby('uplay').agg(date=('date', 'first'), game=('game', 'first'), prop=('prop_type', 'first'), play=('play', 'first'),
                                    best=('line_book', 'max'), staked=('units_standardized_bet', 'sum'), net=('units_standardized_net', 'sum'))
        print('\n-- largest wins'); print(hp.sort_values('net', ascending=False).head(5).round(2).to_string(index=False))
    for prod in sorted(os.listdir(M)) if os.path.isdir(M) else []:
        f = M + prod + '/roi_daily.csv'
        if not os.path.exists(f): continue
        df = pd.read_csv(f); df = df[df.market == 'ALL']; df['date'] = pd.to_datetime(df.date)
        m = df[df.date.dt.to_period('M') == period]
        if m.empty: continue
        std = df[df.date <= m.date.max()]
        print('=' * 30, 'MLB', prod, month)
        print('month net %.1f staked %.1f roi %.1f%%' % (m.net_units_std.sum(), m.staked_units_std.sum(), 100 * m.net_units_std.sum() / m.staked_units_std.sum()))
        print('season to date net %.1f staked %.1f roi %.1f%%' % (std.net_units_std.sum(), std.staked_units_std.sum(), 100 * std.net_units_std.sum() / std.staked_units_std.sum()))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('usage: month_stats.py YYYY-MM')
    main(sys.argv[1])
