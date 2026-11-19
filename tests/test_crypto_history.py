import unittest
from datetime import datetime,timezone,timedelta
from sme.crypto_history import aggregate_trade_rows,repair_misaligned
from sme.model import Bar


class ArchivedCryptoRepair(unittest.TestCase):
    def test_true_trade_aggregation_not_candle_timestamp_rounding(self):
        start=datetime(2018,2,9,tzinfo=timezone.utc)
        def row(i,minutes,price,quantity):
            return [str(i),str(price),str(quantity),'0','0',str(int((start+timedelta(minutes=minutes)).timestamp()*1000))]
        bars,count=aggregate_trade_rows([row(1,28,100,2),row(2,45,105,3),row(3,59,99,1),row(4,65,102,4)],'2018-02-09')
        self.assertEqual(count,4)
        self.assertEqual(bars[0],Bar(start,100,105,99,99,6))
        self.assertEqual(bars[1].time,start+timedelta(hours=1))

    def test_rejects_out_of_order_trades(self):
        a=['1','100','1','0','0','1518138000000']
        b=['2','100','1','0','0','1518137900000']
        with self.assertRaises(ValueError):
            aggregate_trade_rows([a,b],'2018-02-09')

    def test_replaces_entire_affected_day_from_finer_source(self):
        day=datetime(2018,2,9,tzinfo=timezone.utc)
        wrong=Bar(day+timedelta(minutes=28),100,999,1,900,10)
        right=Bar(day,100,110,90,105,20)
        unaffected=Bar(day-timedelta(days=1),10,11,9,10,1)
        repaired,meta=repair_misaligned('BTCUSD',[unaffected,wrong],lambda symbol,date:([right],{'day':date}))
        self.assertEqual(repaired,[unaffected,right])
        self.assertEqual(meta[0]['replaced_misaligned_candles'],1)
