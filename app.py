import os, json, sqlite3, secrets, random, time
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

ROOT=Path(__file__).parent
DB=Path(os.environ.get('BITS_DB',str(ROOT/'12bits.sqlite')))
ADMIN_KEY=os.environ.get('BITS_ADMIN_KEY') or secrets.token_urlsafe(18)
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=4*1024*1024
PEOPLE=['Ana','Tomás','Jaime','Cecilia']; PLACES=['Colombia','Perú','Ecuador','Brasil']
ANSWER=[[0,3,2,1],[3,1,0,2],[1,2,3,0],[2,0,1,3]]
CLUES=json.loads((ROOT/'clues.json').read_text())

def connect():
 c=sqlite3.connect(DB,timeout=15,isolation_level=None);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA busy_timeout=4000');return c

def setup():
 with connect() as db:
  db.executescript('''CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,config TEXT NOT NULL,open INTEGER NOT NULL DEFAULT 1,started INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL,board TEXT NOT NULL,integrator TEXT,attempts INTEGER NOT NULL DEFAULT 0,solved INTEGER NOT NULL DEFAULT 0,revealed INTEGER NOT NULL DEFAULT 0);CREATE TABLE IF NOT EXISTS players(token TEXT PRIMARY KEY, session_id TEXT NOT NULL, name TEXT NOT NULL, clue INTEGER NOT NULL, joined REAL NOT NULL);''')
setup()

def config_default():return {'people':PEOPLE[:], 'places':PLACES[:], 'clues':CLUES[:], 'photos':{'people':['']*4,'places':['']*4,'clues':['']*12}}
def row(s):return dict(s) if s else None

def admin_required(fn):
 @wraps(fn)
 def wrapped(*args,**kwargs):
  if request.headers.get('X-Admin-Key')!=ADMIN_KEY:return jsonify(error='Acceso de facilitador no autorizado'),403
  return fn(*args,**kwargs)
 return wrapped

def player(c,session_id):
 token=request.headers.get('X-Player-Token') or ''
 return row(c.execute('SELECT * FROM players WHERE token=? AND session_id=?',(token,session_id)).fetchone())

def gate(c,sid,admin=False):
 s=row(c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone())
 if not s:return None,None,(jsonify(error='Sesión no encontrada'),404)
 if admin:
  if request.headers.get('X-Admin-Key')!=ADMIN_KEY:return None,None,(jsonify(error='No autorizado'),403)
  return s,None,None
 p=player(c,sid)
 if not p:return None,None,(jsonify(error='Ingresa al juego para acceder'),403)
 return s,p,None

def snapshot(c,s,admin=False,player_obj=None):
 cfg=json.loads(s['config']); roster=c.execute('SELECT name,clue,token FROM players WHERE session_id=? ORDER BY joined',(s['id'],)).fetchall()
 base={'id':s['id'],'open':bool(s['open']),'started':bool(s['started']),'board':json.loads(s['board']),'integrator':s['integrator'],'attempts':s['attempts'],'solved':bool(s['solved']),'revealed':bool(s['revealed']),'people':cfg['people'],'places':cfg['places'],'photos':cfg['photos'],'question':'¿Cuál fue el itinerario que el equipo de '+cfg['people'][1]+' siguió para visitar los países?','count':len(roster)}
 if admin:
  base.update({'clues':cfg['clues'],'roster':[{'name':r['name'],'clue':r['clue']+1,'token':r['token']} for r in roster]})
 else:
  base.update({'myName':player_obj['name'],'myClue':player_obj['clue']+1,'clueText':cfg['clues'][player_obj['clue']],'isIntegrator':s['integrator']==player_obj['token']})
 if s['revealed'] or admin:base['answer']=ANSWER
 return base

@app.get('/')
def home():return render_template('app.html',admin=False)
@app.get('/f/<sid>')
def facilitator(sid):return render_template('app.html',admin=True,session_id=sid,admin_key=ADMIN_KEY if request.args.get('key')==ADMIN_KEY else '')
@app.get('/s/<sid>')
def participant(sid):return render_template('app.html',admin=False,session_id=sid)
@app.get('/facilitador')
def admin_page():
 if request.args.get('key')!=ADMIN_KEY:return 'Acceso no autorizado',403
 return render_template('app.html',admin=True,session_id='',admin_key=ADMIN_KEY)

@app.post('/api/create')
@admin_required
def create():
 cfg=request.get_json(silent=True) or config_default()
 if len(cfg.get('people',[]))!=4 or len(cfg.get('places',[]))!=4 or len(cfg.get('clues',[]))!=12 or any(not isinstance(x,str) for x in cfg['clues']):return jsonify(error='Se requieren 4 personajes, 4 lugares y 12 pistas'),400
 if len(set(cfg['places']))!=4:return jsonify(error='Los cuatro lugares deben ser distintos'),400
 if 'photos' not in cfg:cfg['photos']=config_default()['photos']
 sid=secrets.token_hex(3).upper()
 with connect() as c:c.execute('INSERT INTO sessions(id,config,created,board) VALUES(?,?,?,?)',(sid,json.dumps(cfg,ensure_ascii=False),time.time(),json.dumps([[-1]*4 for _ in range(4)])))
 return jsonify(id=sid,participantUrl=request.host_url.rstrip('/')+'/s/'+sid,adminUrl=request.host_url.rstrip('/')+'/f/'+sid+'?key='+ADMIN_KEY)

