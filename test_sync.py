import unittest, tempfile, threading, json, urllib.request, urllib.error, http.cookiejar
from pathlib import Path
import server
class SyncAPI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();server.DATA=Path(cls.temp.name);server.DB=server.DATA/'app.db';server.init();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.url='http://127.0.0.1:'+str(cls.http.server_port)+'/api/v1';cls.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));cls.csrf=''
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()
 def req(self,path,method='GET',body=None):
  request=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json','X-CSRF-Token':self.csrf})
  try:
   with self.client.open(request) as response:return response.status,json.load(response)
  except urllib.error.HTTPError as error:return error.code,json.load(error)
 def data(self,path,method='GET',body=None):
  status,result=self.req(path,method,body);self.assertLess(status,300,result);return result['data']
 def test_sync_and_clock(self):
  session=self.data('/system/bootstrap-admin','POST',{'account':'sync-test','password':'test-local-1234'});self.csrf=session['csrfToken']
  self.assertEqual(self.data('/admin/storage')['lastModifiedAt'],0)
  job=self.data('/jobs','POST',{'companyName':'演示公司','jobTitle':'工程师'});stamp=self.data('/admin/storage')['lastModifiedAt'];self.assertGreater(stamp,0)
  for _ in range(3):self.data('/jobs');self.data('/admin/sync');self.data('/admin/backups','POST',{})
  self.assertEqual(self.data('/admin/storage')['lastModifiedAt'],stamp)
  job=self.data('/jobs/'+job['id'],'PATCH',{'version':job['version'],'companyName':'演示公司'})
  self.assertEqual(self.data('/admin/storage')['lastModifiedAt'],stamp)
  self.data('/jobs/'+job['id'],'DELETE',{'version':job['version']});deleted_stamp=self.data('/admin/storage')['lastModifiedAt'];self.assertGreater(deleted_stamp,stamp)
  incoming=self.data('/admin/sync');self.assertEqual(incoming['records'][0]['deleted'],1)
  self.assertNotIn('owner',incoming['records'][0]);self.assertNotIn('users',incoming)
  self.assertEqual(self.req('/admin/sync/validate','POST',{'snapshot':incoming})[0],409)
  incoming['modifiedAt']=deleted_stamp-1;status,result=self.req('/admin/sync/import','POST',{'snapshot':incoming,'expectedModifiedAt':deleted_stamp});self.assertEqual(status,409);self.assertEqual(result['error']['code'],'SYNC_OLDER')
  incoming['modifiedAt']=deleted_stamp+1000;body=json.loads(incoming['records'][0]['body']);body['jobTitle']='同步后的岗位';incoming['records'][0]['body']=json.dumps(body)
  plan=self.data('/admin/sync/validate','POST',{'snapshot':incoming});self.assertEqual(self.data('/admin/storage')['lastModifiedAt'],deleted_stamp)
  self.assertEqual(self.req('/admin/sync/import','POST',{'snapshot':incoming,'expectedModifiedAt':0})[0],409)
  self.data('/admin/sync/import','POST',{'snapshot':incoming,'expectedModifiedAt':plan['currentModifiedAt']})
  self.assertEqual(self.data('/admin/storage')['lastModifiedAt'],incoming['modifiedAt'])
  self.assertEqual(self.data('/jobs?deleted=1')[0]['jobTitle'],'同步后的岗位')
  backup=self.data('/admin/sync/previous');self.assertEqual(json.loads(backup['payload']['records'][0]['body'])['jobTitle'],'工程师');self.data('/admin/restores/validate','POST',{'backup':backup})
  restored=self.data('/jobs?deleted=1')[0];self.data('/jobs/'+restored['id']+'/restore','POST',{'version':restored['version']});self.assertGreater(self.data('/admin/storage')['lastModifiedAt'],incoming['modifiedAt'])
if __name__=='__main__':unittest.main()
