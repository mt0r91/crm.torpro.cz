import sqlite3, os, bcrypt
from datetime import datetime, date
from flask import Flask, request, jsonify, session
from flask_session import Session

app = Flask(__name__, static_folder='public', static_url_path='')

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'torpro-crm-secret-2025')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_sessions'
app.config['PERMANENT_SESSION_LIFETIME'] = 28800
os.makedirs('./flask_sessions', exist_ok=True)
Session(app)

DB = os.environ.get('DB_PATH', 'crm.db')

def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M')

def today():
    return date.today().isoformat()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'sales',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT, city TEXT, region TEXT, country TEXT DEFAULT 'CZ',
        phone TEXT, email TEXT, website TEXT, ico TEXT, linkedin TEXT, source TEXT,
        owner_id INTEGER,
        status TEXT DEFAULT 'Новая компания',
        priority TEXT DEFAULT 'med',
        next_action TEXT, next_action_at TEXT, last_contact_at TEXT, notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(owner_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        position TEXT, phone TEXT, email TEXT, linkedin TEXT,
        language TEXT DEFAULT 'RU',
        is_primary INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        contact_id INTEGER, user_id INTEGER,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT, result TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        due_at TEXT,
        FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, contact_id INTEGER, user_id INTEGER,
        type TEXT DEFAULT 'other',
        title TEXT NOT NULL,
        description TEXT, due_at TEXT,
        status TEXT DEFAULT 'open',
        priority TEXT DEFAULT 'med',
        created_at TEXT DEFAULT (datetime('now')),
        completed_at TEXT,
        FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS email_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, subject TEXT, body TEXT,
        created_by INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    admin = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if not admin:
        h = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
        db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)", ('Администратор','admin@torpro.cz',h,'admin'))
        h2 = bcrypt.hashpw(b'sales123', bcrypt.gensalt()).decode()
        s1 = db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)", ('Марек Новак','marek@torpro.cz',h2,'manager')).lastrowid
        s2 = db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)", ('Яна Горакова','jana@torpro.cz',h2,'sales')).lastrowid
        cos = [
            ('METROSTAV a.s.','Генподрядчик','Прага','Прага','+420 731 456 789','info@metrostav.cz','metrostav.cz','Заинтересован','high','Отправить КП','2025-06-05','2025-05-29',s1),
            ('Skanska CZ','Генподрядчик','Брно','Южноморавский','+420 777 234 567','brno@skanska.cz','skanska.cz','Ждём ответа','high','Follow-up звонок','2025-06-06','2025-05-23',s2),
            ('OHL ŽS','Строительная компания','Острава','Моравскосилезский','+420 602 111 222','ohl@ohl.cz','ohlzs.cz','Коллбэк запланирован','med','Коллбэк','2025-06-04 14:30','2025-05-19',s1),
            ('STRABAG SE','Генподрядчик','Пльзень','Пльзеньский','+420 733 888 999','strabag@strabag.cz','strabag.cz','К звонку','high','Первый звонок','2025-06-04',None,s1),
            ('Facility Tech s.r.o.','Facility management','Прага','Прага','+420 608 765 432','info@facilitytech.cz','facilitytech.cz','Ждём ответа','med','Follow-up','2025-06-07','2025-05-13',s2),
            ('D-Construction','Строительная компания','Оломоуц','Оломоуцкий','+420 724 555 666','info@dconstruction.cz','dconstruction.cz','Отправить КП / информацию','high','Подготовить КП','2025-06-05','2025-05-10',s1),
            ('AŽD Praha','Мосты / инфраструктура','Прага','Прага','+420 602 300 400','azd@azd.cz','azd.cz','Встреча / осмотр','high','Осмотр объекта','2025-06-10','2025-05-05',s1),
            ('Hinková Logistika','Логистический центр','Градец Кралове','Краловеградецкий','+420 731 100 200','info@hinkova.cz','hinkova.cz','Звонили — не взял','low','Перезвонить','2025-06-05','2025-05-08',s2),
        ]
        cids = []
        for c in cos:
            cids.append(db.execute("INSERT INTO companies(name,type,city,region,phone,email,website,status,priority,next_action,next_action_at,last_contact_at,owner_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", c).lastrowid)
        db.execute("INSERT INTO contacts(company_id,full_name,position,phone,email,is_primary) VALUES(?,?,?,?,?,1)", (cids[0],'Инж. Павел Коварж','Руководитель проекта','+420 731 456 789','kovar@metrostav.cz'))
        db.execute("INSERT INTO contacts(company_id,full_name,position,phone,email,is_primary) VALUES(?,?,?,?,?,1)", (cids[1],'Яна Горакова','Закупки','+420 777 234 567','horakova@skanska.cz'))
        db.execute("INSERT INTO contacts(company_id,full_name,position,phone,email,is_primary) VALUES(?,?,?,?,?,1)", (cids[2],'Инж. Томаш Блаха','Прораб','+420 602 111 222','blaha@ohl.cz'))
        db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)", (cids[0],s1,'call','Звонок — заинтересован','Дозвонились, интерес к торкрету. Просит КП до пятницы.'))
        db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)", (cids[1],s2,'email','E-mail отправлен','Отправлена презентация TORPRO + референции.'))
        db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)", (cids[2],s1,'call','Звонок — коллбэк','Инж. Блаха просит перезвонить в четверг в 14:30.'))
        db.execute("INSERT INTO tasks(company_id,user_id,type,title,description,due_at,status,priority) VALUES(?,?,?,?,?,?,?,?)", (cids[2],s1,'callback','Коллбэк — OHL ŽS','Инж. Блаха, после совещания.','2025-06-04 14:30','open','high'))
        db.execute("INSERT INTO tasks(company_id,user_id,type,title,description,due_at,status,priority) VALUES(?,?,?,?,?,?,?,?)", (cids[3],s1,'call','Первый звонок — STRABAG','Холодный звонок, контакт из LinkedIn.','2025-06-04','open','high'))
        db.execute("INSERT INTO tasks(company_id,user_id,type,title,description,due_at,status,priority) VALUES(?,?,?,?,?,?,?,?)", (cids[5],s1,'offer','Подготовить КП — D-Construction','Торкрет + ремонт ЖБК. Отправить до пятницы.','2025-06-05','open','high'))
        db.execute("INSERT INTO tasks(company_id,user_id,type,title,description,due_at,status,priority) VALUES(?,?,?,?,?,?,?,?)", (cids[7],s2,'call','Перезвонить — Hinková Logistika','2x не взял. Попробовать 14:00–16:00.','2025-05-30','overdue','low'))
        db.execute("INSERT INTO email_templates(name,subject,body) VALUES(?,?,?)", ('Первичное представление TORPRO','TORPRO — специализированные строительные работы','Добрый день,\n\nХотели бы представить компанию TORPRO — специализированные строительные работы: санация бетона, промышленная гидроизоляция, торкрет, инъекции, ремонт ЖБК.\n\nС уважением,\nКоманда TORPRO'))
        db.execute("INSERT INTO email_templates(name,subject,body) VALUES(?,?,?)", ('Follow-up после звонка','TORPRO — продолжаем наш разговор','Добрый день,\n\nКак договаривались по телефону, прикладываем презентацию и референции TORPRO.\n\nС уважением,\nКоманда TORPRO'))
        db.execute("INSERT INTO email_templates(name,subject,body) VALUES(?,?,?)", ('Коммерческое предложение','TORPRO — Коммерческое предложение','Добрый день,\n\nНа основании нашего разговора направляем коммерческое предложение.\n\nС уважением,\nКоманда TORPRO'))
    db.commit()
    db.close()

# ── HELPERS ──
def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user', {}).get('role') != 'admin':
            return jsonify({'error': 'Только для администратора'}), 403
        return f(*args, **kwargs)
    return decorated

# ── AUTH ──
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=? AND active=1", (data.get('email',''),)).fetchone()
    db.close()
    if not user:
        return jsonify({'error': 'Неверный email или пароль'}), 401
    if not bcrypt.checkpw(data.get('password','').encode(), user['password'].encode()):
        return jsonify({'error': 'Неверный email или пароль'}), 401
    session.permanent = True
    session['user'] = {'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']}
    return jsonify({'ok': True, 'user': session['user']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def me():
    if 'user' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    return jsonify(session['user'])

# ── USERS ──
@app.route('/api/users', methods=['GET'])
@auth_required
def get_users():
    db = get_db()
    users = rows_to_list(db.execute("SELECT id,name,email,role,active,created_at FROM users").fetchall())
    db.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@auth_required
@admin_required
def create_user():
    d = request.json
    if not d.get('name') or not d.get('email') or not d.get('password'):
        return jsonify({'error': 'Заполните все поля'}), 400
    db = get_db()
    if db.execute("SELECT id FROM users WHERE email=?", (d['email'],)).fetchone():
        db.close()
        return jsonify({'error': 'Пользователь с таким email уже существует'}), 400
    h = bcrypt.hashpw(d['password'].encode(), bcrypt.gensalt()).decode()
    uid = db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)", (d['name'],d['email'],h,d.get('role','sales'))).lastrowid
    db.commit(); db.close()
    return jsonify({'ok': True, 'id': uid})

@app.route('/api/users/<int:uid>', methods=['PUT'])
@auth_required
@admin_required
def update_user(uid):
    d = request.json
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u: db.close(); return jsonify({'error': 'Не найдено'}), 404
    if d.get('password'):
        h = bcrypt.hashpw(d['password'].encode(), bcrypt.gensalt()).decode()
        db.execute("UPDATE users SET name=?,email=?,role=?,active=?,password=? WHERE id=?", (d['name'],d['email'],d['role'],1 if d.get('active') else 0,h,uid))
    else:
        db.execute("UPDATE users SET name=?,email=?,role=?,active=? WHERE id=?", (d['name'],d['email'],d['role'],1 if d.get('active') else 0,uid))
    db.commit(); db.close()
    return jsonify({'ok': True})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@auth_required
@admin_required
def delete_user(uid):
    if uid == session['user']['id']:
        return jsonify({'error': 'Нельзя удалить себя'}), 400
    db = get_db()
    db.execute("UPDATE users SET active=0 WHERE id=?", (uid,))
    db.commit(); db.close()
    return jsonify({'ok': True})

# ── COMPANIES ──
@app.route('/api/companies', methods=['GET'])
@auth_required
def get_companies():
    q = "SELECT c.*, u.name as owner_name FROM companies c LEFT JOIN users u ON c.owner_id=u.id WHERE 1=1"
    params = []
    u = session['user']
    if u['role'] == 'sales':
        q += " AND c.owner_id=?"; params.append(u['id'])
    if request.args.get('status') and request.args['status'] != 'all':
        q += " AND c.status=?"; params.append(request.args['status'])
    if request.args.get('priority') and request.args['priority'] != 'all':
        q += " AND c.priority=?"; params.append(request.args['priority'])
    if request.args.get('search'):
        s = f"%{request.args['search']}%"
        q += " AND (c.name LIKE ? OR c.city LIKE ? OR c.type LIKE ?)"; params += [s,s,s]
    q += " ORDER BY c.updated_at DESC"
    db = get_db()
    cos = rows_to_list(db.execute(q, params).fetchall())
    db.close()
    return jsonify(cos)

@app.route('/api/companies/<int:cid>', methods=['GET'])
@auth_required
def get_company(cid):
    db = get_db()
    c = row_to_dict(db.execute("SELECT c.*, u.name as owner_name FROM companies c LEFT JOIN users u ON c.owner_id=u.id WHERE c.id=?", (cid,)).fetchone())
    if not c: db.close(); return jsonify({'error': 'Не найдено'}), 404
    c['contacts'] = rows_to_list(db.execute("SELECT * FROM contacts WHERE company_id=?", (cid,)).fetchall())
    c['activities'] = rows_to_list(db.execute("SELECT a.*, u.name as user_name FROM activities a LEFT JOIN users u ON a.user_id=u.id WHERE a.company_id=? ORDER BY a.created_at DESC", (cid,)).fetchall())
    c['tasks'] = rows_to_list(db.execute("SELECT t.*, u.name as user_name FROM tasks t LEFT JOIN users u ON t.user_id=u.id WHERE t.company_id=? ORDER BY t.due_at ASC", (cid,)).fetchall())
    db.close()
    return jsonify(c)

@app.route('/api/companies', methods=['POST'])
@auth_required
def create_company():
    d = request.json
    if not d.get('name'): return jsonify({'error': 'Укажите название'}), 400
    db = get_db()
    cid = db.execute("INSERT INTO companies(name,type,city,region,phone,email,website,ico,source,priority,notes,owner_id,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d['name'],d.get('type'),d.get('city'),d.get('region'),d.get('phone'),d.get('email'),d.get('website'),d.get('ico'),d.get('source'),d.get('priority','med'),d.get('notes'),session['user']['id'],'Новая компания')).lastrowid
    db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)", (cid,session['user']['id'],'note','Компания добавлена',f"Добавил {session['user']['name']}"))
    db.commit(); db.close()
    return jsonify({'ok': True, 'id': cid})

@app.route('/api/companies/<int:cid>', methods=['PUT'])
@auth_required
def update_company(cid):
    d = request.json
    db = get_db()
    fields = ['name','type','city','region','phone','email','website','ico','linkedin','source','owner_id','priority','next_action','next_action_at','last_contact_at','notes']
    updates = [f"{f}=?" for f in fields if f in d]
    updates.append("updated_at=datetime('now')")
    vals = [d[f] for f in fields if f in d] + [cid]
    if updates:
        db.execute(f"UPDATE companies SET {','.join(updates)} WHERE id=?", vals)
    db.commit(); db.close()
    return jsonify({'ok': True})

@app.route('/api/companies/<int:cid>/status', methods=['PUT'])
@auth_required
def update_status(cid):
    d = request.json
    db = get_db()
    c = row_to_dict(db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone())
    if not c: db.close(); return jsonify({'error': 'Не найдено'}), 404
    db.execute("UPDATE companies SET status=?,next_action=?,next_action_at=?,updated_at=datetime('now') WHERE id=?",
        (d['status'],d.get('next_action',c['next_action']),d.get('next_action_at',c['next_action_at']),cid))
    db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)",
        (cid,session['user']['id'],'status','Статус изменён',f"{c['status']} → {d['status']}"))
    db.commit(); db.close()
    return jsonify({'ok': True})

