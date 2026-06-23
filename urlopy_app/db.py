import sqlite3
from werkzeug.security import generate_password_hash
from .config import DATABASE


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL,
            department TEXT DEFAULT 'Spedycja',
            job_title TEXT DEFAULT '',
            manager_id INTEGER,
            vacation_days INTEGER DEFAULT 26,
            carryover_days INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            date_from TEXT NOT NULL,
            date_to TEXT NOT NULL,
            days_count INTEGER NOT NULL,
            comment TEXT,
            status TEXT DEFAULT 'oczekuje_menedzer',
            decision_comment TEXT,
            decided_by INTEGER,
            decided_at TEXT,
            replacement_user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for dep in ["Spedycja", "Księgowość", "Kadry", "IT", "Zarząd"]:
        cur.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (dep,))

    demo = [
        ("jan", "jan123", "Jan Kowalski", "jan.kowalski@emerlog.pl", "pracownik", "Spedycja", "Spedytor", "anna"),
        ("anna", "anna123", "Anna Nowak", "anna.nowak@emerlog.pl", "menedzer", "Spedycja", "Kierownik spedycji", "ewa"),
        ("pawel", "pawel123", "Paweł Pisarczyk", "pawel.pisarczyk@emerlog.pl", "menedzer", "IT", "Menedżer IT", "ewa"),
        ("ewa", "ewa123", "Ewa Dusińska", "ewa.dusinska@emerlog.pl", "admin", "Kadry", "Kadry / Admin", None),
        ("kadry", "kadry123", "Kadry EMERLOG", "kadry@emerlog.pl", "kadry", "Kadry", "Kadry", "ewa"),
        ("admin", "admin123", "Administrator", "admin@emerlog.pl", "admin", "IT", "Administrator", None),
    ]

    for login, password, name, email, role, dep, job, manager in demo:
        if not cur.execute("SELECT id FROM users WHERE login = ?", (login,)).fetchone():
            cur.execute("""
                INSERT INTO users (login, password_hash, full_name, email, role, department, job_title)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (login, generate_password_hash(password), name, email, role, dep, job))

    conn.commit()

    for login, _, _, _, _, _, _, manager_login in demo:
        if manager_login:
            manager = cur.execute("SELECT id FROM users WHERE login = ?", (manager_login,)).fetchone()
            employee = cur.execute("SELECT id FROM users WHERE login = ?", (login,)).fetchone()
            if manager and employee:
                cur.execute("UPDATE users SET manager_id = ? WHERE id = ?", (manager["id"], employee["id"]))

    conn.commit()
    conn.close()
