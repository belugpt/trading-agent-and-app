import tempfile,unittest,zipfile
from pathlib import Path
from datetime import datetime,timezone
from sme.m15_history import minute_archive

class GenuineM15Aggregation(unittest.TestCase):
    def parse(self,rows):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('data.csv','\n'.join(rows))
            return minute_archive(p)
    def test_real_minutes_aggregate_in_fixed_est_to_utc(self):
        bars,meta=self.parse(['20200101 170000;10;12;9;11;2','20200101 170100;11;14;10;13;3'])
        self.assertEqual(bars[0].time,datetime(2020,1,1,22,tzinfo=timezone.utc))
        self.assertEqual((bars[0].open,bars[0].high,bars[0].low,bars[0].close,bars[0].volume),(10,14,9,13,5))
        self.assertEqual(meta['partial_buckets'],1)
    def test_duplicate_minute_drops_whole_bucket(self):
        bars,meta=self.parse(['20200101 170000;10;12;9;11;2','20200101 170000;10;12;9;11;2'])
        self.assertEqual(bars,[]);self.assertEqual(meta['excluded_buckets'],1)
    def test_out_of_order_rows_keep_first_and_last_by_time(self):
        bars,_=self.parse(['20200101 170100;11;14;10;13;3','20200101 170000;10;12;9;11;2'])
        self.assertEqual((bars[0].open,bars[0].close,bars[0].volume),(10,13,5))
