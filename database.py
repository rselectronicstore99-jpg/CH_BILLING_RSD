import os
import json
import uuid
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 లైసెన్స్ సెక్యూరిటీ కీ
SECRET_SALT = "RS_ELECTRONIC_SUPER_SECRET_2026"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

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