import unittest
from dataclasses import replace
from unittest.mock import patch
from sme.exit_research import ExitEngine,VARIANTS,simulate_exit
from sme.engine import Engine
from sme.model import Config
from test_strategy import fixture


class ExitResearchTests(unittest.TestCase):
    def config(self):
        return Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,
                      commission_per_million=0,max_leverage=100)

    def run_policy(self,policy,bars=None):
        bars=bars or fixture()
        c=self.config()
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*(len(bars)-2),[0]*len(bars)]):
            return simulate_exit(bars,c,'EURUSD',None,policy)

    def test_baseline_exit_metrics_preserved(self):
        r=self.run_policy(VARIANTS[0])
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*8,[0]*10]):
            original=Engine(self.config()).run(fixture())
        self.assertEqual(r['metrics'],original['metrics'])
        self.assertEqual(r['equity'],original['equity'])

    def test_minus100_uses_one_range(self):
        a=self.run_policy(VARIANTS[0])['trades'][0]
        b=self.run_policy(VARIANTS[1])['trades'][0]
        self.assertEqual((a['entry'],a['stop']),(b['entry'],b['stop']))
        self.assertEqual((a['target'],b['target']),(32,24))

    def test_runner_does_not_exit_at_reference_target(self):
        r=self.run_policy(VARIANTS[5]);t=r['trades'][0]
        self.assertEqual(t['status'],'Open')
        self.assertFalse(t['target_active'])
        self.assertEqual(t['target'],32)

    def test_no_fill_bar_extrema_or_current_bar_information(self):
        e=ExitEngine(self.config(),exit_policy=VARIANTS[4]);e.bars=fixture()
        t=dict(entry=12,entry_index=8,direction=1,stop=5,initial_risk_price=7)
        e.update_trail(t,9)
        self.assertEqual(t['stop'],5)
        self.assertNotIn('trail_activated',t)

    def test_ratchet_is_next_bar_and_never_loosened(self):
        bars=fixture();bars.append(replace(bars[-1],time=bars[-1].time.replace(hour=10),open=32,high=34,low=30,close=31))
        e=ExitEngine(self.config(),exit_policy=VARIANTS[4]);e.bars=bars
        t=dict(entry=12,entry_index=8,direction=1,stop=5,initial_risk_price=7)
        e.update_trail(t,10)
        self.assertEqual(t['stop'],26)
        self.assertEqual(t['trail_updates'][0]['known_at'],e.stamp(9))
        self.assertEqual(t['trail_updates'][0]['active_from'],e.stamp(10,False))
        e.bars[9]=replace(e.bars[9],high=20,close=19)
        e.update_trail(t,10)
        self.assertEqual(t['stop'],26)

    def test_short_ratchet_uses_ask_prices(self):
        c=replace(self.config(),spread=.2)
        e=ExitEngine(c,exit_policy=VARIANTS[4]);e.bars=fixture(True)
        e.bars.append(replace(e.bars[-1],time=e.bars[-1].time.replace(hour=10)))
        t=dict(entry=28,entry_index=8,direction=-1,stop=35,initial_risk_price=7)
        e.update_trail(t,10)
        self.assertAlmostEqual(t['stop'],14.2)

    def test_runner_trailing_stop_obeys_adverse_gap(self):
        bars=fixture()
        bars.append(replace(bars[-1],time=bars[-1].time.replace(hour=10),open=25,high=30,low=24,close=28))
        t=self.run_policy(VARIANTS[4],bars)['trades'][0]
        self.assertEqual(t['stop'],26)
        self.assertEqual(t['exit'],25)
        self.assertTrue(t['trailing_stop_exit'])

    def test_current_extrema_cannot_change_new_stop(self):
        bars=fixture();bars.append(replace(bars[-1],time=bars[-1].time.replace(hour=10)))
        e=ExitEngine(self.config(),exit_policy=VARIANTS[4]);e.bars=bars
        a=dict(entry=12,entry_index=8,direction=1,stop=5,initial_risk_price=7)
        e.update_trail(a,10)
        e.bars[10]=replace(e.bars[10],high=10000,low=.1,close=50)
        b=dict(entry=12,entry_index=8,direction=1,stop=5,initial_risk_price=7)
        e.update_trail(b,10)
        self.assertEqual(a,b)
