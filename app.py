import importlib.util
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flask import Flask, render_template, session, redirect, url_for

_config_path = os.path.join(ROOT_DIR, "config.py")
_config_spec = importlib.util.spec_from_file_location("config", _config_path)
if _config_spec is None or _config_spec.loader is None:
    raise ImportError(f"Unable to load config module from {_config_path}")
_config_module = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(_config_module)
Config = _config_module.Config

_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "db.py")
_db_spec = importlib.util.spec_from_file_location("database.db", _db_path)
if _db_spec is None or _db_spec.loader is None:
    raise ImportError(f"Unable to load database module from {_db_path}")
_database_db = importlib.util.module_from_spec(_db_spec)
_db_spec.loader.exec_module(_database_db)
init_db = _database_db.init_db
query = _database_db.query

from modules.auth import auth_bp, login_required, create_admin
from modules.guests import guests_bp
from modules.invitations import invitations_bp
from modules.whatsapp import whatsapp_bp
from modules.checkin import checkin_bp
from modules.settings import settings_bp

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(guests_bp)
app.register_blueprint(invitations_bp)
app.register_blueprint(whatsapp_bp)
app.register_blueprint(checkin_bp)
app.register_blueprint(settings_bp)


@app.route("/")
@login_required
def dashboard():
    stats = {
        "total_guests": query("SELECT COUNT(*) c FROM guests", one=True)["c"],
        "total_invitations": query("SELECT COUNT(*) c FROM invitations", one=True)["c"],
        "sent": query(
            "SELECT COUNT(DISTINCT guest_id) c FROM whatsapp_logs "
            "WHERE status IN ('sent','delivered')", one=True
        )["c"],
        "pending": query(
            "SELECT COUNT(DISTINCT guest_id) c FROM whatsapp_logs WHERE status='pending'",
            one=True
        )["c"],
        "failed": query(
            "SELECT COUNT(DISTINCT guest_id) c FROM whatsapp_logs WHERE status='failed'",
            one=True
        )["c"],
        "checked_in_guests": query(
            "SELECT COUNT(DISTINCT guest_id) c FROM checkins", one=True
        )["c"],
        "total_people_checked_in": query(
            "SELECT COALESCE(SUM(people_count),0) c FROM checkins", one=True
        )["c"],
    }
    stats["not_checked_in"] = stats["total_guests"] - stats["checked_in_guests"]

    by_category = query("""
        SELECT g.category,
               COUNT(DISTINCT g.id) AS total,
               COUNT(DISTINCT c.guest_id) AS checked_in
        FROM guests g
        LEFT JOIN checkins c ON c.guest_id = g.id
        GROUP BY g.category
    """)

    return render_template("dashboard.html", stats=stats, by_category=by_category)


if __name__ == "__main__":
    init_db()
    create_admin("admin", "admin123")   # Change in production!
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)