@app.route('/api/companies/<int:cid>', methods=['DELETE'])
@auth_required
@admin_required
def delete_company(cid):
    db = get_db()
    db.execute("DELETE FROM companies WHERE id=?", (cid,))
    db.commit(); db.close()
    return jsonify({'ok': True})

# ── CALL LOGGING ──
@app.route('/api/companies/<int:cid>/call', methods=['POST'])
@auth_required
def log_call(cid):
    d = request.json
    result = d.get('result','')
    note = d.get('note','')
    db = get_db()
    c = row_to_dict(db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone())
    if not c: db.close(); return jsonify({'error': 'Не найдено'}), 404
    db.execute("INSERT INTO activities(company_id,user_id,type,title,description,result) VALUES(?,?,?,?,?,?)",
        (cid,session['user']['id'],'call','Звонок — '+result,note,result))
    db.execute("UPDATE companies SET last_contact_at=?,updated_at=datetime('now') WHERE id=?", (today(),cid))
    ns, na, nat = c['status'], c['next_action'], c['next_action_at']
    if 'заинтересован' in result: ns,na = 'Заинтересован','Подготовить КП'
    elif 'коллбэк' in result:
        ns,na,nat = 'Коллбэк запланирован','Коллбэк',d.get('callback_at')
        if d.get('callback_at'):
            db.execute("INSERT INTO tasks(company_id,user_id,type,title,description,due_at,status,priority) VALUES(?,?,?,?,?,?,?,?)",
                (cid,session['user']['id'],'callback','Коллбэк — '+c['name'],note,d['callback_at'],'open','high'))
            if note:
                db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)",
                    (cid,session['user']['id'],'callback','Коллбэк запланирован',note+' · '+d['callback_at']))
    elif 'e-mail' in result.lower() or 'email' in result.lower():
        ns,na = 'Отправить e-mail','Отправить письмо'
        db.execute("INSERT INTO tasks(company_id,user_id,type,title,description,due_at,status,priority) VALUES(?,?,?,?,?,?,?,?)",
            (cid,session['user']['id'],'send_email','Отправить e-mail — '+c['name'],note,today(),'open','med'))
    elif result in ('Не взял трубку','Занято'): ns,na = 'Звонили — не взял','Перезвонить'
    elif result == 'Не интересно': ns,na = 'Не интересно',None
    elif result == 'Не беспокоить': ns,na = 'Не беспокоить',None
    else: ns = 'Звонили — дозвонились'
    db.execute("UPDATE companies SET status=?,next_action=?,next_action_at=?,updated_at=datetime('now') WHERE id=?", (ns,na,nat,cid))
    db.commit(); db.close()
    return jsonify({'ok': True, 'new_status': ns})

# ── CONTACTS ──
@app.route('/api/contacts', methods=['GET'])
@auth_required
def get_contacts():
    db = get_db()
    u = session['user']
    if u['role'] == 'sales':
        cts = rows_to_list(db.execute("SELECT ct.*,c.name as company_name FROM contacts ct JOIN companies c ON ct.company_id=c.id WHERE c.owner_id=? ORDER BY ct.full_name", (u['id'],)).fetchall())
    else:
        cts = rows_to_list(db.execute("SELECT ct.*,c.name as company_name FROM contacts ct JOIN companies c ON ct.company_id=c.id ORDER BY ct.full_name").fetchall())
    db.close()
    return jsonify(cts)

@app.route('/api/contacts', methods=['POST'])
@auth_required
def create_contact():
    d = request.json
    if not d.get('company_id') or not d.get('full_name'):
        return jsonify({'error': 'Укажите компанию и имя'}), 400
    db = get_db()
    if d.get('is_primary'):
        db.execute("UPDATE contacts SET is_primary=0 WHERE company_id=?", (d['company_id'],))
    uid = db.execute("INSERT INTO contacts(company_id,full_name,position,phone,email,linkedin,language,is_primary,notes) VALUES(?,?,?,?,?,?,?,?,?)",
        (d['company_id'],d['full_name'],d.get('position'),d.get('phone'),d.get('email'),d.get('linkedin'),d.get('language','RU'),1 if d.get('is_primary') else 0,d.get('notes'))).lastrowid
    db.commit(); db.close()
    return jsonify({'ok': True, 'id': uid})

@app.route('/api/contacts/<int:ctid>', methods=['PUT'])
@auth_required
def update_contact(ctid):
    d = request.json
    db = get_db()
    ct = row_to_dict(db.execute("SELECT * FROM contacts WHERE id=?", (ctid,)).fetchone())
    if not ct: db.close(); return jsonify({'error': 'Не найдено'}), 404
    if d.get('is_primary'):
        db.execute("UPDATE contacts SET is_primary=0 WHERE company_id=?", (ct['company_id'],))
    db.execute("UPDATE contacts SET full_name=?,position=?,phone=?,email=?,language=?,is_primary=?,notes=? WHERE id=?",
        (d.get('full_name',ct['full_name']),d.get('position'),d.get('phone'),d.get('email'),d.get('language','RU'),1 if d.get('is_primary') else 0,d.get('notes'),ctid))
    db.commit(); db.close()
    return jsonify({'ok': True})

@app.route('/api/contacts/<int:ctid>', methods=['DELETE'])
@auth_required
def delete_contact(ctid):
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id=?", (ctid,))
    db.commit(); db.close()
    return jsonify({'ok': True})

# ── ACTIVITIES ──
@app.route('/api/activities', methods=['POST'])
@auth_required
def create_activity():
    d = request.json
    if not d.get('company_id') or not d.get('type') or not d.get('title'):
        return jsonify({'error': 'Заполните обязательные поля'}), 400
    db = get_db()
    aid = db.execute("INSERT INTO activities(company_id,contact_id,user_id,type,title,description,result,due_at) VALUES(?,?,?,?,?,?,?,?)",
        (d['company_id'],d.get('contact_id'),session['user']['id'],d['type'],d['title'],d.get('description'),d.get('result'),d.get('due_at'))).lastrowid
    db.execute("UPDATE companies SET last_contact_at=?,updated_at=datetime('now') WHERE id=?", (today(),d['company_id']))
    db.commit(); db.close()
    return jsonify({'ok': True, 'id': aid})

# ── TASKS ──
@app.route('/api/tasks', methods=['GET'])
@auth_required
def get_tasks():
    q = "SELECT t.*,c.name as company_name,u.name as user_name FROM tasks t LEFT JOIN companies c ON t.company_id=c.id LEFT JOIN users u ON t.user_id=u.id WHERE 1=1"
    params = []
    u = session['user']
    if u['role'] == 'sales': q += " AND t.user_id=?"; params.append(u['id'])
    if request.args.get('status') and request.args['status'] != 'all': q += " AND t.status=?"; params.append(request.args['status'])
    if request.args.get('type'): q += " AND t.type=?"; params.append(request.args['type'])
    if request.args.get('company_id'): q += " AND t.company_id=?"; params.append(request.args['company_id'])
    q += " ORDER BY t.due_at ASC"
    db = get_db()
    tasks = rows_to_list(db.execute(q, params).fetchall())
    db.close()
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
@auth_required
def create_task():
    d = request.json
    if not d.get('title'): return jsonify({'error': 'Укажите название'}), 400
    db = get_db()
    tid = db.execute("INSERT INTO tasks(company_id,contact_id,user_id,type,title,description,due_at,priority) VALUES(?,?,?,?,?,?,?,?)",
        (d.get('company_id'),d.get('contact_id'),session['user']['id'],d.get('type','other'),d['title'],d.get('description'),d.get('due_at'),d.get('priority','med'))).lastrowid
    if d.get('company_id'):
        db.execute("INSERT INTO activities(company_id,user_id,type,title,description) VALUES(?,?,?,?,?)",
            (d['company_id'],session['user']['id'],'note','Задача создана: '+d['title'],d.get('description','')))
    db.commit(); db.close()
    return jsonify({'ok': True, 'id': tid})

@app.route('/api/tasks/<int:tid>', methods=['PUT'])
@auth_required
def update_task(tid):
    d = request.json
    db = get_db()
    t = row_to_dict(db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone())
    if not t: db.close(); return jsonify({'error': 'Не найдено'}), 404
    completed = now() if d.get('status') == 'completed' else t['completed_at']
    db.execute("UPDATE tasks SET status=?,title=?,description=?,due_at=?,priority=?,completed_at=? WHERE id=?",
        (d.get('status',t['status']),d.get('title',t['title']),d.get('description',t['description']),d.get('due_at',t['due_at']),d.get('priority',t['priority']),completed,tid))
    db.commit(); db.close()
    return jsonify({'ok': True})

@app.route('/api/tasks/<int:tid>', methods=['DELETE'])
@auth_required
def delete_task(tid):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit(); db.close()
    return jsonify({'ok': True})

# ── EMAIL TEMPLATES ──
@app.route('/api/email-templates', methods=['GET'])
@auth_required
def get_templates():
    db = get_db()
    tpls = rows_to_list(db.execute("SELECT * FROM email_templates ORDER BY name").fetchall())
    db.close()
    return jsonify(tpls)

@app.route('/api/email-templates', methods=['POST'])
@auth_required
def create_template():
    d = request.json
    if not d.get('name'): return jsonify({'error': 'Укажите название'}), 400
    db = get_db()
    tid = db.execute("INSERT INTO email_templates(name,subject,body,created_by) VALUES(?,?,?,?)",
        (d['name'],d.get('subject',''),d.get('body',''),session['user']['id'])).lastrowid
    db.commit(); db.close()
    return jsonify({'ok': True, 'id': tid})

@app.route('/api/email-templates/<int:tid>', methods=['PUT'])
@auth_required
def update_template(tid):
    d = request.json
    db = get_db()
    db.execute("UPDATE email_templates SET name=?,subject=?,body=? WHERE id=?", (d['name'],d.get('subject',''),d.get('body',''),tid))
    db.commit(); db.close()
    return jsonify({'ok': True})

