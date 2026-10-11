import sqlite3
import os
from config import Config


def get_db():
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    with open(os.path.join(Config.BASE_DIR, "database", "schema.sql"), "r") as f:
        conn.executescript(f.read())

    cur = conn.execute("SELECT COUNT(*) AS c FROM wedding_settings")
    if cur.fetchone()["c"] == 0:
        conn.execute("""
            INSERT INTO wedding_settings
                (id, bride_name, groom_name, wedding_date, ceremony_time,
                 venue, venue_address, reception_details, dress_code,
                 invitation_message, contact_phone, background_image)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Bride Name", "Groom Name",
            "2025-12-20", "14:00",
            "St. Mary's Cathedral",
            "123 Wedding Avenue, Lusaka, Zambia",
            "Reception at 18:00 at Grand Hall",
            "Formal / Elegant",
            "Together with joy, we invite you to celebrate our wedding.",
            "+260 97 000 0000",
            ""
        ))
    conn.commit()
    conn.close()


def query(sql, args=(), one=False):
    conn = get_db()
    cur = conn.execute(sql, args)
    rows = cur.fetchall()
    conn.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    conn = get_db()
    cur = conn.execute(sql, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id