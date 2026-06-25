import streamlit as st
from datetime import datetime, date, timedelta
from database import get_gspread_sheet, generate_system_id, register_system_customer, calculate_valid_key

# 1. Page Configuration
st.set_page_config(page_title="RS Electronic Ultimate", layout="centered")

# --- సెషన్ స్టేట్ వేరియబుల్స్ ---
if "manual_date" not in st.session_state: st.session_state.manual_date = datetime.now().strftime('%d-%m-%Y')
if "cust_name" not in st.session_state: st.session_state.cust_name = ""
if "cust_phone" not in st.session_state: st.session_state.cust_phone = ""
if "cust_pro" not in st.session_state: st.session_state.cust_pro = ""
if "cust_area" not in st.session_state: st.session_state.cust_area = ""
if "bill_items" not in st.session_state: st.session_state.bill_items = []
if "is_logged_in" not in st.session_state: st.session_state.is_logged_in = False
if "bill_no" not in st.session_state: st.session_state.bill_no = "100"

from billing_dashboard import show_billing_dashboard

# గూగుల్ షీట్ డేటాని సేఫ్ గా క్యాష్ చేయడం
@st.cache_data(ttl=15)
def fetch_all_users_cached():
    try:
        sheet_obj = get_gspread_sheet()
        if sheet_obj: return sheet_obj.get_all_values()
    except: pass
    return None

# 2. 🔄 మొబైల్ రీఫ్రెష్ ప్రొటెక్షన్ లాజిక్ (Auto-Login via URL)
url_params = st.query_params
url_id = url_params.get("id", None)

if not st.session_state.is_logged_in and url_id:
    # మొబైల్ రీఫ్రెష్ చేసినప్పుడు రిజిస్ట్రేషన్ ఫామ్ కనిపించకుండా ఇక్కడ లోడింగ్ స్పిన్నర్ పెట్టాము
    with st.spinner("🔄 Reconnecting your session... Please wait..."):
        try:
            rows = fetch_all_users_cached()
            if rows:
                user_found = None
                row_idx = 1
                for idx in range(1, len(rows)):
                    row = rows[idx]
                    if len(row) > 0 and str(row[0]).strip() == str(url_id).strip():
                        while len(row) < 12: row.append("")
                        user_found = {
                            "Username": row[0], "Password": row[1], "Phone_No": row[2],
                            "Status": row[3], "Key_Type": row[4], "Expiry_Date": row[5],
                            "Profile_Setup_Done": row[6], "Shop_Name": row[7], "Lic_1": row[8],
                            "Lic_2": row[9], "Address_Line1": row[10], "Address_Line2": row[11]
                        }
                        row_idx = idx + 1
                        break
                
                if user_found and str(user_found.get('Status', '')).strip().upper() not in ["CLOSED", "EXPIRED"]:
                    st.session_state.is_logged_in = True
                    st.session_state.user_profile = user_found
                    st.session_state.user_row_idx = row_idx
                    st.rerun()
        except:
            pass

