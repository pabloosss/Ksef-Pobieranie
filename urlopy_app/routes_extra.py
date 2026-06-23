from datetime import date, timedelta
import calendar
import csv
import io
from flask import Response, render_template, request, session, url_for, redirect, flash
from werkzeug.security import generate_password_hash

from .config import LEAVE_TYPES
from .db import get_db
from .helpers import login_required, role_required, is_hr, is_manager, parse_date, visible_user_ids, vacation_summary, log_action


def register_extra_routes(app):
    @app.route("/presence")
    @login_required
    def presence():
        selected = request.args.get("date") or date.today().isoformat()
        department = request.args.get("department", "")
        employee = request.args.get("employee", "")
        day_status = request.args.get("day_status", "")
        leave_type = request.args.get("leave_type", "")
        conn = get_db()
        ids = visible_user_ids(conn)
        employees = []
        stats = {"all": 0, "present": 0, "absent": 0, "remote": 0, "delegation": 0}
        if ids:
            ph = ",".join("?" for _ in ids)
            filters = [f"u.id IN ({ph})", "u.active=1"]
            params = list(ids)
            if department:
                filters.append("u.department=?"); params.append(department)
            if employee:
                filters.append("u.full_name LIKE ?"); params.append(f"%{employee}%")
            people = conn.execute(f"SELECT u.*, m.full_name AS manager_name FROM users u LEFT JOIN users m ON u.manager_id=m.id WHERE {' AND '.join(filters)} ORDER BY u.department, u.full_name", params).fetchall()
            for person in people:
                absence = conn.execute("SELECT * FROM leave_requests WHERE user_id=? AND status IN ('zaakceptowany','rozliczony_kadry') AND date_from<=? AND date_to>=? LIMIT 1", (person["id"], selected, selected)).fetchone()
                st = "obecny"; typ = "—"
                if absence:
                    typ = absence["leave_type"]
                    st = "praca zdalna" if typ == "Praca zdalna" else "delegacja" if typ == "Delegacja" else "nieobecny"
                if day_status and st != day_status:
                    continue
                if leave_type and typ != leave_type:
                    continue
                employees.append({"user": person, "absence": absence, "day_status": st, "type": typ})
                if st == "obecny": stats["present"] += 1
                elif st == "praca zdalna": stats["remote"] += 1
                elif st == "delegacja": stats["delegation"] += 1
                else: stats["absent"] += 1
        stats["all"] = len(employees)
        departments = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
        conn.close()
        return render_template("presence.html", employees=employees, stats=stats, selected_date=selected, departments=departments)

    @app.route("/calendar")
    @login_required
    def calendar_view():
        year = int(request.args.get("year", date.today().year))
        month = int(request.args.get("month", date.today().month))
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        department = request.args.get("department", "")
        employee = request.args.get("employee", "")
        leave_type = request.args.get("leave_type", "")
        conn = get_db()
        ids = visible_user_ids(conn)
        rows = []
        by_day = {}
        if ids:
            ph = ",".join("?" for _ in ids)
            filters = ["lr.status IN ('zaakceptowany','rozliczony_kadry')", "lr.date_from<=?", "lr.date_to>=?", f"lr.user_id IN ({ph})"]
            params = [last.isoformat(), first.isoformat(), *ids]
            if department:
                filters.append("u.department=?"); params.append(department)
            if employee:
                filters.append("u.full_name LIKE ?"); params.append(f"%{employee}%")
            if leave_type:
                filters.append("lr.leave_type=?"); params.append(leave_type)
            rows = conn.execute(f"SELECT lr.*, u.full_name, u.department FROM leave_requests lr JOIN users u ON u.id=lr.user_id WHERE {' AND '.join(filters)} ORDER BY lr.date_from, u.full_name", params).fetchall()
            for row in rows:
                current = max(parse_date(row["date_from"]), first)
                end = min(parse_date(row["date_to"]), last)
                while current <= end:
                    by_day.setdefault(current.day, []).append(row)
                    current += timedelta(days=1)
        departments = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
        conn.close()
        return render_template("calendar.html", selected_year=year, selected_month=month, month_days=calendar.Calendar(firstweekday=0).monthdatescalendar(year, month), requests_by_day=by_day, requests_list=rows, departments=departments)

    @app.route("/employees", methods=["GET", "POST"])
    @login_required
    @role_required("admin", "kadry")
    def employees():
        conn = get_db()
        if request.method == "POST":
            try:
                cur = conn.execute("INSERT INTO users (login, password_hash, full_name, email, role, department, job_title, manager_id, vacation_days, carryover_days, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)", (request.form.get("login"), generate_password_hash(request.form.get("password") or "Start123!"), request.form.get("full_name"), request.form.get("email"), request.form.get("role"), request.form.get("department"), request.form.get("job_title"), request.form.get("manager_id") or None, int(request.form.get("vacation_days") or 26), int(request.form.get("carryover_days") or 0)))
                log_action(conn, "dodano pracownika", "user", cur.lastrowid, request.form.get("full_name"))
                conn.commit(); flash("Pracownik dodany.")
            except Exception:
                flash("Nie udało się dodać pracownika. Sprawdź login.")
        users = conn.execute("SELECT u.*, m.full_name AS manager_name FROM users u LEFT JOIN users m ON u.manager_id=m.id ORDER BY u.active DESC, u.full_name").fetchall()
        departments = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
        managers = conn.execute("SELECT id, full_name FROM users WHERE role IN ('menedzer','admin','kadry') ORDER BY full_name").fetchall()
        conn.close()
        return render_template("employees.html", users=users, departments=departments, managers=managers)

    @app.route("/limits")
    @login_required
    @role_required("admin", "kadry")
    def limits():
        conn = get_db()
        users = conn.execute("SELECT * FROM users WHERE active=1 ORDER BY full_name").fetchall()
        rows = [{"user": u, "summary": vacation_summary(conn, u)} for u in users]
        conn.close()
        return render_template("limits.html", rows=rows)

    @app.route("/reports")
    @login_required
    @role_required("admin", "kadry", "menedzer")
    def reports():
        conn = get_db()
        rows = conn.execute("SELECT lr.*, u.full_name, u.department FROM leave_requests lr JOIN users u ON u.id=lr.user_id ORDER BY lr.created_at DESC LIMIT 200").fetchall()
        conn.close()
        return render_template("reports.html", rows=rows)

    @app.route("/reports/export.csv")
    @login_required
    @role_required("admin", "kadry", "menedzer")
    def export_csv():
        conn = get_db()
        rows = conn.execute("SELECT lr.*, u.full_name, u.department FROM leave_requests lr JOIN users u ON u.id=lr.user_id ORDER BY lr.created_at DESC").fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["Pracownik", "Dział", "Typ", "Od", "Do", "Dni", "Status"])
        for r in rows:
            writer.writerow([r["full_name"], r["department"], r["leave_type"], r["date_from"], r["date_to"], r["days_count"], r["status"]])
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=emerlog_urlopy.csv"})

    @app.route("/audit")
    @login_required
    @role_required("admin", "kadry")
    def audit():
        conn = get_db()
        logs = conn.execute("SELECT al.*, u.full_name AS actor_name FROM audit_logs al LEFT JOIN users u ON u.id=al.actor_user_id ORDER BY al.created_at DESC LIMIT 200").fetchall()
        conn.close()
        return render_template("audit.html", logs=logs)
