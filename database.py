import os
import json
import uuid
import hashlib
import tempfile
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client, Client
# database.py కి పైన ఈ ఇంపోర్ట్స్ యాడ్ చేయండి
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
    except Exception as e:
        pass
    return None

supabase_client = get_supabase_client()

# 📥 సుపాబేస్ నుండి డేటాను చదివే ఫంక్షన్ (PDF & HISTORY FIX)
def load_json(file_path, default_value=None):
    if default_value is None:
        default_value = []
        
    filename = os.path.basename(file_path)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
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

    if supabase_client:
        try:
            if filename == "users.json":
                response = supabase_client.table("users").select("data").execute()
                cloud_data = [row["data"] for row in response.data] if response.data else []
                for path in [file_path, temp_path]:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(cloud_data, f, indent=4, ensure_ascii=False)
                    except: pass
                return cloud_data

            elif filename == "history.json":
                current_user = st.session_state.get("user_profile", {}).get("Username", "")
                
                # సెక్యూరిటీ మరియు ఖచ్చితత్వం కోసం లాగిన్ అయిన క్లయింట్ బిల్లులు మాత్రమే తెస్తుంది
                if current_user and current_user != "admin":
                    response = supabase_client.table("history").select("username", "bill_no", "data").eq("username", current_user).execute()
                else:
                    response = supabase_client.table("history").select("username", "bill_no", "data").execute()
                    
                cloud_data = []
                if response and response.data:
                    for row in response.data:
                        h = row["data"]
                        if isinstance(h, dict):
                            # 🔥 CRITICAL PDF FIX: క్లౌడ్ నుండి తెచ్చేటప్పుడు బిల్ లోపల 'username' మరియు 'bill_no' ని ఇంజెక్ట్ చేస్తుంది!
                            h["username"] = row["username"]
                            h["bill_no"] = row["bill_no"]
                            h["Username"] = row["username"]
                        cloud_data.append(h)
                        
                if cloud_data:
                    for path in [file_path, temp_path]:
                        try:
                            with open(path, "w", encoding="utf-8") as f:
                                json.dump(cloud_data, f, indent=4, ensure_ascii=False)
                        except: pass
                    return cloud_data
                return local_data
        except:
            return local_data
            
    return local_data

# 📤 సుపాబేస్ లోకి డేటాను రైట్ చేసే ఫంక్షన్
def save_json(file_path, data):
    filename = os.path.basename(file_path)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
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
                payload = [{"username": u["Username"], "data": u} for u in data]
                supabase_client.table("users").upsert(payload).execute()
                return True
                
            elif filename == "history.json":
                current_user = st.session_state.get("user_profile", {}).get("Username", "unknown")
                payload = []
                for h in data:
                    if not isinstance(h, dict): continue
                    uname = h.get('username') or h.get('user_id') or h.get('Username') or current_user
                    bno = str(h.get('bill_no') or "100")
                    
                    # బిల్ ఆబ్జెక్ట్ లోపల కూడా విలువలను ఖచ్చితంగా భద్రపరుస్తుంది
                    h['username'] = uname
                    h['bill_no'] = bno
                    h['Username'] = uname
                    
                    unique_bill_id = f"{uname}_{bno}"
                    payload.append({
                        "id": unique_bill_id, 
                        "username": uname, 
                        "bill_no": bno, 
                        "sub_client": h.get("sub_client", ""),  # 👈 ఈ లైన్ యాడ్ అయింది!
                        "data": h
                    })
                
                if payload:
                    supabase_client.table("history").upsert(payload).execute()
                return True
        except Exception as e:
            st.error(f"❌ Cloud Database Save Error: {e}")
            
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
    except Exception as e:
        st.error(f"❌ డేటాబేస్ సేవింగ్ లోపం: {e}")
        return False

# చివర్లో ఉన్న పాత upload_to_drive తీసేసి ఇది పెట్టండి
def upload_to_client_google_drive(file_path, client_refresh_token):
    try:
        # క్లయింట్ టోకెన్ మరియు మన సీక్రెట్ కీస్ ఉపయోగించి పర్మిషన్ క్రియేట్ చేయడం
        creds = Credentials(
            token=None,
            refresh_token=client_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets["google_oauth"]["client_id"],
            client_secret=st.secrets["google_oauth"]["client_secret"]
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # ఫైల్ పేరు, టైప్ సెట్ చేయడం
        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        # క్లయింట్ సొంత డ్రైవ్ లోకి అప్‌లోడ్ అవుతుంది
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return uploaded_file.get('webViewLink') # అప్‌లోడ్ అయిన ఫైల్ లింక్ వస్తుంది
    except Exception as e:
        st.error(f"❌ Google Drive Upload Error: {e}")
        return None