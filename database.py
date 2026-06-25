import os
import json
import uuid
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 లైసెన్స్ సెక్యూరిటీ కీ మరియు ఫైల్ పాత్‌లు
SECRET_SALT = "RS_ELECTRONIC_SUPER_SECRET_2026"
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")      # మీ లోగో ఫైల్ నేమ్
SIGN_PATH = os.path.join(BASE_DIR, "signature.png") # మీ సంతకం ఫైల్ నేమ్

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

def load_json(file_path, default_value=None):
    if default_value is None:
        default_value = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_value
    return default_value

def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

def upload_to_drive(file_path):
    # యాప్ ఎక్కడా బ్రేక్ అవ్వకుండా ఉండటానికి దీనికి సేఫ్ ట్రై-ఎక్సెప్ట్ బ్లాక్ ఇవ్వబడింది
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        creds_dict = get_safe_creds_dict()
        if not creds_dict: return None
        
        # Drive API కి కూడా ఈ క్రెడెన్షియల్స్ పనిచేస్తాయి
        creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/drive"])
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        return None

def get_safe_creds_dict():
    if "google_credentials" not in st.secrets:
        st.error("Error: Streamlit Secrets లో 'google_credentials' లేదు!")
        return None
    try:
        raw_creds = st.secrets["google_credentials"]
        return dict(raw_creds) if not isinstance(raw_creds, str) else json.loads(raw_creds)
    except Exception as e:
        st.error(f"❌ కీ రీడింగ్ లోపం: {e}")
        return None

def get_gspread_sheet():
    creds_dict = get_safe_creds_dict()
    if not creds_dict: return None
    gc = gspread.service_account_from_dict(creds_dict)
    sheet = gc.open("RS_Customers").sheet1 
    return sheet

def generate_system_id():
    return f"RS-{uuid.uuid4().hex[:5].upper()}-SYS"

def calculate_valid_key(system_id):
    import hashlib
    raw_string = f"{system_id}_{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_string.encode()).hexdigest().upper()
    return secure_hash[:8]

def register_system_customer(system_id, password, phone, shop_name, lic_1, lic_2, addr_1, addr_2):
    try:
        sheet = get_gspread_sheet()
        if not sheet: return False
        
        expiry_date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        new_row = [
            system_id, password, phone, "ACTIVE", "Trial", expiry_date_str,
            "TRUE", shop_name, lic_1, lic_2, addr_1, addr_2, "" # డ్రైవ్ ఫోల్డర్ ఐడి ఖాళీగా వదిలేశాం
        ]
        sheet.append_row(new_row)
        return True
    except Exception as e:
        st.error(f"❌ గూగుల్ షీట్ రిజిస్ట్రేషన్ లోపం: {e}")
        return False