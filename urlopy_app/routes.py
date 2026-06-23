from datetime import date, timedelta
import calendar
import csv
import io
from flask import Response, flash, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from .config import LEAVE_TYPES, LIMIT_TYPES
from .db import get_db
from .helpers import (
    login_required, role_required, is_hr, is_manager, parse_date, count_workdays,
    current_user, visible_user_ids, vacation_summary, log_action
)


def can_decide(owner):
    if is_hr():
        return True
    if is_manager() and owner and owner["manager_id"] == session.get("user_id") and owner["id"] != session.get("user_id"):
        return True
    return False


def register_routes(app):
    @app.route("/grafiki/<path:filename>")
    def graphics(filename):
        return send_from_directory("grafiki", filename)

    @app.route("/")
    def index():
        return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE login=? AND active=1", (request.form.get("login", "").strip(),)).fetchone()
            conn.close()
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.update({"user_id": user["id"], "login": user["login"], "full_name": user["full_name"], "role": user["role"]})
                return redirect(url_for("dashboard"))
            flash("Błędny login albo hasło.")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        conn = get_db()
        user = current_user(conn)
        ids = visible_user_ids(conn)
        today = date.today().isoformat()
        stats = {"pending": 0, "absent_today": 0, "employee_count": len(ids), "upcoming": [], "latest": []}
        if ids:
            ph = ",".join("?" for _ in ids)
            stats["pending"] = conn.execute(f"SELECT COUNT(*) AS c FROM leave_requests WHERE status IN ('oczekuje_menedzer','oczekuje_kadry') AND user_id IN ({ph})", ids).fetchone()["c"] or 0
            stats["absent_today"] = conn.execute(f"SELECT COUNT(DISTINCT user_id) AS c FROM leave_requests WHERE status IN ('zaakceptowany','rozliczony_kadry') AND date_from<=? AND date_to>=? AND user_id IN ({ph})", (today, today, *ids)).fetchone()["c"] or 0
            stats["upcoming"] = conn.execute(f"SELECT lr.*, u.full_name, u.department FROM leave_requests lr JOIN users u ON u.id=lr.user_id WHERE lr.status IN ('zaakceptowany','rozliczony_kadry') AND lr.date_from>=? AND lr.user_id IN ({ph}) ORDER BY lr.date_from LIMIT 6", (today, *ids)).fetchall()
        if is_hr():
            stats["employee_count"] = conn.execute("SELECT COUNT(*) AS c FROM users WHERE active=1").fetchone()["c"] or 0
        stats["latest"] = conn.execute("SELECT * FROM leave_requests WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (user["id"],)).fetchall()
        summary = vacation_summary(conn, user)
        conn.close()
        return render_template("dashboard.html", user=user, stats=stats, summary=summary)

    @app.route("/leave/new", methods=["GET", "POST"])
    @login_required
    def new_leave():
        conn = get_db()
        user = current_user(conn)
        employees = conn.execute("SELECT id, full_name FROM users WHERE active=1 AND id!=? ORDER BY full_name", (user["id"],)).fetchall()
        summary = vacation_summary(conn, user)
        if request.method == "POST":
            leave_type = request.form.get("leave_type")
            date_from = request.form.get("date_from")
            date_to = request.form.get("date_to")
            comment = request.form.get("comment")
            replacement = request.form.get("replacement_user_id") or None
            try:
                days = count_workdays(parse_date(date_from), parse_date(date_to))
            except Exception as e:
                flash(str(e)); conn.close(); return redirect(url_for("new_leave"))
            if days <= 0:
                flash("Wybrany zakres nie zawiera dni roboczych."); conn.close(); return redirect(url_for("new_leave"))
            if leave_type in LIMIT_TYPES and days > summary["available"]:
                flash(f"Brak limitu. Dostępne: {summary['available']} dni, wybrano: {days} dni."); conn.close(); return redirect(url_for("new_leave"))
            status = "oczekuje_menedzer" if user["manager_id"] else "oczekuje_kadry"
            cur = conn.execute("INSERT INTO leave_requests (user_id, leave_type, date_from, date_to, days_count, comment, status, replacement_user_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (user["id"], leave_type, date_from, date_to, days, comment, status, replacement))
            log_action(conn, "złożono wniosek", "leave_request", cur.lastrowid, f"{leave_type}: {date_from} - {date_to}")
            conn.commit(); conn.close()
            flash(f"Wniosek wysłany. System policzył {days} dni roboczych.")
            return redirect(url_for("requests_view"))
        conn.close()
        return render_template("leave_form.html", employees=employees, summary=summary)

    @app.route("/requests")
    @login_required
    def requests_view():
        conn = get_db()
        ids = visible_user_ids(conn)
        rows = []
        if ids:
            ph = ",".join("?" for _ in ids)
            filters = [f"lr.user_id IN ({ph})"]
            params = list(ids)
            for arg, col in [("status", "lr.status"), ("department", "u.department"), ("leave_type", "lr.leave_type")]:
                val = request.args.get(arg, "").strip()
                if val:
                    filters.append(f"{col}=?"); params.append(val)
            employee = request.args.get("employee", "").strip()
            if employee:
                filters.append("u.full_name LIKE ?"); params.append(f"%{employee}%")
            rows = conn.execute(f"""
                SELECT lr.*, u.full_name, u.department, u.manager_id, m.full_name AS manager_name, d.full_name AS decider_name
                FROM leave_requests lr
                JOIN users u ON u.id=lr.user_id
                LEFT JOIN users m ON u.manager_id=m.id
                LEFT JOIN users d ON lr.decided_by=d.id
                WHERE {' AND '.join(filters)}
                ORDER BY lr.created_at DESC
            """, params).fetchall()
        departments = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
        conn.close()
        return render_template("requests.html", requests_list=rows, departments=departments)

    @app.route("/requests/<int:request_id>")
    @login_required
    def request_detail(request_id):
        conn = get_db()
        req = conn.execute("""
            SELECT lr.*, u.full_name, u.department, u.email, u.manager_id, m.full_name AS manager_name, d.full_name AS decider_name
            FROM leave_requests lr
            JOIN users u ON u.id=lr.user_id
            LEFT JOIN users m ON u.manager_id=m.id
            LEFT JOIN users d ON lr.decided_by=d.id
            WHERE lr.id=?
        """, (request_id,)).fetchone()
        logs = conn.execute("SELECT al.*, u.full_name AS actor_name FROM audit_logs al LEFT JOIN users u ON u.id=al.actor_user_id WHERE al.entity_type='leave_request' AND al.entity_id=? ORDER BY al.created_at DESC", (request_id,)).fetchall()
        conn.close()
        return render_template("request_detail.html", req=req, logs=logs)

    @app.route("/requests/<int:request_id>/<action>", methods=["POST"])
    @login_required
    def request_action(request_id, action):
        status_map = {"accept": "zaakceptowany", "reject": "odrzucony", "return": "do_poprawy", "cancel": "anulowany", "settle": "rozliczony_kadry"}
        if action not in status_map:
            flash("Nieznana akcja."); return redirect(url_for("requests_view"))
        comment = request.form.get("decision_comment", "").strip()
        if action in {"reject", "return"} and not comment:
            flash("Komentarz jest wymagany przy odrzuceniu lub cofnięciu do poprawy."); return redirect(url_for("requests_view"))
        conn = get_db()
        req = conn.execute("SELECT * FROM leave_requests WHERE id=?", (request_id,)).fetchone()
        owner = conn.execute("SELECT * FROM users WHERE id=?", (req["user_id"],)).fetchone() if req else None
        if not req:
            conn.close(); flash("Nie znaleziono wniosku."); return redirect(url_for("requests_view"))
        if action in {"accept", "reject", "return", "settle"} and not can_decide(owner):
            conn.close(); flash("Brak uprawnień do decyzji."); return redirect(url_for("requests_view"))
        if action == "settle" and not is_hr():
            conn.close(); flash("Tylko kadry/admin mogą rozliczyć wniosek."); return redirect(url_for("requests_view"))
        if action == "cancel" and not (req["user_id"] == session["user_id"] or can_decide(owner)):
            conn.close(); flash("Nie można anulować tego wniosku."); return redirect(url_for("requests_view"))
        new_status = status_map[action]
        conn.execute("UPDATE leave_requests SET status=?, decision_comment=?, decided_by=?, decided_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_status, comment, session["user_id"], request_id))
        log_action(conn, f"zmieniono status na {new_status}", "leave_request", request_id, comment)
        conn.commit(); conn.close()
        flash(f"Status zmieniony na: {new_status}.")
        return redirect(url_for("requests_view"))

    @app.route("/approvals")
    @login_required
    def approvals():
        return redirect(url_for("requests_view", status="oczekuje_menedzer"))
