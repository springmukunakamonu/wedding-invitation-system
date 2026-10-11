import os
import sys
import uuid
import qrcode
from io import BytesIO
from pathlib import Path

from flask import Blueprint, send_file, abort, redirect, url_for, flash
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config  # type: ignore[import-not-found]
from database.db import query, execute  # type: ignore[import-not-found]
from modules.auth import login_required

invitations_bp = Blueprint("invitations", __name__)

def _ensure_dirs():
    os.makedirs(Config.INVITATION_FOLDER, exist_ok=True)
    os.makedirs(Config.BACKGROUND_FOLDER, exist_ok=True)

def _make_qr(token: str) -> ImageReader:
    qr = qrcode.QRCode(version=None, box_size=10, border=2)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)

def generate_pdf(guest, invitation, settings) -> str:
    _ensure_dirs()
    filename = f"{invitation['reference_no']}.pdf"
    filepath = os.path.join(Config.INVITATION_FOLDER, filename)

    c = canvas.Canvas(filepath, pagesize=A5)
    width, height = A5

    # Cream background
    bg_color = colors.HexColor("#FAF7F0")
    c.setFillColor(bg_color)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Dark green border
    c.setStrokeColor(colors.HexColor("#0B3D2E"))
    c.setLineWidth(3)
    c.rect(8 * mm, 8 * mm, width - 16 * mm, height - 16 * mm)

    # Optional background image
    if settings["background_image"]:
        bg_path = os.path.join(Config.BACKGROUND_FOLDER, settings["background_image"])
        if os.path.exists(bg_path):
            c.drawImage(bg_path, 8 * mm, 8 * mm,
                        width=width - 16 * mm, height=height - 16 * mm,
                        mask="auto", preserveAspectRatio=True)

    # Title
    c.setFillColor(colors.HexColor("#0B3D2E"))
    c.setFont("Times-Bold", 22)
    c.drawCentredString(width / 2, height - 25 * mm, "WEDDING INVITATION")

    c.setFont("Times-Italic", 14)
    c.setFillColor(colors.HexColor("#B8860B"))
    c.drawCentredString(width / 2, height - 33 * mm, "Together with joy")

    # Couple names
    c.setFillColor(colors.HexColor("#0B3D2E"))
    c.setFont("Times-Bold", 18)
    c.drawCentredString(width / 2, height - 45 * mm,
                        f"{settings['bride_name']}  &  {settings['groom_name']}")

    # Guest line
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawCentredString(width / 2, height - 58 * mm, "Dear")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 65 * mm, guest["full_name"])

    # Message (wrapped)
    c.setFont("Helvetica-Oblique", 10)
    text = c.beginText(18 * mm, height - 78 * mm)
    text.setLeading(13)
    msg = settings["invitation_message"] or ""
    line = ""
    for word in msg.split():
        if c.stringWidth(line + " " + word, "Helvetica-Oblique", 10) < (width - 36 * mm):
            line = (line + " " + word).strip()
        else:
            text.textLine(line)
            line = word
    if line:
        text.textLine(line)
    c.drawText(text)

    # Details block
    y = height - 105 * mm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#0B3D2E"))
    c.drawString(18 * mm, y, "Date & Time:")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(50 * mm, y, f"{settings['wedding_date']} at {settings['ceremony_time']}")

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#0B3D2E"))
    c.drawString(18 * mm, y - 7 * mm, "Venue:")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(50 * mm, y - 7 * mm, f"{settings['venue']}")
    c.drawString(50 * mm, y - 13 * mm, f"{settings['venue_address']}")

    if settings["reception_details"]:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#0B3D2E"))
        c.drawString(18 * mm, y - 22 * mm, "Reception:")
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(50 * mm, y - 22 * mm, settings["reception_details"])

    if settings["dress_code"]:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#0B3D2E"))
        c.drawString(18 * mm, y - 31 * mm, "Dress Code:")
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(50 * mm, y - 31 * mm, settings["dress_code"])

    # QR code (bottom right)
    qr_img = _make_qr(invitation["token"])
    qr_size = 35 * mm
    c.drawImage(qr_img, width - qr_size - 15 * mm, 15 * mm,
                width=qr_size, height=qr_size)

    # Footer info
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(15 * mm, 22 * mm, f"Reference: {invitation['reference_no']}")
    c.drawString(15 * mm, 17 * mm, f"Admits: {guest['allowed_count']} person(s)")
    c.drawString(15 * mm, 12 * mm, f"Contact: {settings['contact_phone'] or ''}")

    c.showPage()
    c.save()
    return filepath

def generate_invitation_for_guest(guest_id: int) -> dict:
    guest = query("SELECT * FROM guests WHERE id = ?", (guest_id,), one=True)
    if not guest:
        raise ValueError("Guest not found")

    settings = query("SELECT * FROM wedding_settings WHERE id = 1", one=True)

    inv = query("SELECT * FROM invitations WHERE guest_id = ?", (guest_id,), one=True)
    if inv:
        token = inv["token"]
        reference = inv["reference_no"]
        execute("UPDATE invitations SET generated_at=CURRENT_TIMESTAMP WHERE id=?",
                (inv["id"],))
        inv = dict(inv)
        inv["token"] = token
        inv["reference_no"] = reference
    else:
        token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
        reference = "INV-" + uuid.uuid4().hex[:10].upper()
        inv_id = execute("""
            INSERT INTO invitations (guest_id, token, reference_no)
            VALUES (?, ?, ?)
        """, (guest_id, token, reference))
        inv = {"id": inv_id, "guest_id": guest_id,
               "token": token, "reference_no": reference}

    filepath = generate_pdf(guest, inv, settings)
    execute("UPDATE invitations SET file_path = ? WHERE id = ?",
            (filepath, inv["id"]))
    return inv

@invitations_bp.route("/invitations/<int:invitation_id>/preview")
@login_required
def preview(invitation_id):
    inv = query("SELECT * FROM invitations WHERE id = ?", (invitation_id,), one=True)
    if not inv or not inv["file_path"] or not os.path.exists(inv["file_path"]):
        abort(404)
    return send_file(inv["file_path"], mimetype="application/pdf")

@invitations_bp.route("/invitations/<int:invitation_id>/download")
@login_required
def download(invitation_id):
    inv = query("SELECT * FROM invitations WHERE id = ?", (invitation_id,), one=True)
    if not inv or not inv["file_path"] or not os.path.exists(inv["file_path"]):
        abort(404)
    return send_file(inv["file_path"], as_attachment=True,
                     download_name=f"{inv['reference_no']}.pdf")

@invitations_bp.route("/invitations/<int:guest_id>/regenerate", methods=["POST"])
@login_required
def regenerate(guest_id):
    try:
        generate_invitation_for_guest(guest_id)
        flash("Invitation regenerated.", "success")
    except Exception as e:
        flash(f"Regeneration failed: {e}", "error")
    return redirect(url_for("guests.list_guests"))