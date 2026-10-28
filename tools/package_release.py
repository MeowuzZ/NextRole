"""Build public distribution bundles from an explicit, data-free source allowlist."""
from pathlib import Path
import sys, argparse, shutil, zipfile, hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'portable'));from package_assets import prepare
ROOT_FILES=['README.md','CHANGELOG.md','VERSION','.gitignore','server.py','workflow.py','resume_validation.py','experience_validation.py','sync_state.py','tests.py','test_experience.py','test_sync.py','启动工作台.command']
SOURCE_DIRS=['web','portable','android-client','tools','docs','.github']
def source_files():
 files=[ROOT/name for name in ROOT_FILES if (ROOT/name).is_file()]
 for folder in SOURCE_DIRS:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and not any(part in ('build','.signing','__pycache__') for part in p.relative_to(ROOT/folder).parts) and p.suffix not in ('.p12','.jks','.keystore','.pyc','.log'):files.append(p)
 return sorted(set(files))
def build(output,apk):
 output=output.resolve();output.mkdir(parents=True,exist_ok=True);folder=output/'NextRole-Web'
 if folder.exists():shutil.rmtree(folder)
 prepare(folder);(folder/'使用说明.txt').write_text('NextRole 本地求职工作台\n\n完整解压后使用 Chrome / Edge 打开 index.html，无需启动服务器。\n资料仅保存在当前浏览器的本地存储中。迁移或更新文件位置前，请生成同步码保存资料。\n总表右上角：生成同步码 / 导入同步码。包含回收站，仅允许较新版本覆盖。\n密码选填；填写后导入须使用相同密码，未设密码时持码者可恢复资料。\n设置页保留资料备份与同步前备份恢复入口。\n发布包初次打开为空白，不包含任何用户资料。\n',encoding='utf-8')
 for filename,files,relative in [('NextRole-Web.zip',list(folder.rglob('*')),output),('NextRole-Source.zip',source_files(),ROOT)]:
  with zipfile.ZipFile(output/filename,'w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(files):
    if p.is_file():z.write(p,p.relative_to(relative))
 if not apk.is_file():raise SystemExit('Build the APK before packaging')
 shutil.copy2(apk,output/'NextRole.apk')
 assets=[output/name for name in ('NextRole-Web.zip','NextRole-Source.zip','NextRole.apk')]
 (output/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in assets))
 for p in assets:
  if p.suffix=='.zip':
   with zipfile.ZipFile(p) as z:
    if z.testzip():raise SystemExit('Archive verification failed')
    for name in z.namelist():
     parts=Path(name).parts
     if any(part in ('data','.signing','__pycache__') for part in parts) or Path(name).suffix in ('.db','.p12','.jks','.keystore'):raise SystemExit('Private file in release: '+name)
 print('Public release assets verified:',output)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');parser.add_argument('--apk',type=Path,default=ROOT/'releases'/('NextRole-Android-'+(ROOT/'VERSION').read_text().strip()+'.apk'));args=parser.parse_args();build(args.output,args.apk)
