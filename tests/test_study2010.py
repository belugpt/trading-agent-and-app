import unittest
from datetime import datetime, timezone, timedelta
from dataclasses import replace
from sme.model import Bar
from sme.study2010 import merge_histories


class ExtendedHistoryMerge(unittest.TestCase):
    def bar(self,year):
        return Bar(datetime(year,1,4,tzinfo=timezone.utc),1,2,.5,1.5,0)

    def test_retains_pre_2020_and_deduplicates_identical_overlap(self):
        a,b=self.bar(2010),self.bar(2020)
        result,conflicts=merge_histories([a,b],[b])
        self.assertEqual(result,[a,b])
        self.assertEqual(conflicts,[])

    def test_conflicting_overlap_excluded_and_reported(self):
        b=self.bar(2020)
        result,conflicts=merge_histories([b],[replace(b,close=1.6)])
        self.assertEqual(result,[])
        self.assertEqual(conflicts,[b.time.isoformat()])

    def test_requested_start_and_complete_end_boundaries(self):
        start=datetime(2010,1,1,tzinfo=timezone.utc)
        end=start+timedelta(hours=2)
        bars=[replace(self.bar(2010),time=start+timedelta(hours=i)) for i in [-1,0,1,2]]
        merged,_=merge_histories(bars,[],start,end)
        self.assertEqual([b.time for b in merged],[start,start+timedelta(hours=1)])
