import os
import json
import uuid
import hashlib
import tempfile
from datetime import datetime, timedelta
import streamlit as st
import gspread

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 లైసెన్స్ సెక్యూరిటీ మరియు ఫైల్ పాత్‌లు
SECRET_SALT = "RS_ELECTRONIC_SUPER_SECRET_2026"
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")  
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")      
SIGN_PATH = os.path.join(BASE_DIR, "signature.png") 

# 🌐 గూగుల్ షీట్స్ కనెక్ట్ చేయడానికి హెల్పర్ ఫంక్షన్
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            credentials = st.secrets["gcp_service_account"]
            return gspread.service_account_from_dict(credentials)
    except:
        pass
    return None

# 📥 గూగుల్ షీట్ నుండి డేటాను చదివే ఫంక్షన్
@st.cache_data(ttl=10)
def fetch_from_sheets(worksheet_name):
    client = get_gspread_client()
    if not client:
        return None
    try:
        sheet = client.open("RS_Billing_Database").worksheet(worksheet_name)
        records = sheet.get_all_values()
        
        if not records or len(records) <= 1:
            return []
            
        data_list = []
        for row in records[1:]:
            if len(row) >= 2 and row[1]:
                try:
                    data_list.append(json.loads(row[1]))
                except:
                    pass
        return data_list
    except:
        return None

# 📤 డేటాను గూగుల్ షీట్ లోకి సింక్ చేసే ఫంక్షన్
def sync_to_sheets(worksheet_name, data_list, id_key):
    client = get_gspread_client()
    if not client:
        return False
    try:
        sheet = client.open("RS_Billing_Database").worksheet(worksheet_name)
        rows = [['ID', 'JSON_DATA']]
        for item in data_list:
            item_id = item.get(id_key, "")
            rows.append([str(item_id), json.dumps(item, ensure_ascii=False)])
        
        sheet.clear()
        sheet.update(range_name='A1', values=rows)
        return True
    except:
        return False

# 📥 JSON డేటా రీడ్ ఫంక్షన్ (గూగుల్ షీట్ ఫస్ట్ ప్రాధాన్యత)
def load_json(file_path, default_value=None):
    if default_value is None:
        default_value = []
        
    filename = os.path.basename(file_path)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    local_data = default_value

    # లోకల్ లేదా సేఫ్ టెంప్ ఫోల్డర్ నుండి చదువుతుంది (Fallback కోసం)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except: pass
    elif os.path.exists(temp_path):
        try:
            with open(temp_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except: pass

    # గూగుల్ షీట్ నుండి లేటెస్ట్ డేటా తెచ్చుకుంటుంది
    worksheet_name = "Users" if filename == "users.json" else "History" if filename == "history.json" else None
    if worksheet_name:
        cloud_data = fetch_from_sheets(worksheet_name)
        if cloud_data is not None:
            # బ్యాకప్ కోసం లోకల్ గా రాసుకుంటుంది
            for path in [file_path, temp_path]:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(cloud_data, f, indent=4, ensure_ascii=False)
                except: pass
            return cloud_data
            
    return local_data

# 📤 JSON డేటా రైట్ ఫంక్షన్ (క్లౌడ్ కి పంపుతుంది)
def save_json(file_path, data):
    filename = os.path.basename(file_path)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    local_saved = False

    # 1. లోకల్ సర్వర్ లో సేవ్ చేయడానికి ట్రై చేస్తుంది
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        local_saved = True
    except:
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            local_saved = True
        except:
            pass

    # 2. గూగుల్ షీట్ క్లౌడ్ లోకి పంపుతుంది
    worksheet_name = "Users" if filename == "users.json" else "History" if filename == "history.json" else None
    id_key = "Username" if filename == "users.json" else "bill_no"
        
    if worksheet_name:
        cloud_saved = sync_to_sheets(worksheet_name, data, id_key)
        fetch_from_sheets.clear()
        return cloud_saved or local_saved
        
    return local_saved

def generate_system_id():
    return f"RS-{uuid.uuid4().hex[:5].upper()}-SYS"

def calculate_valid_key(system_id):
    raw_string = f"{system_id}_{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_string.encode()).hexdigest().upper()
    return secure_hash[:8]

# 📝 కొత్త కస్టమర్ ని సేవ్ చేసే ఫంక్షన్
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
        st.error(f"❌ డేటాబేస్ సేవింగ్ లోపం: {e}")
        return False

def upload_to_drive(file_path):
    return True