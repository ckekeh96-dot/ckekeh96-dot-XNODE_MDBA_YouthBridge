"""Local HTTP integration smoke test using fictional data only."""
import os, sys, tempfile, subprocess, time, urllib.request, urllib.parse, http.cookiejar, re, sqlite3, pathlib
root=pathlib.Path(__file__).parent
with tempfile.TemporaryDirectory() as d:
 import shutil
 shutil.copy(root/'server.py',d+'/server.py');shutil.copytree(root/'static',d+'/static')
 port='18089';env=dict(os.environ,PORT=port)
 p=subprocess.Popen([sys.executable,'-u',d+'/server.py'],cwd=d,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 try:
  base='http://127.0.0.1:'+port
  for _ in range(50):
   try:urllib.request.urlopen(base,timeout=.5);break
   except Exception:time.sleep(.1)
  cookies=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
  def get(path):return opener.open(base+path).read().decode()
  def post(path,data):return opener.open(base+path,urllib.parse.urlencode(data).encode()).read().decode()
  assert 'Practice Lab' in get('/')
  assert 'Mini Challenges' in get('/static/practice.html')
  assert 'Student sign-up' in get('/register')
  post('/register',dict(name='Demo Student',email='student@example.test',password='ExamplePassword123!',grade='11',school='Sample School',sponsor_email='sponsor@example.test'))
  assert 'Waiting for sponsor' in post('/login',dict(email='student@example.test',password='ExamplePassword123!'))
  con=sqlite3.connect(d+'/pilot.sqlite3');user_id=con.execute('SELECT id FROM users WHERE email=?',('student@example.test',)).fetchone()[0]
  csrf=con.execute('SELECT csrf FROM sessions WHERE user_id=?',(user_id,)).fetchone()[0]
  try:post('/submit',dict(csrf=csrf,track='AI',title='Community Helper',summary='Helping local students find resources'))
  except urllib.error.HTTPError as e:assert e.code==400
  # Capture printed approval link from unbuffered stdout
  line=''
  for _ in range(6):
   x=p.stdout.readline();line+=x
   if 'approve?token=' in x:break
  match=re.search(r'/approve\?token=([A-Za-z0-9_-]+)',line);assert match,line
  token=match.group(1)
  assert 'Sponsor confirmation' in get('/approve?token='+token)
  assert 'approval recorded' in post('/approve',dict(token=token,confirm='yes')).lower()
  assert 'Practice approval recorded' not in get('/dashboard') # student view, not approval page
  assert 'My submissions' in post('/submit',dict(csrf=csrf,track='AI',title='Community Helper',summary='Helping local students find resources'))
  assert con.execute('SELECT count(*) FROM submissions').fetchone()[0]==1
  try:get('/approve?token='+token)
  except urllib.error.HTTPError as e:assert e.code==400
  else:raise AssertionError('Approval link should be single use')
  import importlib.util
  spec=importlib.util.spec_from_file_location('pilotserver',d+'/server.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  con.execute('INSERT INTO users(role,name,email,password_hash,approved,created) VALUES(?,?,?,?,1,?)',('mentor','Demo Mentor','mentor@example.test',module.pwd_hash('MentorPassword123!'),int(time.time())));con.commit()
  post('/logout',dict(csrf=csrf))
  assert 'Mentor review desk' in post('/login',dict(email='mentor@example.test',password='MentorPassword123!'))
  mid=con.execute('SELECT id FROM users WHERE email=?',('mentor@example.test',)).fetchone()[0]
  mcsrf=con.execute('SELECT csrf FROM sessions WHERE user_id=?',(mid,)).fetchone()[0]
  assert 'Mentor review desk' in post('/feedback',dict(csrf=mcsrf,submission_id='1',note='Great start! Consider interviewing a community member.'))
  assert con.execute('SELECT count(*) FROM feedback').fetchone()[0]==1
  print('PASS: pages, registration, login, sponsor gate, one-time approval, submission, practice lab')
 finally:
  p.terminate();p.wait(timeout=5)
