import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE = os.path.join(BASE_DIR, "data", "wedding.db")

    # File storage
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    INVITATION_FOLDER = os.path.join(UPLOAD_FOLDER, "invitations")
    BACKGROUND_FOLDER = os.path.join(UPLOAD_FOLDER, "backgrounds")

    # WhatsApp Cloud API (Meta)
    WHATSAPP_API_URL = os.getenv(
        "WHATSAPP_API_URL",
        "https://graph.facebook.com/v19.0"
    )
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_ENABLED = bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)