@app.route('/api/email-templates/<int:tid>', methods=['DELETE'])
@auth_required
@admin_required
def delete_template(tid):
    db = get_db()
    db.execute("DELETE FROM email_templates WHERE id=?", (tid,))
    db.commit(); db.close()
    return jsonify({'ok': True})

# ── DASHBOARD ──
@app.route('/api/dashboard', methods=['GET'])
@auth_required
def dashboard():
    u = session['user']
    can_all = u['role'] in ('admin','manager')
    db = get_db()
    co_filter = "" if can_all else f"AND c.owner_id={u['id']}"
    t_filter = "" if can_all else f"AND t.user_id={u['id']}"
    td = today()
    stats = {
        'total': db.execute(f"SELECT COUNT(*) FROM companies c WHERE 1=1 {co_filter}").fetchone()[0],
        'interested': db.execute(f"SELECT COUNT(*) FROM companies c WHERE c.status='Заинтересован' {co_filter}").fetchone()[0],
        'to_call': db.execute(f"SELECT COUNT(*) FROM companies c WHERE c.status='К звонку' {co_filter}").fetchone()[0],
        'waiting': db.execute(f"SELECT COUNT(*) FROM companies c WHERE c.status='Ждём ответа' {co_filter}").fetchone()[0],
        'callbacks_today': db.execute(f"SELECT COUNT(*) FROM tasks t WHERE t.type='callback' AND t.status='open' AND date(t.due_at)<=? {t_filter}", (td,)).fetchone()[0],
        'overdue': db.execute(f"SELECT COUNT(*) FROM tasks t WHERE t.status='open' AND date(t.due_at)<? {t_filter}", (td,)).fetchone()[0],
    }
    today_tasks = rows_to_list(db.execute(f"SELECT t.*,c.name as company_name FROM tasks t LEFT JOIN companies c ON t.company_id=c.id WHERE t.status IN('open','overdue') AND (date(t.due_at)<=? OR t.status='overdue') {t_filter} ORDER BY t.due_at ASC LIMIT 10", (td,)).fetchall())
    interested_cos = rows_to_list(db.execute(f"SELECT c.*,u.name as owner_name FROM companies c LEFT JOIN users u ON c.owner_id=u.id WHERE c.status IN('Заинтересован','Отправить КП / информацию','Встреча / осмотр') {co_filter} ORDER BY c.updated_at DESC LIMIT 8").fetchall())
    recent_acts = rows_to_list(db.execute("SELECT a.*,c.name as company_name,u.name as user_name FROM activities a LEFT JOIN companies c ON a.company_id=c.id LEFT JOIN users u ON a.user_id=u.id ORDER BY a.created_at DESC LIMIT 15").fetchall())
    team_stats = rows_to_list(db.execute(f"SELECT u.id,u.name,u.role, (SELECT COUNT(*) FROM activities a WHERE a.user_id=u.id AND a.type='call' AND date(a.created_at)=?) as calls, (SELECT COUNT(*) FROM activities a WHERE a.user_id=u.id AND a.type='email' AND date(a.created_at)=?) as emails FROM users u WHERE u.active=1", (td,td)).fetchall())
    db.close()
    return jsonify({'stats':stats,'today_tasks':today_tasks,'interested_cos':interested_cos,'recent_activities':recent_acts,'team_stats':team_stats})

