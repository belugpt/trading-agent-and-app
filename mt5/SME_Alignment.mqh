#ifndef SME_ALIGNMENT_MQH
#define SME_ALIGNMENT_MQH
ENUM_TIMEFRAMES SMEHigherTimeframe(ENUM_TIMEFRAMES lower)
{
   if(PeriodSeconds(lower)<PeriodSeconds(PERIOD_H1)) return PERIOD_H1;
   if(PeriodSeconds(lower)<PeriodSeconds(PERIOD_H4)) return PERIOD_H4;
   if(PeriodSeconds(lower)<PeriodSeconds(PERIOD_D1)) return PERIOD_D1;
   if(lower==PERIOD_D1) return PERIOD_W1;
   return PERIOD_MN1;
}
int SMEConfirmedSide(int fastHandle,int slowHandle,ENUM_TIMEFRAMES tf,datetime decision)
{
   // The candle containing decision is still forming: only its predecessor confirms alignment.
   int current=iBarShift(_Symbol,tf,decision,false);
   if(current<0) return 0;
   int closed=current+1;
   double fast[1],slow[1];
   if(CopyBuffer(fastHandle,0,closed,1,fast)!=1 || CopyBuffer(slowHandle,0,closed,1,slow)!=1) return 0;
   if(fast[0]==EMPTY_VALUE || slow[0]==EMPTY_VALUE || !MathIsValidNumber(fast[0]) || !MathIsValidNumber(slow[0])) return 0;
   return fast[0]>slow[0]?1:fast[0]<slow[0]?-1:0;
}
#endif
