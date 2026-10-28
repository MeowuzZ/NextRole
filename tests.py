import server, tempfile, threading, json, urllib.request, urllib.error, http.cookiejar, unittest
from pathlib import Path
class Flow(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(); server.DATA=Path(cls.tmp.name); server.DB=server.DATA/'app.db'; server.init(); cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler); threading.Thread(target=cls.http.serve_forever,daemon=True).start(); cls.url='http://127.0.0.1:'+str(cls.http.server_port)+'/api/v1'; cls.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())); cls.csrf=''
 @classmethod
 def tearDownClass(cls): cls.http.shutdown(); cls.http.server_close(); cls.tmp.cleanup()
 def req(self,p,m='GET',b=None,csrf=True):
  headers={'Content-Type':'application/json'}
  if csrf: headers['X-CSRF-Token']=self.csrf
  q=urllib.request.Request(self.url+p,data=json.dumps(b).encode() if b is not None else None,headers=headers,method=m)
  try:
   with self.client.open(q) as r: return r.status,json.load(r)
  except urllib.error.HTTPError as e: return e.code,json.load(e)
 def test_core(self):
  self.assertEqual(self.req('/applications')[0],401)
  s,v=self.req('/system/bootstrap-admin','POST',{'account':'test','password':'local-testing-123'}); self.assertEqual(s,200); self.csrf=v['data']['csrfToken']
  self.assertEqual(self.req('/applications','POST',{},False)[0],403)
  s,v=self.req('/applications','POST',{'companyName':'企业','jobTitle':'前端','stage':'TO_APPLY'}); self.assertEqual(s,201); a=v['data']; aid=a['id']
  self.assertEqual(self.req('/applications/'+aid+'/stage','PATCH',{'toStage':'OFFER','version':1})[0],409)
  self.assertEqual(self.req('/applications/'+aid+'/stage','PATCH',{'toStage':'APPLIED','version':1})[0],200)
  self.assertEqual(self.req('/applications/'+aid,'PATCH',{'notes':'stale','version':1})[0],409)
  self.assertEqual(len(self.req('/applications/'+aid+'/history')[1]['data']),2)
  self.assertEqual(self.req('/applications/'+aid+'/interviews','POST',{'round':1,'startAt':'2026-10-25T09:00:00+08:00','title':'技术一面'})[0],201)
  self.assertEqual(len(self.req('/reminders')[1]['data']),2)
  _,v=self.req('/resumes','POST',{'name':'简历','content':{'skills':['Vue, CSS']}}); r=v['data']
  _,v=self.req('/jobs','POST',{'companyName':'公司','jobTitle':'开发','requirements':'Vue,CSS,React'}); j=v['data']
  self.assertEqual(self.req('/jobs/'+j['id']+'/match-analyses','POST',{'resumeId':r['id'],'resumeVersion':1})[0],404)
  self.assertEqual(self.req('/match-analyses')[0],404)
  _,v=self.req('/job-imports','POST',{'type':'CSV','text':'公司,岗位,城市\n新公司,开发,上海\n新公司,开发,上海\n,错误,北京'}); self.assertEqual([r['status'] for r in v['data']['rows']],['VALID','DUPLICATE','INVALID'])
  _,v=self.req('/admin/backups','POST',{}); backup=v['data']; self.assertEqual(self.req('/admin/restores/validate','POST',{'backup':backup})[0],200)
  self.req('/applications/'+aid,'DELETE',{'version':2}); self.assertEqual(len(self.req('/applications')[1]['data']),0); self.assertEqual(len(self.req('/applications?deleted=1')[1]['data']),1)
  self.assertEqual(self.req('/admin/restores','POST',{'backup':backup,'confirmation':'恢复本机数据'})[0],200); self.assertEqual(len(self.req('/applications')[1]['data']),1)
  backup['checksum']='bad'; self.assertEqual(self.req('/admin/restores/validate','POST',{'backup':backup})[0],422)
  self.assertNotIn('local-testing-123',server.DB.read_bytes().decode('latin1'))
  # The unified workspace stores job/application changes atomically.
  status,v=self.req('/workspace-records','POST',{'companyName':'联动公司','jobTitle':'工程师','city':'杭州','requirements':'Vue,CSS','resumeId':r['id'],'resumeVersion':1})
  self.assertEqual(status,201); row=v['data']; record_id=row['recordId']; job_version=row['jobVersion']
  self.assertTrue(row['applicationId']); self.assertTrue(row['jobId'])
  status,v=self.req('/workspace-records/'+record_id,'PATCH',{'applicationVersion':row['applicationVersion'],'jobVersion':row['jobVersion'],'notes':'表格备注','stage':'APPLIED'})
  self.assertEqual(status,200); updated=v['data']; self.assertEqual(updated['jobVersion'],job_version)
  self.assertEqual(updated['stage'],'APPLIED'); self.assertTrue(updated['appliedAt'])
  self.assertEqual(self.req('/workspace-records/'+record_id,'PATCH',{'applicationVersion':row['applicationVersion'],'jobVersion':row['jobVersion'],'city':'旧页面'})[0],409)
  status,v=self.req('/workspace-records/'+record_id,'PATCH',{'applicationVersion':updated['applicationVersion'],'jobVersion':updated['jobVersion'],'city':'上海'})
  self.assertEqual(status,200); updated=v['data']
  self.assertEqual(self.req('/applications/'+updated['applicationId'])[1]['data']['city'],'上海')
  self.assertEqual(self.req('/jobs/'+updated['jobId'])[1]['data']['city'],'上海')
  self.assertEqual(self.req('/workspace-records/'+record_id,'PATCH',{'applicationVersion':updated['applicationVersion'],'jobVersion':updated['jobVersion'],'stage':'ACCEPTED','companyName':'不应写入'})[0],409)
  self.assertEqual(self.req('/jobs/'+updated['jobId'])[1]['data']['companyName'],'联动公司')
  # A job imported earlier is represented once and gains an application on edit.
  _,v=self.req('/jobs','POST',{'companyName':'导入公司','jobTitle':'测试','city':'苏州','requirements':'Vue'})
  imported_id=v['data']['id']; rows=self.req('/workspace-records')[1]['data']; imported=next(x for x in rows if x['recordId']==imported_id)
  self.assertIsNone(imported['applicationId'])
  status,v=self.req('/workspace-records/'+imported_id,'PATCH',{'applicationVersion':None,'jobVersion':1,'stage':'APPLIED'})
  self.assertEqual(status,200); promoted=v['data']; self.assertNotEqual(promoted['recordId'],imported_id)
  self.assertEqual(len([x for x in self.req('/workspace-records')[1]['data'] if x['jobId']==imported_id]),1)
  status,_=self.req('/workspace-records/'+promoted['recordId'],'DELETE',{'applicationVersion':promoted['applicationVersion'],'jobVersion':promoted['jobVersion']})
  self.assertEqual(status,200)
  self.assertFalse(any(x['jobId']==imported_id for x in self.req('/workspace-records')[1]['data']))
  archived=next(x for x in self.req('/workspace-records-trash')[1]['data'] if x['id']==promoted['applicationId'])
  self.assertEqual(self.req('/workspace-records/'+archived['id']+'/restore','POST',{'version':archived['version']})[0],200)
  self.assertEqual(len([x for x in self.req('/workspace-records')[1]['data'] if x['jobId']==imported_id]),1)
  status,base=self.req('/workspace-records','POST',{'companyName':'Base演示','jobTitle':'开发','applicationBase':'上海 / 苏州，均可'})
  self.assertEqual(status,201);base=base['data'];self.assertEqual(base['applicationBase'],'上海 / 苏州，均可')
  status,base=self.req('/workspace-records/'+base['recordId'],'PATCH',{'applicationVersion':base['applicationVersion'],'jobVersion':base['jobVersion'],'applicationBase':'杭州远程'})
  self.assertEqual(status,200);self.assertEqual(base['data']['applicationBase'],'杭州远程')
  self.req('/workspace-records/'+base['data']['recordId'],'DELETE',{'applicationVersion':base['data']['applicationVersion'],'jobVersion':base['data']['jobVersion']})
  # All new workflow choices are reachable, with repeatable assessments.
  status,flow=self.req('/workspace-records','POST',{'companyName':'流程演示','jobTitle':'测试岗','applicationBase':'杭州','stageGroup':'TEST','stageDetail':'','assessments':[{'title':'综合测评','deadline':'2026-11-01T18:00'},{'title':'技术笔试','deadline':'2026-11-03T20:30'}]})
  self.assertEqual(status,201);flow=flow['data'];self.assertEqual(flow['stageGroup'],'TEST');self.assertEqual(len(flow['assessments']),2)
  from workflow import GROUPS
  for group,details in GROUPS.items():
   for detail in details or ['']:
    status,result=self.req('/workspace-records/'+flow['recordId'],'PATCH',{'applicationVersion':flow['applicationVersion'],'jobVersion':flow['jobVersion'],'stageGroup':group,'stageDetail':detail})
    self.assertEqual(status,200);flow=result['data'];self.assertEqual((flow['stageGroup'],flow['stageDetail']),(group,detail));self.assertEqual(len(flow['assessments']),2)
  for changes in [{'stageGroup':'TEST','stageDetail':'FIRST'},{'stageGroup':'INTERVIEW','stageDetail':'PENDING'},{'assessments':[{'title':'空日期','deadline':''}]},{'assessments':[{'title':'','deadline':'2026-11-01T18:00'}]}]:
   self.assertEqual(self.req('/workspace-records/'+flow['recordId'],'PATCH',dict(changes,applicationVersion=flow['applicationVersion'],jobVersion=flow['jobVersion']))[0],400)
  status,result=self.req('/workspace-records/'+flow['recordId'],'PATCH',{'applicationVersion':flow['applicationVersion'],'jobVersion':flow['jobVersion'],'assessments':[]})
  self.assertEqual(status,200);self.assertEqual(result['data']['assessments'],[])
  # Progress undo restores precise substages, while experience notes stay attached.
  status,progress=self.req('/workspace-records','POST',{'companyName':'经验演示','jobTitle':'工程师','city':'杭州','stageGroup':'TEST','stageDetail':'','notes':'保留备注','assessments':[{'title':'技术测评','deadline':'2026-11-03T18:00'}]})
  self.assertEqual(status,201);progress=progress['data']
  def progress_request(action,extra):
   return self.req('/workspace-records/'+progress['recordId']+'/'+action,'POST',dict(extra,applicationVersion=progress['applicationVersion'],jobVersion=progress['jobVersion']))
  self.assertEqual(progress_request('undo-progress',{'historyIndex':0})[0],400)
  status,result=self.req('/workspace-records/'+progress['recordId'],'PATCH',{'applicationVersion':progress['applicationVersion'],'jobVersion':progress['jobVersion'],'stageGroup':'INTERVIEW','stageDetail':'FIRST'})
  self.assertEqual(status,200);progress=result['data'];index=len(progress['history'])-1
  self.assertEqual(progress['history'][index]['fromStageGroup'],'TEST')
  self.assertEqual(progress_request('progress-experience',{'historyIndex':index,'summary':' '})[0],400)
  status,result=progress_request('progress-experience',{'historyIndex':index,'summary':'测评复盘：先做擅长题型'});self.assertEqual(status,200);progress=result['data']
  status,result=progress_request('progress-experience',{'historyIndex':index,'experience':{'notes':'测评复盘：先做擅长题型','kind':'INTERVIEW'}});self.assertEqual(status,200);progress=result['data']
  self.assertEqual(progress['history'][index]['experience']['kind'],'TEST')
  status,result=progress_request('undo-progress',{'historyIndex':index});self.assertEqual(status,200);progress=result['data']
  self.assertEqual((progress['stageGroup'],progress['stageDetail']),('TEST',''));self.assertEqual(progress['notes'],'保留备注');self.assertEqual(len(progress['assessments']),1)
  self.assertTrue(progress['history'][index]['undoneAt']);self.assertEqual(progress['history'][index]['experience']['summary'],'测评复盘：先做擅长题型')
  self.assertEqual(progress_request('undo-progress',{'historyIndex':index})[0],409)
  for detail in ['SECOND','THIRD']:
   status,result=self.req('/workspace-records/'+progress['recordId'],'PATCH',{'applicationVersion':progress['applicationVersion'],'jobVersion':progress['jobVersion'],'stageGroup':'INTERVIEW','stageDetail':detail});self.assertEqual(status,200);progress=result['data']
  last=len(progress['history'])-1
  self.assertEqual(progress_request('undo-progress',{'historyIndex':last-1})[0],409)
  stale_version=progress['applicationVersion']
  status,result=progress_request('undo-progress',{'historyIndex':last});self.assertEqual(status,200);progress=result['data']
  self.assertEqual((progress['stageGroup'],progress['stageDetail']),('INTERVIEW','SECOND'))
  self.assertEqual(self.req('/workspace-records/'+progress['recordId']+'/undo-progress','POST',{'historyIndex':last-1,'applicationVersion':stale_version,'jobVersion':progress['jobVersion']})[0],409)
  # Full form saves without agreements; optional groups may all be empty.
  from resume_validation import _SCHEMA, _OPTIONS
  complete={'editorSchema':'honor-reference-v2'}
  for group in _SCHEMA:
   row={}
   for field in group['fields']:
    if not field['required']: continue
    row[field['key']]=_OPTIONS[field['options']][0] if field.get('options') else ('22' if field['key']=='age' else 'data:image/png;base64,aGVsbG8=' if field['type']=='photo' else '2026-10-22' if field['type']=='date' else '演示内容')
   complete[group['key']]=row if group['key']=='basics' else [row] if group['required'] else []
  complete['basics']['firstWorkCity']='杭州 / 苏州 / 远程'
  for key in ['secondJob','secondWorkCity','sourceChannel']: self.assertNotIn(key,complete['basics'])
  self.assertNotIn('relatives',complete)
  self.assertEqual(complete['papers'],[])
  status,saved=self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':1})
  self.assertEqual(status,200)
  self.assertEqual(saved['data']['content']['basics']['firstWorkCity'],'杭州 / 苏州 / 远程')
  self.assertNotIn('consent',saved['data'])
  complete['projects']=[{'projectName':'','description':'已有描述不得丢失'}]
  self.assertEqual(self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':2})[0],400)
  complete['projects']=[{'projectName':'演示项目','description':'保留描述'}]
  self.assertEqual(self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':2})[0],200)
  complete['projects']=[]
  self.assertEqual(self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':3})[0],200)
  complete['languages']=[]
  self.assertEqual(self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':4})[0],400)
  complete['languages']=[{'language':'非法字典值','certificate':'测试'}]
  self.assertEqual(self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':4})[0],400)
  complete['languages']=[{'language':'英语','certificate':'测试'}]
  complete['basics']['firstWorkCity']=''
  self.assertEqual(self.req('/resumes/'+r['id']+'/content','PUT',{'content':complete,'version':4})[0],400)

if __name__=='__main__': unittest.main()
