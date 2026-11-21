#property copyright "SME research"
#property version "1.30"
#include <SME_Alignment.mqh>
#property indicator_chart_window
#property indicator_buffers 6
#property indicator_plots 2
#property indicator_label1 "126 SMA Open"
#property indicator_type1 DRAW_LINE
#property indicator_color1 clrDodgerBlue
#property indicator_label2 "252 SMA Open"
#property indicator_type2 DRAW_LINE
#property indicator_color2 clrOrange

input int FastPeriod=126;
input int SlowPeriod=252;
input int StructureLookback=50;
input double RetracementPercent=0.1;
input bool EnableAlerts=false;
input int LevelBars=100;
input int LineWidth=3;
input int LabelSize=10;
input string ObjectTag="SME_Original";
input int StopBufferTicks=1;
double Fast[],Slow[];
double Signal[],EntrySignal[],StopSignal[],TargetSignal[];
datetime lastBar=0,lastAlert=0;
string prefix;
int HigherFast=INVALID_HANDLE,HigherSlow=INVALID_HANDLE;
ENUM_TIMEFRAMES HigherTF;

void Label(string id,datetime stamp,double price,string text,color col,bool above=true)
{
   string name=prefix+"label_"+id;
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_TEXT,0,stamp,price);
   ObjectMove(0,name,0,stamp,price);
   string number="";
   if(StringFind(id,"entry_")==0) number="8";
   else if(StringFind(id,"stop_")==0) number="9";
   else if(StringFind(id,"target_")==0) number="10";
   else
   {
      int start=0;
      for(int k=0;k<StringLen(id);k++)
         if(StringGetCharacter(id,k)==95) start=k+1;
      number=StringSubstr(id,start);
   }
   ObjectSetString(0,name,OBJPROP_TEXT,number);
   ObjectSetString(0,name,OBJPROP_TOOLTIP,text+" "+DoubleToString(price,_Digits));
   ObjectSetString(0,name,OBJPROP_FONT,"Arial Bold");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,LabelSize);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,above?ANCHOR_LEFT_LOWER:ANCHOR_LEFT_UPPER);
}

void Level(string id,datetime a,datetime b,double price,color col,string label)
{
   string name=prefix+id;
   ObjectCreate(0,name,OBJ_TREND,0,a,price,b,price);
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,LineWidth);
   ObjectSetString(0,name,OBJPROP_TOOLTIP,label+" "+DoubleToString(price,_Digits));
   Label(id,a,price,label,col);
}
void Arrow(string id,datetime stamp,double price,int code,color col)
{
   string name=prefix+id;
   ObjectCreate(0,name,OBJ_ARROW,0,stamp,price);
   ObjectSetInteger(0,name,OBJPROP_ARROWCODE,code);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,2);
}
int OnInit()
{
   if(FastPeriod<1 || SlowPeriod<=FastPeriod || StructureLookback<1 || RetracementPercent<=0 || LevelBars<1 || LineWidth<1 || LineWidth>5 || LabelSize<6 || StopBufferTicks<1)
      return INIT_PARAMETERS_INCORRECT;
   if(PeriodSeconds(_Period)<300) { Print("SME requires M5 or higher."); return INIT_PARAMETERS_INCORRECT; }
   prefix=ObjectTag+"_";
   HigherTF=SMEHigherTimeframe(_Period);
   HigherFast=iMA(_Symbol,HigherTF,FastPeriod,0,MODE_SMA,PRICE_OPEN);
   HigherSlow=iMA(_Symbol,HigherTF,SlowPeriod,0,MODE_SMA,PRICE_OPEN);
   if(HigherFast==INVALID_HANDLE || HigherSlow==INVALID_HANDLE) return INIT_FAILED;
   SetIndexBuffer(0,Fast,INDICATOR_DATA); SetIndexBuffer(1,Slow,INDICATOR_DATA);
   SetIndexBuffer(2,Signal,INDICATOR_DATA); SetIndexBuffer(3,EntrySignal,INDICATOR_DATA);
   SetIndexBuffer(4,StopSignal,INDICATOR_DATA); SetIndexBuffer(5,TargetSignal,INDICATOR_DATA);
   ArraySetAsSeries(Signal,false); ArraySetAsSeries(EntrySignal,false);
   ArraySetAsSeries(StopSignal,false); ArraySetAsSeries(TargetSignal,false);
   ArraySetAsSeries(Fast,false); ArraySetAsSeries(Slow,false);
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,FastPeriod-1);
   PlotIndexSetInteger(1,PLOT_DRAW_BEGIN,SlowPeriod-1);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,LineWidth);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,LineWidth);
   IndicatorSetString(INDICATOR_SHORTNAME,"SME Original SMA OPEN");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { if(HigherFast!=INVALID_HANDLE)IndicatorRelease(HigherFast);if(HigherSlow!=INVALID_HANDLE)IndicatorRelease(HigherSlow);ObjectsDeleteAll(0,prefix); Comment(""); }

