import csv
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from sme.model import Config
from sme.data import load_csv,quality
from sme.analytics import wilson,bootstrap,trade_stats
from sme.configuration import save,load
from sme.server import resample_h4
from test_strategy import controlled,fixture


class DataAndAnalytics(unittest.TestCase):
    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'c.json'
            save(p,Config())
            self.assertEqual(load(p),Config())

    def test_timezone_normalized_and_volume_optional(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'b.csv'
            p.write_text('timestamp,open,high,low,close\n2020-01-01T01:00:00+01:00,1,2,0.5,1.5\n')
            bars=load_csv(p)
            self.assertEqual(bars[0].time,datetime(2020,1,1,tzinfo=timezone.utc))
            self.assertEqual(bars[0].volume,0)

    def test_csv_mixed_instruments_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'b.csv'
            p.write_text('timestamp,open,high,low,close,instrument\n2020-01-01T00:00:00Z,1,2,.5,1,A\n2020-01-01T01:00:00Z,1,2,.5,1,B\n')
            with self.assertRaises(ValueError):
                load_csv(p)

    def test_wilson_zero_and_finite_sample(self):
        self.assertEqual(wilson(0,0),[None,None])
        lo,hi=wilson(5,10)
        self.assertLess(lo,.5)
        self.assertGreater(hi,.5)

    def test_equity_reconciles_closed_pnl(self):
        r=controlled()
        self.assertAlmostEqual(r['equity'][-1]['equity'],10000+sum(t['pnl'] for t in r['trades']))
        self.assertEqual(r['metrics']['completed_trades'],1)

    def test_profit_factor_is_null_without_losses(self):
        self.assertIsNone(controlled()['metrics']['profit_factor'])

    def test_bootstrap_seed_reproducible(self):
        trades=controlled()['trades']*3
        self.assertEqual(bootstrap(trades,20),bootstrap(trades,20))

    def test_h4_drops_incomplete_groups(self):
        bars=fixture()
        out=resample_h4(bars)
        self.assertEqual(len(out),2)
        self.assertEqual(out[0].open,bars[0].open)
        self.assertEqual(out[0].close,bars[3].close)
        self.assertEqual(out[0].high,max(b.high for b in bars[:4]))

    def test_json_finite_metrics_empty_sample(self):
        r=controlled(fixture()[:3])
        json.dumps(r,allow_nan=False)
        self.assertEqual(r['metrics']['total_trades'],0)
        self.assertIsNone(r['metrics']['win_rate'])

if __name__=='__main__':
    unittest.main()
