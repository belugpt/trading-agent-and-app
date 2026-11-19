import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from dataclasses import replace
from sme.opt_features import permits,simulate,NUMERIC
from sme.optimize import specs,asset_base,window_ok,proposals
from sme.engine import Engine
from sme.model import Config
from test_strategy import fixture


class OptimizationSafety(unittest.TestCase):
    def config(self):
        return Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,commission_per_million=0,max_leverage=100)

    def run_fixture(self,rule=None,diagnostic=False):
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*8,[0]*10]):
            return simulate(fixture(),self.config(),'EURUSD',None,rule=rule,diagnostic=diagnostic)

    def test_no_filter_preserves_core_trades_and_equity(self):
        r=self.run_fixture()
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*8,[0]*10]):
            original=Engine(self.config()).run(fixture())
        for t in r['trades']:t.pop('entry_features')
        self.assertEqual(r['trades'],original['trades'])
        self.assertEqual(r['equity'],original['equity'])

    def test_filter_cancels_before_any_fill(self):
        r=self.run_fixture({'kind':'cash'})
        self.assertEqual(r['trades'],[])
        self.assertEqual(r['setups'][0]['reason'],'experimental_order_filter')

    def test_only_entry_known_features_are_candidates(self):
        self.assertTrue({'mfe','mae','duration','pnl','exit','r'}.isdisjoint(NUMERIC))
        r=self.run_fixture();t=r['trades'][0]
        self.assertLessEqual(t['entry_features']['known_at'],t['entry_time'])

    def test_diagnostic_outcomes_match_actual_geometry(self):
        real=self.run_fixture()['trades'][0]
        diagnostic=self.run_fixture(diagnostic=True)['trades'][0]
        self.assertEqual((real['entry'],real['stop'],real['target'],real['exit']),
                         (diagnostic['entry'],diagnostic['stop'],diagnostic['target'],diagnostic['exit']))

    def test_opportunity_sizing_preserves_r_and_price_geometry(self):
        real=self.run_fixture()['trades'][0]
        config=replace(self.config(),sizing='fixed_units',fixed_units=.000001)
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*8,[0]*10]):
            tiny=simulate(fixture(),config,'EURUSD',None,diagnostic=True)['trades'][0]
        self.assertEqual(tuple(real[k] for k in ['entry','stop','target','exit','entry_time','exit_time']),
                         tuple(tiny[k] for k in ['entry','stop','target','exit','entry_time','exit_time']))
        self.assertAlmostEqual(real['r_multiple'],tiny['r_multiple'],places=10)

    def test_and_rule(self):
        rule={'kind':'and','rules':[{'kind':'condition','feature':'reward_risk','op':'ge','value':2},
                                   {'kind':'condition','feature':'direction','op':'in','value':[1]}]}
        self.assertTrue(permits(rule,{'reward_risk':3,'direction':1}))
        self.assertFalse(permits(rule,{'reward_risk':3,'direction':-1}))

    def test_candidate_mandatory_rules_remain_fixed(self):
        self.assertEqual(len(specs()),26)
        for spec in specs():
            c=replace(asset_base('CHFJPY'),**spec['changes'])
            c.validate()
            self.assertEqual((c.entry_fraction,c.extension,c.stop_buffer,c.ma_source),(.5,2,0,'open'))
            self.assertEqual((c.pip_size,c.spread,c.max_leverage),(.01,.02,30))

    def test_future_training_labels_do_not_change_proposals(self):
        start=datetime(2010,1,1,tzinfo=timezone.utc);end=datetime(2014,1,1,tzinfo=timezone.utc)
        rows=[]
        for i in range(40):
            stamp=datetime(2010+i//10,1,5,tzinfo=timezone.utc).isoformat()
            rows.append(dict(r=2 if i%2 else -1,entry_time=stamp,exit_time=stamp,crossover_time=stamp,safe=True,
                             features={**{k:float(i%7) for k in NUMERIC},'direction':1,'order_session':'Europe','order_weekday':1}))
        a=proposals([dict(id='baseline',rows=rows)],start,end)
        future=dict(rows[-1],r=999,entry_time='2025-01-01T00:00:00+00:00',exit_time='2025-02-01T00:00:00+00:00')
        b=proposals([dict(id='baseline',rows=rows+[future])],start,end)
        self.assertEqual(a,b)

    def test_windows_with_missing_data_are_rejected(self):
        bars=fixture()
        bars[-1]=replace(bars[-1],time=bars[-2].time+timedelta(days=20))
        valid,reason=window_ok(bars,bars[0].time,bars[-1].time+timedelta(hours=1))
        self.assertFalse(valid)
        self.assertIn('gap',reason)
