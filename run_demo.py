#!/usr/bin/env python3
"""Launch a loopback-only YouthBridge demonstration with startup preflight."""
import os,sys,socket,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
port=int(os.environ.get('PORT','8080'))
if not 1<=port<=65535:sys.exit('PORT must be between 1 and 65535')
for f in ('server.py','static/practice.html','JUDGE_GUIDE.md','JUDGE_GUIDE.html'):
 if not (ROOT/f).is_file():sys.exit('Missing required file: '+f)
with socket.socket() as s:
 try:s.bind(('127.0.0.1',port))
 except OSError:sys.exit(f'Port {port} is unavailable. Set PORT to another local port.')
print(f'YouthBridge local demo: http://127.0.0.1:{port}/',flush=True)
print('Judge guide: open JUDGE_GUIDE.html in a browser.',flush=True)
print('Use fictional students only. Do not expose the service to the internet.',flush=True)
raise SystemExit(subprocess.call([sys.executable,str(ROOT/'server.py')],cwd=str(ROOT)))