int OnCalculate(const int total,const int calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],
                const double &close[],const long &tick_volume[],const long &volume[],const int &spread[])
{
   if(total<SlowPeriod+2) return 0;
   if(BarsCalculated(HigherSlow)<SlowPeriod+2) return 0;
   ArraySetAsSeries(time,false); ArraySetAsSeries(open,false);
   ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);
   // SMA values include today's bar OPEN, which is known at the bar's start.
   double fs=0,ss=0;
   for(int i=0;i<total;i++)
   {
      fs+=open[i]; ss+=open[i];
      if(i>=FastPeriod) fs-=open[i-FastPeriod];
      if(i>=SlowPeriod) ss-=open[i-SlowPeriod];
      Fast[i]=i>=FastPeriod-1 ? fs/FastPeriod : EMPTY_VALUE;
      Slow[i]=i>=SlowPeriod-1 ? ss/SlowPeriod : EMPTY_VALUE;
   }
   if(calculated>0 && lastBar==time[total-1]) return total;
   lastBar=time[total-1]; ObjectsDeleteAll(0,prefix);
   ArrayInitialize(Signal,EMPTY_VALUE); ArrayInitialize(EntrySignal,EMPTY_VALUE);
   ArrayInitialize(StopSignal,EMPTY_VALUE); ArrayInitialize(TargetSignal,EMPTY_VALUE);
   int side=0,d=0,state=0,order=-1,serial=0;
   int priorIndex=0,postIndex=0,originIndex=0,endpointIndex=0;
   double previous=0,post=0,origin=0,endpoint=0,stop=0,entry=0,target=0;
   string status="Waiting for crossover";
   // Replay closed candles only. A midpoint signal is created at confirmation CLOSE.
   for(int i=SlowPeriod-1;i<total-1;i++)
   {
      int s=Fast[i]>Slow[i] ? 1 : Fast[i]<Slow[i] ? -1 : 0;
      int cross=(side!=0 && s!=0 && s!=side) ? s : 0;
      if(s!=0) side=s; // equality does not erase the previous strict side
      if(cross!=0)
      {
         // The open-price opposite cross cancels a pending order before any fill.
         d=cross; state=1; serial++; order=-1;
         stop=d==1 ? low[i] : high[i];
         previous=d==1 ? high[i-1] : low[i-1];
         priorIndex=i-1;
         for(int j=MathMax(0,i-StructureLookback);j<i;j++)
         {
            double candidate=d==1?high[j]:low[j];
            if(d*(candidate-previous)>0) { previous=candidate; priorIndex=j; }
         }
         string key=IntegerToString(serial)+"_";
         Label(key+"1",time[i],stop,"#"+IntegerToString(serial)+" 1 CROSS CANDLE",clrGray,d!=1);
         Label(key+"2",time[priorIndex],previous,"#"+IntegerToString(serial)+(d==1?" 2 PRIOR HIGH":" 2 PRIOR LOW"),clrGold,d==1);
         Arrow("cross_"+IntegerToString(serial),time[i],stop,d==1?233:234,clrGray);
         status="Waiting for post-cross structure";
         continue;
      }
      if(state==0) continue;
      if(state==5 && (i<1 || (Fast[i-1]>Slow[i-1]?1:Fast[i-1]<Slow[i-1]?-1:0)!=d || SMEConfirmedSide(HigherFast,HigherSlow,HigherTF,time[i])!=d))
      { state=0;status="Pending cancelled: closed-candle SMA alignment unconfirmed";continue; }
      double extreme=d==1?high[i]:low[i],opposite=d==1?low[i]:high[i];
      string key=IntegerToString(serial)+"_";
      if(state==1 && d*(extreme-previous)>0)
      {
         post=extreme; postIndex=i; state=2;
         Label(key+"3",time[i],post,d==1?"3 POST-CROSS HIGH":"3 POST-CROSS LOW",clrGold,d==1);
      }
      else if(state==2)
      {
         if(d*(extreme-post)>0)
         {
            post=extreme; postIndex=i;
            Label(key+"3",time[i],post,d==1?"3 POST-CROSS HIGH":"3 POST-CROSS LOW",clrGold,d==1);
         }
         else if(d*(post-close[i])>=MathAbs(post)*RetracementPercent/100.0)
         {
            origin=opposite; originIndex=i; state=3;
            Label(key+"4",time[i],origin,"4 SWING ORIGIN",clrAqua,d!=1);
         }
      }
      else if(state==3)
      {
         if(d*(extreme-post)>0)
         {
            endpoint=extreme; endpointIndex=i; state=4;
            // Freeze the pre-breakout swing origin as the stop reference.
            // The breakout candle's intrabar low/high has unknown ordering.
            double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
            if(tickSize<=0) tickSize=_Point;
            stop=origin-d*StopBufferTicks*tickSize;
            Label(key+"5",time[i],extreme,"5 FIRST WICK BREAKOUT",clrMagenta,d==1);
            Label(key+"6",time[i],endpoint,"6 ENDPOINT (TRACKING)",clrLimeGreen,d==1);
         }
         else if(d*(opposite-origin)<0)
         {
            origin=opposite; originIndex=i;
            Label(key+"4",time[i],origin,"4 SWING ORIGIN",clrAqua,d!=1);
         }
      }
      else if(state==4)
      {
         if(d*(extreme-endpoint)>0)
         {
            endpoint=extreme; endpointIndex=i;
            Label(key+"6",time[i],endpoint,"6 ENDPOINT (TRACKING)",clrLimeGreen,d==1);
         }
         else if(d*(endpoint-close[i])>=MathAbs(endpoint)*RetracementPercent/100.0)
         {
            entry=(origin+endpoint)/2.0; target=endpoint+d*2.0*(d*(endpoint-origin));
            Label(key+"6",time[endpointIndex],endpoint,"6 FROZEN ENDPOINT",clrLimeGreen,d==1);
            string swing=prefix+key+"swing";
            ObjectCreate(0,swing,OBJ_TREND,0,time[originIndex],origin,time[endpointIndex],endpoint);
            ObjectSetInteger(0,swing,OBJPROP_COLOR,clrLimeGreen);
            ObjectSetInteger(0,swing,OBJPROP_WIDTH,LineWidth);
            ObjectSetInteger(0,swing,OBJPROP_RAY_RIGHT,false);
            Label(key+"7",time[i+1],close[i],"7 RETRACEMENT CONFIRMED",clrWhite,d==1);
            if(d*(entry-stop)<=0 || d*(close[i]-entry)<=0)
            { state=0; status="Setup cancelled: invalid stop or midpoint already passed"; continue; }
            if((Fast[i]>Slow[i]?1:Fast[i]<Slow[i]?-1:0)!=d || SMEConfirmedSide(HigherFast,HigherSlow,HigherTF,time[i+1])!=d)
            { state=0;status="No limit: closed-candle higher timeframe SMA alignment unconfirmed";continue; }
            order=i; state=5;
            Signal[i+1]=d; EntrySignal[i+1]=entry;
            StopSignal[i+1]=stop; TargetSignal[i+1]=target;
            datetime known=time[i+1];
            datetime until=(datetime)(known+(long)LevelBars*PeriodSeconds(_Period));
            string id=IntegerToString(serial);
            Level("entry_"+id,known,until,entry,clrDeepSkyBlue,"#"+id+" 8 ENTRY 50%");
            Level("stop_"+id,known,until,stop,clrTomato,"#"+id+" 9 SWING STOP");
            Level("target_"+id,known,until,target,clrLimeGreen,"#"+id+" 10 TARGET -200");
            Arrow("signal_"+id,known,entry,d==1?241:242,d==1?clrLimeGreen:clrTomato);
            status="Pending 50% limit";
            if(EnableAlerts && calculated>0 && i==total-2 && known>lastAlert)
            { Alert(_Symbol," ",EnumToString(_Period)," SME ",d==1?"BUY LIMIT":"SELL LIMIT"," at ",DoubleToString(entry,_Digits)); lastAlert=known; }
         }
      }
      else if(state==5 && i>order)
      {
         // Visual touch only: chart OHLC cannot establish broker fill/exit sequence.
         if(d==1 ? low[i]<=entry : high[i]>=entry)
         { state=0; status="Midpoint touched (not a verified trade fill)"; }
      }
   }
   // Current OPEN can invalidate a pending order, even though its candle is not closed.
   int current=Fast[total-1]>Slow[total-1]?1:Fast[total-1]<Slow[total-1]?-1:0;
   if(state==5 && current!=0 && side!=0 && current!=side)
      status="Pending cancelled by current-bar opposite crossover";
   if(state==5 && SMEConfirmedSide(HigherFast,HigherSlow,HigherTF,time[total-1])!=d)
      status="Pending cancelled: closed higher-timeframe SMA alignment lost";
   Comment("SME Original | ",EnumToString(_Period)," | SMA ",FastPeriod,"/",SlowPeriod," OPEN\n",
           "1 Cross candle   |   2 Prior high/low   |   3 Post-cross high/low\n",
           "4 Swing origin   |   5 First breakout   |   6 Final endpoint\n",
           "7 Retracement confirmed   |   8 Midpoint entry   |   9 Stop   |   10 Target -200\n",
           status,"\nHistorical setup annotations; not live orders.");
   return total;
}
