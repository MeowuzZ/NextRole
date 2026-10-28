"""Track semantic workspace writes atomically; sync excludes credentials and sessions."""
import json, hashlib, sqlite3, time, re
KINDS={'applications','resumes','jobs','interviews','reminders','tasks','match-analyses'}
def fingerprint(rows):
 result=[]
 for row in rows:
  body=json.loads(row['body'])
  for key in ('id','version','owner','kind','deleted'):body.pop(key,None)
  result.append([row['id'],row['kind'],bool(row['deleted']),body])
 return hashlib.sha256(json.dumps(sorted(result,key=lambda r:r[0]),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def state_rows(connection,owner):
 return [dict(r) for r in connection.execute('SELECT id,kind,body,version,deleted FROM records WHERE owner=? ORDER BY rowid',(owner,))]
def modified_at(connection,owner):
 row=connection.execute('SELECT modified_at FROM workspace_meta WHERE owner=?',(owner,)).fetchone()
 return row[0] if row else 0
class WorkspaceConnection(sqlite3.Connection):
 def __enter__(self):
  self.execute('BEGIN IMMEDIATE');self.sync_times={};self.before={}
  if self.execute("SELECT 1 FROM sqlite_master WHERE name='records'").fetchone():
   for row in self.execute('SELECT DISTINCT owner FROM records'):
    self.before[row[0]]=fingerprint(state_rows(self,row[0]))
  return self
 def __exit__(self,typ,value,traceback):
  try:
   if typ is None and self.execute("SELECT 1 FROM sqlite_master WHERE name='workspace_meta'").fetchone():
    owners=set(self.before)|{r[0] for r in self.execute('SELECT DISTINCT owner FROM records')}|set(self.sync_times)
    for owner in owners:
     rows=state_rows(self,owner);changed=fingerprint(rows)!=self.before.get(owner,fingerprint([]))
     if owner in self.sync_times:stamp=self.sync_times[owner]
     elif changed:stamp=max(int(time.time()*1000),modified_at(self,owner)+1)
     else:continue
     self.execute('INSERT INTO workspace_meta(owner,modified_at) VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET modified_at=excluded.modified_at',(owner,stamp))
   return super().__exit__(typ,value,traceback)
  except BaseException:
   self.rollback();raise
  finally:self.close()

def validate_snapshot(snapshot):
 if not isinstance(snapshot,dict) or snapshot.get('schemaVersion')!=1:raise ValueError('同步码版本不支持')
 stamp=snapshot.get('modifiedAt')
 if isinstance(stamp,bool) or not isinstance(stamp,int) or not 0<=stamp<=9007199254740991:raise ValueError('同步时间不正确')
 rows=snapshot.get('records');seen=set()
 if not isinstance(rows,list):raise ValueError('同步内容格式不正确')
 for r in rows:
  if not isinstance(r,dict) or r.get('kind') not in KINDS:raise ValueError('同步记录类型不正确')
  ident=r.get('id')
  if not isinstance(ident,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',ident) or ident in seen:raise ValueError('同步记录编号不正确')
  seen.add(ident)
  if isinstance(r.get('version'),bool) or not isinstance(r.get('version'),int) or r['version']<1 or type(r.get('deleted')) not in (int,bool) or r['deleted'] not in (0,1):raise ValueError('同步记录版本不正确')
  body=json.loads(r.get('body',''))
  if not isinstance(body,dict):raise ValueError('同步记录内容不正确')
 return stamp,rows
