import streamlit as st
import os
import json
from datetime import datetime, date, timedelta
from database import load_json, get_gspread_sheet, HISTORY_FILE, generate_system_id, register_system_customer, calculate_valid_key, SECRET_SALT

# 1. Page Configuration
st.set_page_config(page_title="RS Electronic Ultimate", layout="centered")

# 🔥 [రక్షణ 1] - హార్డ్ రీఫ్రెష్ చేసినా ఏ వేరియబుల్ మిస్ అవ్వకుండా ఇక్కడే డిఫాల్ట్ వాల్యూస్ సెట్ అవుతాయి
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

# ⚙️ బిల్ నంబర్ లెక్కించే ప్రత్యేక ఫంక్షన్
def set_next_bill_no_for_user(username):
    history_records = load_json(HISTORY_FILE, [])
    user_bill_numbers = []
    
    for r in history_records:
        if r.get('username') == username or r.get('user_id') == username:
            try:
                user_bill_numbers.append(int(r.get('bill_no', 0)))
            except: pass
            
    if user_bill_numbers:
        st.session_state.bill_no = str(max(user_bill_numbers) + 1)
    else:
        st.session_state.bill_no = "100"

# Connect to Google Sheets
try:
    sheet = get_gspread_sheet()
except Exception as e:
    st.error(f"Google Sheet Connection Error: {e}")
    st.stop()

# 3. Background Auto-Login via URL ID Only (Safe for multi-user cloud deployments)
url_params = st.query_params
url_id = url_params.get("id", None)

# 🔥 [రక్షణ 2] - రీఫ్రెష్ అవ్వగానే ఫామ్స్ కనిపించకుండా లోడింగ్ స్пиన్నర్ రన్ అవుతుంది
if not st.session_state.is_logged_in and url_id:
    with st.spinner("🔄 Reconnecting to your session... Please wait..."):
        try:
            rows = sheet.get_all_values()
            user_found = None
            row_idx = 1
            target_id = str(url_id).strip().upper() # Case-Insensitive Check
            
            for idx in range(1, len(rows)):
                row = rows[idx]
                if len(row) > 0 and str(row[0]).strip().upper() == target_id:
                    while len(row) < 12: row.append("")
                    user_found = {
                        "Username": row[0], "Password": row[1], "Phone_No": row[2],
                        "Status": row[3], "Key_Type": row[4], "Expiry_Date": row[5],
                        "Profile_Setup_Done": row[6], "Shop_Name": row[7], "Lic_1": row[8],
                        "Lic_2": row[9], "Address_Line1": row[10], "Address_Line2": row[11]
                    }
                    row_idx = idx + 1
                    break
                        
            if user_found:
                if str(user_found.get('Status', '')).strip().upper() not in ["CLOSED", "EXPIRED"]:
                    st.session_state.is_logged_in = True
                    st.session_state.user_profile = user_found
                    st.session_state.user_row_idx = row_idx
                    set_next_bill_no_for_user(user_found["Username"])
                    st.query_params["id"] = user_found["Username"]
                    st.rerun()
        except: pass

# 4. Screen Display Logic (If Not Logged In)
if not st.session_state.is_logged_in:
    st.title("RS Electronic Ultimate")
    st.markdown("---")
    
    # 🔥 [రక్షణ 3] - ట్యాబ్స్ పెట్టడం వల్ల పొరపాటున కూడా రిజిస్ట్రేషన్ స్క్రీన్ డైరెక్ట్ గా రాదు! 
    tab1, tab2 = st.tabs(["🔐 Existing User Login", "📝 Register New Shop (7 Days Trial)"])
    
    with tab1:
        st.subheader("Login to your Account")
        with st.form("login_form"):
            login_user = st.text_input("User ID / Username").strip().upper() # Auto Upper-case conversion
            login_pass = st.text_input("Password", type="password", value="123").strip()
            login_submit = st.form_submit_button("Login to App", use_container_width=True)
            
            if login_submit:
                if login_user == "ADMIN" and login_pass == "rs2026":
                    st.session_state.is_logged_in = True
                    st.session_state.user_profile = {
                        "Username": "admin", "Key_Type": "Lifetime", "Shop_Name": "RS ELECTRONICS DEVELOPER",
                        "Lic_1": "MASTER-01", "Lic_2": "", "Address_Line1": "ADMIN ZONE", "Address_Line2": "HYDERABAD"
                    }
                    st.session_state.bill_no = "1000"
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    with st.spinner("Checking credentials..."):
                        rows = sheet.get_all_values()
                        user_matched = None
                        r_idx = 1
                        for idx in range(1, len(rows)):
                            row = rows[idx]
                            # Case-Insensitive Row Matching
                            if len(row) > 1 and str(row[0]).strip().upper() == login_user and str(row[1]).strip() == login_pass:
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
                            set_next_bill_no_for_user(user_matched["Username"])
                            
                            st.query_params["id"] = user_matched["Username"]
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid User ID or Password!")
                            
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
            
            st.markdown("---")
            st.subheader("Media Uploads (Optional)")
            logo_file = st.file_uploader("Upload Shop Logo (PNG)", type=["png"])
            sign_file = st.file_uploader("Upload Owner Signature (PNG)", type=["png"])
            
            submit_btn = st.form_submit_button("Create Account & Login To App", type="primary", use_container_width=True)
            
            if submit_btn:
                if not shop_name or not phone or not lic_1 or not addr_1 or not addr_2:
                    st.error("Please fill in all mandatory fields marked with an asterisk (*).")
                else:
                    try:
                        with st.spinner("Creating account in database..."):
                            generated_id = generate_system_id()
                            default_password = "123"
                            
                            if logo_file is not None:
                                with open("logo.png", "wb") as f: f.write(logo_file.getbuffer())
                            if sign_file is not None:
                                with open("sign.png", "wb") as f: f.write(sign_file.getbuffer())
                            
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
                                st.success("Account created successfully!")
                                st.rerun()
                            else:
                                st.error("Data not saved. Check network connection.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        st.stop()

# 5. License Verification Logic
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
                    try:
                        sheet.update_cell(st.session_state.user_row_idx, 5, "Lifetime")
                        st.session_state.user_profile["Key_Type"] = "Lifetime"
                        st.success("App successfully activated for lifetime!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Activation Error: {e}")
                else:
                    st.error("Invalid activation key.")
            st.stop()
        else: 
            st.sidebar.warning(f"Trial: {days_left} Days Left")
    except: pass
else:
    st.sidebar.success("PREMIUM LIFETIME")

if st.sidebar.button("Logout Account"):
    st.session_state.is_logged_in = False
    st.query_params.clear()
    st.rerun()

st.sidebar.info(f"ID: {current_user.get('Username')}")

from billing_dashboard import show_billing_dashboard
# Run main dashboard module
show_billing_dashboard(current_user)