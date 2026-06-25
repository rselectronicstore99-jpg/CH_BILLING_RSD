import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 లైసెన్స్ సెక్యూరిటీ మరియు లోకల్ ఫైల్ పాత్‌లు
SECRET_SALT = "RS_ELECTRONIC_SUPER_SECRET_2026"
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")  # 📁 గూగుల్ షీట్ ప్లేస్ లో కొత్త లోకల్ డేటాబేస్
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")      
SIGN_PATH = os.path.join(BASE_DIR, "signature.png") 

# JSON డేటా రీడ్ మరియు రైట్ చేయడానికి కామన్ హెల్పర్ ఫంక్షన్స్
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

def generate_system_id():
    return f"RS-{uuid.uuid4().hex[:5].upper()}-SYS"

def calculate_valid_key(system_id):
    raw_string = f"{system_id}_{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_string.encode()).hexdigest().upper()
    return secure_hash[:8]

# 📝 కొత్త కస్టమర్ ని లోకల్ JSON లో సేవ్ చేసే ఫంక్షన్
def register_system_customer(system_id, password, phone, shop_name, lic_1, lic_2, addr_1, addr_2):
    try:
        users = load_json(USERS_FILE, [])
        expiry_date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        new_user = {
            "Username": system_id,
            "Password": password,
            "Phone_No": phone,
            "Status": "ACTIVE",
            "Key_Type": "Trial",
            "Expiry_Date": expiry_date_str,
            "Profile_Setup_Done": "TRUE",
            "Shop_Name": shop_name,
            "Lic_1": lic_1,
            "Lic_2": lic_2,
            "Address_Line1": addr_1,
            "Address_Line2": addr_2
        }
        
        users.append(new_user)
        return save_json(USERS_FILE, users)
    except Exception as e:
        st.error(f"❌ లోకల్ డేటాబేస్ సేవింగ్ లోపం: {e}")
        return False

# 🎯 [CRITICAL ADDITION] ఈ కింద ఉన్న ఫంక్షన్ లేకపోవడం వల్లే ImportError వచ్చింది. దీన్ని ఇక్కడ యాడ్ చేశాను.
def upload_to_drive(file_path):
    """పిడిఎఫ్ ఫైల్స్ ని గూగుల్ డ్రైవ్ కి అప్‌లోడ్ చేసే ఫంక్షన్ ప్లేస్ హోల్డర్"""
    try:
        # భవిష్యత్తులో గూగుల్ డ్రైవ్ బ్యాకప్ కోడ్ కావాలంటే ఇక్కడ రాసుకోవచ్చు
        return True
    except Exception as e:
        return False