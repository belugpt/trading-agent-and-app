import unittest
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from sme.adaptive_engine import simulate,allowed,session,AdaptiveEngine
from sme.adaptive_study import higher_series
from sme.swing_study import SwingEngine
from sme.model import Config,Bar
from test_strategy import fixture

class AdaptiveSafety(unittest.TestCase):
    def config(self):return Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,commission_per_million=0,max_leverage=100)
    def run_policy(self,gate='all',higher=None,exit_name='original',bars=None):
        bars=bars or fixture()
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*(len(bars)-2),[0]*len(bars)]):
            return simulate(bars,self.config(),'EURUSD',None,gate=gate,higher=higher,exit_name=exit_name)
    def test_original_preserves_swing_baseline(self):
        r=self.run_policy()
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*8,[0]*10]):b=SwingEngine(self.config()).run(fixture())
        self.assertEqual(r['metrics'],b['metrics']);self.assertEqual(r['equity'],b['equity'])
    def test_alignment_missing_blocks_all_limits(self):
        self.assertEqual(self.run_policy('higher')['trades'],[])
    def test_higher_lost_before_fill_cancels(self):
        bars=fixture();higher=([bars[0].time,bars[8].time],[1,-1])
        self.assertEqual(self.run_policy('higher',higher)['trades'],[])
    def test_aligned_higher_allows_setup(self):
        self.assertEqual(len(self.run_policy('higher',([fixture()[0].time],[1]))['trades']),1)
    def test_future_higher_value_not_available_early(self):
        e=AdaptiveEngine(self.config(),higher=([fixture()[0].time,fixture()[5].time],[1,-1]))
        self.assertEqual(e.higher_side(fixture()[4].time),1)
    def test_partial_bookkeeping_reconciles(self):
        bars=fixture();bars.append(replace(bars[-1],time=bars[-1].time+timedelta(hours=1),open=25,high=30,low=24,close=28))
        r=self.run_policy(exit_name='partial1R_runner2R',bars=bars);t=r['trades'][0]
        self.assertEqual(t['status'],'Closed');self.assertTrue(t['partial_taken'])
        self.assertAlmostEqual(r['equity'][-1]['balance'],10000+t['pnl'],places=8)
        self.assertAlmostEqual(t['partial_exit']['units']+t['units'],t['original_units'])
        self.assertAlmostEqual(t['pnl']/t['initial_risk'],t['r_multiple'])
    def test_session_handles_us_dst_gap_between_regions(self):
        # 12:00 UTC is New York 08:00 in summer, 07:00 in winter.
        self.assertEqual(session(datetime(2024,7,1,12,tzinfo=timezone.utc)),'Overlap')
        self.assertEqual(session(datetime(2024,1,1,12,tzinfo=timezone.utc)),'London')
    def test_higher_filter_is_mandatory_in_combinations(self):
        self.assertFalse(allowed('higher_liquid',dict(higher_aligned=False,session='Overlap')))
    def test_higher_series_marks_confirmation_at_close(self):
        bars=[Bar(datetime(2020,1,1,tzinfo=timezone.utc)+timedelta(hours=i),1,2,.5,1) for i in range(12)]
        times,_=higher_series(bars,'H1');self.assertEqual(times[0],bars[4].time)
    def test_partial_sma_warmup_cannot_confirm_alignment(self):
        bars=[Bar(datetime(2020,1,1,tzinfo=timezone.utc)+timedelta(hours=i),1+i/1000,2+i/1000,.5+i/1000,1+i/1000) for i in range(1200)]
        _,sides=higher_series(bars,'H1');self.assertEqual(sides[:251],[0]*251);self.assertEqual(sides[-1],1)
