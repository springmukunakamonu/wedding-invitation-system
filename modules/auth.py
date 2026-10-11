from functools import wraps
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from database.db import query, execute  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    def _missing_db(*args, **kwargs):
        raise ModuleNotFoundError("database.db could not be imported")

    query = _missing_db
    execute = _missing_db

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = query("SELECT * FROM admins WHERE username = ?", (username,), one=True)
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["username"] = admin["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

def create_admin(username, password):
    exists = query("SELECT id FROM admins WHERE username = ?", (username,), one=True)
    if exists:
        return
    execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)))