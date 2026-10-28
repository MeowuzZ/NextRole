"""Run only with explicit authorization to store this signing identity in GitHub Secrets."""
from pathlib import Path
import subprocess, base64
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'android-client/.signing';repo='MeowuzZ/NextRole'
for name,value in [('ANDROID_KEYSTORE_BASE64',base64.b64encode((folder/'qitu-release.p12').read_bytes())),('ANDROID_KEYSTORE_PASSWORD',(folder/'password.txt').read_bytes().strip())]:
 subprocess.run(['gh','secret','set',name,'--repo',repo],input=value,check=True)
 print('Configured encrypted repository secret:',name)
