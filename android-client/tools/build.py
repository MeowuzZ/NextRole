"""Build a signed NextRole APK using an installed Android SDK; no Gradle required."""
from pathlib import Path
import os, subprocess, shutil, sys, secrets, zipfile, re
ROOT=Path(__file__).resolve().parents[2];PROJECT=ROOT/'android-client';BUILD=PROJECT/'build';BUILD.mkdir(exist_ok=True)
SDK=Path(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME') or str(Path.home()/'Library/Android/sdk'))
TOOLS=SDK/'build-tools'/os.environ.get('ANDROID_BUILD_TOOLS_VERSION','34.0.0');ANDROID=SDK/'platforms/android-34/android.jar'
local_java=Path('/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home')
JAVA=Path(os.environ['JAVA_HOME']) if os.environ.get('JAVA_HOME') else local_java if local_java.exists() else Path(shutil.which('java') or '/usr/bin/java').resolve().parents[1]
version=os.environ.get('NEXTROLE_VERSION_NAME',(ROOT/'VERSION').read_text().strip())
if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?',version):raise SystemExit('Invalid release version')
manifest=(PROJECT/'AndroidManifest.xml').read_text();base_code=int(re.search(r'versionCode="(\d+)"',manifest)[1]);code=int(os.environ.get('NEXTROLE_VERSION_CODE',base_code))
if not 0<code<=2147483647:raise SystemExit('Invalid Android version code')
manifest=re.sub(r'versionCode="[^"]+"',f'versionCode="{code}"',manifest);manifest=re.sub(r'versionName="[^"]+"',f'versionName="{version}"',manifest)
(BUILD/'AndroidManifest.xml').write_text(manifest)
def run(args,**kwargs):
 print('Running:',Path(str(args[0])).name,flush=True)
 return subprocess.run([str(x) for x in args],check=True,**kwargs)
sys.path.insert(0,str(ROOT/'portable'));from package_assets import prepare
assets=BUILD/'assets/www'
if assets.exists():shutil.rmtree(assets)
prepare(assets)
run([TOOLS/'aapt2','compile','--dir',PROJECT/'res','-o',BUILD/'resources.zip'])
run([TOOLS/'aapt2','link','-o',BUILD/'base.apk','--manifest',BUILD/'AndroidManifest.xml','-I',ANDROID,'-A',BUILD/'assets','--min-sdk-version','26','--target-sdk-version','34',BUILD/'resources.zip'])
classes=BUILD/'classes'
if classes.exists():shutil.rmtree(classes)
classes.mkdir()
run([JAVA/'bin/javac','-encoding','UTF-8','--release','8','-classpath',ANDROID,'-d',classes,*sorted((PROJECT/'src').rglob('*.java'))])
with zipfile.ZipFile(BUILD/'classes.jar','w',zipfile.ZIP_DEFLATED) as z:
 for p in classes.rglob('*.class'):z.write(p,p.relative_to(classes))
dex=BUILD/'dex'
if dex.exists():shutil.rmtree(dex)
dex.mkdir();env=os.environ.copy();env['JAVA_HOME']=str(JAVA)
run([TOOLS/'d8','--release','--min-api','26','--lib',ANDROID,'--output',dex,BUILD/'classes.jar'],env=env)
unsigned=BUILD/'unsigned.apk';shutil.copyfile(BUILD/'base.apk',unsigned)
with zipfile.ZipFile(unsigned,'a',zipfile.ZIP_DEFLATED) as z:
 for p in dex.glob('*.dex'):z.write(p,p.name)
run([TOOLS/'zipalign','-f','-p','4',unsigned,BUILD/'aligned.apk'])
signing=PROJECT/'.signing';signing.mkdir(mode=0o700,exist_ok=True)
# Retain the existing certificate and package id so installed clients can upgrade.
key=Path(os.environ.get('NEXTROLE_KEYSTORE',str(signing/'qitu-release.p12')))
password_file=Path(os.environ.get('NEXTROLE_KEYSTORE_PASSWORD_FILE',str(signing/'password.txt')))
if not key.exists():
 if os.environ.get('CI'):raise SystemExit('Missing Android signing secrets; refusing to create a different CI signing identity')
 password_file.write_text(secrets.token_urlsafe(32));password_file.chmod(0o600)
 keyenv=env.copy();keyenv['NEXTROLE_SIGN_PASS']=password_file.read_text().strip()
 run([JAVA/'bin/keytool','-genkeypair','-keystore',key,'-storetype','PKCS12','-storepass:env','NEXTROLE_SIGN_PASS','-keypass:env','NEXTROLE_SIGN_PASS','-alias','qitu','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=NextRole Local, OU=Offline, O=NextRole, C=CN'],env=keyenv)
 key.chmod(0o600)
release=ROOT/'releases';release.mkdir(exist_ok=True);apk=release/f'NextRole-Android-{version}.apk'
run([TOOLS/'apksigner','sign','--ks',key,'--ks-key-alias',os.environ.get('NEXTROLE_KEY_ALIAS','qitu'),'--ks-pass','file:'+str(password_file),'--out',apk,BUILD/'aligned.apk'],env=env)
verified=run([TOOLS/'apksigner','verify','--verbose','--print-certs',apk],env=env,capture_output=True,text=True)
actual=re.search(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]+)',verified.stdout)
expected=(PROJECT/'signing-certificate.sha256').read_text().strip()
if not actual or actual[1]!=expected:raise SystemExit('Signing certificate does not match the installed-client certificate')
run([TOOLS/'zipalign','-c','4',apk]);print('Verified APK:',apk,flush=True)
