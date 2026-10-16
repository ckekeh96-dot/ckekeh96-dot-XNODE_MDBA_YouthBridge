#!/usr/bin/env python3
"""Read-only local demo smoke checks. Run while the server is running."""
import os,sys,urllib.request,urllib.error
port=int(os.environ.get('PORT','8080'))
base=f'http://127.0.0.1:{port}'
for path,needle in [('/health',b'YouthBridge local pilot OK'),('/',b'YouthBridge'),('/practice',b''),('/static/practice.html',b'html')]:
 try:
  with urllib.request.urlopen(base+path,timeout=4) as response:
   body=response.read();assert response.status==200 and needle.lower() in body.lower(),path
  print('PASS',path)
 except (urllib.error.URLError,AssertionError) as e:print('FAIL',path,str(e));sys.exit(1)
print('Smoke checks passed; browser interactions and security review still required.')
