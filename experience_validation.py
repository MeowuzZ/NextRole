"""Normalize stage-owned experience forms, retaining legacy plain notes."""
def normalize_experience(entry, body):
 from workflow import workflow
 group=entry.get('fromStageGroup') or workflow({'stage':entry.get('fromStage')})[0]
 data=body.get('experience')
 if data is None:
  summary=body.get('summary','')
  if not isinstance(summary,str) or not summary.strip() or len(summary)>20000: raise ValueError('请填写经验记录，最多 20000 字')
  return {'summary':summary.strip()}
 if group not in ('TEST','INTERVIEW','OFFER_CALL') or not isinstance(data,dict): raise ValueError('该开始阶段不支持经验记录')
 result={'schemaVersion':2,'kind':group}
 def text(key):
  value=data.get(key,'')
  if not isinstance(value,str) or len(value)>20000: raise ValueError('记录字段最多 20000 字')
  result[key]=value.strip();return result[key]
 if group=='TEST':
  summary=text('notes')
 elif group=='INTERVIEW':
  kind=data.get('interviewType')
  if kind not in ('GROUP','SOLO'): raise ValueError('请选择面试类型')
  result['interviewType']=kind
  if kind=='SOLO':
   count=data.get('candidateCount')
   if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=20: raise ValueError('面试候选人人数需为 1–20 的整数')
   result['candidateCount']=count
  content=[text(k) for k in ('interviewer','questions','other')]
  summary='\n'.join(x for x in content if x)
 else:
  summary='\n'.join(x for x in (text('initialOffer'),text('negotiatedOffer')) if x)
 if not summary or not summary.replace('1.','').strip(): raise ValueError('请填写经验记录')
 result['summary']=summary
 return result
