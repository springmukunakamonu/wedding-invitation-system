import sqlite3
import os
from config import Config


def get_db():
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
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
    try:
        cur = conn.execute(sql, args)
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        conn.close()


def execute(sql, args=()):
    conn = get_db()
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        last_id = cur.lastrowid
        return last_id
    except sqlite3.OperationalError:
        # If somehow the write still fails, roll back cleanly
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_guest(guest_id):
    conn = get_db()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            DELETE FROM checkins
            WHERE guest_id = ?
               OR invitation_id IN (SELECT id FROM invitations WHERE guest_id = ?)
        """, (guest_id, guest_id))
        conn.execute("""
            DELETE FROM whatsapp_logs
            WHERE guest_id = ?
               OR invitation_id IN (SELECT id FROM invitations WHERE guest_id = ?)
        """, (guest_id, guest_id))
        conn.execute("DELETE FROM invitations WHERE guest_id = ?", (guest_id,))
        cur = conn.execute("DELETE FROM guests WHERE id = ?", (guest_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()