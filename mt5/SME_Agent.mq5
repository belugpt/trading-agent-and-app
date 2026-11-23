#property version "1.40"
#include <SME_Alerts.mqh>
#include <SME_Alignment.mqh>
#property strict
#property tester_indicator "SMAStrat.ex5"
#include <Trade/Trade.mqh>
input bool ExecuteTrades=false;
input double RiskPercent=1.0;
input double CostReservePercent=10.0;
input bool PopupAlerts=true;
input bool PushNotifications=false;
input ulong MagicNumber=126252;
input int FastPeriod=126;
input int SlowPeriod=252;
input int StructureLookback=50;
input double RetracementPercent=0.1;
input string IndicatorName="SMAStrat";
input int StopBufferTicks=1;
input bool CrossoverAlerts=true;
input bool SetupAlerts=true;
input bool AppAlerts=true;
CTrade trade;
int indicator=INVALID_HANDLE;
datetime processed=0;
int lastSide=0;
int AlertSide=0;
int HigherFast=INVALID_HANDLE,HigherSlow=INVALID_HANDLE,LowerFast=INVALID_HANDLE,LowerSlow=INVALID_HANDLE;
ENUM_TIMEFRAMES HigherTF;

bool Read(int buffer,int shift,double &value)
{
   double a[1];
   if(CopyBuffer(indicator,buffer,shift,1,a)!=1) return false;
   value=a[0]; return value!=EMPTY_VALUE && MathIsValidNumber(value);
}
void Notify(string message)
{
   Print(message);
   if(PopupAlerts) Alert(message);
   if(PushNotifications && !SendNotification(message)) Print("Push notification failed: ",GetLastError());
}
bool OwnedExposure()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
      if(OrderGetTicket(i)>0 && OrderGetString(ORDER_SYMBOL)==_Symbol && (ulong)OrderGetInteger(ORDER_MAGIC)==MagicNumber) return true;
   // Any position on this symbol blocks a new entry, including netting/manual exposure.
   return PositionSelect(_Symbol);
}
void CancelOpposite(int side)
{
   if(!ExecuteTrades) return;
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || OrderGetString(ORDER_SYMBOL)!=_Symbol || (ulong)OrderGetInteger(ORDER_MAGIC)!=MagicNumber) continue;
      ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if((side==0 && (type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_SELL_LIMIT)) || (side==1 && type==ORDER_TYPE_SELL_LIMIT) || (side==-1 && type==ORDER_TYPE_BUY_LIMIT))
      {
         bool ok=trade.OrderDelete(ticket);
         Notify(StringFormat("SME cancellation #%I64u: %s / %s",ticket,ok?"request sent":"failed",trade.ResultRetcodeDescription()));
      }
   }
}
int OnInit()
{
   if(PeriodSeconds(_Period)<300 || RiskPercent<=0 || RiskPercent>100 || CostReservePercent<0 || StopBufferTicks<1) return INIT_PARAMETERS_INCORRECT;
   indicator=iCustom(_Symbol,_Period,IndicatorName,FastPeriod,SlowPeriod,StructureLookback,RetracementPercent,false,100,3,10,"SME_Agent",StopBufferTicks,false,false,false,false);
   if(indicator==INVALID_HANDLE) { Print("Compile SMAStrat.mq5 in MQL5/Indicators first. Error ",GetLastError()); return INIT_FAILED; }
   HigherTF=SMEHigherTimeframe(_Period);
   HigherFast=iMA(_Symbol,HigherTF,FastPeriod,0,MODE_SMA,PRICE_OPEN);HigherSlow=iMA(_Symbol,HigherTF,SlowPeriod,0,MODE_SMA,PRICE_OPEN);
   LowerFast=iMA(_Symbol,_Period,FastPeriod,0,MODE_SMA,PRICE_OPEN);LowerSlow=iMA(_Symbol,_Period,SlowPeriod,0,MODE_SMA,PRICE_OPEN);
   if(HigherFast==INVALID_HANDLE || HigherSlow==INVALID_HANDLE || LowerFast==INVALID_HANDLE || LowerSlow==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(MagicNumber); trade.SetTypeFillingBySymbol(_Symbol);
   // Skip setup execution on attach/restart; wait for the next new candle.
   processed=iTime(_Symbol,_Period,0);
   AlertSide=SMEConfirmedSide(LowerFast,LowerSlow,_Period,TimeCurrent());
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { if(indicator!=INVALID_HANDLE) IndicatorRelease(indicator);if(HigherFast!=INVALID_HANDLE)IndicatorRelease(HigherFast);if(HigherSlow!=INVALID_HANDLE)IndicatorRelease(HigherSlow);if(LowerFast!=INVALID_HANDLE)IndicatorRelease(LowerFast);if(LowerSlow!=INVALID_HANDLE)IndicatorRelease(LowerSlow); }
void OnTradeTransaction(const MqlTradeTransaction &transaction,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(transaction.deal)) return;
   if(HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol || (ulong)HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=MagicNumber) return;
   Notify(StringFormat("SME deal #%I64u | %s | volume %.8f | price %.*f | profit %.2f",transaction.deal,
          EnumToString((ENUM_DEAL_ENTRY)HistoryDealGetInteger(transaction.deal,DEAL_ENTRY)),
          HistoryDealGetDouble(transaction.deal,DEAL_VOLUME),_Digits,HistoryDealGetDouble(transaction.deal,DEAL_PRICE),HistoryDealGetDouble(transaction.deal,DEAL_PROFIT)));
}
void OnTick()
{
   datetime bar=iTime(_Symbol,_Period,0);
   int higher=SMEConfirmedSide(HigherFast,HigherSlow,HigherTF,TimeCurrent());
   int lower=SMEConfirmedSide(LowerFast,LowerSlow,_Period,TimeCurrent());
   int confirmed=higher!=0 && higher==lower?higher:0;
   CancelOpposite(confirmed);
   double fast,slow;
   if(!Read(0,0,fast) || !Read(1,0,slow)) return;
   int side=fast>slow?1:fast<slow?-1:0;
   if(side!=0) { CancelOpposite(side); lastSide=side; }
   if(bar==0 || bar==processed || BarsCalculated(indicator)<SlowPeriod+2) return;
   if(CrossoverAlerts){
      if(AlertSide!=0 && lower!=0 && AlertSide!=lower)
         SMEAlertEvent("crossover",bar,lower,_Symbol+" "+EnumToString(_Period)+(lower==1?" bullish":" bearish")+" closed-candle SMA crossover (not an entry setup)",PopupAlerts,PushNotifications,AppAlerts);
      if(lower!=0)AlertSide=lower;
   }
   double direction,entry,stop,target;
   if(!Read(2,0,direction)) { processed=bar; return; }
   if(!Read(3,0,entry) || !Read(4,0,stop) || !Read(5,0,target)) return;
   processed=bar;
   int d=(int)direction;
   if(d!=1 && d!=-1) return;
   if(confirmed!=d) { Notify("SME: no limit submitted; closed-candle SMA alignment is unconfirmed.");return; }
   if(side!=0 && side!=d) { Notify("SME setup invalidated by opposite open-price crossover."); return; }
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0) return;
   entry=NormalizeDouble(MathRound(entry/tick)*tick,_Digits);
   stop=NormalizeDouble((d==1?MathFloor(stop/tick):MathCeil(stop/tick))*tick,_Digits);
   target=NormalizeDouble(MathRound(target/tick)*tick,_Digits);
   double loss=0;
   ENUM_ORDER_TYPE market=d==1?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double reference=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(reference<=0 || d*(entry-stop)<=0 || d*(target-entry)<=0 || !OrderCalcProfit(market,_Symbol,reference,entry,stop,loss) || loss>=0)
   { Notify("SME setup: position sizing unavailable or invalid levels."); return; }
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*RiskPercent/100.0;
   double perLot=(-loss/reference)*(1+CostReservePercent/100.0);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0) return;
   double lots=NormalizeDouble(MathFloor(MathMin(budget/perLot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))/step)*step,8);
   string message=StringFormat("SME %s %s %s | Entry %.*f SL %.*f TP %.*f | Lots %.8f | Risk budget %.2f %s | %s",_Symbol,EnumToString(_Period),d==1?"BUY LIMIT":"SELL LIMIT",_Digits,entry,_Digits,stop,_Digits,target,lots,budget,AccountInfoString(ACCOUNT_CURRENCY),ExecuteTrades?"EXECUTION ENABLED":"ALERT ONLY");
   if(SetupAlerts)SMEAlertEvent("setup",bar,d,message,PopupAlerts,PushNotifications,AppAlerts);else Print(message);
   if(lots<reference) { Notify("SME: minimum lot would exceed risk budget; skipped."); return; }
   if(!ExecuteTrades || OwnedExposure()) return;
   MqlTick quote; if(!SymbolInfoTick(_Symbol,quote)) return;
   double distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if((d==1 && quote.ask-entry<=distance) || (d==-1 && entry-quote.bid<=distance) || MathAbs(entry-stop)<distance || MathAbs(target-entry)<distance)
   { Notify("SME: midpoint passed or broker minimum distance violated; skipped."); return; }
   double margin=0;
   if(!OrderCalcMargin(market,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
   { Notify("SME: insufficient free margin; skipped."); return; }
   bool ok=d==1?trade.BuyLimit(lots,entry,_Symbol,stop,target,ORDER_TIME_GTC,0,"SME Original"):
                trade.SellLimit(lots,entry,_Symbol,stop,target,ORDER_TIME_GTC,0,"SME Original");
   uint code=trade.ResultRetcode();
   Notify(StringFormat("SME order %s: %s | ticket %I64u",ok && (code==TRADE_RETCODE_DONE || code==TRADE_RETCODE_PLACED)?"accepted":"not accepted",trade.ResultRetcodeDescription(),trade.ResultOrder()));
}