# 3. 🔐 స్క్రీన్ డిస్ప్లే లాజిక్ (లాగిన్ అవ్వకపోతే)
if not st.session_state.is_logged_in:
    st.title("RS Electronic Ultimate")
    st.markdown("---")
    
    # ✨ ఇక్కడ ట్యాబ్స్ సిస్టమ్ పెట్టాము. దీనివల్ల డీఫాల్ట్ గా లాగిన్ స్క్రీన్ మాత్రమే కనిపిస్తుంది!
    tab1, tab2 = st.tabs(["🔐 Existing User Login", "📝 Register New Shop (7 Days Trial)"])
    
    # --- ట్యాబ్ 1: కేవలం లాగిన్ కోసం మాత్రమే ---
    with tab1:
        st.subheader("Login to your Account")
        with st.form("login_form"):
            login_user = st.text_input("User ID / Username (e.g., RS-XXXXX-SYS)").strip()
            login_pass = st.text_input("Password", type="password", value="123").strip()
            login_submit = st.form_submit_button("Login to App", use_container_width=True)
            
            if login_submit:
                if login_user == "admin" and login_pass == "rs2026":
                    st.session_state.is_logged_in = True
                    st.session_state.user_profile = {
                        "Username": "admin", "Key_Type": "Lifetime", "Shop_Name": "RS ELECTRONICS DEVELOPER",
                        "Lic_1": "MASTER-01", "Lic_2": "", "Address_Line1": "ADMIN ZONE", "Address_Line2": "HYDERABAD"
                    }
                    st.query_params["id"] = "admin"
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    with st.spinner("Checking database..."):
                        rows = fetch_all_users_cached()
                        if rows:
                            user_matched = None
                            r_idx = 1
                            for idx in range(1, len(rows)):
                                row = rows[idx]
                                if len(row) > 0 and str(row[0]).strip() == login_user and str(row[1]).strip() == login_pass:
                                    while len(row) < 12: row.append("")
                                    user_matched = {
                                        "Username": row[0], "Password": row[1], "Phone_No": row[2],
                                        "Status": row[3], "Key_Type": row[4], "Expiry_Date": row[5],
                                        "Profile_Setup_Done": row[6], "Shop_Name": row[7], "Lic_1": row[8],
                                        "Lic_2": row[9], "Address_Line1": row[10], "Address_Line2": row[11]
                                    }
                                    r_idx = idx + 1
                                    break
                            if user_matched:
                                st.session_state.is_logged_in = True
                                st.session_state.user_profile = user_matched
                                st.session_state.user_row_idx = r_idx
                                st.query_params["id"] = login_user
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid User ID or Password! Please check again.")
                        else:
                            st.error("Database connection busy. Please try again in 5 seconds.")
                            
    # --- ట్యాబ్ 2: కొత్త కస్టమర్ రిజిస్ట్రేషన్ కోసం (కస్టమర్ క్లిక్ చేస్తేనే ఓపెన్ అవుతుంది) ---
    with tab2:
        st.subheader("Shop Details Setup & Registration")
        with st.form("shop_registration_form"):
            shop_name = st.text_input("Shop Name *").upper().strip()
            phone = st.text_input("Phone Number *").strip()
            col1, col2 = st.columns(2)
            with col1: lic_1 = st.text_input("Lic No 1 *").upper().strip()
            with col2: lic_2 = st.text_input("Lic No 2 - Optional").upper().strip()
            addr_1 = st.text_input("Address Line 1 *").upper().strip()
            addr_2 = st.text_input("Address Line 2 *").upper().strip()
            
            submit_btn = st.form_submit_button("Create Account & Login To App", type="primary", use_container_width=True)
            
            if submit_btn:
                if not shop_name or not phone or not lic_1 or not addr_1 or not addr_2:
                    st.error("Please fill in all mandatory fields marked with (*).")
                else:
                    with st.spinner("Registering your shop in Google Sheets..."):
                        generated_id = generate_system_id()
                        default_password = "123"
                        success = register_system_customer(generated_id, default_password, phone, shop_name, lic_1, lic_2, addr_1, addr_2)
                        
                        if success:
                            st.cache_data.clear() # క్యాష్ క్లియర్
                            expiry_date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                            st.session_state.user_profile = {
                                "Username": generated_id, "Password": default_password, "Phone_No": phone,
                                "Status": "ACTIVE", "Key_Type": "Trial", "Expiry_Date": expiry_date_str,
                                "Profile_Setup_Done": "TRUE", "Shop_Name": shop_name, "Lic_1": lic_1,
                                "Lic_2": lic_2, "Address_Line1": addr_1, "Address_Line2": addr_2
                            }
                            st.session_state.is_logged_in = True
                            st.query_params["id"] = generated_id
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            st.error("Google Sheet error! డేటా సేవ్ అవ్వలేదు. మీ ఇంటర్నెట్ చెక్ చేసుకోండి లేదా మళ్ళీ ట్రై చేయండి.")
        st.stop()
    st.stop()

# 4. 🔑 లైసెన్స్ వెరిఫికేషన్ మరియు డ్యాష్‌బోర్డ్ రన్ లాజిక్
try:
    sheet = get_gspread_sheet()
except: pass

current_user = st.session_state.user_profile
if current_user.get("Key_Type") == "Trial":
    try:
        expiry_date = datetime.strptime(str(current_user.get("Expiry_Date")), "%Y-%m-%d").date()
        days_left = (expiry_date - date.today()).days
        if days_left < 0:
            st.error("Your 7-day free trial has expired.")
            st.warning(f"Please contact developer for Lifetime activation.\n\nSystem ID: {current_user.get('Username')}")
            input_key = st.text_input("Enter Activation Key:").strip().upper()
            if st.button("Activate App", type="primary", use_container_width=True):
                if input_key == calculate_valid_key(current_user.get('Username')):
                    if sheet: sheet.update_cell(st.session_state.user_row_idx, 5, "Lifetime")
                    st.cache_data.clear()
                    st.session_state.user_profile["Key_Type"] = "Lifetime"
                    st.success("Activated for lifetime!")
                    st.rerun()
                else: st.error("Invalid key.")
            st.stop()
        else: st.sidebar.warning(f"Trial: {days_left} Days Left")
    except: pass
else:
    st.sidebar.success("PREMIUM LIFETIME")

if st.sidebar.button("Logout Account"):
    st.session_state.is_logged_in = False
    st.query_params.clear()
    st.cache_data.clear()
    st.rerun()

st.sidebar.info(f"ID: {current_user.get('Username')}")
show_billing_dashboard(current_user)