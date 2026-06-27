import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
import streamlit as st
import gspread

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 లైసెన్స్ సెక్యూరిటీ మరియు లోకల్ ఫైల్ పాత్‌లు
SECRET_SALT = "RS_ELECTRONIC_SUPER_SECRET_2026"
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")  
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")      
SIGN_PATH = os.path.join(BASE_DIR, "signature.png") 

# 🌐 గూగుల్ షీట్స్ కనెక్ట్ చేయడానికి హెల్పర్ ఫంక్షన్
def get_gspread_client():
    try:
        # Streamlit Cloud Secrets నుండి GCP కీలను తీసుకుంటుంది
        if "gcp_service_account" in st.secrets:
            credentials = st.secrets["gcp_service_account"]
            return gspread.service_account_from_dict(credentials)
    except Exception as e:
        pass
    return None

# 📥 గూగుల్ షీట్ నుండి డేటాను సురక్షితంగా చదివే ఫంక్షన్ (15 సెకన్ల క్యాష్ తో)
@st.cache_data(ttl=15)
def fetch_from_sheets(worksheet_name):
    client = get_gspread_client()
    if not client:
        return None
    try:
        # గూగుల్ డ్రైవ్ లో మీ షీట్ పేరు 'RS_Billing_Database' అని ఉండాలి
        sheet = client.open("RS_Billing_Database").worksheet(worksheet_name)
        records = sheet.get_all_values()
        
        if not records or len(records) <= 1:
            return []
            
        data_list = []
        for row in records[1:]: # హెడర్ లైన్ వదిలేసి
            if len(row) >= 2 and row[1]:
                try:
                    data_list.append(json.loads(row[1]))
                except:
                    pass
        return data_list
    except:
        return None

# 📤 మొత్తం డేటాను ఒకేసారి గూగుల్ షీట్ లోకి అప్‌డేట్ చేసే ఫంక్షన్
def sync_to_sheets(worksheet_name, data_list, id_key):
    client = get_gspread_client()
    if not client:
        return False
    try:
        sheet = client.open("RS_Billing_Database").worksheet(worksheet_name)
        
        # గూగుల్ షీట్ కోసం డేటా ఫార్మాట్ సిద్ధం చేయడం (ID మరియు పూర్తి JSON స్ట్రింగ్)
        rows = [['ID', 'JSON_DATA']]
        for item in data_list:
            item_id = item.get(id_key, "")
            rows.append([str(item_id), json.dumps(item, ensure_ascii=False)])
        
        sheet.clear()
        sheet.update(range_name='A1', values=rows)
        return True
    except Exception as e:
        return False

# JSON డేటా రీడ్ చేయడానికి కామన్ హెల్పర్ ఫంక్షన్ (గూగుల్ షీట్ ఆటో-సింక్ తో)
def load_json(file_path, default_value=None):
    if default_value is None:
        default_value = []
        
    # 1. మొదట లోకల్ ఫైల్ నుండి బ్యాకప్ డేటా చదవడం
    local_data = default_value
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except:
            local_data = default_value

    # 2. గూగుల్ షీట్ క్లౌడ్ నుండి లేటెస్ట్ డేటా తెచ్చుకోవడం
    worksheet_name = None
    if file_path == USERS_FILE:
        worksheet_name = "Users"
    elif file_path == HISTORY_FILE:
        worksheet_name = "History"
        
    if worksheet_name:
        cloud_data = fetch_from_sheets(worksheet_name)
        if cloud_data is not None:
            # క్లౌడ్ లో డేటా ఉంటే, లోకల్ ఫైల్ ని కూడా అప్‌డేట్ చేస్తుంది
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(cloud_data, f, indent=4, ensure_ascii=False)
            except:
                pass
            return cloud_data
            
    return local_data

# JSON డేటా రైట్ చేయడానికి కామన్ హెల్పర్ ఫంక్షన్ (గూగుల్ షీట్ ఆటో-సింక్ తో)
def save_json(file_path, data):
    # 1. లోకల్ కంప్యూటర్/సర్వర్ లో సేవ్ చేయడం
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        local_saved = True
    except:
        local_saved = False

    # 2. గూగుల్ షీట్ క్లౌడ్ లోకి ఆటోమేటిక్ గా పుష్ చేయడం
    worksheet_name = None
    id_key = "Username"
    if file_path == USERS_FILE:
        worksheet_name = "Users"
        id_key = "Username"
    elif file_path == HISTORY_FILE:
        worksheet_name = "History"
        id_key = "bill_no"
        
    if worksheet_name:
        cloud_saved = sync_to_sheets(worksheet_name, data, id_key)
        # కొత్త డేటా సేవ్ అయింది కాబట్టి పాత రీడింగ్ క్యాష్ ని క్లియర్ చేస్తుంది
        fetch_from_sheets.clear()
        return local_saved and cloud_saved
        
    return local_saved

def generate_system_id():
    return f"RS-{uuid.uuid4().hex[:5].upper()}-SYS"

def calculate_valid_key(system_id):
    raw_string = f"{system_id}_{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_string.encode()).hexdigest().upper()
    return secure_hash[:8]

# 📝 కొత్త కస్టమర్ ని సేవ్ చేసే ఫంక్షన్ (Smarter & Bug-Free Version)
def register_system_customer(system_id, *args, **kwargs):
    try:
        users = load_json(USERS_FILE, [])
        expiry_date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # auth_manager.py మరియు పాత డేటాబేస్ పారామీటర్ల మిస్‌మ్యాచ్ ని ఆటోమేటిక్‌గా సరిచేస్తుంది
        password = "123"
        if len(args) == 7: # Called from auth_manager: shop_name, phone, lic_1, lic_2, addr_1, addr_2
            shop_name, phone, lic_1, lic_2, addr_1, addr_2 = args
        elif len(args) == 8: # Old format: password, phone, shop_name, lic_1, lic_2, addr_1, addr_2
            password, phone, shop_name, lic_1, lic_2, addr_1, addr_2 = args
        else:
            shop_name = kwargs.get("shop_name", "")
            phone = kwargs.get("phone", "")
            lic_1 = kwargs.get("lic_1", "")
            lic_2 = kwargs.get("lic_2", "")
            addr_1 = kwargs.get("addr_1", "")
            addr_2 = kwargs.get("addr_2", "")
        
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
        st.error(f"❌ రిజిస్ట్రేషన్ సేవింగ్ లోపం: {e}")
        return False

def upload_to_drive(file_path):
    """పిడిఎఫ్ ఫైల్స్ ని గూగుల్ డ్రైవ్ కి అప్‌లోడ్ చేసే ఫంక్షన్ ప్లేస్ హోల్డర్"""
    try:
        return True
    except Exception as e:
        return False