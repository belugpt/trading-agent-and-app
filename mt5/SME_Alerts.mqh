#ifndef SME_ALERTS_MQH
#define SME_ALERTS_MQH
string SMEJson(string value){StringReplace(value,"\\","\\\\");StringReplace(value,"\"","\\\"");StringReplace(value,"\r","\\r");StringReplace(value,"\n","\\n");StringReplace(value,"\t","\\t");return value;}
void SMEAlertEvent(string kind,datetime candle,int direction,string message,bool popup,bool push,bool queue)
{
   string id=_Symbol+"_"+IntegerToString((int)_Period)+"_"+kind+"_"+IntegerToString((long)candle);
   string safe=id;StringReplace(safe,"/","_");StringReplace(safe,"\\","_");StringReplace(safe,":","_");
   uint hash=2166136261;
   for(int j=0;j<StringLen(id);j++){hash^=(uint)StringGetCharacter(id,j);hash*=16777619;}
   string key="SMEA_"+StringSubstr(safe,0,38)+"_"+IntegerToString((long)hash);
   // Per-terminal persistent deduplication also suppresses duplicate indicator/EA alerts.
   if(queue && !GlobalVariableCheck(key+"_app")){
      FolderCreate("SMEAlerts");string file="SMEAlerts\\"+safe+".json";
      int handle=FileOpen(file,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
      if(handle!=INVALID_HANDLE){FileWriteString(handle,"{\"eventId\":\""+SMEJson(id)+"\",\"kind\":\""+kind+"\",\"symbol\":\""+SMEJson(_Symbol)+"\",\"message\":\""+SMEJson(message)+"\",\"strategyVersion\":\"confirmed-alignment-1.40\"}");FileClose(handle);GlobalVariableSet(key+"_app",(double)TimeCurrent());}
      else Print("SME alert queue write failed: ",GetLastError());
   }
   if(popup && !GlobalVariableCheck(key+"_pop")){Alert(message);GlobalVariableSet(key+"_pop",(double)TimeCurrent());}
   if(push && !GlobalVariableCheck(key+"_push")){
      if(SendNotification(message))GlobalVariableSet(key+"_push",(double)TimeCurrent());else Print("SME push failed: ",GetLastError());
   }
}
#endif
