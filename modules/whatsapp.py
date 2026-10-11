import os
import requests
from flask import Blueprint, request, redirect, url_for, flash, jsonify

try:
    from config import Config  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from modules.config import Config  # type: ignore[import-not-found]

try:
    from database.db import query, execute  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from modules.database.db import query, execute  # type: ignore[import-not-found]

from modules.auth import login_required

whatsapp_bp = Blueprint("whatsapp", __name__)

def _log(guest_id, invitation_id, status, provider_id=None, error=None, attempts=1):
    execute("""
        INSERT INTO whatsapp_logs
            (guest_id, invitation_id, status, provider_message_id, error_message, attempts)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (guest_id, invitation_id, status, provider_id, error, attempts))

def send_invitation_via_api(guest, invitation) -> dict:
    """
    Send the invitation PDF via WhatsApp Cloud API (Meta).
    Returns: {"ok": True/False, "provider_id": ..., "error": ...}
    """
    if not Config.WHATSAPP_ENABLED:
        return {"ok": False, "error": "WhatsApp API not configured"}

    if not invitation or not invitation.get("file_path"):
        return {"ok": False, "error": "Invitation PDF not available"}

    pdf_path = invitation["file_path"]
    if not os.path.exists(pdf_path):
        return {"ok": False, "error": "PDF file missing on disk"}

    caption = (
        f"Hello {guest['full_name']}, you are cordially invited to our wedding. "
        f"Please find your invitation attached. Kindly present the QR code at the "
        f"entrance. We look forward to celebrating with you!"
    )

    # ---- Step 1: upload the PDF to WhatsApp's media endpoint ----
    media_url = f"{Config.WHATSAPP_API_URL}/{Config.WHATSAPP_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {Config.WHATSAPP_ACCESS_TOKEN}"}

    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
            data = {"messaging_product": "whatsapp", "type": "application/pdf"}
            r = requests.post(media_url, headers=headers, files=files, data=data, timeout=30)
        if r.status_code >= 300:
            return {"ok": False, "error": f"Media upload failed: {r.text}"}
        media_id = r.json().get("id")

        # ---- Step 2: send the document message ----
        msg_url = f"{Config.WHATSAPP_API_URL}/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": guest["phone"].replace("+", ""),
            "type": "document",
            "document": {
                "id": media_id,
                "filename": os.path.basename(pdf_path),
                "caption": caption,
            },
        }
        r2 = requests.post(
            msg_url,
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if r2.status_code >= 300:
            return {"ok": False, "error": f"Send failed: {r2.text}"}

        provider_id = r2.json().get("messages", [{}])[0].get("id")
        return {"ok": True, "provider_id": provider_id}

    except Exception as e:
        return {"ok": False, "error": str(e)}


@whatsapp_bp.route("/guests/<int:guest_id>/send", methods=["POST"])
@login_required
def send_to_guest(guest_id):
    guest = query("SELECT * FROM guests WHERE id = ?", (guest_id,), one=True)
    inv = query("SELECT * FROM invitations WHERE guest_id = ?", (guest_id,), one=True)
    if not guest or not inv:
        flash("Guest or invitation missing.", "error")
        return redirect(url_for("guests.list_guests"))

    result = send_invitation_via_api(guest, inv)

    if result["ok"]:
        _log(guest_id, inv["id"], "sent", result.get("provider_id"))
        flash(f"Invitation sent to {guest['full_name']}.", "success")
    else:
        _log(guest_id, inv["id"], "failed", None, result["error"])
        flash(f"Send failed: {result['error']}", "error")

    return redirect(url_for("guests.list_guests"))


@whatsapp_bp.route("/api/whatsapp/share-link/<int:guest_id>")
@login_required
def share_link(guest_id):
    """
    Returns a wa.me link with a prefilled message.

    ⚠️ IMPORTANT: wa.me links CANNOT auto-attach a PDF. The admin must
    download the PDF and attach it manually in WhatsApp.
    """
    guest = query("SELECT * FROM guests WHERE id = ?", (guest_id,), one=True)
    if not guest:
        return jsonify({"error": "Guest not found"}), 404

    phone = guest["phone"].replace("+", "").replace(" ", "").replace("-", "")
    message = (
        f"Hello {guest['full_name']}, you are cordially invited to our wedding. "
        f"Please find your invitation attached. Kindly present the QR code at the entrance."
    )
    wa_link = f"https://wa.me/{phone}?text={requests.utils.quote(message)}"
    return jsonify({"link": wa_link})