# ── IMPORT ──
@app.route('/api/import', methods=['POST'])
@auth_required
def import_companies():
    rows = request.json.get('rows', [])
    if not rows: return jsonify({'error': 'Нет данных'}), 400
    db = get_db()
    count = 0
    for r in rows:
        if not r.get('name'): continue
        db.execute("INSERT INTO companies(name,type,city,region,phone,email,website,ico,source,owner_id,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (r['name'],r.get('type'),r.get('city'),r.get('region'),r.get('phone'),r.get('email'),r.get('website'),r.get('ico'),r.get('source'),session['user']['id'],'Новая компания'))
        count += 1
    db.commit(); db.close()
    return jsonify({'ok': True, 'imported': count})

# ── STATIC ──
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TORPRO CRM</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.5.0/dist/tabler-icons.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
:root{--bg:#0d1b2a;--bg2:#112236;--bg3:#1a2f45;--red:#e02020;--red2:#b81818;--w:#eef2f7;--mu:#7a8fa6;--mu2:#4a6278;--bd:rgba(238,242,247,0.08);--bd2:rgba(238,242,247,0.15);--gr:#22c55e;--am:#f59e0b;--bl:#3b82f6;--pu:#8b5cf6}
body{background:var(--bg);color:var(--w);min-height:100vh;overflow:hidden}

/* LOGIN */
#login-screen{position:fixed;inset:0;background:var(--bg);display:flex;align-items:center;justify-content:center;z-index:100}
.login-box{background:var(--bg2);border:0.5px solid var(--bd2);border-radius:12px;padding:36px 32px;width:340px}
.login-logo{font-size:22px;font-weight:700;letter-spacing:2px;text-align:center;margin-bottom:4px}
.login-logo span{color:var(--red)}
.login-sub{font-size:11px;color:var(--mu);text-align:center;letter-spacing:2px;text-transform:uppercase;margin-bottom:28px}
.login-err{background:rgba(224,32,32,.15);border:0.5px solid rgba(224,32,32,.3);color:#f87171;font-size:12px;padding:8px 12px;border-radius:6px;margin-bottom:12px;display:none}
.form-group{margin-bottom:14px}
.form-label{font-size:11px;color:var(--mu);margin-bottom:5px;display:block}
.form-input{width:100%;background:var(--bg3);border:0.5px solid var(--bd2);color:var(--w);font-size:13px;padding:9px 12px;border-radius:6px;outline:none;transition:border-color .15s}
.form-input:focus{border-color:var(--red)}
.login-btn{width:100%;background:var(--red);color:#fff;border:none;padding:10px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;margin-top:4px;transition:background .15s}
.login-btn:hover{background:var(--red2)}
.login-hint{font-size:11px;color:var(--mu2);text-align:center;margin-top:14px}
.login-hint b{color:var(--mu)}

/* APP */
#app{display:flex;height:100vh;display:none}
.sb{width:210px;background:var(--bg2);border-right:0.5px solid var(--bd2);display:flex;flex-direction:column;flex-shrink:0}
.logo{padding:16px 14px 12px;border-bottom:0.5px solid var(--bd)}
.logo-t{font-size:17px;font-weight:700;letter-spacing:1px}.logo-t span{color:var(--red)}
.logo-s{font-size:9px;color:var(--mu);letter-spacing:2px;text-transform:uppercase;margin-top:2px}
.nav{padding:10px 6px;flex:1;overflow-y:auto}
.ns{font-size:9px;color:var(--mu2);letter-spacing:2px;text-transform:uppercase;padding:10px 8px 4px}
.ni{display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:5px;font-size:12px;color:var(--mu);cursor:pointer;transition:all .12s;margin-bottom:1px}
.ni:hover{background:var(--bg3);color:var(--w)}
.ni.active{background:rgba(224,32,32,.12);color:var(--w);border-left:2px solid var(--red);padding-left:6px}
.ni i{font-size:15px}
.nbadge{margin-left:auto;font-size:10px;background:var(--red);color:#fff;padding:1px 6px;border-radius:8px;min-width:18px;text-align:center}
.sf{padding:10px;border-top:0.5px solid var(--bd)}
.ur{display:flex;align-items:center;gap:8px;padding:5px 6px;border-radius:5px;cursor:pointer}
.ur:hover{background:var(--bg3)}
.av{width:28px;height:28px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.topbar{background:var(--bg2);border-bottom:0.5px solid var(--bd2);padding:0 16px;height:48px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.tbt{font-size:14px;font-weight:500;display:flex;align-items:center;gap:8px}
.tbr{display:flex;align-items:center;gap:8px}
.btn{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:5px;font-size:11px;cursor:pointer;border:none;transition:all .12s;font-weight:500;white-space:nowrap}
.btn-red{background:var(--red);color:#fff}.btn-red:hover{background:var(--red2)}
.btn-ghost{background:transparent;color:var(--mu);border:0.5px solid var(--bd2)}.btn-ghost:hover{color:var(--w);background:var(--bg3)}
.btn-gr{background:#16a34a;color:#fff}.btn-gr:hover{background:#15803d}
.btn-sm{padding:3px 9px;font-size:11px}
.btn-danger{background:rgba(224,32,32,.15);color:#f87171;border:0.5px solid rgba(224,32,32,.3)}.btn-danger:hover{background:var(--red);color:#fff}
.sw{position:relative}
.sinp{background:var(--bg3);border:0.5px solid var(--bd2);color:var(--w);font-size:12px;padding:5px 9px 5px 28px;border-radius:5px;width:200px}
.sinp:focus{outline:none;border-color:var(--red)}
.sico{position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--mu);font-size:13px;pointer-events:none}
.content{flex:1;overflow:hidden;display:flex;min-height:0}
.screen{flex:1;overflow:hidden;display:flex;flex-direction:column;min-width:0}
.hidden{display:none!important}
.scroll{flex:1;overflow-y:auto;padding:14px}
.scroll::-webkit-scrollbar{width:4px}
.scroll::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:2px}

/* STATS */
.sgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:14px}
.sc{background:var(--bg2);border:0.5px solid var(--bd);border-radius:8px;padding:10px 12px;cursor:pointer;transition:border-color .12s}
.sc:hover{border-color:var(--bd2)}.sc.alert{border-color:rgba(224,32,32,.4)}
.snum{font-size:22px;font-weight:700;line-height:1}
.slbl{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:1px;margin-top:3px}
.ssub{font-size:10px;margin-top:2px}
.red{color:var(--red)}.gr{color:var(--gr)}.am{color:var(--am)}.bl{color:var(--bl)}.pu{color:var(--pu)}
.stitle{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;margin-top:14px}
.tlist{display:flex;flex-direction:column;gap:4px;margin-bottom:14px}
.titem{background:var(--bg2);border:0.5px solid var(--bd);border-radius:7px;padding:9px 12px;display:flex;align-items:center;gap:10px;cursor:pointer;transition:all .12s}
.titem:hover{border-color:var(--bd2)}.titem.ov{border-color:rgba(224,32,32,.4)}.titem.cb{border-left:2px solid var(--am);border-radius:0 7px 7px 0}
.tdot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.tm{flex:1;min-width:0}.tco{font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tsub2{font-size:11px;color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ttime{font-size:11px;color:var(--mu);flex-shrink:0}

/* FILTER BAR */
.fb-bar{display:flex;gap:5px;padding:9px 14px;background:var(--bg2);border-bottom:0.5px solid var(--bd);flex-wrap:wrap;align-items:center;flex-shrink:0}
.fbl{font-size:9px;color:var(--mu2);text-transform:uppercase;letter-spacing:1px}
.fb{font-size:11px;padding:3px 9px;border-radius:4px;border:0.5px solid var(--bd2);background:transparent;color:var(--mu);cursor:pointer;transition:all .1s}
.fb:hover,.fb.act{background:rgba(224,32,32,.12);color:var(--w);border-color:rgba(224,32,32,.3)}
select.fb{appearance:none;padding-right:20px}

/* TABLE */
.tw{flex:1;overflow:auto}
.tw::-webkit-scrollbar{height:4px;width:4px}
.tw::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:2px}
table{width:100%;border-collapse:collapse;font-size:12px;min-width:600px}
thead th{background:var(--bg2);padding:8px 12px;text-align:left;font-size:10px;font-weight:500;color:var(--mu);text-transform:uppercase;letter-spacing:1px;border-bottom:0.5px solid var(--bd2);white-space:nowrap;position:sticky;top:0;z-index:2}
tbody tr{border-bottom:0.5px solid var(--bd);transition:background .1s;cursor:pointer}
tbody tr:hover{background:var(--bg2)}
td{padding:8px 12px;vertical-align:middle;white-space:nowrap}
.cn{font-weight:500;font-size:12px}.cc{font-size:11px;color:var(--mu)}

/* PILLS */
.pill{display:inline-flex;align-items:center;padding:2px 8px;border-radius:3px;font-size:10px;font-weight:600;white-space:nowrap}
.p-new{background:rgba(59,130,246,.15);color:#60a5fa}.p-call{background:rgba(245,158,11,.15);color:#fbbf24}
.p-sent{background:rgba(139,92,246,.15);color:#c084fc}.p-wait{background:rgba(59,130,246,.12);color:#93c5fd}
.p-int{background:rgba(34,197,94,.15);color:#4ade80}.p-off{background:rgba(20,184,166,.15);color:#2dd4bf}
.p-meet{background:rgba(245,158,11,.2);color:#fbbf24}.p-won{background:rgba(34,197,94,.2);color:#22c55e}
.p-lost{background:rgba(224,32,32,.15);color:#f87171}.p-dnc{background:rgba(122,143,166,.15);color:#7a8fa6}
.p-cb{background:rgba(245,158,11,.2);color:#f59e0b}.p-nz{background:rgba(245,158,11,.12);color:#fbbf24}
.p-admin{background:rgba(224,32,32,.2);color:#f87171}.p-mgr{background:rgba(59,130,246,.2);color:#60a5fa}
.p-sales{background:rgba(34,197,94,.2);color:#4ade80}.p-viewer{background:rgba(122,143,166,.2);color:#94a3b8}
.pdot{width:7px;height:7px;border-radius:50%;display:inline-block}
.ph{background:var(--red)}.pm{background:var(--am)}.pl{background:var(--gr)}

/* DETAIL PANEL */
.dp{width:340px;background:var(--bg2);border-left:0.5px solid var(--bd2);display:flex;flex-direction:column;flex-shrink:0;overflow:hidden}
.dph{padding:14px 16px;border-bottom:0.5px solid var(--bd);flex-shrink:0}
.dptop{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.dpco{font-size:15px;font-weight:600}.dpct{font-size:12px;color:var(--mu);margin-top:2px}
.dpacts{display:flex;gap:6px;flex-wrap:wrap}
.dpb{flex:1;overflow-y:auto}.dpb::-webkit-scrollbar{width:3px}.dpb::-webkit-scrollbar-thumb{background:var(--bd2)}
.dpsec{padding:12px 16px;border-bottom:0.5px solid var(--bd)}
.dpst{font-size:9px;color:var(--mu);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
.dpr{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;font-size:12px;gap:8px}
.dplbl{color:var(--mu);flex-shrink:0}.dpval{font-weight:500;text-align:right;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dpsel{background:var(--bg3);border:0.5px solid var(--bd2);color:var(--w);font-size:12px;padding:5px 8px;border-radius:5px;cursor:pointer;width:100%;margin-top:3px;outline:none}
.dpsel:focus{border-color:var(--red)}
.alist{padding:0 16px}
.ai{padding:8px 0;border-bottom:0.5px solid var(--bd);display:flex;gap:9px}
.aico{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}
.aico i{font-size:12px}
.aic{background:rgba(59,130,246,.15);color:#60a5fa}.aie{background:rgba(139,92,246,.15);color:#c084fc}
.ain{background:rgba(122,143,166,.15);color:#94a3b8}.aicb{background:rgba(245,158,11,.15);color:#fbbf24}
.ais{background:rgba(34,197,94,.15);color:#4ade80}
.ab{flex:1;min-width:0}.at2{font-size:12px;font-weight:500}.ad{font-size:11px;color:var(--mu);margin-top:1px;line-height:1.4}.atm{font-size:10px;color:var(--mu2);margin-top:2px}
.nb{padding:10px 14px;border-top:0.5px solid var(--bd);display:flex;gap:6px;flex-shrink:0}
.nta{flex:1;background:var(--bg3);border:0.5px solid var(--bd2);color:var(--w);font-size:12px;padding:6px 9px;border-radius:5px;resize:none;height:32px;line-height:1.4;outline:none}
.nta:focus{border-color:var(--red)}
.nsend{background:var(--red);border:none;color:#fff;width:32px;border-radius:5px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.nsend:hover{background:var(--red2)}

/* KANBAN */
.kanban{flex:1;overflow-x:auto;padding:12px;display:flex;gap:10px}
.kanban::-webkit-scrollbar{height:4px}.kanban::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:2px}
.kcol{min-width:185px;width:185px;flex-shrink:0;display:flex;flex-direction:column}
.kh{padding:8px 10px;border-top:2px solid;margin-bottom:6px}
.ktitle{font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase}
.kcnt{font-size:10px;color:var(--mu);margin-top:2px}
.kbody{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.kbody::-webkit-scrollbar{display:none}
.kcard{background:var(--bg2);border:0.5px solid var(--bd);border-radius:7px;padding:9px 10px;cursor:pointer;transition:all .12s}
.kcard:hover{border-color:var(--bd2);transform:translateY(-1px)}
.kco{font-size:12px;font-weight:500;margin-bottom:2px}.kct{font-size:10px;color:var(--mu);margin-bottom:5px}
.kbot{display:flex;justify-content:space-between;align-items:center}

/* TASKS */
.tr2{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:0.5px solid var(--bd);cursor:pointer;transition:background .1s}
.tr2:hover{background:var(--bg2)}.tr2.ov{border-left:2px solid var(--red)}.tr2.td{border-left:2px solid var(--am)}
.tck{width:16px;height:16px;border-radius:50%;border:0.5px solid var(--bd2);display:flex;align-items:center;justify-content:center;flex-shrink:0;cursor:pointer;transition:all .1s}
.tck:hover{border-color:var(--gr)}.tck.done{background:var(--gr);border-color:var(--gr)}
.ttm{flex:1;min-width:0}.ttt{font-size:12px;font-weight:500}.ttsub{font-size:11px;color:var(--mu);margin-top:1px}
.tdue{font-size:11px;flex-shrink:0}
.abar{background:rgba(245,158,11,.12);border:0.5px solid rgba(245,158,11,.3);border-radius:7px;padding:9px 12px;display:flex;align-items:center;gap:9px;margin-bottom:10px;cursor:pointer}
.abar i{color:var(--am);font-size:16px;flex-shrink:0}.abt{font-size:12px;flex:1}.abt strong{color:var(--am)}

/* MODAL */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:200;display:flex;align-items:center;justify-content:center}
.modal{background:var(--bg2);border:0.5px solid var(--bd2);border-radius:10px;padding:20px;width:400px;max-height:90vh;overflow-y:auto;max-width:95vw}
.modal::-webkit-scrollbar{width:3px}.modal::-webkit-scrollbar-thumb{background:var(--bd2)}
.modal-title{font-size:14px;font-weight:600;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center}
.fg{margin-bottom:12px}
.fl{font-size:11px;color:var(--mu);margin-bottom:4px;display:block}
.fi{width:100%;background:var(--bg3);border:0.5px solid var(--bd2);color:var(--w);font-size:12px;padding:7px 10px;border-radius:5px;outline:none}
.fi:focus{border-color:var(--red)}
.fi-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
select.fi{appearance:none;cursor:pointer}
textarea.fi{resize:vertical;min-height:70px}
.modal-footer{display:flex;gap:8px;margin-top:16px;justify-content:flex-end}
.modal-err{background:rgba(224,32,32,.15);border:0.5px solid rgba(224,32,32,.3);color:#f87171;font-size:12px;padding:7px 10px;border-radius:5px;margin-bottom:10px;display:none}

/* CALL MODAL */
.cres{display:flex;flex-direction:column;gap:4px;margin-bottom:12px;max-height:260px;overflow-y:auto}
.cres::-webkit-scrollbar{width:3px}.cres::-webkit-scrollbar-thumb{background:var(--bd2)}
.crb{background:var(--bg3);border:0.5px solid var(--bd2);color:var(--w);font-size:12px;padding:7px 12px;border-radius:5px;cursor:pointer;text-align:left;transition:all .1s}
.crb:hover{border-color:var(--red);background:rgba(224,32,32,.1)}.crb.sel{border-color:var(--red);background:rgba(224,32,32,.15)}
.clbl{font-size:11px;color:var(--mu);margin-bottom:4px}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login-screen">
  <div class="login-box">
    <div class="login-logo">TOR<span>PRO</span></div>
    <div class="login-sub">Sales CRM</div>
    <div class="login-err" id="login-err"></div>
    <div class="fg">
      <label class="fl">Email</label>
      <input class="form-input" type="email" id="l-email" placeholder="admin@torpro.cz" onkeydown="if(event.key==='Enter')login()">
    </div>
    <div class="fg">
      <label class="fl">Пароль</label>
      <input class="form-input" type="password" id="l-pass" placeholder="••••••••" onkeydown="if(event.key==='Enter')login()">
    </div>
    <button class="login-btn" onclick="login()">Войти</button>
    <div class="login-hint">Демо: <b>admin@torpro.cz</b> / <b>admin123</b><br>Менеджер: <b>marek@torpro.cz</b> / <b>sales123</b></div>
  </div>
</div>

<!-- APP -->
<div id="app">
  <div class="sb">
    <div class="logo">
      <div class="logo-t">TOR<span>PRO</span></div>
      <div class="logo-s">Sales CRM</div>
    </div>
    <div class="nav">
      <div class="ni active" onclick="go('dash')" id="nav-dash"><i class="ti ti-layout-dashboard"></i> Дашборд <span class="nbadge" id="nb-dash">0</span></div>
      <div class="ni" onclick="go('cos')" id="nav-cos"><i class="ti ti-building"></i> Компании</div>
      <div class="ni" onclick="go('kanban')" id="nav-kanban"><i class="ti ti-layout-kanban"></i> Pipeline</div>
      <div class="ni" onclick="go('tasks')" id="nav-tasks"><i class="ti ti-checkbox"></i> Задачи <span class="nbadge" id="nb-tasks">0</span></div>
      <div class="ni" onclick="go('contacts')" id="nav-contacts"><i class="ti ti-users"></i> Контакты</div>
      <div class="ns">Настройки</div>
      <div class="ni" onclick="go('settings')" id="nav-settings"><i class="ti ti-settings"></i> Настройки</div>
      <div class="ni admin-only hidden" onclick="go('admin')" id="nav-admin"><i class="ti ti-shield"></i> Администратор</div>
    </div>
    <div class="sf">
      <div class="ur" onclick="go('profile')">
        <div class="av" id="si-av">??</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:11px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" id="si-name">...</div>
          <div style="font-size:10px;color:var(--mu)" id="si-role">...</div>
        </div>
        <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();logout()" title="Выйти"><i class="ti ti-logout" style="font-size:14px"></i></button>
      </div>
    </div>
  </div>

  <div class="main">
    <div class="topbar">
      <div class="tbt" id="tbt"><i class="ti ti-layout-dashboard"></i> Дашборд</div>
      <div class="tbr">
        <div class="sw"><i class="ti ti-search sico"></i><input class="sinp" type="text" id="sinp" placeholder="Поиск компании..." oninput="searchCos(this.value)"></div>
        <button class="btn btn-ghost" onclick="showImportModal()"><i class="ti ti-upload"></i> Импорт CSV</button>
        <button class="btn btn-red" onclick="showAddCoModal()"><i class="ti ti-plus"></i> Компания</button>
      </div>
    </div>

    <div class="content">

      <!-- ДАШБОРД -->
      <div class="screen" id="scr-dash">
        <div class="scroll">
          <div id="cb-alert"></div>
          <div class="stitle">Обзор на сегодня</div>
          <div class="sgrid" id="dash-stats"></div>
          <div class="stitle">Задачи и коллбэки</div>
          <div class="tlist" id="dash-tasks"></div>
          <div class="stitle">Заинтересованные компании</div>
          <div class="tlist" id="dash-inter"></div>
          <div class="stitle">Последние активности</div>
          <div class="tlist" id="dash-acts"></div>
          <div class="stitle">Активность команды сегодня</div>
          <div class="tlist" id="dash-team"></div>
        </div>
      </div>

      <!-- КОМПАНИИ -->
      <div class="screen hidden" id="scr-cos">
        <div class="fb-bar" id="co-filters">
          <span class="fbl">Статус:</span>
          <button class="fb act" onclick="setCof(this,'all')">Все</button>
          <button class="fb" onclick="setCof(this,'К звонку')">К звонку</button>
          <button class="fb" onclick="setCof(this,'Заинтересован')">Интерес</button>
          <button class="fb" onclick="setCof(this,'Коллбэк запланирован')">Коллбэк</button>
          <button class="fb" onclick="setCof(this,'Ждём ответа')">Ждём</button>
          <button class="fb" onclick="setCof(this,'Не интересно')">Не интересно</button>
          <span class="fbl" style="margin-left:6px">Приоритет:</span>
          <button class="fb" onclick="setPrf(this,'all')">Все</button>
          <button class="fb" onclick="setPrf(this,'high')">Высокий</button>
          <button class="fb" onclick="setPrf(this,'med')">Средний</button>
        </div>
        <div class="tw"><table>
          <thead><tr>
            <th style="width:20px"></th><th>Компания</th><th>Тип</th><th>Город</th>
            <th>Статус</th><th>Ответственный</th><th>Посл. контакт</th><th>След. действие</th><th style="width:80px"></th>
          </tr></thead>
          <tbody id="co-tb"></tbody>
        </table></div>
      </div>

      <!-- PIPELINE -->
      <div class="screen hidden" id="scr-kanban">
        <div class="kanban" id="kb"></div>
      </div>

      <!-- ЗАДАЧИ -->
      <div class="screen hidden" id="scr-tasks">
        <div class="fb-bar">
          <span class="fbl">Фильтр:</span>
          <button class="fb act" onclick="setTf(this,'all')">Все</button>
          <button class="fb" onclick="setTf(this,'overdue')">Просроченные</button>
          <button class="fb" onclick="setTf(this,'callback')">Коллбэки</button>
          <button class="fb" onclick="setTf(this,'open')">Открытые</button>
          <button class="fb" onclick="setTf(this,'completed')">Выполненные</button>
        </div>
        <div class="scroll" style="padding:0"><div id="task-list"></div></div>
      </div>

      <!-- КОНТАКТЫ -->
      <div class="screen hidden" id="scr-contacts">
        <div class="tw"><table>
          <thead><tr><th>Имя</th><th>Компания</th><th>Должность</th><th>Телефон</th><th>E-mail</th><th style="width:80px"></th></tr></thead>
          <tbody id="ct-tb"></tbody>
        </table></div>
      </div>

      <!-- НАСТРОЙКИ -->
      <div class="screen hidden" id="scr-settings">
        <div class="scroll">
          <div class="stitle">E-mail шаблоны</div>
          <div id="etpls" style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px"></div>
          <button class="btn btn-ghost" onclick="showTplModal()"><i class="ti ti-plus"></i> Добавить шаблон</button>
        </div>
      </div>

      <!-- ADMIN -->
      <div class="screen hidden" id="scr-admin">
        <div class="scroll">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div class="stitle" style="margin:0">Пользователи CRM</div>
            <button class="btn btn-red btn-sm" onclick="showAddUserModal()"><i class="ti ti-plus"></i> Добавить</button>
          </div>
          <div id="user-list" style="display:flex;flex-direction:column;gap:6px"></div>
        </div>
      </div>

      <!-- ПРОФИЛЬ -->
      <div class="screen hidden" id="scr-profile">
        <div class="scroll">
          <div class="stitle">Мой профиль</div>
          <div id="profile-card" style="background:var(--bg2);border:0.5px solid var(--bd);border-radius:8px;padding:20px;max-width:400px"></div>
          <div style="margin-top:16px;max-width:400px">
            <div class="stitle">Изменить пароль</div>
            <div class="fg"><label class="fl">Новый пароль</label><input class="fi" type="password" id="new-pass" placeholder="Минимум 6 символов"></div>
            <div class="fg"><label class="fl">Повторите пароль</label><input class="fi" type="password" id="new-pass2" placeholder="Повторите пароль"></div>
            <button class="btn btn-red" onclick="changePass()"><i class="ti ti-key"></i> Сменить пароль</button>
            <div id="pass-msg" style="font-size:12px;margin-top:8px"></div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- DETAIL PANEL -->
  <div class="dp hidden" id="dp">
    <div class="dph">
      <div class="dptop">
        <div><div class="dpco" id="dp-co">—</div><div class="dpct" id="dp-ct">—</div></div>
        <button class="btn btn-ghost btn-sm" onclick="closeDp()"><i class="ti ti-x"></i></button>
      </div>
      <div class="dpacts">
        <button class="btn btn-gr btn-sm" onclick="openCallModal()"><i class="ti ti-phone"></i> Звонок</button>
        <button class="btn btn-ghost btn-sm" onclick="logEmail()"><i class="ti ti-mail"></i> E-mail</button>
        <button class="btn btn-ghost btn-sm" onclick="showAddTaskModal()"><i class="ti ti-checkbox"></i> Задача</button>
        <button class="btn btn-ghost btn-sm" onclick="showEditCoModal()"><i class="ti ti-edit"></i></button>
      </div>
    </div>
    <div class="dpb">
      <div class="dpsec">
        <div class="dpst">Детали компании</div>
        <div class="dpr"><span class="dplbl">Тип</span><span class="dpval" id="dp-type">—</span></div>
        <div class="dpr"><span class="dplbl">Город</span><span class="dpval" id="dp-city">—</span></div>
        <div class="dpr"><span class="dplbl">Телефон</span><span class="dpval" id="dp-phone">—</span></div>
        <div class="dpr"><span class="dplbl">Email</span><span class="dpval" id="dp-email">—</span></div>
        <div class="dpr"><span class="dplbl">Сайт</span><span class="dpval" id="dp-web">—</span></div>
        <div class="dpr"><span class="dplbl">Источник</span><span class="dpval" id="dp-src">—</span></div>
        <div class="dpr"><span class="dplbl">Ответственный</span><span class="dpval" id="dp-own">—</span></div>
      </div>
      <div class="dpsec">
        <div class="dpst">Статус</div>
        <select class="dpsel" id="dp-st" onchange="changeStatus(this.value)">
          <option>Новая компания</option><option>К звонку</option><option>Звонили — не взял</option>
          <option>Звонили — дозвонились</option><option>Отправить e-mail</option><option>E-mail отправлен</option>
          <option>Ждём ответа</option><option>Коллбэк запланирован</option><option>Заинтересован</option>
          <option>Отправить КП / информацию</option><option>Встреча / осмотр</option>
          <option>Получен запрос</option><option>Активный партнёр</option>
          <option>Не интересно</option><option>Не беспокоить</option>
        </select>
        <div class="fg" style="margin-top:8px">
          <label class="fl">След. действие</label>
          <input class="fi" type="text" id="dp-na" placeholder="Что сделать..." onchange="saveNextAction()">
        </div>
        <div class="fg">
          <label class="fl">Когда</label>
          <input class="fi" type="datetime-local" id="dp-nat" onchange="saveNextAction()">
        </div>
      </div>
      <div class="dpsec">
        <div class="dpst">Контакты</div>
        <div id="dp-contacts"></div>
        <button class="btn btn-ghost btn-sm" style="margin-top:6px" onclick="showAddContactModal()"><i class="ti ti-plus"></i> Добавить контакт</button>
      </div>
      <div class="dpsec" style="border-bottom:none"><div class="dpst">История</div></div>
      <div class="alist" id="dp-al"></div>
    </div>
    <div class="nb">
      <textarea class="nta" id="nta" placeholder="Заметка..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();addNote()}"></textarea>
      <button class="nsend" onclick="addNote()"><i class="ti ti-send" style="font-size:13px"></i></button>
    </div>
  </div>
</div>

<!-- MODALS -->
<div id="modal-root"></div>

<script>
const API = '';
let ME = null;
let selCoId = null;
let coFilter = 'all', prFilter = 'all', tfFilter = 'all';
let coSearch = '';

const SPILL = {'Новая компания':'p-new','К звонку':'p-call','Звонили — не взял':'p-nz','Звонили — дозвонились':'p-nz','Отправить e-mail':'p-sent','E-mail отправлен':'p-sent','Ждём ответа':'p-wait','Коллбэк запланирован':'p-cb','Заинтересован':'p-int','Отправить КП / информацию':'p-off','Встреча / осмотр':'p-meet','Получен запрос':'p-off','Активный партнёр':'p-won','Не интересно':'p-lost','Не беспокоить':'p-dnc'};
const SKAN={'Новая компания':'Новые','К звонку':'К контакту','Звонили — не взял':'К контакту','Звонили — дозвонились':'Контактировано','Отправить e-mail':'Контактировано','E-mail отправлен':'Follow-up','Ждём ответа':'Follow-up','Коллбэк запланирован':'Follow-up','Заинтересован':'Интерес','Отправить КП / информацию':'Интерес','Встреча / осмотр':'Запрос','Получен запрос':'Запрос','Активный партнёр':'Партнёр','Не интересно':'Потеряно','Не беспокоить':'Потеряно'};
const KCOLS=[{id:'Новые',c:'#3b82f6'},{id:'К контакту',c:'#f59e0b'},{id:'Контактировано',c:'#8b5cf6'},{id:'Follow-up',c:'#06b6d4'},{id:'Интерес',c:'#22c55e'},{id:'Запрос',c:'#e02020'},{id:'Партнёр',c:'#22c55e'},{id:'Потеряно',c:'#4a6278'}];
const CALL_RES=['Не взял трубку','Занято','Неверный номер','Дозвонились — нет времени','Дозвонились — отправить e-mail','Дозвонились — заинтересован','Дозвонились — коллбэк','Дозвонились — не тот человек','Не интересно','Не беспокоить'];
const ROLES = {admin:'Администратор', manager:'Менеджер', sales:'Продажи', viewer:'Просмотр'};
const ROLE_PILLS = {admin:'p-admin', manager:'p-mgr', sales:'p-sales', viewer:'p-viewer'};

async function api(method, url, body) {
  const opts = {method, headers:{'Content-Type':'application/json'}};
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + url, opts);
  return r.json();
}

// ── AUTH ──
async function login() {
  const email = document.getElementById('l-email').value.trim();
  const pass = document.getElementById('l-pass').value;
  const err = document.getElementById('login-err');
  err.style.display = 'none';
  if (!email || !pass) { err.textContent = 'Введите email и пароль'; err.style.display = 'block'; return; }
  const r = await api('POST', '/api/login', {email, password: pass});
  if (r.error) { err.textContent = r.error; err.style.display = 'block'; return; }
  ME = r.user;
  startApp();
}

async function logout() {
  await api('POST', '/api/logout');
  ME = null;
  document.getElementById('app').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('l-pass').value = '';
}

function startApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  document.getElementById('si-name').textContent = ME.name;
  document.getElementById('si-role').textContent = ROLES[ME.role] || ME.role;
  document.getElementById('si-av').textContent = ME.name.split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase();
  if (ME.role === 'admin' || ME.role === 'manager') document.querySelectorAll('.admin-only').forEach(e=>e.classList.remove('hidden'));
  go('dash');
}

async function checkAuth() {
  const r = await api('GET', '/api/me');
  if (r.id) { ME = r; startApp(); }
}

// ── NAVIGATION ──
const SCREENS = {dash:'Дашборд',cos:'Компании',kanban:'Pipeline',tasks:'Задачи',contacts:'Контакты',settings:'Настройки',admin:'Администратор',profile:'Профиль'};
const ICONS = {dash:'ti-layout-dashboard',cos:'ti-building',kanban:'ti-layout-kanban',tasks:'ti-checkbox',contacts:'ti-users',settings:'ti-settings',admin:'ti-shield',profile:'ti-user'};

function go(s) {
  document.querySelectorAll('.screen').forEach(e=>e.classList.add('hidden'));
  document.querySelectorAll('.ni').forEach(e=>e.classList.remove('active'));
  document.getElementById('scr-'+s)?.classList.remove('hidden');
  document.getElementById('nav-'+s)?.classList.add('active');
  document.getElementById('tbt').innerHTML = `<i class="ti ${ICONS[s]||'ti-circle'}"></i> ${SCREENS[s]||s}`;
  if (s==='dash') loadDash();
  if (s==='cos') loadCos();
  if (s==='kanban') loadKanban();
  if (s==='tasks') loadTasks();
  if (s==='contacts') loadContacts();
  if (s==='settings') loadSettings();
  if (s==='admin') loadAdmin();
  if (s==='profile') loadProfile();
}

// ── DASHBOARD ──
async function loadDash() {
  const d = await api('GET', '/api/dashboard');
  const {stats, today_tasks, interested_cos, recent_activities, team_stats} = d;
  document.getElementById('nb-dash').textContent = (stats.overdue||0) + (stats.callbacks_today||0);

  document.getElementById('dash-stats').innerHTML = `
    <div class="sc alert" onclick="go('tasks')"><div class="snum red">${stats.overdue||0}</div><div class="slbl">Просроченные</div><div class="ssub red">Нужно действие</div></div>
    <div class="sc" onclick="filterGoTasks('callback')"><div class="snum am">${stats.callbacks_today||0}</div><div class="slbl">Коллбэки сегодня</div></div>
    <div class="sc" onclick="filterGoCos('К звонку')"><div class="snum bl">${stats.to_call||0}</div><div class="slbl">К звонку</div></div>
    <div class="sc" onclick="filterGoCos('Заинтересован')"><div class="snum gr">${stats.interested||0}</div><div class="slbl">Заинтересованы</div></div>
    <div class="sc"><div class="snum">${stats.total||0}</div><div class="slbl">Всего компаний</div></div>
    <div class="sc"><div class="snum pu">${stats.waiting||0}</div><div class="slbl">Ждём ответа</div></div>`;

  const cbTask = today_tasks.find(t=>t.type==='callback' && t.status==='open');
  document.getElementById('cb-alert').innerHTML = cbTask ? `<div class="abar" onclick="selCo(${cbTask.company_id})"><i class="ti ti-bell"></i><div class="abt">Коллбэк: <strong>${cbTask.company_name}</strong> — ${cbTask.due_at||''} &nbsp;·&nbsp; ${cbTask.description||''}</div></div>` : '';

  const icoMap = {call:'ti-phone',callback:'ti-phone-call',offer:'ti-file-text',send_email:'ti-mail',follow_up:'ti-refresh',other:'ti-checkbox'};
  document.getElementById('dash-tasks').innerHTML = today_tasks.slice(0,6).map(t=>`<div class="titem ${t.status==='overdue'?'ov':''} ${t.type==='callback'?'cb':''}" onclick="selCo(${t.company_id})">
    <div class="tdot" style="background:${t.status==='overdue'?'var(--red)':t.type==='callback'?'var(--am)':'var(--bl)'}"></div>
    <i class="ti ${icoMap[t.type]||'ti-checkbox'}" style="font-size:14px;color:var(--mu);flex-shrink:0"></i>
    <div class="tm"><div class="tco">${t.title}</div><div class="tsub2">${t.description||''} ${t.company_name?'· '+t.company_name:''}</div></div>
    <div class="ttime">${t.status==='overdue'?'<span class="red">Просрочено</span>':t.due_at||''}</div>
  </div>`).join('') || '<div style="font-size:12px;color:var(--mu);padding:8px 0">Нет задач на сегодня</div>';

  document.getElementById('dash-inter').innerHTML = interested_cos.map(c=>`<div class="titem" onclick="selCo(${c.id})">
    <div class="tdot" style="background:var(--gr)"></div>
    <div class="tm"><div class="tco">${c.name}</div><div class="tsub2">${c.next_action||''} · ${c.city||''}</div></div>
    <span class="pill ${SPILL[c.status]||'p-new'}">${c.status}</span>
  </div>`).join('') || '<div style="font-size:12px;color:var(--mu);padding:8px 0">Нет активных компаний</div>';

  const aicoMap = {call:'aic',email:'aie',note:'ain',callback:'aicb',status:'ais'};
  const aicoIcon = {call:'ti-phone',email:'ti-mail',note:'ti-pencil',callback:'ti-phone-call',status:'ti-refresh'};
  document.getElementById('dash-acts').innerHTML = recent_activities.slice(0,6).map(a=>`<div class="titem">
    <div class="aico ${aicoMap[a.type]||'ain'}"><i class="ti ${aicoIcon[a.type]||'ti-circle'}"></i></div>
    <div class="tm"><div class="tco">${a.title}</div><div class="tsub2">${a.company_name||''} · ${a.user_name||''}</div></div>
    <div class="ttime">${(a.created_at||'').replace('T',' ').substring(5,16)}</div>
  </div>`).join('');

  document.getElementById('dash-team').innerHTML = team_stats.map(u=>`<div class="titem">
    <div class="av" style="width:26px;height:26px;font-size:10px">${u.name.split(' ').map(w=>w[0]).join('').substring(0,2)}</div>
    <div class="tm"><div class="tco">${u.name}</div><div class="tsub2">${ROLES[u.role]||u.role}</div></div>
    <div style="display:flex;gap:12px;font-size:11px">
      <span style="color:var(--bl)"><i class="ti ti-phone"></i> ${u.calls||0}</span>
      <span style="color:var(--pu)"><i class="ti ti-mail"></i> ${u.emails||0}</span>
    </div>
  </div>`).join('');
}

// ── COMPANIES ──
async function loadCos() {
  const params = new URLSearchParams();
  if (coFilter !== 'all') params.set('status', coFilter);
  if (prFilter !== 'all') params.set('priority', prFilter);
  if (coSearch) params.set('search', coSearch);
  const cos = await api('GET', '/api/companies?' + params);
  document.getElementById('co-tb').innerHTML = cos.map(c=>`<tr onclick="selCo(${c.id})">
    <td><span class="pdot p${c.priority}"></span></td>
    <td><div class="cn">${c.name}</div><div class="cc">${c.website||''}</div></td>
    <td><span style="font-size:11px;color:var(--mu)">${c.type||'—'}</span></td>
    <td>${c.city||'—'}</td>
    <td><span class="pill ${SPILL[c.status]||'p-new'}">${c.status}</span></td>
    <td><span style="font-size:11px">${c.owner_name||'—'}</span></td>
    <td><span style="font-size:11px;color:var(--mu)">${c.last_contact_at||'—'}</span></td>
    <td><span style="font-size:11px">${c.next_action||'—'}</span></td>
    <td><button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();selCo(${c.id});openCallModal()"><i class="ti ti-phone"></i></button></td>
  </tr>`).join('') || '<tr><td colspan="9" style="text-align:center;padding:20px;color:var(--mu)">Нет компаний</td></tr>';
}

// ── KANBAN ──
async function loadKanban() {
  const cos = await api('GET', '/api/companies');
  const kb = document.getElementById('kb');
  kb.innerHTML = '';
  KCOLS.forEach(col => {
    const list = cos.filter(c => (SKAN[c.status]||'Новые') === col.id);
    const d = document.createElement('div');
    d.className = 'kcol';
    d.innerHTML = `<div class="kh" style="border-color:${col.c}">
      <div class="ktitle" style="color:${col.c}">${col.id}</div>
      <div class="kcnt">${list.length} компаний</div>
    </div>
    <div class="kbody">${list.map(c=>`<div class="kcard" onclick="selCo(${c.id})">
      <div class="kco">${c.name}</div>
      <div class="kct">${c.city||''} · ${c.type||''}</div>
      <div class="kbot"><span class="pdot p${c.priority}"></span><span style="font-size:10px;color:var(--mu)">${c.next_action||''}</span></div>
    </div>`).join('')}</div>`;
    kb.appendChild(d);
  });
}

// ── TASKS ──
async function loadTasks() {
  const params = new URLSearchParams();
  if (tfFilter === 'callback') params.set('type','callback');
  else if (tfFilter === 'overdue') params.set('status','overdue');
  else if (tfFilter === 'open') params.set('status','open');
  else if (tfFilter === 'completed') params.set('status','completed');
  const tasks = await api('GET', '/api/tasks?' + params);
  const icoMap = {call:'ti-phone',callback:'ti-phone-call',offer:'ti-file-text',send_email:'ti-mail',follow_up:'ti-refresh',other:'ti-checkbox'};
  document.getElementById('task-list').innerHTML = tasks.map(t=>{
    const ov = t.status==='overdue';
    return `<div class="tr2 ${ov?'ov':'td'}" onclick="selCo(${t.company_id})">
      <div class="tck ${t.status==='completed'?'done':''}" onclick="event.stopPropagation();completeTask(${t.id})"><i class="ti ti-check" style="font-size:10px"></i></div>
      <i class="ti ${icoMap[t.type]||'ti-checkbox'}" style="font-size:15px;color:var(--mu);flex-shrink:0"></i>
      <div class="ttm"><div class="ttt">${t.title}</div><div class="ttsub">${t.description||''} ${t.company_name?'· '+t.company_name:''}</div></div>
      <div class="tdue ${ov?'red':'am'}">${t.due_at||''}</div>
      <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();deleteTask(${t.id})"><i class="ti ti-trash"></i></button>
    </div>`;
  }).join('') || '<div style="text-align:center;padding:20px;color:var(--mu);font-size:13px">Нет задач</div>';
  document.getElementById('nb-tasks').textContent = tasks.filter(t=>t.status==='open'||t.status==='overdue').length;
}

// ── CONTACTS ──
async function loadContacts() {
  const cts = await api('GET', '/api/contacts');
  document.getElementById('ct-tb').innerHTML = cts.map(c=>`<tr onclick="selCo(${c.company_id})">
    <td><div style="font-weight:500;font-size:12px">${c.full_name}</div>${c.is_primary?'<span style="font-size:9px;color:var(--gr)">● Основной</span>':''}</td>
    <td><span style="font-size:11px;color:var(--mu)">${c.company_name}</span></td>
    <td><span style="font-size:11px">${c.position||'—'}</span></td>
    <td><a href="tel:${c.phone}" style="font-size:11px;color:var(--bl);text-decoration:none" onclick="event.stopPropagation()">${c.phone||'—'}</a></td>
    <td><a href="mailto:${c.email}" style="font-size:11px;color:var(--pu);text-decoration:none" onclick="event.stopPropagation()">${c.email||'—'}</a></td>
    <td><button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteContact(${c.id})"><i class="ti ti-trash"></i></button></td>
  </tr>`).join('');
}

// ── SETTINGS ──
async function loadSettings() {
  const tpls = await api('GET', '/api/email-templates');
  document.getElementById('etpls').innerHTML = tpls.map(t=>`<div style="background:var(--bg2);border:0.5px solid var(--bd);border-radius:7px;padding:12px 14px">
    <div style="font-size:13px;font-weight:500;margin-bottom:2px">${t.name}</div>
    <div style="font-size:11px;color:var(--mu);margin-bottom:4px">${t.subject}</div>
    <div style="font-size:11px;color:var(--mu2);white-space:pre-line">${(t.body||'').substring(0,120)}${(t.body||'').length>120?'...':''}</div>
    <div style="display:flex;gap:6px;margin-top:8px">
      <button class="btn btn-ghost btn-sm" onclick="copyTemplate(${t.id})"><i class="ti ti-copy"></i> Копировать</button>
      <button class="btn btn-ghost btn-sm" onclick="mailtoTemplate(${t.id})"><i class="ti ti-mail"></i> В почту</button>
      <button class="btn btn-danger btn-sm admin-only" onclick="deleteTpl(${t.id})"><i class="ti ti-trash"></i></button>
    </div>
  </div>`).join('');
  if (ME?.role !== 'admin' && ME?.role !== 'manager') document.querySelectorAll('#etpls .admin-only').forEach(e=>e.classList.add('hidden'));
}

let _tpls = [];
async function copyTemplate(id) {
  const t = (await api('GET', '/api/email-templates')).find(x=>x.id===id);
  if (t) { navigator.clipboard.writeText(`${t.subject}\n\n${t.body}`).then(()=>alert('Скопировано!')); }
}
async function mailtoTemplate(id) {
  const tpls = await api('GET', '/api/email-templates');
  const t = tpls.find(x=>x.id===id);
  if (!t) return;
  const co = selCoId ? (await api('GET', '/api/companies/'+selCoId)) : null;
  const to = co?.email || '';
  window.open(`mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(t.subject)}&body=${encodeURIComponent(t.body)}`);
}
async function deleteTpl(id) {
  if (!confirm('Удалить шаблон?')) return;
  await api('DELETE', '/api/email-templates/'+id);
  loadSettings();
}

// ── ADMIN ──
async function loadAdmin() {
  const users = await api('GET', '/api/users');
  document.getElementById('user-list').innerHTML = users.map(u=>`<div style="background:var(--bg2);border:0.5px solid var(--bd);border-radius:7px;padding:10px 14px;display:flex;align-items:center;gap:10px">
    <div class="av">${u.name.split(' ').map(w=>w[0]).join('').substring(0,2)}</div>
    <div style="flex:1;min-width:0">
      <div style="font-size:13px;font-weight:500">${u.name}</div>
      <div style="font-size:11px;color:var(--mu)">${u.email}</div>
    </div>
    <span class="pill ${ROLE_PILLS[u.role]||'p-viewer'}">${ROLES[u.role]||u.role}</span>
    <span class="pill ${u.active?'p-int':'p-lost'}">${u.active?'Активен':'Заблокирован'}</span>
    <button class="btn btn-ghost btn-sm" onclick="showEditUserModal(${u.id})"><i class="ti ti-edit"></i></button>
    ${u.id !== ME.id ? `<button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})"><i class="ti ti-trash"></i></button>` : ''}
  </div>`).join('');
}

async function deleteUser(id) {
  if (!confirm('Заблокировать пользователя?')) return;
  await api('DELETE', '/api/users/'+id);
  loadAdmin();
}

// ── PROFILE ──
function loadProfile() {
  document.getElementById('profile-card').innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <div class="av" style="width:44px;height:44px;font-size:16px">${ME.name.split(' ').map(w=>w[0]).join('').substring(0,2)}</div>
      <div><div style="font-size:16px;font-weight:600">${ME.name}</div><div style="font-size:12px;color:var(--mu)">${ME.email}</div></div>
    </div>
    <div class="dpr"><span class="dplbl">Роль</span><span class="pill ${ROLE_PILLS[ME.role]||'p-viewer'}">${ROLES[ME.role]||ME.role}</span></div>`;
}

async function changePass() {
  const p1 = document.getElementById('new-pass').value;
  const p2 = document.getElementById('new-pass2').value;
  const msg = document.getElementById('pass-msg');
  if (p1.length < 6) { msg.textContent = 'Минимум 6 символов'; msg.style.color = 'var(--red)'; return; }
  if (p1 !== p2) { msg.textContent = 'Пароли не совпадают'; msg.style.color = 'var(--red)'; return; }
  await api('PUT', '/api/users/'+ME.id, {name:ME.name, email:ME.email, role:ME.role, active:true, password:p1});
  msg.textContent = 'Пароль изменён!'; msg.style.color = 'var(--gr)';
  document.getElementById('new-pass').value = '';
  document.getElementById('new-pass2').value = '';
}

// ── COMPANY DETAIL ──
async function selCo(id) {
  selCoId = id;
  const c = await api('GET', '/api/companies/'+id);
  document.getElementById('dp').classList.remove('hidden');
  document.getElementById('dp-co').textContent = c.name;
  const primary = c.contacts?.find(x=>x.is_primary) || c.contacts?.[0];
  document.getElementById('dp-ct').textContent = primary ? primary.full_name + (primary.position?' · '+primary.position:'') : c.type||'';
  document.getElementById('dp-type').textContent = c.type||'—';
  document.getElementById('dp-city').textContent = (c.city||'—') + (c.region?' ('+c.region+')':'');
  document.getElementById('dp-phone').textContent = c.phone||'—';
  document.getElementById('dp-email').textContent = c.email||'—';
  document.getElementById('dp-web').textContent = c.website||'—';
  document.getElementById('dp-src').textContent = c.source||'—';
  document.getElementById('dp-own').textContent = c.owner_name||'—';
  document.getElementById('dp-st').value = c.status||'Новая компания';
  document.getElementById('dp-na').value = c.next_action||'';
  document.getElementById('dp-nat').value = c.next_action_at ? c.next_action_at.replace(' ','T').substring(0,16) : '';
  renderContacts(c.contacts||[]);
  renderActivities(c.activities||[]);
}

function closeDp() { selCoId = null; document.getElementById('dp').classList.add('hidden'); }

function renderContacts(cts) {
  document.getElementById('dp-contacts').innerHTML = cts.map(c=>`<div style="background:var(--bg3);border-radius:5px;padding:7px 9px;margin-bottom:4px;display:flex;align-items:center;gap:8px">
    <div style="flex:1;min-width:0">
      <div style="font-size:12px;font-weight:500">${c.full_name}${c.is_primary?' <span style="font-size:9px;color:var(--gr)">●</span>':''}</div>
      <div style="font-size:11px;color:var(--mu)">${c.position||''}</div>
      ${c.phone?`<a href="tel:${c.phone}" style="font-size:11px;color:var(--bl);text-decoration:none;display:block">${c.phone}</a>`:''}
      ${c.email?`<a href="mailto:${c.email}" style="font-size:11px;color:var(--pu);text-decoration:none;display:block">${c.email}</a>`:''}
    </div>
    <button class="btn btn-danger btn-sm" onclick="deleteContact(${c.id})"><i class="ti ti-trash"></i></button>
  </div>`).join('') || '<div style="font-size:12px;color:var(--mu)">Нет контактов</div>';
}

function renderActivities(acts) {
  const aicoMap = {call:'aic',email:'aie',note:'ain',callback:'aicb',status:'ais'};
  const aicoIcon = {call:'ti-phone',email:'ti-mail',note:'ti-pencil',callback:'ti-phone-call',status:'ti-refresh'};
  document.getElementById('dp-al').innerHTML = acts.map(a=>`<div class="ai">
    <div class="aico ${aicoMap[a.type]||'ain'}"><i class="ti ${aicoIcon[a.type]||'ti-circle'}"></i></div>
    <div class="ab"><div class="at2">${a.title}</div><div class="ad">${a.description||''}</div><div class="atm">${(a.created_at||'').replace('T',' ').substring(0,16)} · ${a.user_name||''}</div></div>
  </div>`).join('') || '<div style="padding:10px 0;font-size:12px;color:var(--mu);text-align:center">Нет активностей</div>';
}

async function addNote() {
  const ta = document.getElementById('nta');
  const text = ta.value.trim();
  if (!text || !selCoId) return;
  await api('POST', '/api/activities', {company_id: selCoId, type:'note', title:'Заметка', description: text});
  ta.value = '';
  selCo(selCoId);
}

async function changeStatus(val) {
  if (!selCoId) return;
  await api('PUT', '/api/companies/'+selCoId+'/status', {status:val});
  selCo(selCoId);
  if (document.getElementById('scr-cos').classList.contains('hidden') === false) loadCos();
  if (document.getElementById('scr-kanban').classList.contains('hidden') === false) loadKanban();
}

async function saveNextAction() {
  if (!selCoId) return;
  const na = document.getElementById('dp-na').value;
  const nat = document.getElementById('dp-nat').value;
  await api('PUT', '/api/companies/'+selCoId, {next_action: na, next_action_at: nat});
}

async function logEmail() {
  if (!selCoId) return;
  await api('POST', '/api/activities', {company_id: selCoId, type:'email', title:'E-mail отправлен', description:'Вручную отмечено отправление письма.'});
  await api('PUT', '/api/companies/'+selCoId+'/status', {status:'E-mail отправлен'});
  selCo(selCoId);
}

// ── CALL MODAL ──
let selCallRes = null;
function openCallModal() {
  if (!selCoId) return;
  const co = document.getElementById('dp-co').textContent;
  const ph = document.getElementById('dp-phone').textContent;
  selCallRes = null;
  showModal(`<div class="modal-title">Записать звонок <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div style="font-size:14px;font-weight:600;margin-bottom:2px">${co}</div>
    <div style="font-size:12px;color:var(--mu);margin-bottom:12px">${ph}</div>
    <div style="font-size:11px;color:var(--mu);margin-bottom:6px">Результат звонка:</div>
    <div class="cres" id="call-results">${CALL_RES.map((r,i)=>`<button class="crb" onclick="selCallResult('${r}',this)">${r}</button>`).join('')}</div>
    <div class="hidden fg" id="cb-row">
      <label class="fl">Дата и время коллбэка:</label>
      <input class="fi" type="datetime-local" id="cb-dt">
      <label class="fl" style="margin-top:6px">Заметка:</label>
      <input class="fi" type="text" id="cb-note" placeholder="Что сказал контакт...">
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
      <button class="btn btn-red" onclick="saveCall()"><i class="ti ti-check"></i> Сохранить</button>
    </div>`);
}

function selCallResult(r, btn) {
  selCallRes = r;
  document.querySelectorAll('.crb').forEach(b=>b.classList.remove('sel'));
  btn.classList.add('sel');
  const cbRow = document.getElementById('cb-row');
  if (cbRow) cbRow.classList.toggle('hidden', r !== 'Дозвонились — коллбэк');
}

async function saveCall() {
  if (!selCallRes || !selCoId) { alert('Выберите результат звонка'); return; }
  const note = document.getElementById('cb-note')?.value || '';
  const cbDt = document.getElementById('cb-dt')?.value || '';
  await api('POST', '/api/companies/'+selCoId+'/call', {result: selCallRes, note, callback_at: cbDt});
  closeModal();
  selCo(selCoId);
  loadDash();
}

// ── MODALS ──
function showModal(html) {
  document.getElementById('modal-root').innerHTML = `<div class="modal-bg" onclick="if(event.target===this)closeModal()"><div class="modal">${html}</div></div>`;
}
function closeModal() { document.getElementById('modal-root').innerHTML = ''; }

function showAddCoModal() {
  showModal(`<div class="modal-title">Новая компания <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="modal-err" id="co-err"></div>
    <div class="fi-row"><div class="fg"><label class="fl">Название *</label><input class="fi" id="c-name" placeholder="ООО Строй..."></div>
    <div class="fg"><label class="fl">Тип</label><select class="fi" id="c-type"><option value="">—</option>${['Генподрядчик','Строительная компания','Facility management','Управляющая компания','Логистический центр','Промышленный объект','Парковка','Мосты / инфраструктура','Девелопер','Проектная организация','Производственный цех','Гос. сектор','Другой'].map(t=>`<option>${t}</option>`).join('')}</select></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Город</label><input class="fi" id="c-city"></div>
    <div class="fg"><label class="fl">Регион</label><input class="fi" id="c-region"></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Телефон</label><input class="fi" id="c-phone"></div>
    <div class="fg"><label class="fl">Email</label><input class="fi" type="email" id="c-email"></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Сайт</label><input class="fi" id="c-web"></div>
    <div class="fg"><label class="fl">ИНН / IČO</label><input class="fi" id="c-ico"></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Источник</label><input class="fi" id="c-src" placeholder="LinkedIn, Google Maps..."></div>
    <div class="fg"><label class="fl">Приоритет</label><select class="fi" id="c-pri"><option value="med">Средний</option><option value="high">Высокий</option><option value="low">Низкий</option></select></div></div>
    <div class="fg"><label class="fl">Заметка</label><textarea class="fi" id="c-notes"></textarea></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="saveCo()"><i class="ti ti-check"></i> Создать</button></div>`);
}

async function saveCo() {
  const name = document.getElementById('c-name').value.trim();
  const err = document.getElementById('co-err');
  if (!name) { err.textContent = 'Укажите название'; err.style.display = 'block'; return; }
  const r = await api('POST', '/api/companies', {
    name, type: document.getElementById('c-type').value, city: document.getElementById('c-city').value,
    region: document.getElementById('c-region').value, phone: document.getElementById('c-phone').value,
    email: document.getElementById('c-email').value, website: document.getElementById('c-web').value,
    ico: document.getElementById('c-ico').value, source: document.getElementById('c-src').value,
    priority: document.getElementById('c-pri').value, notes: document.getElementById('c-notes').value
  });
  if (r.error) { err.textContent = r.error; err.style.display = 'block'; return; }
  closeModal(); loadCos(); selCo(r.id);
}

async function showEditCoModal() {
  if (!selCoId) return;
  const c = await api('GET', '/api/companies/'+selCoId);
  showModal(`<div class="modal-title">Редактировать компанию <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="fi-row"><div class="fg"><label class="fl">Название</label><input class="fi" id="ec-name" value="${c.name||''}"></div>
    <div class="fg"><label class="fl">Тип</label><select class="fi" id="ec-type">${['','Генподрядчик','Строительная компания','Facility management','Управляющая компания','Логистический центр','Промышленный объект','Парковка','Мосты / инфраструктура','Девелопер','Проектная организация','Производственный цех','Гос. сектор','Другой'].map(t=>`<option ${c.type===t?'selected':''}>${t}</option>`).join('')}</select></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Город</label><input class="fi" id="ec-city" value="${c.city||''}"></div>
    <div class="fg"><label class="fl">Регион</label><input class="fi" id="ec-region" value="${c.region||''}"></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Телефон</label><input class="fi" id="ec-phone" value="${c.phone||''}"></div>
    <div class="fg"><label class="fl">Email</label><input class="fi" id="ec-email" value="${c.email||''}"></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Сайт</label><input class="fi" id="ec-web" value="${c.website||''}"></div>
    <div class="fg"><label class="fl">Источник</label><input class="fi" id="ec-src" value="${c.source||''}"></div></div>
    <div class="fg"><label class="fl">Заметки</label><textarea class="fi" id="ec-notes">${c.notes||''}</textarea></div>
    <div class="modal-footer">
      ${ME?.role==='admin'?`<button class="btn btn-danger" onclick="deleteCo(${c.id})"><i class="ti ti-trash"></i> Удалить</button>`:''}
      <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
      <button class="btn btn-red" onclick="updateCo(${c.id})"><i class="ti ti-check"></i> Сохранить</button>
    </div>`);
}

async function updateCo(id) {
  await api('PUT', '/api/companies/'+id, {
    name: document.getElementById('ec-name').value, type: document.getElementById('ec-type').value,
    city: document.getElementById('ec-city').value, region: document.getElementById('ec-region').value,
    phone: document.getElementById('ec-phone').value, email: document.getElementById('ec-email').value,
    website: document.getElementById('ec-web').value, source: document.getElementById('ec-src').value,
    notes: document.getElementById('ec-notes').value
  });
  closeModal(); selCo(id); loadCos();
}

async function deleteCo(id) {
  if (!confirm('Удалить компанию безвозвратно?')) return;
  await api('DELETE', '/api/companies/'+id);
  closeModal(); closeDp(); loadCos();
}

function showAddContactModal() {
  if (!selCoId) return;
  showModal(`<div class="modal-title">Добавить контакт <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="fg"><label class="fl">Имя *</label><input class="fi" id="ct-name" placeholder="Иван Иванов"></div>
    <div class="fi-row"><div class="fg"><label class="fl">Должность</label><input class="fi" id="ct-pos"></div>
    <div class="fg"><label class="fl">Язык</label><select class="fi" id="ct-lang"><option>RU</option><option>CZ</option><option>SK</option><option>EN</option></select></div></div>
    <div class="fi-row"><div class="fg"><label class="fl">Телефон</label><input class="fi" id="ct-phone"></div>
    <div class="fg"><label class="fl">Email</label><input class="fi" type="email" id="ct-email"></div></div>
    <div class="fg"><label class="fl"><input type="checkbox" id="ct-primary" style="margin-right:6px">Основной контакт</label></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="saveCt()"><i class="ti ti-check"></i> Добавить</button></div>`);
}

async function saveCt() {
  const name = document.getElementById('ct-name').value.trim();
  if (!name) return alert('Укажите имя');
  await api('POST', '/api/contacts', {
    company_id: selCoId, full_name: name, position: document.getElementById('ct-pos').value,
    phone: document.getElementById('ct-phone').value, email: document.getElementById('ct-email').value,
    language: document.getElementById('ct-lang').value, is_primary: document.getElementById('ct-primary').checked
  });
  closeModal(); selCo(selCoId); loadContacts();
}

async function deleteContact(id) {
  if (!confirm('Удалить контакт?')) return;
  await api('DELETE', '/api/contacts/'+id);
  if (selCoId) selCo(selCoId);
  loadContacts();
}

function showAddTaskModal() {
  showModal(`<div class="modal-title">Новая задача <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="fg"><label class="fl">Название *</label><input class="fi" id="tk-title" placeholder="Позвонить, отправить КП..."></div>
    <div class="fi-row"><div class="fg"><label class="fl">Тип</label><select class="fi" id="tk-type"><option value="call">Звонок</option><option value="callback">Коллбэк</option><option value="send_email">Отправить e-mail</option><option value="offer">Подготовить КП</option><option value="follow_up">Follow-up</option><option value="other">Другое</option></select></div>
    <div class="fg"><label class="fl">Приоритет</label><select class="fi" id="tk-pri"><option value="med">Средний</option><option value="high">Высокий</option><option value="low">Низкий</option></select></div></div>
    <div class="fg"><label class="fl">Срок</label><input class="fi" type="datetime-local" id="tk-due"></div>
    <div class="fg"><label class="fl">Описание</label><textarea class="fi" id="tk-desc"></textarea></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="saveTask()"><i class="ti ti-check"></i> Создать</button></div>`);
}

async function saveTask() {
  const title = document.getElementById('tk-title').value.trim();
  if (!title) return alert('Укажите название');
  await api('POST', '/api/tasks', {
    company_id: selCoId, title, type: document.getElementById('tk-type').value,
    priority: document.getElementById('tk-pri').value, due_at: document.getElementById('tk-due').value,
    description: document.getElementById('tk-desc').value
  });
  closeModal();
  if (selCoId) selCo(selCoId);
  loadTasks();
}

async function completeTask(id) {
  await api('PUT', '/api/tasks/'+id, {status:'completed'});
  loadTasks();
}
async function deleteTask(id) {
  if (!confirm('Удалить задачу?')) return;
  await api('DELETE', '/api/tasks/'+id);
  loadTasks();
}

// ── USER MODALS ──
function showAddUserModal() {
  showModal(`<div class="modal-title">Новый пользователь <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="modal-err" id="u-err"></div>
    <div class="fg"><label class="fl">Имя *</label><input class="fi" id="u-name" placeholder="Иван Иванов"></div>
    <div class="fg"><label class="fl">Email *</label><input class="fi" type="email" id="u-email" placeholder="ivan@torpro.cz"></div>
    <div class="fi-row"><div class="fg"><label class="fl">Пароль *</label><input class="fi" type="password" id="u-pass" placeholder="Мин. 6 символов"></div>
    <div class="fg"><label class="fl">Роль</label><select class="fi" id="u-role"><option value="sales">Продажи</option><option value="manager">Менеджер</option><option value="admin">Администратор</option><option value="viewer">Просмотр</option></select></div></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="saveUser()"><i class="ti ti-check"></i> Создать</button></div>`);
}

async function saveUser() {
  const err = document.getElementById('u-err');
  const name = document.getElementById('u-name').value.trim();
  const email = document.getElementById('u-email').value.trim();
  const pass = document.getElementById('u-pass').value;
  if (!name || !email || !pass) { err.textContent = 'Заполните все поля'; err.style.display = 'block'; return; }
  const r = await api('POST', '/api/users', {name, email, password: pass, role: document.getElementById('u-role').value});
  if (r.error) { err.textContent = r.error; err.style.display = 'block'; return; }
  closeModal(); loadAdmin();
}

async function showEditUserModal(id) {
  const users = await api('GET', '/api/users');
  const u = users.find(x=>x.id===id);
  if (!u) return;
  showModal(`<div class="modal-title">Редактировать пользователя <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="fg"><label class="fl">Имя</label><input class="fi" id="eu-name" value="${u.name}"></div>
    <div class="fg"><label class="fl">Email</label><input class="fi" type="email" id="eu-email" value="${u.email}"></div>
    <div class="fi-row"><div class="fg"><label class="fl">Новый пароль (необязательно)</label><input class="fi" type="password" id="eu-pass" placeholder="Оставить пустым"></div>
    <div class="fg"><label class="fl">Роль</label><select class="fi" id="eu-role">${['sales','manager','admin','viewer'].map(r=>`<option value="${r}" ${u.role===r?'selected':''}>${ROLES[r]}</option>`).join('')}</select></div></div>
    <div class="fg"><label class="fl"><input type="checkbox" id="eu-active" ${u.active?'checked':''} style="margin-right:6px">Активен</label></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="updateUser(${id})"><i class="ti ti-check"></i> Сохранить</button></div>`);
}

async function updateUser(id) {
  const body = {name: document.getElementById('eu-name').value, email: document.getElementById('eu-email').value, role: document.getElementById('eu-role').value, active: document.getElementById('eu-active').checked};
  const p = document.getElementById('eu-pass').value;
  if (p) body.password = p;
  await api('PUT', '/api/users/'+id, body);
  closeModal(); loadAdmin();
}

// ── TEMPLATE MODAL ──
function showTplModal() {
  showModal(`<div class="modal-title">Новый шаблон <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div class="fg"><label class="fl">Название *</label><input class="fi" id="tpl-name" placeholder="Первичное представление..."></div>
    <div class="fg"><label class="fl">Тема письма</label><input class="fi" id="tpl-subj" placeholder="TORPRO — ..."></div>
    <div class="fg"><label class="fl">Текст письма</label><textarea class="fi" id="tpl-body" style="min-height:120px" placeholder="Добрый день,..."></textarea></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="saveTpl()"><i class="ti ti-check"></i> Сохранить</button></div>`);
}

async function saveTpl() {
  const name = document.getElementById('tpl-name').value.trim();
  if (!name) return alert('Укажите название');
  await api('POST', '/api/email-templates', {name, subject: document.getElementById('tpl-subj').value, body: document.getElementById('tpl-body').value});
  closeModal(); loadSettings();
}

// ── IMPORT CSV ──
function showImportModal() {
  showModal(`<div class="modal-title">Импорт компаний из CSV <button class="btn btn-ghost btn-sm" onclick="closeModal()"><i class="ti ti-x"></i></button></div>
    <div style="font-size:12px;color:var(--mu);margin-bottom:10px">Формат CSV (первая строка — заголовки):<br><code style="font-size:11px;color:var(--am)">name,type,city,region,phone,email,website,source</code></div>
    <div class="fg"><label class="fl">Выбрать CSV файл</label><input class="fi" type="file" id="csv-file" accept=".csv"></div>
    <div id="csv-preview" style="font-size:12px;color:var(--mu);margin-top:8px"></div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal()">Отмена</button><button class="btn btn-red" onclick="doImport()"><i class="ti ti-upload"></i> Импортировать</button></div>`);
  document.getElementById('csv-file').addEventListener('change', previewCsv);
}

let csvRows = [];
function previewCsv(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    const lines = ev.target.result.split('\n').filter(l=>l.trim());
    const headers = lines[0].split(',').map(h=>h.trim().toLowerCase());
    csvRows = lines.slice(1).map(l => {
      const vals = l.split(',').map(v=>v.trim().replace(/^"|"$/g,''));
      const obj = {};
      headers.forEach((h,i) => obj[h] = vals[i]||'');
      return obj;
    }).filter(r=>r.name);
    document.getElementById('csv-preview').textContent = `Найдено ${csvRows.length} компаний для импорта.`;
  };
  reader.readAsText(file);
}

async function doImport() {
  if (!csvRows.length) return alert('Загрузите CSV файл');
  const r = await api('POST', '/api/import', {rows: csvRows});
  closeModal();
  alert(`Импортировано ${r.imported} компаний`);
  loadCos();
}

// ── FILTERS ──
function setCof(btn, v) { coFilter = v; document.querySelectorAll('#scr-cos .fb').forEach(b=>b.classList.remove('act')); btn.classList.add('act'); loadCos(); }
function setPrf(btn, v) { prFilter = v; loadCos(); }
function setTf(btn, v) { tfFilter = v; document.querySelectorAll('#scr-tasks .fb').forEach(b=>b.classList.remove('act')); btn.classList.add('act'); loadTasks(); }
function searchCos(q) { coSearch = q; if (document.getElementById('scr-cos').classList.contains('hidden')===false) loadCos(); }
function filterGoCos(f) { coFilter = f; go('cos'); }
function filterGoTasks(f) { tfFilter = f; go('tasks'); }

// ── INIT ──
checkAuth();
</script>
</body>
</html>
"""

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    return HTML_PAGE, 200, {'Content-Type': 'text/html; charset=utf-8'}

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 3000))
    print(f"TORPRO CRM запущен: http://localhost:{port}")
    print("Логин: admin@torpro.cz / admin123")
    app.run(host='0.0.0.0', port=port, debug=False)
