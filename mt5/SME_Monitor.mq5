#property strict
#property version "1.10"
input string SiteOrigin="";
input string ServiceToken="";
input string AccountAlias="demo-primary";
input string TerminalId="terminal-1";
input string StrategyVersion="confirmed-alignment-1.40";
input int HeartbeatSeconds=60;
input int AlertPollSeconds=5;
datetime LastHeartbeat=0;
void DrainAlerts()
{
   string name;long search=FileFindFirst("SMEAlerts\\*.json",name);
   if(search==INVALID_HANDLE)return;
   int count=0;
   do {
      if(++count>10)break;
      string file="SMEAlerts\\"+name;int handle=FileOpen(file,FILE_READ|FILE_TXT|FILE_ANSI,0,CP_UTF8);
      if(handle==INVALID_HANDLE)continue;
      string body=FileReadString(handle);FileClose(handle);
      if(StringLen(body)<2)continue;
      StringReplace(body,"\"eventId\":\"","\"eventId\":\""+Escape(TerminalId)+":");
      body=StringSubstr(body,0,StringLen(body)-1)+",\"account\":\""+Escape(AccountAlias)+"\",\"terminal\":\""+Escape(TerminalId)+"\"}";
      char data[],result[];string headers;int length=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);ArrayResize(data,length-1);
      int status=WebRequest("POST",SiteOrigin+"/api/bridge","Content-Type: application/json\r\nOAI-Sites-Authorization: Bearer "+ServiceToken+"\r\n",5000,data,result,headers);
      string acknowledgement=CharArrayToString(result,0,-1,CP_UTF8);
      if(status>=200 && status<300 && StringFind(acknowledgement,"\"id\":")>=0)FileDelete(file);else {Print("SME queued alert not acknowledged; HTTP ",status);break;}
   }while(FileFindNext(search,name));
   FileFindClose(search);
}
string Escape(string s){StringReplace(s,"\\","\\\\");StringReplace(s,"\"","\\\"");StringReplace(s,"\r","\\r");StringReplace(s,"\n","\\n");StringReplace(s,"\t","\\t");return s;}
bool Send(string kind,string id,string message,string extra="")
{
   string body="{\"eventId\":\""+Escape(TerminalId+":"+id)+"\",\"kind\":\""+kind+"\",\"account\":\""+Escape(AccountAlias)+"\",\"terminal\":\""+Escape(TerminalId)+"\",\"strategyVersion\":\""+Escape(StrategyVersion)+"\",\"symbol\":\""+Escape(_Symbol)+"\",\"message\":\""+Escape(message)+"\""+extra+"}";
   char data[],result[];string headers;
   int length=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
   if(length>0) ArrayResize(data,length-1);
   string requestHeaders="Content-Type: application/json\r\nOAI-Sites-Authorization: Bearer "+ServiceToken+"\r\n";
   int status=WebRequest("POST",SiteOrigin+"/api/bridge",requestHeaders,5000,data,result,headers);
   if(status<200 || status>=300){Print("SME monitor delivery failed. HTTP ",status," terminal error ",GetLastError(),". Check origin allowlist and service access; event not queued.");return false;}
   return true;
}
int OnInit()
{
   if(StringFind(SiteOrigin,"https://")!=0 || StringLen(ServiceToken)==0 || HeartbeatSeconds<15 || StringLen(TerminalId)==0 || StringLen(AccountAlias)==0)
   {Print("Set HTTPS SiteOrigin (without trailing slash), service token, terminal/account aliases, and heartbeat >=15 seconds.");return INIT_PARAMETERS_INCORRECT;}
   if(StringSubstr(SiteOrigin,StringLen(SiteOrigin)-1)=="/")return INIT_PARAMETERS_INCORRECT;
   if(AlertPollSeconds<5)return INIT_PARAMETERS_INCORRECT;
   EventSetTimer(AlertPollSeconds);return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){EventKillTimer();}
void OnTimer()
{
   DrainAlerts();
   if(TimeCurrent()-LastHeartbeat<HeartbeatSeconds)return;
   LastHeartbeat=TimeCurrent();
   bool demo=(ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO;
   string extra=",\"equity\":"+DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2)+",\"balance\":"+DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2)+",\"mode\":\""+(demo?"demo":"live")+"\"";
   Send("heartbeat","heartbeat:"+IntegerToString((long)TimeGMT()),"Terminal reporting",extra);
}
void OnTradeTransaction(const MqlTradeTransaction &transaction,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(transaction.deal))return;
   if(HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol)return;
   string message=StringFormat("Deal #%I64u %s | lots %.8f | price %.*f | profit %.2f",transaction.deal,EnumToString((ENUM_DEAL_ENTRY)HistoryDealGetInteger(transaction.deal,DEAL_ENTRY)),HistoryDealGetDouble(transaction.deal,DEAL_VOLUME),_Digits,HistoryDealGetDouble(transaction.deal,DEAL_PRICE),HistoryDealGetDouble(transaction.deal,DEAL_PROFIT));
   Send("deal","deal:"+IntegerToString((long)transaction.deal),message);
}
