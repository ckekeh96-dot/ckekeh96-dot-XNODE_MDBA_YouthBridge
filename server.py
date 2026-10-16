#!/usr/bin/env python3
"""YouthBridge v7.4 controlled local demonstration. Optional SMTP is supported; not for real minors."""
import os, sys, sqlite3, json, secrets, hashlib, hmac, time, html, re, smtplib, ssl
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qs, urlparse, quote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from email.utils import formatdate
ROOT=Path(__file__).resolve().parent
DB=ROOT/'pilot.sqlite3'
HOST='127.0.0.1'; PORT=int(os.environ.get('PORT','8080'))
SESSION_TTL=8*3600
SECURE_COOKIES=os.environ.get('YB_SECURE_COOKIES','0')=='1' # Only when served through HTTPS
LOGIN_ATTEMPTS={}  # in-memory demo throttle, reset on restart
TOKEN_TTL=48*3600
SMTP_HOST=os.environ.get('YB_SMTP_HOST','')
SMTP_PORT=int(os.environ.get('YB_SMTP_PORT','587'))
SMTP_USER=os.environ.get('YB_SMTP_USER','')
SMTP_PASSWORD=os.environ.get('YB_SMTP_PASSWORD','')
SMTP_FROM=os.environ.get('YB_SMTP_FROM','')
PUBLIC_BASE_URL=os.environ.get('YB_PUBLIC_BASE_URL','').rstrip('/')
# SMTP remains OFF unless explicitly configured; local pilot does not verify adult identity.

def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c