@app.post('/api/<sid>/join')
def join(sid):
 name=str((request.get_json(silent=True) or {}).get('name','')).strip()[:60]
 if not name:return jsonify(error='Escribe tu nombre'),400
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  s=row(c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone())
  if not s or not s['open']:c.rollback();return jsonify(error='La sesión no está abierta'),404
  used=[r['clue'] for r in c.execute('SELECT clue FROM players WHERE session_id=?',(sid,)).fetchall()]
  remaining=list(set(range(12))-set(used)) if len(used)<12 else []
  clue=random.choice(remaining if remaining else list(range(12)))
  token=secrets.token_urlsafe(26)
  c.execute('INSERT INTO players(token,session_id,name,clue,joined) VALUES(?,?,?,?,?)',(token,sid,name,clue,time.time()))
  c.commit()
 return jsonify(token=token,clue=clue+1)

@app.get('/api/<sid>/state')
def state(sid):
 with connect() as c:
  admin=request.headers.get('X-Admin-Key')==ADMIN_KEY
  s,p,err=gate(c,sid,admin)
  if err:return err
  return jsonify(snapshot(c,s,admin,p))

@app.post('/api/<sid>/action')
def action(sid):
 data=request.get_json(silent=True) or {};kind=data.get('action')
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  admin=request.headers.get('X-Admin-Key')==ADMIN_KEY
  s,p,err=gate(c,sid,admin)
  if err:c.rollback();return err
  board=json.loads(s['board'])
  if kind in ('start','reveal','close','update_config','set_integrator') and not admin:c.rollback();return jsonify(error='Solo el facilitador puede realizar esta acción'),403
  if kind=='start':c.execute('UPDATE sessions SET started=1 WHERE id=?',(sid,))
  elif kind=='reveal':c.execute('UPDATE sessions SET revealed=1 WHERE id=?',(sid,))
  elif kind=='close':c.execute('UPDATE sessions SET open=0 WHERE id=?',(sid,))
  elif kind=='set_integrator':
   token=data.get('token',''); valid=c.execute('SELECT token FROM players WHERE session_id=? AND token=?',(sid,token)).fetchone()
   if not valid:c.rollback();return jsonify(error='Selecciona un participante válido'),400
   c.execute('UPDATE sessions SET integrator=? WHERE id=?',(token,sid))
  elif kind=='update_config':
   cfg=data.get('config')
   if not cfg or len(cfg.get('people',[]))!=4 or len(cfg.get('places',[]))!=4 or len(cfg.get('clues',[]))!=12:c.rollback();return jsonify(error='Configuración incompleta'),400
   c.execute('UPDATE sessions SET config=? WHERE id=?',(json.dumps(cfg,ensure_ascii=False),sid))
  elif kind in ('cell','reset','validate'):
   if not p or p['token']!=s['integrator']:c.rollback();return jsonify(error='Solo el integrador puede modificar el tablero'),403
   if s['solved'] or s['attempts']>=3:c.rollback();return jsonify(error='El tablero está bloqueado'),409
   if kind=='cell':
    try:i=int(data['person']);j=int(data['step']);v=int(data['place'])
    except (ValueError,KeyError,TypeError):c.rollback();return jsonify(error='Movimiento inválido'),400
    if not (0<=i<4 and 0<=j<4 and -1<=v<4):c.rollback();return jsonify(error='Movimiento inválido'),400
    if v>=0:
     for x in range(4):
      if board[i][x]==v:board[i][x]=-1
    board[i][j]=v;c.execute('UPDATE sessions SET board=? WHERE id=?',(json.dumps(board),sid))
   elif kind=='reset':c.execute('UPDATE sessions SET board=? WHERE id=?',(json.dumps([[-1]*4 for _ in range(4)]),sid))
   elif kind=='validate':
    if any(-1 in r or len(set(r))!=4 for r in board) or any(len({board[r][j] for r in range(4)})!=4 for j in range(4)):c.rollback();return jsonify(error='Completa una distribución válida antes de enviar'),400
    correct=board==ANSWER;c.execute('UPDATE sessions SET attempts=attempts+1,solved=? WHERE id=?',(int(correct),sid))
  else:c.rollback();return jsonify(error='Acción desconocida'),400
  c.commit()
 return jsonify(ok=True)

@app.post('/api/upload')
@admin_required
def upload():
 f=request.files.get('image')
 if not f or not f.mimetype or f.mimetype not in ('image/jpeg','image/png','image/webp'):return jsonify(error='Sube una imagen JPG, PNG o WebP'),400
 name=secrets.token_hex(12)+'.'+('png' if f.mimetype=='image/png' else 'webp' if f.mimetype=='image/webp' else 'jpg')
 folder=ROOT/'static'/'uploads';folder.mkdir(parents=True,exist_ok=True);f.save(folder/name)
 return jsonify(url='/static/uploads/'+name)

@app.get('/qr/<sid>.svg')
def qr(sid):
 import qrcode, io
 import qrcode.image.svg
 from flask import Response
 target=request.host_url.rstrip('/')+'/s/'+sid
 img=qrcode.make(target,image_factory=qrcode.image.svg.SvgPathImage,box_size=12,border=3)
 out=io.BytesIO();img.save(out)
 return Response(out.getvalue(),mimetype='image/svg+xml')

if __name__=='__main__':
 print('\n12 BITS — PANEL DEL FACILITADOR\n')
 port=int(os.environ.get('PORT','5000'))
 print(f'Abre en este computador: http://localhost:{port}/facilitador?key={ADMIN_KEY}\n')
 print('Para escanear el QR desde otros dispositivos, usa la IP local de este computador o publica la app con HTTPS.\n')
 app.run(host='0.0.0.0',port=port,debug=False)
