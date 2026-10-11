from flask import Blueprint, request, jsonify, render_template

try:
    from database.db import query, execute  # type: ignore[reportMissingImports]
    from modules.auth import login_required  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - supports package-relative imports.
    from ..database.db import query, execute  # type: ignore[reportMissingImports]
    from .auth import login_required  # type: ignore[reportMissingImports]

checkin_bp = Blueprint("checkin", __name__)

@checkin_bp.route("/scanner")
@login_required
def scanner_page():
    return render_template("scanner.html")


@checkin_bp.route("/api/checkin", methods=["POST"])
@login_required
def api_checkin():
    data = request.get_json() or {}
    token = (data.get("token") or "").strip()
    people_count = int(data.get("people_count") or 0)

    if not token:
        return jsonify({"status": "invalid", "message": "No token provided."}), 400

    # 1. Look up the invitation by token
    inv = query("""
        SELECT i.*, g.full_name, g.allowed_count, g.category, g.phone
        FROM invitations i
        JOIN guests g ON g.id = i.guest_id
        WHERE i.token = ?
    """, (token,), one=True)

    if not inv:
        return jsonify({"status": "invalid", "message": "Invalid or revoked invitation."})

    # 2. Already checked in?
    existing = query("""
        SELECT c.*, g.full_name
        FROM checkins c
        JOIN guests g ON g.id = c.guest_id
        WHERE c.invitation_id = ?
        ORDER BY c.id DESC LIMIT 1
    """, (inv["id"],), one=True)

    if existing:
        return jsonify({
            "status": "used",
            "message": "This invitation has already been used.",
            "guest_name": existing["full_name"],
            "checked_in_at": existing["checked_in_at"],
            "people_count": existing["people_count"],
        })

    # 3. First scan — return info, ask staff to confirm headcount
    if people_count <= 0:
        return jsonify({
            "status": "valid",
            "guest_name": inv["full_name"],
            "allowed_count": inv["allowed_count"],
            "category": inv["category"],
            "invitation_id": inv["id"],
            "guest_id": inv["guest_id"],
            "ask_count": True,
        })

    # 4. Enforce allowed count
    if people_count > inv["allowed_count"]:
        return jsonify({
            "status": "invalid",
            "message": f"Exceeds allowed count ({inv['allowed_count']}).",
        })

    # 5. Re-check inside a fresh read (defense against simultaneous scans)
    again = query("SELECT id FROM checkins WHERE invitation_id = ?", (inv["id"],), one=True)
    if again:
        return jsonify({"status": "used", "message": "Already checked in."})

    # 6. Record attendance
    execute("""
        INSERT INTO checkins (guest_id, invitation_id, people_count)
        VALUES (?, ?, ?)
    """, (inv["guest_id"], inv["id"], people_count))

    return jsonify({
        "status": "ok",
        "message": f"Welcome, {inv['full_name']}! Checked in {people_count} person(s).",
        "guest_name": inv["full_name"],
        "people_count": people_count,
    })


@checkin_bp.route("/api/manual-checkin/<int:guest_id>", methods=["POST"])
@login_required
def manual_checkin(guest_id):
    """Fallback for when QR scanning isn't available — search + check in manually."""
    data = request.get_json() or {}
    people_count = int(data.get("people_count") or 1)

    guest = query("SELECT * FROM guests WHERE id = ?", (guest_id,), one=True)
    inv = query("SELECT * FROM invitations WHERE guest_id = ?", (guest_id,), one=True)
    if not guest or not inv:
        return jsonify({"status": "invalid", "message": "Guest or invitation missing."})

    existing = query("SELECT id FROM checkins WHERE invitation_id = ?", (inv["id"],), one=True)
    if existing:
        return jsonify({"status": "used", "message": "Already checked in."})

    if people_count > guest["allowed_count"] or people_count <= 0:
        return jsonify({
            "status": "invalid",
            "message": f"Count must be 1..{guest['allowed_count']}.",
        })

    execute("INSERT INTO checkins (guest_id, invitation_id, people_count) VALUES (?, ?, ?)",
            (guest_id, inv["id"], people_count))

    return jsonify({
        "status": "ok",
        "message": f"{guest['full_name']} checked in ({people_count}).",
    })