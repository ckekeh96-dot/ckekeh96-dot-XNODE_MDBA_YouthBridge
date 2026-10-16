"""Extra v7.1 tests: in-process integration using fictional records."""
import os,sys,tempfile,subprocess,time,urllib.request,urllib.parse,urllib.error,http.cookiejar,sqlite3,pathlib,shutil
root=pathlib.Path(__file__).parent
with tempfile.TemporaryDirectory() as d:
 shutil.copy(root/'server.py',d+'/server.py');shutil.copytree(root/'static',d+'/static')
 port='18091';env=dict(os.environ,PORT=port)
 p=subprocess.Popen([sys.executable,'-u',d+'/server.py'],cwd=d,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  base='http://127.0.0.1:'+port
  for _ in range(60):
   try:urllib.request.urlopen(base+'/health',timeout=.5);break
   except Exception:time.sleep(.1)
  jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
  def post(path,data):return op.open(base+path,urllib.parse.urlencode(data).encode()).read().decode()
  assert 'OK' in op.open(base+'/health').read().decode()
  post('/register',dict(name='Fictional Learner',email='fictional@example.test',password='PasswordExample123!',grade='11',school='Demo Club',sponsor_email='helper@example.test'))
  assert 'Waiting for sponsor' in post('/login',dict(email='fictional@example.test',password='PasswordExample123!'))
  c=sqlite3.connect(d+'/pilot.sqlite3');uid=c.execute('SELECT id FROM users').fetchone()[0];csrf=c.execute('SELECT csrf FROM sessions').fetchone()[0]
  try:post('/logout',{})
  except urllib.error.HTTPError as e:assert e.code==403
  else:raise AssertionError('logout missing CSRF protection')
  try:post('/delete-account',dict(csrf=csrf,password='incorrect'))
  except urllib.error.HTTPError as e:assert e.code==403
  else:raise AssertionError('delete missing password protection')
  post('/delete-account',dict(csrf=csrf,password='PasswordExample123!'))
  assert c.execute('SELECT count(*) FROM users').fetchone()[0]==0
  print('PASS: health, logout CSRF, account deletion authorization and erasure')
 finally:p.terminate();p.wait(timeout=5)
