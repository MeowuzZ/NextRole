"""Audit only explicit publication inputs, never print or inspect private user bodies."""
from pathlib import Path
import sys, zipfile, re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));from package_release import source_files
for p in source_files():
 rel=p.relative_to(ROOT)
 if any(x in rel.parts for x in ('data','.signing','releases','dist','.local-history','build','__pycache__')):raise SystemExit('Private source path: '+str(rel))
 raw=p.read_text(encoding='utf-8')
 if ''.join(map(chr,(26646,36884))) in raw:raise SystemExit('Old product branding: '+str(rel))
 if re.search(r'^-----BEGIN (?:RSA )?PRIVATE KEY-----',raw,re.M):raise SystemExit('Private key material in: '+str(rel))
for name in ('NextRole-Web.zip','NextRole-Source.zip'):
 target=ROOT/'dist'/name
 if not target.exists():continue
 with zipfile.ZipFile(target) as z:
  if z.testzip():raise SystemExit('Corrupt release archive')
  for item in z.namelist():
   p=Path(item)
   if any(x in p.parts for x in ('data','.signing','.local-history','__pycache__')) or p.suffix in ('.db','.p12','.jks','.keystore'):raise SystemExit('Private release path: '+item)
print('Publication inputs are clean:',len(source_files()),'source files; no user data or signing credentials included')
