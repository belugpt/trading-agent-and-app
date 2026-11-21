import unittest
from unittest.mock import patch
from sme.swing_study import SwingEngine
from sme.model import Config
from test_strategy import fixture

class SwingStopTests(unittest.TestCase):
    def test_stop_is_prebreakout_origin_with_tick_buffer(self):
        for bear in (False,True):
            bars=fixture(bear);d=-1 if bear else 1
            c=Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,commission_per_million=0,max_leverage=100)
            with patch('sme.engine.moving_average',side_effect=[[-d,-d]+[d]*8,[0]*10]):
                r=SwingEngine(c).run(bars)
            t=r['trades'][0];origin=32 if bear else 8
            self.assertAlmostEqual(t['stop'],origin-d*c.pip_size/10)
            self.assertEqual(t['target'],8 if bear else 32)
