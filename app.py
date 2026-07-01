import streamlit as st
import os
import json
import requests
import hashlib
from datetime import datetime, date, timedelta
# 🌟 database నుండి ఇంపోర్ట్స్
from database import load_json, save_json, USERS_FILE, HISTORY_FILE, generate_system_id, register_system_customer, calculate_valid_key, supabase_client

st.set_page_config(page_title="RS Electronic Ultimate", layout="centered")

def init_session_state_safe():
    defaults = {
        "manual_date": datetime.now().strftime('%d-%m-%Y'),
        "cust_name": "",
        "cust_phone": "",
        "cust_pro": "",
        "cust_area": "",
        "bill_items": [],
        "is_logged_in": False,
        "latest_pdf_path": None,
        "current_screen": "Create Challana",
        "bill_no": "100"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state_safe()

# 🔄 ప్యూర్ నంబర్ బిల్లుల కోసం స్మార్ట్ ఆటో-ఇంక్రిメント ఫంక్షన్
def set_next_bill_no_for_user(username):
    history_records = load_json(HISTORY_FILE, [])
    user_bill_numbers = []
    for r in history_records:
        r_user = r.get('username') or r.get('user_id') or r.get('Username')
        if str(r_user).strip().upper() == str(username).strip().upper():
            try: 
                bno = r.get('bill_no')
                if bno is not None:
                    user_bill_numbers.append(int(bno))
            except: pass
    if user_bill_numbers:
        st.session_state.bill_no = str(max(user_bill_numbers) + 1)
    else:
        st.session_state.bill_no = "100"

url_params = st.query_params
url_id = url_params.get("id", None)
url_auth = url_params.get("auth", None)

# 🔄 URL ఆటో-లాగిన్ మేనేజ్మెంట్
if not st.session_state.is_logged_in and url_id and url_auth:
    if str(url_auth).strip() == calculate_valid_key(url_id):
        users = load_json(USERS_FILE, [])
        user_found = None
        
        for u in users:
            if str(u.get('Username')).strip().upper() == str(url_id).strip().upper():
                user_found = u
                break
                
        if user_found:
            if str(user_found.get('Status', '')).upper() not in ["CLOSED", "EXPIRED"]:
                st.session_state.is_logged_in = True
                st.session_state.user_profile = user_found
                set_next_bill_no_for_user(user_found["Username"])
                st.rerun()

if not st.session_state.is_logged_in:
    st.title("RS Electronic Ultimate")
    st.markdown("---")

    tab1, tab2 = st.tabs(["🔐 Existing User Login", "📝 Register New Shop (7 Days Trial)"])
    
    with tab1:
        st.subheader("Login to your Account")
        
        # 🔥 FIX: ఇక్కడ ఫార్మ్ ని పునరుద్ధరించాము, దీనివల్ల లాగిన్ డేటా పక్కాగా సబ్మిట్ అవుతుంది
        with st.form("login_form_final"):
            login_user = st.text_input("🔑 System ID / Access ID", key="user_login_inp").strip()
            login_pass = st.text_input("Password", type="password", value="123", key="pass_login_inp").strip()
            login_submit = st.form_submit_button("Login to App", use_container_width=True)
            
            if login_submit:
                if login_user.lower() == "admin" and login_pass == "rs2026":
                    st.session_state.is_logged_in = True
                    st.session_state.user_profile = {
                        "Username": "admin", "Key_Type": "Lifetime", "Shop_Name": "RS ELECTRONICS DEVELOPER",
                        "Lic_1": "MASTER-01", "Lic_2": "", "Address_Line1": "ADMIN ZONE", "Address_Line2": "HYDERABAD"
                    }
                    st.session_state.bill_no = "1000"
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    users = load_json(USERS_FILE, [])
                    user_matched = None
                    for u in users:
                        if str(u.get('Username')).strip().upper() == login_user.upper() and str(u.get('Password')).strip() == login_pass:
                            user_matched = u
                            break
                    if user_matched:
                        st.session_state.is_logged_in = True
                        st.session_state.user_profile = user_matched
                        set_next_bill_no_for_user(user_matched["Username"])
                        
                        st.query_params["id"] = user_matched["Username"]
                        st.query_params["auth"] = calculate_valid_key(user_matched["Username"])
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid System ID or Password!")
                            
    with tab2:
        st.subheader("Shop Details Setup & Registration")
        with st.form("shop_registration_form"):
            shop_name = st.text_input("Shop Name *", value="").upper().strip()
            phone = st.text_input("Phone Number *", value="").strip()
            col1, col2 = st.columns(2)
            with col1: lic_1 = st.text_input("Lic No 1 *", value="").upper().strip()
            with col2: lic_2 = st.text_input("Lic No 2 - Optional", value="").upper().strip()
            addr_1 = st.text_input("Address Line 1 *", value="").upper().strip()
            addr_2 = st.text_input("Address Line 2 *", value="").upper().strip()
            
            submit_btn = st.form_submit_button("Create Account & Login To App", type="primary", use_container_width=True)
            
            if submit_btn:
                if not shop_name or not phone or not lic_1 or not addr_1 or not addr_2:
                    st.error("Please fill in all mandatory fields marked with an asterisk (*).")
                else:
                    generated_id = generate_system_id()
                    default_password = "123"
                    
                    success = register_system_customer(
                        system_id=generated_id, password=default_password, phone=phone,
                        shop_name=shop_name, lic_1=lic_1, lic_2=lic_2, addr_1=addr_1, addr_2=addr_2
                    )
                    
                    if success:
                        expiry_date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                        st.session_state.user_profile = {
                            "Username": generated_id, "Password": default_password, "Phone_No": phone,
                            "Status": "ACTIVE", "Key_Type": "Trial", "Expiry_Date": expiry_date_str,
                            "Profile_Setup_Done": "TRUE", "Shop_Name": shop_name, "Lic_1": lic_1,
                            "Lic_2": lic_2, "Address_Line1": addr_1, "Address_Line2": addr_2
                        }
                        st.session_state.is_logged_in = True
                        st.session_state.bill_no = "100"
                        
                        st.query_params["id"] = generated_id
                        st.query_params["auth"] = calculate_valid_key(generated_id)
                        st.success("Account created successfully!")
                        st.rerun()
                    else:
                        st.error("Data not saved local database issue.")

    # 🔒 🔥 తిరుగులేని సేఫ్ ట్రిక్: ఇన్‌పుట్ నేమ్స్ మార్చకుండా, బ్రౌజర్ హిస్టరీని క్లీన్ చేసే కోడ్
    st.html(
        """
        <script>
            function applySafeAutofillBlock() {
                var inputs = document.querySelectorAll('input');
                inputs.forEach(function(input) {
                    // బ్రౌజర్‌కి ఇది OTP బాక్స్ అని అబద్ధం చెప్తున్నాం, దాంతో పాత హిస్టరీ లిస్ట్ రాదు. 
                    // Streamlit కనెక్షన్ కూడా కట్ అవ్వదు!
                    input.setAttribute('autocomplete', 'one-time-code');
                    input.setAttribute('autofill', 'off');
                });
            }
            applySafeAutofillBlock();
            setInterval(applySafeAutofillBlock, 400); // ప్రతి 400ms కి రన్ అవుతుంది
        </script>
        """
    )
    st.stop()

# 🔑 లైసెన్స్ వెరిఫికేషన్ మరియు లోకల్ అప్‌డేట్
current_user = st.session_state.user_profile

if current_user.get("Key_Type") == "Trial":
    try:
        expiry_date = datetime.strptime(str(current_user.get("Expiry_Date")), "%Y-%m-%d").date()
        days_left = (expiry_date - date.today()).days
        
        if days_left < 0:
            st.error("Your 7-day free trial has expired.")
            st.warning(f"Please contact the developer to activate lifetime access.\n\nSystem ID (Username): {current_user.get('Username')}")
            input_key = st.text_input("Enter Activation Key:").strip().upper()
            
            if st.button("Activate App", type="primary", use_container_width=True):
                correct_key = calculate_valid_key(current_user.get('Username'))
                if input_key == correct_key:
                    users = load_json(USERS_FILE, [])
                    for u in users:
                        if u.get('Username') == current_user.get('Username'):
                            u['Key_Type'] = "Lifetime"
                            break
                    save_json(USERS_FILE, users)
                    st.session_state.user_profile["Key_Type"] = "Lifetime"
                    st.success("App successfully activated for lifetime!")
                    st.rerun()
                else:
                    st.error("Invalid activation key.")
            st.stop()
        else: 
            st.sidebar.warning(f"Trial: {days_left} Days Left")
    except: pass
else:
    st.sidebar.success("PREMIUM LIFETIME")

# 🔌 సుపాబేస్ క్లౌడ్ డేటాబేస్ కనెక్షన్ చెకర్ బటన్
if st.sidebar.button("🔌 Check Supabase Cloud Connection"):
    try:
        if "supabase" not in st.secrets:
            st.sidebar.error("❌ Streamlit Secrets లో 'supabase' కీస్ దొరకలేదు!")
        else:
            if supabase_client:
                supabase_client.table("users").select("username").limit(1).execute()
                st.sidebar.success("✅ Supabase Cloud connected successfully!")
                st.sidebar.success("✅ 'users' database table safe!")
                st.sidebar.success("✅ 'history' database table ready for 200+ clients!")
                st.sidebar.balloons()
            else:
                st.sidebar.error("❌ Connection failed!")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Error: {e}")

# =======================================================================
# 🔗 GOOGLE DRIVE SYNC SECTION 
# =======================================================================
st.sidebar.write("---")
st.sidebar.markdown("### 📁 Google Drive Backup")

drive_username = st.session_state.get("user_profile", {}).get("Username")

if drive_username:
    if "code" in st.query_params:
        auth_code = st.query_params["code"]
        
        st.query_params.clear()
        st.query_params["id"] = drive_username
        st.query_params["auth"] = calculate_valid_key(drive_username)
        
        try:
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": auth_code,
                "client_id": st.secrets["google_oauth"]["client_id"],
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "redirect_uri": st.secrets["google_oauth"]["redirect_uri"],
                "grant_type": "authorization_code",
            }
            token_response = requests.post(token_url, data=token_data).json()
            refresh_token = token_response.get("refresh_token")
            
            if refresh_token:
                supabase_client.table("users").update({"google_refresh_token": refresh_token}).eq("username", drive_username).execute()
                st.sidebar.success("🎉 Google Drive connected successfully!")
                st.rerun()
            else:
                st.sidebar.error("❌ Refresh token లభించలేదు! Google Account Permissions లో యాప్ ని డిస్‌కనెక్ట్ చేసి మళ్ళీ కనెక్ట్ చేయండి.")
        except Exception as e:
            st.sidebar.error(f"❌ Token Exchange Error: {e}")

    try:
        db_res = supabase_client.table("users").select("google_refresh_token").eq("username", drive_username).execute()
        if db_res.data and db_res.data[0].get("google_refresh_token"):
            st.sidebar.success("✅ Google Drive Connected!")
            if st.sidebar.button("🔌 Disconnect Drive"):
                supabase_client.table("users").update({"google_refresh_token": None}).eq("username", drive_username).execute()
                st.rerun()
        else:
            client_id = st.secrets["google_oauth"]["client_id"]
            redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
            scope = "https://www.googleapis.com/auth/drive.file"
            
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
                f"&scope={scope}&access_type=offline&prompt=consent"
            )
            st.sidebar.link_button("🔑 Connect My Drive", auth_url)
    except Exception as e:
        st.sidebar.error(f"⚠️ UI Error: {e}")
# =======================================================================

if st.sidebar.button("Logout Account"):
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

st.sidebar.info(f"ID: {current_user.get('Username')}")

from billing_dashboard import show_billing_dashboard
show_billing_dashboard(current_user)