def setup():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,role TEXT NOT NULL CHECK(role IN ('student','mentor','admin')),name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,grade INTEGER,school TEXT,sponsor_email TEXT,approved INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,expires INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS approvals(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0);CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),track TEXT NOT NULL,title TEXT NOT NULL,summary TEXT NOT NULL,created INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,submission_id INTEGER NOT NULL REFERENCES submissions(id),mentor_id INTEGER NOT NULL REFERENCES users(id),note TEXT NOT NULL,created INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor_id INTEGER,event TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL);''')

def audit(event,actor_id=None,detail=''):
 with db() as c:c.execute('INSERT INTO audit(actor_id,event,detail,created) VALUES(?,?,?,?)',(actor_id,event,str(detail)[:200],int(time.time())))

def send_sponsor_invitation(recipient,token):
 """Optional SMTP; never put token in logs when SMTP configured."""
 if not (SMTP_HOST and SMTP_FROM and PUBLIC_BASE_URL):return False
 link=f'{PUBLIC_BASE_URL}/approve?token={token}'
 msg=EmailMessage();msg['Subject']='YouthBridge practice sponsor invitation';msg['From']=SMTP_FROM;msg['To']=recipient
 msg.set_content('A practice account listed you as its adult sponsor. If unexpected, ignore this message.\n\n'+link+'\n\nThis is an independent pilot. This link does not establish verified guardian consent.')
 with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=12) as smtp:
  smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
  if SMTP_USER:smtp.login(SMTP_USER,SMTP_PASSWORD)
  smtp.send_message(msg)
 return True

def pwd_hash(password):
 salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,250000)
 return salt.hex()+':'+digest.hex()
def pwd_check(password,stored):
 try:
  salt,expected=stored.split(':');actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),250000)
  return hmac.compare_digest(actual,bytes.fromhex(expected))
 except (ValueError,TypeError):return False

def H(s):return html.escape(str(s or ''),quote=True)
def hash_token(t):return hashlib.sha256(t.encode()).hexdigest()
CSS='''<style>
:root{font-family:Inter,ui-sans-serif,system-ui,Arial;color:#071c51;background:#f3f8ff}*{box-sizing:border-box}body{margin:0;background:#f2f7ff}a{color:#125de6;text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #ffb52c;outline-offset:3px}p{line-height:1.55;color:#465a7b}h1,h2,h3{color:#081e56}h1{font-size:clamp(25px,3vw,40px)}h2{font-size:clamp(19px,2vw,24px)}.shell{display:grid;grid-template-columns:225px minmax(0,1fr);min-height:100vh}.sidebar{background:linear-gradient(170deg,#061643,#071d55 65%,#091044);color:white;padding:20px 11px;position:sticky;top:0;height:100vh;overflow:auto}.sidebrand{display:block;text-align:center;padding:13px 5px 22px;font-weight:950;font-size:20px;line-height:1.06;color:white}.sidebrand span{color:#ac5aff}.sidenav{display:grid;gap:4px}.sidenav a{color:#e5ecff;padding:12px 13px;border-radius:12px;font-size:14px;font-weight:650;display:flex;gap:11px;align-items:center}.sidenav a:hover,.sidenav a.active{background:linear-gradient(95deg,#1166ff,#05a6ef);color:white;text-decoration:none}.sidepromo{margin-top:22px;border-radius:16px;background:linear-gradient(125deg,#009be9,#8522eb);padding:18px 12px;color:white;font-size:14px}.sidepromo p{color:white;font-size:12px}.content{min-width:0}.topbar{min-height:104px;background:linear-gradient(110deg,#dceeff,#fff 60%,#e2f0ff);display:flex;align-items:center;justify-content:space-between;padding:15px 28px;gap:15px;flex-wrap:wrap}.toplogo{display:flex;align-items:center;gap:14px}.toplogo img{width:100px;height:76px;object-fit:contain}.toplogo strong{display:block;font-size:clamp(18px,2.6vw,32px);letter-spacing:-1px;color:#061c58}.toplogo strong span{color:#7126d9}.toplogo small{display:block;color:#354e83;font-size:10px;letter-spacing:1px;font-weight:750}.topnav{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.topnav a{padding:9px 13px;background:white;border-radius:12px;font-weight:750;font-size:13px;box-shadow:0 3px 12px #2a56a010}.contentmain{padding:0 18px 20px;max-width:1650px;margin:auto}.hero{min-height:275px;border-radius:0 0 19px 19px;background:linear-gradient(90deg,#e9f6ffed,#e6f2ffb8 52%,#eaf3ff70),url('/static/assets/students-hero.webp') center 40%/cover;display:flex;align-items:center;justify-content:center;text-align:center;padding:30px;overflow:hidden}.hero-inner{max-width:640px;background:#ffffffbd;backdrop-filter:blur(4px);padding:18px 24px;border-radius:22px}.hero h1{margin:7px 0;font-size:clamp(26px,3.1vw,44px);color:#0a2790}.hero h1 span{color:#6d20dc}.hero p{margin:7px auto 12px;color:#183c79}.hero .eyebrow{font-weight:850;letter-spacing:1.5px;color:#6e28d9;font-size:12px}.btn,button{display:inline-block;background:linear-gradient(100deg,#0867ff,#8027e8);color:white;border:0;border-radius:13px;padding:12px 18px;font-weight:800;cursor:pointer;font:inherit;text-decoration:none}.btn:hover,button:hover{text-decoration:none;filter:brightness(1.06)}.btn.secondary,.secondary{background:#eaf1ff;color:#14458f}.btn.small{padding:9px 14px;font-size:13px}.actions{display:flex;justify-content:center;gap:9px;flex-wrap:wrap}.missiongrid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin:12px 0}.missioncard{border-radius:15px;padding:15px 12px;color:white;min-height:122px;display:flex;flex-direction:column;gap:7px;box-shadow:0 5px 14px #2452b11c}.missioncard strong{font-size:14px}.missioncard small{font-size:11px;line-height:1.4}.missioncard a{color:white;font-size:12px;font-weight:850;margin-top:auto}.m1{background:linear-gradient(120deg,#7331f1,#aa76fa)}.m2{background:linear-gradient(120deg,#0068ed,#51bbff)}.m3{background:linear-gradient(120deg,#fc2582,#ff8da9)}.m4{background:linear-gradient(120deg,#ff800c,#ffc54f)}.m5{background:linear-gradient(120deg,#00a887,#5bd8b5)}.m6{background:linear-gradient(120deg,#0070ed,#45b9ff)}.panelgrid{display:grid;grid-template-columns:1.05fr 1.3fr;gap:13px}.panel{background:white;border:1px solid #e0eafa;border-radius:17px;padding:14px;box-shadow:0 5px 18px #2b53910c;margin:0 0 13px}.panel h2{font-size:18px;margin:0 0 11px}.featured{display:grid;grid-template-columns:1fr 42%;gap:12px;align-items:center}.featured img{width:100%;height:205px;object-fit:cover;border-radius:13px}.featured h3{font-size:22px;color:#08653b}.templates{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.template{border:1px solid #e0eafa;border-radius:13px;overflow:hidden;background:#f9fbff}.template img{width:100%;height:114px;object-fit:cover}.template strong{display:block;font-size:12px;padding:8px}.template small{display:block;font-size:11px;padding:0 8px 8px;color:#52688a}.lowergrid{display:grid;grid-template-columns:1.3fr .8fr 1fr;gap:13px}.steps{display:flex;justify-content:space-between;gap:6px;text-align:center}.steps div{flex:1;font-size:12px;color:#38517b}.steps b{display:block;background:#e1edff;border-radius:50%;width:35px;height:35px;line-height:35px;margin:5px auto;color:#076bff;font-size:18px}.small-imgs{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.small-imgs img{width:100%;height:90px;object-fit:cover;border-radius:9px}.small-imgs p{font-size:11px;margin:4px}.card{background:white;border:1px solid #dce6f8;border-radius:18px;padding:22px;margin:15px 0;box-shadow:0 6px 20px #224b890e}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.warn{background:#fff2d7;padding:14px;border-radius:12px}.good{background:#ddf8e8;padding:14px;border-radius:12px}.error{background:#ffe7e7;padding:14px;border-radius:12px}label{display:block;font-weight:700;margin:14px 0 6px}input,textarea,select{display:block;width:100%;padding:12px;border:1px solid #b8c9e4;border-radius:10px;font:inherit}textarea{min-height:100px}form button{margin-top:13px}.muted,small{color:#587094}.footer{margin:20px 0;color:#5d7091;font-size:12px}.page-banner{background:linear-gradient(90deg,#e3efff,#f8efff);border-radius:16px;padding:15px 20px;margin-top:16px}.page-banner h1{margin:0}.page-banner p{margin:5px 0}.sidebar-toggle{display:none}@media(max-width:1150px){.missiongrid{grid-template-columns:repeat(3,1fr)}.panelgrid{grid-template-columns:1fr}.lowergrid{grid-template-columns:1fr 1fr}}@media(max-width:720px){.shell{grid-template-columns:1fr}.sidebar{position:relative;height:auto;padding:9px}.sidebrand{padding:6px}.sidenav{display:flex;overflow-x:auto;gap:5px}.sidenav a{white-space:nowrap;padding:10px}.sidepromo{display:none}.topbar{padding:12px}.toplogo img{width:65px;height:55px}.toplogo small{display:none}.hero{min-height:270px}.missiongrid{grid-template-columns:repeat(2,1fr)}.templates{grid-template-columns:repeat(2,1fr)}.lowergrid{grid-template-columns:1fr}.featured{grid-template-columns:1fr}.contentmain{padding:0 10px 12px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
</style>'''

def page(title,body,user=None):
 items=[('🏠','Home','/'),('🧭','Explore','/practice?section=challenges'),('🎯','Guided Missions','/practice?section=missions'),('🎓','Learn & Skills','/practice?section=activities'),('🛠️','Project Builder','/practice?section=builder'),('📚','Templates','/practice?section=templates'),('👥','Team Builder','/practice?section=team'),('🛡️','Sponsor Checkpoints','/practice?section=checkpoint'),('🎤','Pitch Creator','/practice?section=pitch'),('📁','My Projects','/dashboard'),('☑️','Submission Checker','/practice?section=checker'),('🏆','Practice Judging','/practice?section=judging'),('🎁','Rewards','/practice?section=certificate'),('💬','Idea Coach','/practice?section=mentor'),('❔','Help & Support','/practice?section=guide')]
 side=''.join('<a '+('class="active" ' if title=='Home' and href=='/' else '')+'href="'+href+'"><span aria-hidden="true">'+icon+'</span>'+label+'</a>' for icon,label,href in items)
 nav='<a href="/practice">Practice Lab</a>'
 if user:nav+='<a href="/dashboard">'+H(user['name'])+' · '+H(user['role'])+'</a><form style="display:inline" method="post" action="/logout"><input type="hidden" name="csrf" value="'+H(user['csrf'])+'"><button class="small" type="submit">Sign out</button></form>'
 else:nav+='<a href="/login">Sign in</a><a href="/register">Join</a>'
 head='<header class="topbar"><a href="/" class="toplogo"><img src="/static/assets/xnode-youthbridge-logo.png" alt="XNODE YouthBridge logo"><div><strong>XNODE <span>MDBA YouthBridge</span></strong><small>STEM HACKATHON PLATFORM · GRADES 10–12</small></div></a><nav class="topnav">'+nav+'</nav></header>'
 return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+H(title)+' | XNODE MDBA YouthBridge</title>'+CSS+'</head><body><div class="shell"><aside class="sidebar"><a class="sidebrand" href="/">✦ XNODE<br><span>YouthBridge</span></a><nav class="sidenav" aria-label="Main navigation">'+side+'</nav><div class="sidepromo">🤖 <strong>XNODE Idea Coach</strong><p>Try a friendly guided idea-building activity.</p><a href="/practice?section=mentor" style="color:white;font-weight:800">Explore coach →</a></div></aside><div class="content">'+head+'<main class="contentmain">'+body+'<footer class="footer">Independent educational practice platform · Not affiliated with MDBA · Local demo only · Fictional student data only</footer></main></div></div></body></html>'

def field(label,name,type='text',required=True,extra=''):
 return f'<label for="{name}">{H(label)}</label><input id="{name}" name="{name}" type="{type}" {"required" if required else ""} {extra}>'

class Handler(BaseHTTPRequestHandler):
 def log_message(self,format,*args):pass
 def send_html(self,body,status=200,cookie=None):
  data=body.encode();self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:")
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(data)
 def redirect(self,path,cookie=None):
  self.send_response(303);self.send_header('Location',path)
  if cookie:self.send_header('Set-Cookie',cookie)
  self.send_header('Content-Length','0');self.end_headers()
 def user(self):
  raw=self.headers.get('Cookie','');cookie=SimpleCookie()
  try:cookie.load(raw);token=cookie['yb_session'].value
  except (KeyError,Exception):return None,None
  with db() as c:
   row=c.execute('SELECT u.*,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',(hash_token(token),int(time.time()))).fetchone()
  return row,token
 def form(self):
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<0 or size>16000:raise ValueError('Invalid form size')
   return {k:v[0] for k,v in parse_qs(self.rfile.read(size).decode(),keep_blank_values=True).items()}
  except (ValueError,UnicodeError):return {}
 def fail(self,message,status=400):self.send_html(page('Please check',f'<div class="card error"><h2>Could not continue</h2><p>{H(message)}</p><a href="/">Go home</a></div>'),status)
 def csrf(self,user,form):return user is not None and hmac.compare_digest(str(form.get('csrf','')),str(user['csrf']))
 def do_GET(self):
  u,token=self.user();url=urlparse(self.path);path=url.path
  if path=='/health':self.send_html('YouthBridge local pilot OK');return
  if path=='/practice':
   section=parse_qs(url.query).get('section',['overview'])[0]
   allowed={'overview','challenges','missions','activities','builder','templates','team','checkpoint','pitch','checker','judging','certificate','mentor','guide','studio','submit','workspace','samples'}
   self.redirect('/static/practice.html#'+(section if section in allowed else 'overview'));return
  if path.startswith('/static/assets/'):
   filename=path[len('/static/assets/'):]
   if filename not in {'dashboard-reference.png','xnode-youthbridge-logo.png','students-hero.webp','green-challenge.webp','ai-robot.webp','gaming.webp','teamwork.webp','ideas.webp','impact.webp'}:self.send_error(404);return
   asset=ROOT/'static'/'assets'/filename
   if not asset.is_file():self.send_error(404);return
   data=asset.read_bytes();self.send_response(200);self.send_header('Content-Type','image/webp' if filename.endswith('.webp') else 'image/png');self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data);return
  if path=='/static/practice.html':
   data=(ROOT/'static'/'practice.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.send_header('Content-Security-Policy',"default-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'");self.end_headers();self.wfile.write(data);return
  if path=='/':
   body='''<section class="hero"><div class="hero-inner"><div class="eyebrow">CREATE · SOLVE · INNOVATE · BELONG</div><h1>Welcome to<br>XNODE <span>MDBA YouthBridge</span></h1><p>A fun, guided STEM innovation space for Grades 10–12. Learn new skills, build projects and turn your ideas into something amazing.</p><div class="actions"><a class="btn" href="/practice?section=guide">🚀 Start Your Journey →</a><a class="btn secondary" href="/practice?section=overview">▶ See How It Works</a></div></div></section>
<section class="missiongrid" aria-label="Explore learning activities"><div class="missioncard m1">🧠 <strong>Learn New Skills</strong><small>Step-by-step STEM missions made for you.</small><a href="/practice?section=missions">Explore →</a></div><div class="missioncard m2">🛠️ <strong>Build Projects</strong><small>Start with a template or create your own.</small><a href="/practice?section=builder">Build →</a></div><div class="missioncard m3">👥 <strong>Work in Teams</strong><small>Collaborate with up to three students.</small><a href="/practice?section=team">Team up →</a></div><div class="missioncard m4">🛡️ <strong>Sponsor Check-in</strong><small>Get guidance from a trusted adult.</small><a href="/practice?section=checkpoint">Learn more →</a></div><div class="missioncard m5">🎤 <strong>Create Your Pitch</strong><small>Turn your idea into a clear presentation.</small><a href="/practice?section=pitch">Create →</a></div><div class="missioncard m6">🏆 <strong>Submit &amp; Learn</strong><small>Check your project and get practice feedback.</small><a href="/practice?section=checker">Check →</a></div></section>
<div class="panelgrid"><section class="panel"><h2>🌿 Featured STEM Challenge <span style="color:#079f72;font-size:12px">· Sustainability</span></h2><div class="featured"><div><h3>Build a Greener Community</h3><p>How could your idea make your neighborhood healthier and more sustainable?</p><a class="btn small" href="/practice?section=challenges">Explore Challenge →</a></div><img src="/static/assets/green-challenge.webp" alt="Student exploring a green community challenge"></div></section><section class="panel"><h2>✨ Popular Project Templates</h2><div class="templates"><a class="template" href="/practice?section=templates"><img src="/static/assets/ai-robot.webp" alt="Friendly AI learning robot"><strong>AI Study Buddy</strong><small>Education assistant</small></a><a class="template" href="/practice?section=templates"><img src="/static/assets/gaming.webp" alt="Creative gaming project"><strong>Game for Good</strong><small>Fun learning game</small></a><a class="template" href="/practice?section=templates"><img src="/static/assets/ideas.webp" alt="Student technology idea"><strong>Blockchain Ideas</strong><small>Digital achievement</small></a><a class="template" href="/practice?section=templates"><img src="/static/assets/impact.webp" alt="Community innovation"><strong>Legal Rights Helper</strong><small>Know your rights</small></a></div></section></div>
<div class="lowergrid"><section class="panel"><h2>🧩 How It Works</h2><div class="steps"><div><b>1</b><strong>Learn</strong><p>Explore guided missions</p></div><div><b>2</b><strong>Build</strong><p>Create your project</p></div><div><b>3</b><strong>Feedback</strong><p>Ask an adult helper</p></div><div><b>4</b><strong>Pitch</strong><p>Tell your story</p></div><div><b>5</b><strong>Share</strong><p>Practice submitting</p></div></div></section><section class="panel"><h2>⭐ Your Progress</h2><p>Every big idea starts with a small step. Open the Practice Lab to see your personal progress saved in this browser.</p><a class="btn small" href="/practice?section=missions">My missions →</a></section><section class="panel"><h2>🌎 Community Inspiration</h2><div class="small-imgs"><div><img src="/static/assets/teamwork.webp" alt="Students collaborating"><p>Build together</p></div><div><img src="/static/assets/ideas.webp" alt="Creative ideas"><p>Try bold ideas</p></div><div><img src="/static/assets/impact.webp" alt="Positive impact"><p>Make a difference</p></div></div><p style="font-size:12px">Illustrative examples, not real student profiles or rankings.</p></section></div><div class="warn" style="margin-bottom:15px">🔒 This is an independent educational demo. All accounts, sponsor checkpoints, scores, and projects should use fictional information only.</div>'''
   self.send_html(page('Home',body,u));return
  if path=='/register':
   form='<h1>Student sign-up</h1><p>For Grade 10–12 practice participants. Ask a trusted adult before registering.</p><form method="post" action="/register">'+field('First name or nickname','name')+field('Practice email (not real student email)','email','email')+field('Practice password (12+ characters)','password','password')+'<label for="grade">Grade</label><select id="grade" name="grade"><option>10</option><option>11</option><option>12</option></select>'+field('School or club (fictional for demo)','school')+field('Adult sponsor email (fictional for demo)','sponsor_email','email')+'<button>Create practice account</button></form>'
   self.send_html(page('Join',f'<div class="card">{form}</div>',u));return
  if path=='/login':
   form='<h1>Sign in</h1><form method="post" action="/login">'+field('Email','email','email')+field('Password','password','password')+'<button>Sign in</button></form>'
   self.send_html(page('Sign in',f'<div class="card">{form}</div>',u));return
  if path=='/approve':
   raw=parse_qs(url.query).get('token',[''])[0]
   with db() as c:row=c.execute('SELECT a.*,u.name,u.sponsor_email FROM approvals a JOIN users u ON u.id=a.user_id WHERE a.token_hash=? AND a.used=0 AND a.expires>?',(hash_token(raw),int(time.time()))).fetchone() if raw else None
   if not row:self.fail('Approval link is invalid, expired or already used.');return
   body=f'<div class="card"><h1>Sponsor confirmation</h1><p>Confirm that you are the trusted adult for <strong>{H(row["name"])}</strong> and agree to their participation in this local practice pilot.</p><p class="warn">This demo does not verify your identity or email ownership. Do not treat this as legally valid guardian consent.</p><form method="post" action="/approve"><input type="hidden" name="token" value="{H(raw)}"><label><input type="checkbox" name="confirm" value="yes" required style="display:inline;width:auto"> I am the sponsor and approve this practice account</label><button>Confirm approval</button></form></div>'
   self.send_html(page('Sponsor approval',body));return
  if path=='/export-data':
   if not u or u['role']!='student':self.fail('Student login required.',403);return
   with db() as c:
    subs=[dict(r) for r in c.execute('SELECT track,title,summary,created FROM submissions WHERE user_id=?',(u['id'],))]
    notes=[dict(r) for r in c.execute('SELECT f.note,s.title FROM feedback f JOIN submissions s ON s.id=f.submission_id WHERE s.user_id=?',(u['id'],))]
   payload=json.dumps({'account':{k:u[k] for k in ('name','email','grade','school','sponsor_email','approved','created')},'submissions':subs,'feedback':notes},indent=2).encode()
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Disposition','attachment; filename="youthbridge-my-data.json"');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
  if path=='/dashboard':
   if not u:self.redirect('/login');return
   if u['role']=='admin':
    with db() as c:
     counts={k:c.execute('SELECT COUNT(*) FROM '+k).fetchone()[0] for k in ('users','submissions','feedback','approvals')}
     events=c.execute('SELECT event,detail,created FROM audit ORDER BY id DESC LIMIT 40').fetchall()
    body='<h1>Administrator overview</h1><div class="card warn">Local demo only. Admin access does not verify guardian identity or authorize processing real minors’ information.</div><div class="grid">'+''.join(f'<div class="card"><h2>{H(k.title())}</h2><p>{v}</p></div>' for k,v in counts.items())+'</div><div class="card"><h2>Recent audit events</h2>'+''.join(f'<p>{H(e["event"])} · {H(e["detail"])} · {e["created"]}</p>' for e in events)+'</div>'
    self.send_html(page('Administrator',body,u));return
   if u['role']=='mentor':
    with db() as c:subs=c.execute('SELECT s.*,u.name student FROM submissions s JOIN users u ON u.id=s.user_id ORDER BY s.created DESC LIMIT 100').fetchall()
    cards=''.join(f'<div class="card"><h3>{H(s["title"])}</h3><p><strong>{H(s["track"])}</strong> · {H(s["student"])}</p><p>{H(s["summary"])}</p><form method="post" action="/feedback"><input type="hidden" name="csrf" value="{H(u["csrf"])}"><input type="hidden" name="submission_id" value="{s["id"]}"><label>Supportive feedback</label><textarea name="note" required maxlength="1000"></textarea><button>Send feedback</button></form></div>' for s in subs)
    self.send_html(page('Mentor dashboard','<h1>Mentor review desk</h1><p>Review submitted project summaries and leave encouraging feedback.</p>'+ (cards or '<div class="card">No student submissions yet.</div>'),u));return
   status='<div class="good">Sponsor approval recorded for this practice account.</div>' if u['approved'] else '<div class="warn">Waiting for sponsor confirmation. A demo approval link was printed in the server terminal at registration.</div>'
   with db() as c:
    subs=c.execute('SELECT * FROM submissions WHERE user_id=? ORDER BY created DESC',(u['id'],)).fetchall()
    notes=c.execute('SELECT f.note,s.title FROM feedback f JOIN submissions s ON s.id=f.submission_id WHERE s.user_id=? ORDER BY f.created DESC',(u['id'],)).fetchall()
   body=f'<h1>Hi, {H(u["name"])}! 👋</h1>{status}<div class="grid"><div class="card"><h2>🧩 Practice your idea</h2><p>Explore the no-code studio and six STEM tracks.</p><a class="btn" href="/practice">Open practice lab</a></div><div class="card"><h2>📤 Share a project</h2><p>Submit a short project summary after sponsor approval.</p>'
   if u['approved']:
    body+=f'<form method="post" action="/submit"><input type="hidden" name="csrf" value="{H(u["csrf"])}"><label>Track</label><select name="track">'+''.join('<option>'+x+'</option>' for x in ['Blockchain','AI','Gaming','LegalTech','Education','Sustainability'])+'</select>'+field('Project title','title')+'<label>What problem does your project solve?</label><textarea name="summary" maxlength="2000" required></textarea><button>Submit project summary</button></form>'
   body+='</div></div><div class="card"><h2>Download my data</h2><p>Export your pilot account and project submissions as JSON.</p><a class="btn secondary" href="/export-data">Export JSON</a></div><div class="card"><h2>Delete practice account</h2><p>Erase this account, submissions and feedback from the local demo database. This cannot be undone.</p><form method="post" action="/delete-account"><input type="hidden" name="csrf" value="'+H(u['csrf'])+'"><label>Enter your password to confirm deletion</label><input type="password" name="password" required><button type="submit">Delete my practice account</button></form></div><h2>My submissions</h2>'+(''.join(f'<div class="card"><strong>{H(s["title"])}</strong> · {H(s["track"])}<p>{H(s["summary"])}</p></div>' for s in subs) or '<p>No submissions yet.</p>')+'<h2>Mentor feedback</h2>'+(''.join(f'<div class="card"><strong>{H(n["title"])}</strong><p>{H(n["note"])}</p></div>' for n in notes) or '<p>No feedback yet.</p>')
   self.send_html(page('Student dashboard',body,u));return
  self.fail('Page not found',404)
 def do_POST(self):
  u,session=self.user();path=urlparse(self.path).path;f=self.form();now=int(time.time())
  if path=='/register':
   name=f.get('name','').strip();email=f.get('email','').strip().lower();pw=f.get('password','');grade=f.get('grade','');school=f.get('school','').strip();sponsor=f.get('sponsor_email','').strip().lower()
   if not (1<=len(name)<=70 and re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) and re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',sponsor) and len(pw)>=12 and grade in ('10','11','12') and 1<=len(school)<=100):self.fail('Please check all fields. Password must have 12+ characters.');return
   if email==sponsor:self.fail('Sponsor must have a different email address.');return
   approval=secrets.token_urlsafe(32)
   try:
    with db() as c:
     cur=c.execute('INSERT INTO users(role,name,email,password_hash,grade,school,sponsor_email,created) VALUES(?,?,?,?,?,?,?,?)',('student',name,email,pwd_hash(pw),int(grade),school,sponsor,now));c.execute('INSERT INTO approvals(token_hash,user_id,expires) VALUES(?,?,?)',(hash_token(approval),cur.lastrowid,now+TOKEN_TTL))
   except sqlite3.IntegrityError:self.fail('This email already has an account.');return
   audit('student_registered',cur.lastrowid)
   try:sent=send_sponsor_invitation(sponsor,approval)
   except (OSError,smtplib.SMTPException) as exc:
    sent=False;print('SMTP invitation failed:',type(exc).__name__,flush=True)
   if not sent:print(f'\n[DEMO SPONSOR LINK for {sponsor}] http://{HOST}:{PORT}/approve?token={approval}\n',flush=True)
   self.send_html(page('Account created','<div class="card good"><h1>Practice account created!</h1><p>Ask your adult helper to use the invitation link. When SMTP is not configured, the link is printed in the server terminal.</p><a class="btn" href="/login">Sign in</a></div>'));return
  if path=='/approve':
   raw=f.get('token','')
   if f.get('confirm')!='yes':self.fail('Sponsor confirmation is required.');return
   with db() as c:
    row=c.execute('SELECT user_id FROM approvals WHERE token_hash=? AND used=0 AND expires>?',(hash_token(raw),now)).fetchone()
    if not row:self.fail('Approval link expired or already used.');return
    updated=c.execute('UPDATE approvals SET used=1 WHERE token_hash=? AND used=0 AND expires>?',(hash_token(raw),now))
    if updated.rowcount!=1:self.fail('Approval link already used.',400);return
    c.execute('UPDATE users SET approved=1 WHERE id=?',(row['user_id'],))
   audit('sponsor_link_confirmed',row['user_id'])
   self.send_html(page('Approved','<div class="card good"><h1>Practice approval recorded</h1><p>The student may now submit a project summary.</p><a href="/">Return home</a></div>'));return
  if path=='/login':
   key=self.client_address[0];attempts=[t for t in LOGIN_ATTEMPTS.get(key,[]) if now-t<300];LOGIN_ATTEMPTS[key]=attempts
   if len(attempts)>=8:self.fail('Too many sign-in attempts. Wait five minutes.',429);return
   with db() as c:row=c.execute('SELECT * FROM users WHERE email=?',(f.get('email','').strip().lower(),)).fetchone()
   if not row or not pwd_check(f.get('password',''),row['password_hash']):LOGIN_ATTEMPTS[key].append(now);self.fail('Email or password not recognized.',401);return
   LOGIN_ATTEMPTS.pop(key,None)
   token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
   with db() as c:c.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires) VALUES(?,?,?,?)',(hash_token(token),row['id'],csrf,now+SESSION_TTL))
   self.redirect('/dashboard',f'yb_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}' + ('; Secure' if SECURE_COOKIES else ''));return
  if path=='/logout':
   if session and not self.csrf(u,f):self.fail('Invalid sign-out request.',403);return
   if session:
    with db() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hash_token(session),))
   self.redirect('/', 'yb_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' + ('; Secure' if SECURE_COOKIES else ''));return
  if path=='/delete-account':
   if not self.csrf(u,f) or u['role']!='student':self.fail('Sign in as a student to delete your account.',403);return
   if not pwd_check(f.get('password',''),u['password_hash']):self.fail('Password not recognized.',403);return
   with db() as c:
    c.execute('DELETE FROM feedback WHERE submission_id IN (SELECT id FROM submissions WHERE user_id=?)',(u['id'],))
    c.execute('DELETE FROM submissions WHERE user_id=?',(u['id'],))
    c.execute('DELETE FROM users WHERE id=?',(u['id'],))
   audit('account_deleted',None,'student self-service')
   self.redirect('/', 'yb_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' + ('; Secure' if SECURE_COOKIES else ''));return
  if path in ('/submit','/feedback'):
   if not self.csrf(u,f):self.fail('Sign in and try again.',403);return
   if path=='/submit':
    track=f.get('track','');title=f.get('title','').strip();summary=f.get('summary','').strip()
    if u['role']!='student' or not u['approved'] or track not in ('Blockchain','AI','Gaming','LegalTech','Education','Sustainability') or not (3<=len(title)<=120) or not (10<=len(summary)<=2000):self.fail('Sponsor approval and a valid title and summary are required.');return
    with db() as c:c.execute('INSERT INTO submissions(user_id,track,title,summary,created) VALUES(?,?,?,?,?)',(u['id'],track,title,summary,now))
   else:
    note=f.get('note','').strip();sid=f.get('submission_id','')
    if u['role']!='mentor' or not sid.isdigit() or not (5<=len(note)<=1000):self.fail('Invalid mentor feedback.');return
    with db() as c:
     exists=c.execute('SELECT 1 FROM submissions WHERE id=?',(int(sid),)).fetchone()
     if not exists:self.fail('Submission not found.',404);return
     c.execute('INSERT INTO feedback(submission_id,mentor_id,note,created) VALUES(?,?,?,?)',(int(sid),u['id'],note,now))
   self.redirect('/dashboard');return
  self.fail('Unknown action',404)

def mentor_create(email,password,name,role='mentor'):
 if len(password)<12:raise ValueError('Mentor password must be at least 12 characters')
 with db() as c:c.execute('INSERT INTO users(role,name,email,password_hash,approved,created) VALUES(?,?,?,?,1,?)',( role,name,email.lower(),pwd_hash(password),int(time.time())))
 print(role.title()+' account created.');

if __name__=='__main__':
 setup()
 if len(sys.argv)>1 and sys.argv[1] in ('create-mentor','create-admin'):
  import getpass
  email=input('Mentor email (demo only): ').strip();name=input('Mentor display name: ').strip();password=getpass.getpass('Password (12+ chars): ');mentor_create(email,password,name,'admin' if sys.argv[1]=='create-admin' else 'mentor')
 else:
  print(f'YouthBridge v7.4 demo pilot: http://{HOST}:{PORT} (Ctrl+C to stop)',flush=True)
  ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
