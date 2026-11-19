"""USD account analytics; no optimization claims, reproducible resampling."""
import math
import random
import statistics
from collections import Counter, defaultdict


def percentile(values,p):
    if not values:
        return None
    data=sorted(values)
    pos=(len(data)-1)*p
    lo=int(pos)
    hi=min(lo+1,len(data)-1)
    return data[lo]+(data[hi]-data[lo])*(pos-lo)


def wilson(wins,n):
    if not n:
        return [None,None]
    z=1.959963984540054
    p=wins/n
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-half,center+half]


def trade_stats(trades):
    ts=[t for t in trades if t['status']=='Closed']
    ps=[t['pnl'] for t in ts]
    wins=[p for p in ps if p>0]
    losses=[p for p in ps if p<0]
    gp,gl=sum(wins),sum(losses)
    return dict(completed_trades=len(ts),winning_trades=len(wins),losing_trades=len(losses),
                breakeven_trades=sum(p==0 for p in ps),win_rate=len(wins)/len(ts) if ts else None,
                win_rate_95ci=wilson(len(wins),len(ts)),gross_profit=gp,gross_loss=gl,
                net_profit=gp+gl,profit_factor=gp/-gl if gl else None,
                profit_factor_note='undefined without losses' if not gl else None,
                expectancy=statistics.mean(ps) if ps else None,
                average_r=statistics.mean(t['r_multiple'] for t in ts) if ts else None,
                average_holding_hours=statistics.mean(t['duration_hours'] for t in ts) if ts else None,
                average_win=statistics.mean(wins) if wins else None,
                average_loss=statistics.mean(losses) if losses else None,
                best_trade=max(ps) if ps else None,worst_trade=min(ps) if ps else None,
                total_transaction_costs=sum(t['total_costs'] for t in ts),
                ambiguous_bars=sum(t['ambiguous_bars'] for t in ts))


def summarize(result):
    trades,curve=result['trades'],result['equity']
    initial=result['config']['initial_balance']
    m=trade_stats(trades)
    peak=initial
    max_dd=max_pct=0.0
    for p in curve:
        peak=max(peak,p['equity'])
        dd=peak-p['equity']
        pct=dd/peak*100 if peak>0 else 0
        p['drawdown']=dd
        p['drawdown_percent']=pct
        max_dd=max(max_dd,dd)
        max_pct=max(max_pct,pct)
    final=curve[-1]['equity'] if curve else initial
    m.update(total_setups=len(result['setups']),qualified_setups=sum(s['qualified'] for s in result['setups']),
             total_trades=len(trades),open_trades=sum(t['status']=='Open' for t in trades),
             final_equity=final,mtm_net_profit=final-initial,return_percent=100*(final/initial-1),
             max_drawdown=max_dd,max_drawdown_percent=max_pct,
             rejected_or_unresolved=dict(Counter(s['reason'] for s in result['setups'] if s.get('reason'))),
             r_distribution=[t['r_multiple'] for t in trades if t['status']=='Closed'])
    if len(curve)>1:
        from datetime import datetime
        years=(datetime.fromisoformat(curve[-1]['time'])-datetime.fromisoformat(curve[0]['time'])).total_seconds()/31557600
        m['cagr_percent']=100*((final/initial)**(1/years)-1) if years>0 and final>0 else None
    for name,length in [('monthly_returns',7),('annual_returns',4)]:
        ends={}
        for p in curve:
            ends[p['time'][:length]]=p['equity']
        previous=initial
        values={}
        for period,end in ends.items():
            values[period]=100*(end/previous-1) if previous>0 else None
            previous=end
        m[name]=values
    longest_win=longest_loss=run_win=run_loss=0
    closed=sorted((t for t in trades if t['status']=='Closed'),key=lambda t:(t['exit_index'],t['id']))
    for t in closed:
        run_win=run_win+1 if t['pnl']>0 else 0
        run_loss=run_loss+1 if t['pnl']<0 else 0
        longest_win=max(longest_win,run_win)
        longest_loss=max(longest_loss,run_loss)
    m.update(consecutive_wins=longest_win,consecutive_losses=longest_loss)
    groups=defaultdict(list)
    for t in closed:
        groups['direction:'+('bullish' if t['direction']==1 else 'bearish')].append(t)
        groups['year:'+t['entry_time'][:4]].append(t)
        groups['month:'+t['entry_time'][:7]].append(t)
        hour=int(t['entry_time'][11:13])
        groups['session_UTC:'+('Asia' if hour<7 else 'Europe' if hour<13 else 'US' if hour<21 else 'Late')].append(t)
        groups['reward_risk:'+('under_3' if t['reward_risk']<3 else '3_to_6' if t['reward_risk']<6 else '6_plus')].append(t)
        groups['duration:'+('under_24h' if t['duration_hours']<24 else '1_to_7d' if t['duration_hours']<168 else '7d_plus')].append(t)
    m['segments']={k:trade_stats(v) for k,v in groups.items()}
    return m


def bootstrap(trades, repetitions=500, block_size=5, seed=1729):
    """Moving-block bootstrap of R. Descriptive uncertainty, not proof of independence."""
    rs=[t['r_multiple'] for t in sorted(trades,key=lambda x:x['entry_index']) if t['status']=='Closed']
    if len(rs)<2:
        return dict(sample_size=len(rs),note='Insufficient sample for bootstrap')
    rng=random.Random(seed)
    means,pfs,dds=[],[],[]
    for _ in range(repetitions):
        sample=[]
        while len(sample)<len(rs):
            start=rng.randrange(len(rs))
            sample.extend(rs[(start+j)%len(rs)] for j in range(block_size))
        sample=sample[:len(rs)]
        means.append(statistics.mean(sample))
        loss=-sum(x for x in sample if x<0)
        if loss:
            pfs.append(sum(x for x in sample if x>0)/loss)
        equity=peak=dd=0.0
        for x in sample:
            equity+=x
            peak=max(peak,equity)
            dd=max(dd,peak-equity)
        dds.append(dd)
    return dict(sample_size=len(rs),repetitions=repetitions,block_size=block_size,seed=seed,
                mean_r_95ci=[percentile(means,.025),percentile(means,.975)],
                profit_factor_95ci=[percentile(pfs,.025),percentile(pfs,.975)],
                max_drawdown_r_95range=[percentile(dds,.025),percentile(dds,.975)],
                note='Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent.')
