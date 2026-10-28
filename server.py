import json, sqlite3, uuid, secrets, hashlib, hmac, time, os, io, csv
from sync_state import WorkspaceConnection, state_rows, modified_at, validate_snapshot
from experience_validation import normalize_experience
from resume_validation import validate_reference_resume
from workflow import workflow, validate_workflow, validate_assessments
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
ROOT=Path(__file__).parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
DB=DATA/'app.db'
def db():
 c=sqlite3.connect(DB,factory=WorkspaceConnection); c.row_factory=sqlite3.Row; c.execute('PRAGMA journal_mode=WAL'); return c
def init():
 with db() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,account TEXT UNIQUE,hash TEXT,salt TEXT); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user TEXT,csrf TEXT,expires REAL); CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,owner TEXT,kind TEXT,body TEXT,version INTEGER DEFAULT 1,deleted INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS workspace_meta(owner TEXT PRIMARY KEY,modified_at INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS sync_rollback(owner TEXT PRIMARY KEY,snapshot TEXT NOT NULL);')
  # Initialize existing workspaces once; subsequent reads never advance the clock.
  for row in c.execute('SELECT DISTINCT owner FROM records'):
   c.execute('INSERT OR IGNORE INTO workspace_meta VALUES(?,?)',(row[0],int(time.time()*1000)))
def uid(): return str(uuid.uuid4())
def password(p,s): return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
STAGES={'TO_APPLY':['APPLIED','WITHDRAWN'],'APPLIED':['SCREENING','TEST','INTERVIEW','REJECTED','WITHDRAWN'],'SCREENING':['TEST','INTERVIEW','OFFER','REJECTED','WITHDRAWN'],'TEST':['INTERVIEW','OFFER','REJECTED','WITHDRAWN'],'INTERVIEW':['INTERVIEW','OFFER','REJECTED','WITHDRAWN'],'OFFER':['ACCEPTED','REJECTED','WITHDRAWN'],'ACCEPTED':[],'REJECTED':['APPLIED','SCREENING'],'WITHDRAWN':['TO_APPLY','APPLIED']}
class APIError(Exception):
 def __init__(self,status,code,message,details=None): self.status=status; self.code=code; self.message=message; self.details=details or {}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def send(self,data=None,status=200,headers=None):
  raw=json.dumps({'requestId':uid(),'data':data,'meta':{'nextCursor':None,'hasMore':False}},ensure_ascii=False).encode(); self.send_response(status)
  for k,v in (headers or {}).items(): self.send_header(k,v)
  self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def fail(self,e):
  raw=json.dumps({'requestId':uid(),'error':{'code':e.code,'message':e.message,'details':e.details,'retryable':False}},ensure_ascii=False).encode(); self.send_response(e.status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def do_GET(self): self.handle_request()
 def do_POST(self): self.handle_request()
 def do_PUT(self): self.handle_request()
 def do_PATCH(self): self.handle_request()
 def do_DELETE(self): self.handle_request()
 def handle_request(self):
  try:
   if not self.path.startswith('/api/v1/'):
    path=ROOT/'web'/('index.html' if self.path=='/' else urlparse(self.path).path.lstrip('/')); path=path.resolve()
    if not path.is_relative_to((ROOT/'web').resolve()) or not path.is_file(): self.send_error(404); return
    raw=path.read_bytes(); self.send_response(200); self.send_header('Content-Type',{'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}.get(path.suffix,'application/octet-stream')); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
   self.api()
  except APIError as e: self.fail(e)
  except (ValueError,KeyError,TypeError): self.fail(APIError(400,'VALIDATION_FAILED','数据格式不正确，请检查输入'))
  except Exception as e: self.fail(APIError(500,'INTERNAL_ERROR','本地操作失败，请重试'))
 def api(self):
  p=urlparse(self.path).path.removeprefix('/api/v1'); parts=p.strip('/').split('/'); method=self.command
  size=int(self.headers.get('Content-Length',0))
  if size>20*1024*1024 and not p.startswith('/admin/sync/'): raise APIError(413,'PAYLOAD_TOO_LARGE','文件超过 20 MB')
  b=json.loads(self.rfile.read(size)) if size else {}
  with db() as c:
   if p=='/system/bootstrap-status': self.send({'needsBootstrap':not c.execute('SELECT 1 FROM users').fetchone()}); return
   if p in ['/system/bootstrap-admin','/auth/login']:
    account=b.get('account','').strip(); pw=b.get('password','')
    if p.endswith('bootstrap-admin'):
     if c.execute('SELECT 1 FROM users').fetchone(): raise APIError(409,'ALREADY_INITIALIZED','系统已初始化')
     if not account or len(pw)<8: raise APIError(400,'VALIDATION_FAILED','请输入账号和至少 8 位密码')
     salt=secrets.token_hex(16); user=uid(); c.execute('INSERT INTO users VALUES(?,?,?,?)',(user,account,password(pw,salt),salt))
    row=c.execute('SELECT * FROM users WHERE account=?',(account,)).fetchone()
    if not row or not hmac.compare_digest(password(pw,row['salt']),row['hash']): raise APIError(401,'INVALID_CREDENTIALS','账号或密码错误')
    token=secrets.token_hex(32); csrf=secrets.token_hex(24); c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],csrf,time.time()+86400)); self.send({'csrfToken':csrf,'user':{'account':account,'id':row['id'],'role':'ADMIN'}},headers={'Set-Cookie':f'LOCAL_SESSION={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'}); return
   cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x); token=hashlib.sha256(cookies.get('LOCAL_SESSION','').encode()).hexdigest(); session=c.execute('SELECT * FROM sessions WHERE token=? AND expires>?',(token,time.time())).fetchone()
   if not session: raise APIError(401,'TOKEN_EXPIRED','请登录本机账号')
   owner=session['user']; user=c.execute('SELECT * FROM users WHERE id=?',(owner,)).fetchone()
   if method!='GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']): raise APIError(403,'FORBIDDEN','会话验证失败，请刷新页面')
   if p=='/auth/session': self.send({'csrfToken':session['csrf'],'user':{'account':user['account'],'id':owner,'role':'ADMIN'}}); return
   if p=='/auth/logout': c.execute('DELETE FROM sessions WHERE token=?',(token,)); self.send(None,headers={'Set-Cookie':'LOCAL_SESSION=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'}); return
   if p=='/users/me/password':
    if not hmac.compare_digest(password(b.get('oldPassword',''),user['salt']),user['hash']): raise APIError(401,'INVALID_CREDENTIALS','原密码错误')
    if len(b.get('newPassword',''))<8: raise APIError(400,'VALIDATION_FAILED','新密码至少 8 位')
    salt=secrets.token_hex(16); c.execute('UPDATE users SET hash=?,salt=? WHERE id=?',(password(b['newPassword'],salt),salt,owner)); self.send({}); return
   if p in ['/system/status','/admin/storage']: self.send({'networkMode':'OFFLINE','schemaVersion':1,'databaseBytes':DB.stat().st_size,'status':'READY','lastModifiedAt':modified_at(c,owner),'hasSyncRollback':bool(c.execute('SELECT 1 FROM sync_rollback WHERE owner=?',(owner,)).fetchone())}); return
   if p=='/admin/sync' and method=='GET':
    self.send({'schemaVersion':1,'modifiedAt':modified_at(c,owner),'records':state_rows(c,owner)});return
   if p in ['/admin/sync/validate','/admin/sync/import'] and method=='POST':
    try: stamp,rows=validate_snapshot(b.get('snapshot'))
    except (ValueError,TypeError) as error: raise APIError(400,'VALIDATION_FAILED',str(error))
    current=modified_at(c,owner)
    if stamp<current: raise APIError(409,'SYNC_OLDER','导入版本早于本地版本，无法覆盖本地记录')
    if stamp==current: raise APIError(409,'SYNC_EQUAL','导入版本与本地修改时间相同，无需同步，无法覆盖')
    if p.endswith('/validate'):self.send({'modifiedAt':stamp,'currentModifiedAt':current,'count':len(rows)});return
    if b.get('expectedModifiedAt')!=current:raise APIError(409,'RESOURCE_VERSION_CONFLICT','本地资料已更新，请重新检查同步码')
    if any(c.execute('SELECT 1 FROM records WHERE id=? AND owner<>?',(r['id'],owner)).fetchone() for r in rows):raise APIError(409,'VALIDATION_FAILED','同步记录编号与其他账号冲突')
    snapshot={'schemaVersion':1,'modifiedAt':current,'records':state_rows(c,owner)}
    c.execute('INSERT INTO sync_rollback VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET snapshot=excluded.snapshot',(owner,json.dumps(snapshot,ensure_ascii=False)))
    c.execute('DELETE FROM records WHERE owner=?',(owner,))
    for r in rows:c.execute('INSERT INTO records VALUES(?,?,?,?,?,?)',(r['id'],owner,r['kind'],r['body'],r['version'],int(r['deleted'])))
    c.sync_times[owner]=stamp
    self.send({'modifiedAt':stamp,'count':len(rows)});return
   if p=='/admin/sync/previous' and method=='GET':
    row=c.execute('SELECT snapshot FROM sync_rollback WHERE owner=?',(owner,)).fetchone()
    if not row:raise APIError(404,'RESOURCE_NOT_FOUND','没有同步前备份')
    snapshot=json.loads(row[0]);payload={'schemaVersion':1,'records':[dict(r,owner=owner) for r in snapshot['records']]}
    self.send({'payload':payload,'checksum':hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()});return
   def records(kind,deleted=0): return [dict(json.loads(r['body']),id=r['id'],version=r['version'],deleted=bool(r['deleted'])) for r in c.execute('SELECT * FROM records WHERE owner=? AND kind=? AND deleted=? ORDER BY rowid DESC',(owner,kind,deleted))]
   def create(kind,body):
    id=uid(); body=dict(body,createdAt=time.strftime('%Y-%m-%dT%H:%M:%S%z')); c.execute('INSERT INTO records VALUES(?,?,?,?,1,0)',(id,owner,kind,json.dumps(body,ensure_ascii=False))); return dict(body,id=id,version=1)
   def get(id,kind=None):
    r=c.execute('SELECT * FROM records WHERE id=? AND owner=?',(id,owner)).fetchone()
    if not r or (kind and r['kind']!=kind): raise APIError(404,'RESOURCE_NOT_FOUND','记录不存在')
    return r,dict(json.loads(r['body']),id=id,version=r['version'])
   # One workspace row joins a saved job and its application without migrating existing data.
   def persist(obj):
    clean={k:v for k,v in obj.items() if k not in ['id','version','deleted']}
    c.execute('UPDATE records SET body=?,version=version+1 WHERE id=? AND owner=?',(json.dumps(clean,ensure_ascii=False),obj['id'],owner))
    return dict(clean,id=obj['id'],version=obj['version']+1)
   def workspace():
    jobs=records('jobs'); applications=records('applications'); used=set(); result=[]
    for a in applications:
     j=next((j for j in jobs if j['id']==a.get('jobId')),None)
     if not j and not a.get('jobId'):
      candidates=[j for j in jobs if all((j.get(k) or '').strip()==(a.get(k) or '').strip() for k in ['companyName','jobTitle','city'])]
      if len(candidates)==1: j=candidates[0]
     if j: used.add(j['id'])
     row=dict(j or {}); row.update(a)
     if j:
      for k in ['companyName','jobTitle','city','salary','requirements','description','sourceName','sourceUrl']: row[k]=j.get(k,a.get(k,''))
     row.update(applicationId=a['id'],applicationVersion=a['version'],jobId=j['id'] if j else None,jobVersion=j['version'] if j else None,recordId=a['id'])
     result.append(row)
    for j in jobs:
     if j['id'] not in used: result.append(dict(j,applicationId=None,applicationVersion=None,jobId=j['id'],jobVersion=j['version'],recordId=j['id'],stage='TO_APPLY'))
    for row in result: row['stageGroup'],row['stageDetail']=workflow(row)
    return result
   if p=='/workspace-records-trash':
    self.send(records('applications',1)); return
   if parts[0]=='workspace-records' and len(parts)==3 and parts[2]=='restore':
    _,a=get(parts[1],'applications')
    if a['version']!=b.get('version'): raise APIError(409,'RESOURCE_VERSION_CONFLICT','记录已更新')
    c.execute('UPDATE records SET deleted=0,version=version+1 WHERE id=? AND owner=?',(a['id'],owner))
    if a.get('jobId'): c.execute('UPDATE records SET deleted=0,version=version+1 WHERE id=? AND owner=? AND deleted=1',(a['jobId'],owner))
    self.send({}); return
   if parts[0]=='workspace-records':
    if method=='GET': self.send(workspace()); return
    fields=['companyName','jobTitle','city','salary','requirements','description','sourceName','sourceUrl']
    if len(parts)==1 and method=='POST':
     if not b.get('companyName','').strip() or not b.get('jobTitle','').strip(): raise APIError(400,'VALIDATION_FAILED','请填写公司与岗位')
     if 'applicationBase' in b and not isinstance(b['applicationBase'],str): raise APIError(400,'VALIDATION_FAILED','申请Base地需为纯文本')
     if 'stageGroup' in b:
      try: b['stage']=validate_workflow(b['stageGroup'],b.get('stageDetail',''));validate_assessments(b.get('assessments',[]))
      except ValueError as e: raise APIError(400,'VALIDATION_FAILED',str(e))
     stage=b.get('stage','TO_APPLY')
     if 'stageGroup' not in b and stage not in ['TO_APPLY','APPLIED']: raise APIError(409,'INVALID_STAGE_TRANSITION','请选择待投递或已投递')
     j=create('jobs',{k:b.get(k,'') for k in fields})
     a=create('applications',dict({k:b.get(k) for k in ['companyName','jobTitle','city','salary','applicationBase','notes','resumeId','resumeVersion','tags','stageGroup','stageDetail','assessments']},jobId=j['id'],stage=stage,sourceType=b.get('sourceType','MANUAL'),appliedAt=b.get('appliedAt') or (time.strftime('%Y-%m-%dT%H:%M:%S%z') if stage=='APPLIED' else None),history=[{'toStage':stage,'stageGroup':b.get('stageGroup'),'stageDetail':b.get('stageDetail',''),'at':time.strftime('%Y-%m-%d %H:%M'),'reason':'创建记录'}]))
     self.send(next(r for r in workspace() if r['recordId']==a['id']),201); return
    current=next((r for r in workspace() if r['recordId']==parts[1]),None)
    if not current: raise APIError(404,'RESOURCE_NOT_FOUND','记录不存在')
    for key in ['applicationVersion','jobVersion']:
     if current[key]!=b.get(key): raise APIError(409,'RESOURCE_VERSION_CONFLICT','记录已更新，请刷新重试')
    if method=='DELETE':
     # Retain both sides for recovery; shared jobs remain available to other applications.
     app_id=current['applicationId']; job_id=current['jobId']
     if not app_id:
      a=create('applications',dict({k:current.get(k) for k in fields},jobId=job_id,stage='TO_APPLY'))
      app_id=a['id']
     if job_id and not any(a.get('jobId')==job_id and a['id']!=app_id for a in records('applications')):
      c.execute('UPDATE records SET deleted=1,version=version+1 WHERE id=? AND owner=?',(job_id,owner))
     c.execute('UPDATE records SET deleted=1,version=version+1 WHERE id=? AND owner=?',(app_id,owner))
     self.send({}); return
    a=get(current['applicationId'],'applications')[1] if current['applicationId'] else None
    j=get(current['jobId'],'jobs')[1] if current['jobId'] else None
    if len(parts)==3 and parts[2] in ['undo-progress','progress-experience']:
     if method!='POST' or a is None: raise APIError(404,'RESOURCE_NOT_FOUND','进度记录不存在')
     history=a.get('history',[]); index=b.get('historyIndex')
     if not isinstance(index,int) or isinstance(index,bool) or not 0<=index<len(history): raise APIError(400,'VALIDATION_FAILED','请选择有效进度记录')
     entry=history[index]
     if not entry.get('fromStage'): raise APIError(400,'BUSINESS_RULE_VIOLATION','初始创建记录不可撤销或记录阶段经验')
     if parts[2]=='undo-progress':
      active=[i for i,h in enumerate(history) if h.get('fromStage') and not h.get('undoneAt')]
      if entry.get('undoneAt') or not active or index!=active[-1]: raise APIError(409,'BUSINESS_RULE_VIOLATION','请从最新一条进度开始撤销')
      target=(entry['stageGroup'],entry.get('stageDetail','')) if entry.get('stageGroup') else workflow({'stage':entry['toStage']})
      if workflow(a)!=target: raise APIError(409,'RESOURCE_VERSION_CONFLICT','当前阶段已变化，无法撤销此记录')
      previous=(entry['fromStageGroup'],entry.get('fromStageDetail','')) if entry.get('fromStageGroup') else workflow({'stage':entry['fromStage']})
      a['stageGroup'],a['stageDetail']=previous; a['stage']=validate_workflow(*previous)
      entry['undoneAt']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
     else:
      try: experience=normalize_experience(entry,b)
      except ValueError as error: raise APIError(400,'VALIDATION_FAILED',str(error))
      entry['experience']=dict(experience,recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
     persist(a);self.send(next(r for r in workspace() if r['recordId']==a['id']));return
    if 'resumeId' in b and b['resumeId']:
     _,resume=get(b['resumeId'],'resumes')
     if b.get('resumeVersion')!=resume['version']: raise APIError(409,'RESOURCE_VERSION_CONFLICT','简历版本已更新')
    if j is None: j=create('jobs',{k:current.get(k,'') for k in fields})
    if a is None:
     a=create('applications',dict({k:current.get(k) for k in ['companyName','jobTitle','city','salary','applicationBase']},jobId=j['id'],stage='TO_APPLY',history=[{'toStage':'TO_APPLY','at':time.strftime('%Y-%m-%d %H:%M'),'reason':'关联求职记录'}]))
    if 'assessments' in b:
     try: validate_assessments(b['assessments'])
     except ValueError as e: raise APIError(400,'VALIDATION_FAILED',str(e))
    if 'stageGroup' in b:
     try: new_stage=validate_workflow(b['stageGroup'],b.get('stageDetail',''))
     except ValueError as e: raise APIError(400,'VALIDATION_FAILED',str(e))
     if workflow(a)!=(b['stageGroup'],b.get('stageDetail','')): a.setdefault('history',[]).append({'id':uid(),'fromStageGroup':workflow(a)[0],'fromStageDetail':workflow(a)[1],'fromStage':a.get('stage'),'toStage':new_stage,'stageGroup':b['stageGroup'],'stageDetail':b.get('stageDetail',''),'at':time.strftime('%Y-%m-%d %H:%M')})
     a['stage']=new_stage
    if 'stageGroup' not in b and 'stage' in b and b['stage']!=a.get('stage','TO_APPLY'):
     old=a.get('stage','TO_APPLY'); new=b['stage']
     if new not in STAGES[old]: raise APIError(409,'INVALID_STAGE_TRANSITION','不允许此阶段变更',{'allowedStages':STAGES[old]})
     a['stage']=new; a.setdefault('history',[]).append({'fromStage':old,'toStage':new,'at':time.strftime('%Y-%m-%d %H:%M'),'reason':b.get('reason','表格更新')})
     if new=='APPLIED' and not a.get('appliedAt'): a['appliedAt']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
    if 'applicationBase' in b and not isinstance(b['applicationBase'],str): raise APIError(400,'VALIDATION_FAILED','申请Base地需为纯文本')
    job_before=dict(j)
    for k in fields:
     if k in b:
      if k in ['companyName','jobTitle'] and not str(b[k]).strip(): raise APIError(400,'VALIDATION_FAILED','公司与岗位不能为空')
      j[k]=b[k]
    for k in ['notes','resumeId','resumeVersion','tags','appliedAt','applicationBase','stageGroup','stageDetail','assessments']:
     if k in b: a[k]=b[k]
    a['jobId']=j['id']
    for k in ['companyName','jobTitle','city','salary']: a[k]=j.get(k,'')
    if any(j.get(k)!=job_before.get(k) for k in fields): j=persist(j)
    a=persist(a)
    # Shared job fields stay consistent for other applications referencing this job.
    for other in records('applications'):
     if other['id']!=a['id'] and other.get('jobId')==j['id']:
      for k in ['companyName','jobTitle','city','salary']: other[k]=j.get(k,'')
      persist(other)
    self.send(next(r for r in workspace() if r['recordId']==a['id'])); return
   if p=='/admin/backups' and method=='POST':
    payload={'schemaVersion':1,'records':[dict(r) for r in c.execute('SELECT * FROM records WHERE owner=?',(owner,))]}; content=json.dumps(payload,ensure_ascii=False); digest=hashlib.sha256(content.encode()).hexdigest(); self.send({'payload':payload,'checksum':digest}); return
   if p=='/admin/restores/validate':
    backup=b['backup']; valid=hashlib.sha256(json.dumps(backup['payload'],ensure_ascii=False).encode()).hexdigest()==backup['checksum']
    if not valid or backup['payload']['schemaVersion']!=1: raise APIError(422,'VALIDATION_FAILED','备份校验失败')
    self.send({'valid':True,'count':len(backup['payload']['records'])}); return
   if p=='/admin/restores':
    if b.get('confirmation')!='恢复本机数据': raise APIError(422,'VALIDATION_FAILED','确认短语不正确')
    backup=b['backup']; payload=backup['payload']
    if hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()!=backup['checksum'] or payload['schemaVersion']!=1: raise APIError(422,'VALIDATION_FAILED','备份校验失败')
    rollback=DATA/'backups'; rollback.mkdir(exist_ok=True)
    target=sqlite3.connect(rollback/(uid()+'.db')); source=sqlite3.connect(DB); source.backup(target); source.close(); target.close()
    rows=payload['records']
    for r in rows:
     if r['kind'] not in ['applications','resumes','jobs','interviews','reminders','match-analyses','tasks']: raise APIError(422,'VALIDATION_FAILED','未知数据类型')
     json.loads(r['body'])
    c.execute('DELETE FROM records WHERE owner=?',(owner,))
    for r in rows: c.execute('INSERT INTO records VALUES(?,?,?,?,?,?)',(r['id'],owner,r['kind'],r['body'],r['version'],r['deleted']))
    self.send({'restoredCounts':len(rows)}); return
   if p=='/job-imports':
    content=b.get('text',''); typ=b.get('type'); rows=json.loads(content) if typ=='JSON' else list(csv.DictReader(io.StringIO(content)))
    if not isinstance(rows,list): raise APIError(422,'IMPORT_FORMAT_INVALID','JSON 必须是岗位数组')
    preview=[]; existing=records('jobs'); keys={(j.get('companyName'),j.get('jobTitle'),j.get('city')) for j in existing}
    for i,r in enumerate(rows):
     normalized={'companyName':r.get('companyName',r.get('公司','')),'jobTitle':r.get('jobTitle',r.get('岗位','')),'city':r.get('city',r.get('岗位城市',r.get('城市',''))),'applicationBase':r.get('applicationBase',r.get('申请Base地','')),'salary':r.get('salary',r.get('薪资','')),'requirements':r.get('requirements',r.get('要求','')),'sourceName':b.get('name','文件导入')}; key=tuple(normalized.get(k) for k in ['companyName','jobTitle','city']); status='INVALID' if not normalized['companyName'] or not normalized['jobTitle'] else ('DUPLICATE' if key in keys else 'VALID'); keys.add(key); preview.append({'rowNumber':i+1,'status':status,'normalizedPreview':normalized})
    self.send({'rows':preview}); return
   if p=='/job-imports/confirm':
    existing={(j.get('companyName'),j.get('jobTitle'),j.get('city')) for j in records('jobs')}; count=0
    for r in b['rows']:
     key=tuple(r.get(k) for k in ['companyName','jobTitle','city'])
     if key not in existing and r.get('companyName') and r.get('jobTitle'): create('jobs',r); existing.add(key); count+=1
    self.send({'created':count}); return
   if parts[0]=='match-analyses' or (len(parts)>2 and parts[2]=='match-analyses'): raise APIError(404,'RESOURCE_NOT_FOUND','关键词匹配功能已移除')
   if p=='/applications/board': self.send(records('applications')); return
   if parts[0] not in ['applications','resumes','jobs','interviews','reminders','tasks']: raise APIError(404,'RESOURCE_NOT_FOUND','接口未实现')
   kind=parts[0]
   if len(parts)==1:
    if method=='GET': self.send(records(kind,1 if parse_qs(urlparse(self.path).query).get('deleted')==['1'] else 0)); return
    if method=='POST':
     if kind=='resumes' and b.get('content',{}).get('editorSchema') in ('honor-reference-v1','honor-reference-v2'):
      errors=validate_reference_resume(b['content'],b.get('consent'))
      if errors: raise APIError(400,'VALIDATION_FAILED',errors[0]['reason'],{'fieldErrors':errors})
     if kind in ['applications','jobs'] and (not b.get('companyName','').strip() or not b.get('jobTitle','').strip()): raise APIError(400,'VALIDATION_FAILED','请填写公司与岗位')
     if kind=='applications':
      if b.get('stage','TO_APPLY') not in ['TO_APPLY','APPLIED']: raise APIError(409,'INVALID_STAGE_TRANSITION','新投递只能选择待投递或已投递')
      b['history']=[{'toStage':b.get('stage','TO_APPLY'),'at':time.strftime('%Y-%m-%d %H:%M'),'reason':'创建投递'}]
     self.send(create(kind,b),201); return
   row,obj=get(parts[1],kind)
   if method=='GET': self.send(obj.get('history',[]) if len(parts)>2 and parts[2]=='history' else obj); return
   if kind=='applications' and len(parts)>2 and parts[2]=='interviews':
    from datetime import datetime, timedelta
    start=datetime.fromisoformat(b['startAt'])
    if start.tzinfo is None: raise APIError(400,'VALIDATION_FAILED','时间必须包含时区')
    if any(i.get('applicationId')==obj['id'] and i.get('round')==b['round'] for i in records('interviews')): raise APIError(409,'BUSINESS_RULE_VIOLATION','该轮面试已存在')
    interview=create('interviews',dict(b,applicationId=obj['id'],companyName=obj['companyName'],jobTitle=obj['jobTitle']))
    for minutes,title in [(120,'面试前提醒'),(-120,'面试复盘')]: create('reminders',{'title':obj['companyName']+' · '+title,'applicationId':obj['id'],'interviewId':interview['id'],'triggerAt':(start-timedelta(minutes=minutes)).isoformat(),'status':'SCHEDULED'})
    self.send(interview,201); return
   if method=='DELETE' or (len(parts)>2 and parts[2]=='restore'):
    if b.get('version')!=obj['version']: raise APIError(409,'RESOURCE_VERSION_CONFLICT','记录版本已更新，请刷新后重试')
    c.execute('UPDATE records SET deleted=?,version=version+1 WHERE id=?',(0 if method!='DELETE' else 1,obj['id'])); self.send({}); return
   if kind=='reminders' and len(parts)>2: b={'status':'READ' if parts[2]=='read' else 'DISMISSED','version':obj['version']}
   requested=b.get('version'); match=self.headers.get('If-Match','').strip('"')
   if requested!=obj['version'] or (match and match!=str(obj['version'])): raise APIError(409,'RESOURCE_VERSION_CONFLICT','数据已在其他页面更新，请重新加载',{'currentVersion':obj['version']})
   if kind=='resumes' and (b.get('content',{}).get('editorSchema') in ('honor-reference-v1','honor-reference-v2') or obj.get('content',{}).get('editorSchema') in ('honor-reference-v1','honor-reference-v2')):
    content=b.get('content',obj.get('content',{}))
    if obj.get('content',{}).get('editorSchema')=='honor-reference-v2': content['editorSchema']='honor-reference-v2'
    errors=validate_reference_resume(content,b.get('consent'))
    if errors: raise APIError(400,'VALIDATION_FAILED',errors[0]['reason'],{'fieldErrors':errors})
   if len(parts)>2 and parts[2]=='stage':
    to=b['toStage']; current=obj.get('stage','TO_APPLY')
    if to not in STAGES[current]: raise APIError(409,'INVALID_STAGE_TRANSITION','不能直接流转至该阶段',{'allowedStages':STAGES[current]})
    obj['stage']=to; obj.setdefault('history',[]).append({'fromStage':current,'toStage':to,'at':time.strftime('%Y-%m-%d %H:%M'),'reason':b.get('reason','手动更新')})
   else:
    if kind=='applications' and 'stage' in b and b['stage']!=obj.get('stage'): raise APIError(409,'INVALID_STAGE_TRANSITION','请使用阶段流转接口')
    obj.update({k:v for k,v in b.items() if k not in ['id','version','history','owner']})
   c.execute('UPDATE records SET body=?,version=version+1 WHERE id=?',(json.dumps(obj,ensure_ascii=False),obj['id'])); obj['version']+=1; self.send(obj)
if __name__=='__main__':
 init(); print('求职工作台已启动：http://127.0.0.1:18080',flush=True); ThreadingHTTPServer(('127.0.0.1',18080),Handler).serve_forever()
