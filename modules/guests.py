import uuid
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from database.db import query, execute
from modules.auth import login_required
from modules.invitations import generate_invitation_for_guest

guests_bp = Blueprint("guests", __name__)


def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


def validate_phone(phone: str) -> bool:
    digits = phone.lstrip("+")
    return digits.isdigit() and 8 <= len(digits) <= 15


@guests_bp.route("/guests")
@login_required
def list_guests():
    q = request.args.get("q", "").strip()
    if q:
        rows = query("""
            SELECT g.*,
                   i.id AS invitation_id, i.token, i.reference_no, i.file_path,
                   (SELECT status FROM whatsapp_logs w
                    WHERE w.guest_id = g.id ORDER BY w.id DESC LIMIT 1) AS wa_status,
                   (SELECT COUNT(*) FROM checkins c WHERE c.guest_id = g.id) AS checked_in
            FROM guests g
            LEFT JOIN invitations i ON i.guest_id = g.id
            WHERE g.full_name LIKE ? OR g.phone LIKE ?
            ORDER BY g.created_at DESC
        """, (f"%{q}%", f"%{q}%"))
    else:
        rows = query("""
            SELECT g.*,
                   i.id AS invitation_id, i.token, i.reference_no, i.file_path,
                   (SELECT status FROM whatsapp_logs w
                    WHERE w.guest_id = g.id ORDER BY w.id DESC LIMIT 1) AS wa_status,
                   (SELECT COUNT(*) FROM checkins c WHERE c.guest_id = g.id) AS checked_in
            FROM guests g
            LEFT JOIN invitations i ON i.guest_id = g.id
            ORDER BY g.created_at DESC
        """)
    return render_template("guests.html", guests=rows, q=q)


@guests_bp.route("/guests/new", methods=["GET", "POST"])
@login_required
def new_guest():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = normalize_phone(request.form.get("phone", ""))
        allowed = int(request.form.get("allowed_count", 1))
        category = request.form.get("category", "Friends").strip()

        if not full_name or not validate_phone(phone):
            flash("Invalid name or phone number.", "error")
            return redirect(url_for("guests.new_guest"))

        existing = query("SELECT * FROM guests WHERE phone = ?", (phone,), one=True)
        if existing:
            flash(f"Phone already registered to {existing['full_name']}.", "warning")
            return redirect(url_for("guests.edit_guest", guest_id=existing["id"]))

        guest_code = "G-" + uuid.uuid4().hex[:8].upper()
        guest_id = execute("""
            INSERT INTO guests (guest_code, full_name, phone, allowed_count, category)
            VALUES (?, ?, ?, ?, ?)
        """, (guest_code, full_name, phone, allowed, category))

        try:
            generate_invitation_for_guest(guest_id)
        except Exception as e:
            flash(f"Guest saved but invitation failed: {e}", "warning")

        flash("Guest registered and invitation generated.", "success")
        return redirect(url_for("guests.list_guests"))

    return render_template("guest_form.html", guest=None)


@guests_bp.route("/guests/<int:guest_id>/edit", methods=["GET", "POST"])
@login_required
def edit_guest(guest_id):
    guest = query("SELECT * FROM guests WHERE id = ?", (guest_id,), one=True)
    if not guest:
        flash("Guest not found.", "error")
        return redirect(url_for("guests.list_guests"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = normalize_phone(request.form.get("phone", ""))
        allowed = int(request.form.get("allowed_count", 1))
        category = request.form.get("category", "Friends").strip()

        if not validate_phone(phone):
            flash("Invalid phone.", "error")
            return redirect(url_for("guests.edit_guest", guest_id=guest_id))

        execute("""
            UPDATE guests SET full_name=?, phone=?, allowed_count=?, category=?,
                              updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (full_name, phone, allowed, category, guest_id))
        flash("Guest updated.", "success")
        return redirect(url_for("guests.list_guests"))

    return render_template("guest_form.html", guest=guest)


@guests_bp.route("/guests/<int:guest_id>/delete", methods=["POST"])
@login_required
def delete_guest(guest_id):
    execute("DELETE FROM guests WHERE id = ?", (guest_id,))
    flash("Guest deleted.", "success")
    return redirect(url_for("guests.list_guests"))


@guests_bp.route("/api/guests/search")
@login_required
def api_search():
    q = request.args.get("q", "").strip()
    rows = query("""
        SELECT id, guest_code, full_name, phone, allowed_count, category
        FROM guests
        WHERE full_name LIKE ? OR phone LIKE ?
        LIMIT 20
    """, (f"%{q}%", f"%{q}%"))
    return jsonify([dict(r) for r in rows])