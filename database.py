import os
import json
import uuid
import hashlib
import tempfile
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client, Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 CH-Billing-App సెక్యూరిటీ మరియు ఫైల్ పాత్‌లు
SECRET_SALT = "CH_BILLING_APP_SUPER_SECRET_2026"
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")  
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")      
SIGN_PATH = os.path.join(BASE_DIR, "signature.png") 

@st.cache_resource
def get_supabase_client() -> Client:
    try:
        if "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key)
    except: pass
    return None

supabase_client = get_supabase_client()

def load_json(file_path, default_value=None):
    if default_value is None: default_value = []
    filename = os.path.basename(file_path)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    local_data = default_value

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: local_data = json.load(f)
        except: pass
    elif os.path.exists(temp_path):
        try:
            with open(temp_path, "r", encoding="utf-8") as f: local_data = json.load(f)
        except: pass

    if supabase_client:
        try:
            if filename == "users.json":
                response = supabase_client.table("users").select("data").execute()
                cloud_data = [row["data"] for row in response.data] if response.data else []
                for path in [file_path, temp_path]:
                    try:
                        with open(path, "w", encoding="utf-8") as f: json.dump(cloud_data, f, indent=4, ensure_ascii=False)
                    except: pass
                return cloud_data
            elif filename == "history.json":
                response = supabase_client.table("history").select("data").execute()
                cloud_data = [row["data"] for row in response.data] if response.data else []
                for path in [file_path, temp_path]:
                    try:
                        with open(path, "w", encoding="utf-8") as f: json.dump(cloud_data, f, indent=4, ensure_ascii=False)
                    except: pass
                return cloud_data
        except: return local_data
    return local_data

def save_json(file_path, data):
    filename = os.path.basename(file_path)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    local_saved = False

    try:
        with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
        local_saved = True
    except:
        try:
            with open(temp_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
            local_saved = True
        except: pass

    if supabase_client:
        try:
            if filename == "users.json":
                payload = [{"username": u["Username"], "data": u} for u in data]
                supabase_client.table("users").upsert(payload).execute()
                return True
            elif filename == "history.json":
                payload = []
                for h in data:
                    uname = h.get('username') or h.get('user_id') or h.get('Username') or "unknown"
                    bno = h.get('bill_no') or "0"
                    unique_bill_id = f"{uname}_{bno}"
                    payload.append({"id": unique_bill_id, "username": uname, "bill_no": bno, "data": h})
                supabase_client.table("history").upsert(payload).execute()
                return True
        except Exception as e: 
            st.error(f"❌ CH-Billing-App Cloud Database Save Error: {e}")
    return local_saved

def generate_system_id():
    return f"CH-{uuid.uuid4().hex[:5].upper()}-SYS"

def calculate_valid_key(system_id):
    raw_string = f"{system_id}_{SECRET_SALT}"
    return hashlib.sha256(raw_string.encode()).hexdigest().upper()[:8]

def register_system_customer(system_id, password, phone, shop_name, lic_1, lic_2, addr_1, addr_2):
    try:
        users = load_json(USERS_FILE, [])
        expiry_date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        new_user = {
            "Username": system_id, "Password": password, "Phone_No": phone, "Status": "ACTIVE",
            "Key_Type": "Trial", "Expiry_Date": expiry_date_str, "Profile_Setup_Done": "TRUE",
            "Shop_Name": shop_name, "Lic_1": lic_1, "Lic_2": lic_2, "Address_Line1": addr_1, "Address_Line2": addr_2
        }
        users.append(new_user)
        return save_json(USERS_FILE, users)
    except: return False

def upload_to_drive(file_path): return True