from pathlib import Path
import shutil,re
ROOT=Path(__file__).resolve().parents[1]
def prepare(target):
 target=Path(target);target.mkdir(parents=True,exist_ok=True)
 for p in (ROOT/'web').iterdir():
  if p.is_file() and p.suffix in ('.css','.js','.json','.html'):shutil.copy2(p,target/p.name)
 for name in ['local-service.js','offline-adapter.js','offline.css']:shutil.copy2(ROOT/'portable'/name,target/name)
 index=(target/'index.html').read_text()
 index=re.sub(r'((?:src|href)=")/([^"?]+)(?:\?[^\"]*)?"',r'\1\2"',index)
 index=index.replace('<script src="resume-schema.js"></script>','<script src="resume-schema.js"></script><script src="local-service.js"></script><script src="offline-adapter.js"></script>')
 index=index.replace('</head>','<link rel="stylesheet" href="offline.css"><meta http-equiv="Content-Security-Policy" content="default-src \'self\' data: blob:; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data: blob:; connect-src \'none\'; object-src \'none\'; base-uri \'none\'; form-action \'none\'"></head>')
 # The CSP must precede scripts; it is last in head, before all body scripts.
 (target/'index.html').write_text(index)
 app=(target/'app.js').read_text().replace("async function api(path,method='GET',data){", "async function api(path,method='GET',data){if(window.QituOffline)return QituOffline.request(path,method,data);")
 app=app.replace("function download(name,data){", "function download(name,data){if(window.QituNative){QituNative.exportText(name,name.endsWith('.csv')?'text/csv':'application/json',typeof data==='string'?data:JSON.stringify(data,null,2));return}")
 app=app.replace('<button id="restore">恢复备份</button>', """<button id="restore">恢复备份</button>${info.hasRollback?'<button id="rollback-backup">恢复前备份</button>':''}""")
 app=app.replace("$('#restore').onclick=", "$('#rollback-backup')?.addEventListener('click',async()=>download('NextRole恢复前备份.json',await api('/admin/rollback-backup')));$('#restore').onclick=")
 app=app.replace('本机离线服务 · 数据不上传远端','纯本地运行 · 数据不上传远端')
 (target/'app.js').write_text(app)
 return target
if __name__=='__main__':
 import sys
 prepare(sys.argv[1])
