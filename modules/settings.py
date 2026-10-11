import os
from flask import Blueprint, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from config import Config
from database.db import query, execute
from modules.auth import login_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def wedding_settings():
    if request.method == "POST":
        fields = [
            "bride_name", "groom_name", "wedding_date", "ceremony_time",
            "venue", "venue_address", "reception_details", "dress_code",
            "invitation_message", "contact_phone",
        ]
        values = {f: request.form.get(f, "").strip() for f in fields}

        # Handle background image upload
        bg_filename = None
        bg = request.files.get("background_image")
        if bg and bg.filename:
            os.makedirs(Config.BACKGROUND_FOLDER, exist_ok=True)
            bg_filename = secure_filename(bg.filename)
            bg.save(os.path.join(Config.BACKGROUND_FOLDER, bg_filename))

        if bg_filename:
            execute("""
                UPDATE wedding_settings SET
                    bride_name=?, groom_name=?, wedding_date=?, ceremony_time=?,
                    venue=?, venue_address=?, reception_details=?, dress_code=?,
                    invitation_message=?, contact_phone=?, background_image=?
                WHERE id=1
            """, (*values.values(), bg_filename))
        else:
            execute("""
                UPDATE wedding_settings SET
                    bride_name=?, groom_name=?, wedding_date=?, ceremony_time=?,
                    venue=?, venue_address=?, reception_details=?, dress_code=?,
                    invitation_message=?, contact_phone=?
                WHERE id=1
            """, tuple(values.values()))

        flash("Wedding settings updated.", "success")
        return redirect(url_for("settings.wedding_settings"))

    settings = query("SELECT * FROM wedding_settings WHERE id = 1", one=True)
    return render_template("settings.html", settings=settings)