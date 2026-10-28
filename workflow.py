from datetime import datetime
GROUPS={'RESUME':['SUBMITTED','REVISION'],'TEST':[],'INTERVIEW':['GROUP','FIRST','SECOND','THIRD'],'OFFER_CALL':['ACCEPTED','PENDING','REJECTED','WITHDRAWN'],'TERMINATED':[]}
def workflow(row):
 if row.get('stageGroup') in GROUPS:return row['stageGroup'],row.get('stageDetail','')
 return {'TO_APPLY':('RESUME','REVISION'),'APPLIED':('RESUME','SUBMITTED'),'SCREENING':('RESUME','SUBMITTED'),'TEST':('TEST',''),'INTERVIEW':('INTERVIEW','FIRST'),'OFFER':('OFFER_CALL','PENDING'),'ACCEPTED':('OFFER_CALL','ACCEPTED'),'REJECTED':('OFFER_CALL','REJECTED'),'WITHDRAWN':('OFFER_CALL','WITHDRAWN'),'TERMINATED':('TERMINATED','')}.get(row.get('stage'),('RESUME','REVISION'))
def validate_workflow(group,detail):
 if group not in GROUPS or (detail not in GROUPS[group] if GROUPS[group] else bool(detail)):raise ValueError('请选择有效的阶段及子阶段')
 return {'RESUME':{'SUBMITTED':'APPLIED','REVISION':'TO_APPLY'},'OFFER_CALL':{'ACCEPTED':'ACCEPTED','PENDING':'OFFER','REJECTED':'REJECTED','WITHDRAWN':'WITHDRAWN'}}.get(group,{}).get(detail,{'TEST':'TEST','INTERVIEW':'INTERVIEW','TERMINATED':'TERMINATED'}.get(group))
def validate_assessments(rows):
 if not isinstance(rows,list) or len(rows)>100:raise ValueError('测评最多 100 项')
 for row in rows:
  if not isinstance(row,dict) or not isinstance(row.get('title'),str) or not row['title'].strip():raise ValueError('请填写测评标题')
  if not isinstance(row.get('deadline'),str) or 'T' not in row['deadline']:raise ValueError('请填写测评截止日期时间')
  try:datetime.fromisoformat(row['deadline'])
  except ValueError:raise ValueError('请填写有效的测评截止日期时间')
 return rows
