import os
import json
import uuid
import hashlib
import tempfile
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔐 లైసెన్స్ సెక్యూరిటీ మరియు ఫైల్ పాత్‌లు
SECRET_SALT = "RS_ELECTRONIC_SUPER_SECRET_2026"
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")  
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")      
SIGN_PATH = os.path.join(BASE_DIR, "signature.png") 

# 🌐 Supabase క్లౌడ్ కనెక్షన్ ఇనిషియలైజేషన్
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        if "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key)
    except:
        pass
    return None

supabase_client = get_supabase_client()

# 📥 సుపాబేస్ నుండి డేటాను చదివే ఫంక్షన్ (FULLY SECURED MULTI-TENANT)
def load_json(file_path, default_value=None):
    if default_value is None:
        default_value = []
        
    # 🔥 FIX: కేస్-సెన్సిటివిటీ మరియు స్పేస్ బైపాస్ సమస్యలు రాకుండా క్లీన్ చేస్తున్నాం
    filename = os.path.basename(file_path).lower().strip()
    temp_path = os.path.join(tempfile.gettempdir(), os.path.basename(file_path))
    
    # యూజర్‌నేమ్ ని కూడా ఇరువైపులా స్పేసెస్ లేకుండా క్లీన్ గా తీసుకుంటున్నాం
    current_user = str(st.session_state.get("user_profile", {}).get("Username", "")).strip()

    # 1. ఒకవేళ సుపాబేస్ క్లౌడ్ అందుబాటులో ఉంటే (Cloud Fetch)
    if supabase_client:
        try:
            if filename == "users.json":
                response = supabase_client.table("users").select("data").execute()
                cloud_data = [row["data"] for row in response.data] if response.data else []
                return cloud_data

            elif filename == "history.json":
                if not current_user:
                    return []
                
                if current_user != "admin":
                    response = supabase_client.table("history").select("username", "bill_no", "data").eq("username", current_user).execute()
                else:
                    response = supabase_client.table("history").select("username", "bill_no", "data").execute()
                    
                cloud_data = []
                if response and response.data:
                    for row in response.data:
                        h = row["data"]
                        if isinstance(h, dict):
                            h["username"] = row["username"]
                            h["bill_no"] = row["bill_no"]
                            h["Username"] = row["username"]
                        cloud_data.append(h)
                return cloud_data
        except:
            # క్లౌడ్ డేటాబేస్ ఎర్రర్ వస్తే లోకల్ ఫాల్‌బ్యాక్ కి వెళ్తుంది
            pass

    # 2. లోకల్ ఫాల్‌బ్యాక్ సిస్టమ్ (సుపాబేస్ డౌన్ అయినప్పుడు లేదా ఇంటర్నెట్ లేనప్పుడు)
    local_data = default_value
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

    # 🔥 CRITICAL LOCAL FILTER FIX: 
    # ఇక్కడ కూడా క్లీన్ చేసిన ఫైల్ నేమ్ తో స్ట్రిక్ట్ ఫిల్టర్ అప్లై చేసాం, కాబట్టి డేటా లీక్ అయ్యే ఛాన్సే లేదు!
    if filename == "history.json" and isinstance(local_data, list):
        if not current_user:
            return []
        if current_user != "admin":
            filtered_local = []
            for r in local_data:
                if isinstance(r, dict):
                    r_user = str(r.get('username') or r.get('user_id') or r.get('Username') or "").strip()
                    if r_user == current_user:
                        filtered_local.append(r)
            return filtered_local

    return local_data

# 📤 సుపాబేస్ లోకల్ మరియు క్లౌడ్ లోకి డేటాను రైట్ చేసే ఫంక్షన్
def save_json(file_path, data):
    # 🔥 FIX: ఇక్కడ కూడా ఫైల్ నేమ్ ని క్లీన్ చేస్తున్నాం
    filename = os.path.basename(file_path).lower().strip()
    temp_path = os.path.join(tempfile.gettempdir(), os.path.basename(file_path))
    local_saved = False

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        local_saved = True
    except:
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            local_saved = True
        except: pass

    if supabase_client:
        try:
            if filename == "users.json":
                payload = [{"username": str(u["Username"]).strip(), "data": u} for u in data]
                supabase_client.table("users").upsert(payload).execute()
                return True
                
            elif filename == "history.json":
                current_user = str(st.session_state.get("user_profile", {}).get("Username", "unknown")).strip()
                payload = []
                for h in data:
                    if not isinstance(h, dict): continue
                    uname = str(h.get('username') or h.get('user_id') or h.get('Username') or current_user).strip()
                    bno = str(h.get('bill_no') or "100")
                    
                    h['username'] = uname
                    h['bill_no'] = bno
                    h['Username'] = uname
                    
                    unique_bill_id = f"{uname}_{bno}"
                    payload.append({
                        "id": unique_bill_id, 
                        "username": uname, 
                        "bill_no": bno, 
                        "sub_client": h.get("sub_client", ""),
                        "data": h
                    })
                
                if payload:
                    supabase_client.table("history").upsert(payload).execute()
                return True
        except:
            pass
            
    return local_saved

def generate_system_id():
    return f"RS-{uuid.uuid4().hex[:5].upper()}-SYS"

def calculate_valid_key(system_id):
    raw_string = f"{system_id}_{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_string.encode()).hexdigest().upper()
    return secure_hash[:8]

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
    except:
        return False

# Google Drive Backup ఫంక్షన్లు
def upload_to_client_google_drive(file_path, client_refresh_token):
    try:
        creds = Credentials(
            token=None,
            refresh_token=client_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets["google_oauth"]["client_id"],
            client_secret=st.secrets["google_oauth"]["client_secret"]
        )
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        return uploaded_file.get('webViewLink')
    except Exception as e:
        st.error(f"❌ Google Drive Upload Error: {e}")
        return None

def upload_to_drive(file_path):
    try:
        # 🔥 FIX: ఒకవేళ సుపాబేస్ క్లయింట్ లేకపోతే ఇక్కడే రిటర్న్ అవుతుంది, క్రాష్ అవ్వదు
        if not supabase_client:
            return False
            
        current_user = str(st.session_state.get("user_profile", {}).get("Username", "")).strip()
        if not current_user:
            return False
            
        response = supabase_client.table("users").select("google_refresh_token").eq("username", current_user).execute()
        if response.data and response.data[0].get("google_refresh_token"):
            token = response.data[0]["google_refresh_token"]
            return upload_to_client_google_drive(file_path, token)
        return False
    except:
        return False