import sqlite3, os, bcrypt
from datetime import datetime, date
from flask import Flask, request, jsonify, session, send_from_directory
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
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join('public', path)):
        return send_from_directory('public', path)
    return send_from_directory('public', 'index.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 3000))
    print(f"TORPRO CRM запущен: http://localhost:{port}")
    print("Логин: admin@torpro.cz / admin123")
    app.run(host='0.0.0.0', port=port, debug=False)
