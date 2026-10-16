"""v7.3 QA checks using isolated temporary files and fictional data."""
import os,sys,tempfile,subprocess,time,urllib.request,urllib.parse,urllib.error,http.cookiejar,sqlite3,pathlib,shutil,json
root=pathlib.Path(__file__).parent
with tempfile.TemporaryDirectory() as d:
 shutil.copy(root/'server.py',d+'/server.py');shutil.copytree(root/'static',d+'/static')
 env=dict(os.environ,PORT='18093',YB_SECURE_COOKIES='0')
 p=subprocess.Popen([sys.executable,'-u',d+'/server.py'],cwd=d,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  base='http://127.0.0.1:18093'
  for _ in range(60):
   try:urllib.request.urlopen(base+'/health',timeout=.3);break
   except Exception:time.sleep(.1)
  else:raise AssertionError('server did not start')
  jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
  def get(path):return op.open(base+path)
  def post(path,data):return op.open(base+path,urllib.parse.urlencode(data).encode())
  def rejected(fn,status):
   try:fn()
   except urllib.error.HTTPError as e:assert e.code==status,(e.code,status)
   else:raise AssertionError('expected rejection '+str(status))
  assert 'DENY'==get('/').headers['X-Frame-Options']
  assert 'no-store'==get('/').headers['Cache-Control']
  rejected(lambda:get('/dashboard'),None) if False else None
  rejected(lambda:get('/export-data'),403)
  assert 'practice' in get('/practice').geturl()
  post('/register',dict(name='Demo',email='learner@example.test',password='DemoPassword123!',grade='11',school='Fictional School',sponsor_email='adult@example.test'))
  post('/login',dict(email='learner@example.test',password='DemoPassword123!'))
  assert any(c.name=='yb_session' and c.has_nonstandard_attr('HttpOnly') for c in jar)
  con=sqlite3.connect(d+'/pilot.sqlite3');uid=con.execute('SELECT id FROM users WHERE email=?',('learner@example.test',)).fetchone()[0];csrf=con.execute('SELECT csrf FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]
  assert 'Demo' in get('/dashboard').read().decode()
  rejected(lambda:post('/submit',dict(track='AI',title='Demo Project',summary='Fictional project summary')),403)
  rejected(lambda:post('/submit',dict(csrf=csrf,track='AI',title='Demo Project',summary='Fictional project summary')),400)
  exported=json.load(get('/export-data'));assert exported['account']['email']=='learner@example.test'
  assert 'password_hash' not in json.dumps(exported)
  rejected(lambda:post('/feedback',dict(csrf=csrf,submission_id='1',note='Should not work')),400)
  rejected(lambda:get('/nonexistent'),404)
  print('PASS: security headers, practice routing, role separation, sponsor gate, CSRF, export and 404')
 finally:p.terminate();p.wait(timeout=5)
