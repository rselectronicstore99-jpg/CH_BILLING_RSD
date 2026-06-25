import streamlit as st
import os
from datetime import datetime
from pdf_history import generate_challana_pdf, show_history_log_section
import json
from database import load_json, HISTORY_FILE, BASE_DIR

AUTOSUGGEST_FILE = "autosuggest.json"

def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

def show_billing_dashboard(current_user):
    dashboard_defaults = {
        "current_screen": "Create Challana",
        "manual_date": datetime.now().strftime('%d-%m-%Y'),
        "cust_name": "",
        "cust_phone": "",
        "cust_pro": "",
        "cust_area": "",
        "bill_items": [],
        "latest_pdf_path": None,
        "bill_no": "100"
    }
    for key, value in dashboard_defaults.items():
        if key not in st.session_state: st.session_state[key] = value

    # 🌟 3 ట్యాబ్స్ సిస్టమ్
    tab_create, tab_history, tab_settings = st.tabs([
        "🧾 CREATE CHALLANA", 
        "📅 BILLING HISTORY", 
        "⚙️ SHOP SETTINGS (LOGO & SIGN)"
    ])

    # ---- ట్యాబ్ 1: బిల్ జనరేటర్ ----
    with tab_create:
        st.subheader("Challana Generator")
        
        if st.session_state.latest_pdf_path and os.path.exists(st.session_state.latest_pdf_path):
            st.success("PDF generated successfully!")
            with open(st.session_state.latest_pdf_path, "rb") as f:
                st.download_button(label="DOWNLOAD GENERATED CHALLANA PDF", data=f, file_name=os.path.basename(st.session_state.latest_pdf_path), mime="application/pdf", use_container_width=True, type="primary")
            st.divider()

        sug = load_json(AUTOSUGGEST_FILE, {
            "jurisdictions": ["GUNTUR", "TENALI"], "towns": ["TENALI"], "villages": ["PERAVALI"], "pins": ["522201"], "trades": ["KIRANA STORE"],
            "makes": ["E-SCALE"], "models": ["STANDARD"], "max_caps": ["30KG"], "min_caps": ["100G"], "accuracies": ["1G"], "classes": ["CLASS-III"]
        })

        history_records = load_json(HISTORY_FILE, [])
        user_bill_numbers = [int(r.get('bill_no', 0)) for r in history_records if r.get('username') == current_user.get('Username')]
        
        next_regular_bill = str(max(user_bill_numbers) + 1) if user_bill_numbers else "100"
        if not st.session_state.bill_no: st.session_state.bill_no = next_regular_bill

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t3: manual_mode = st.checkbox("Manual Mode (Skip PDF)")
        with col_t1: st.session_state.bill_no = st.text_input("Bill No *", value=st.session_state.bill_no)
        with col_t2: st.session_state.manual_date = st.text_input("Date *", value=st.session_state.manual_date)

        st.markdown("#### Customer Information")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.session_state.cust_name = st.text_input("Customer Name *", value=st.session_state.cust_name).upper()
            st.session_state.cust_phone = st.text_input("Phone Number", value=st.session_state.cust_phone)
            st.session_state.cust_pro = st.text_input("Proprietor Name", value=st.session_state.cust_pro).upper()
        with col_c2:
            st.session_state.cust_area = st.text_input("Area / Landmark", value=st.session_state.cust_area).upper()
            final_jurisdiction = st.selectbox("Jurisdiction", sug.get("jurisdictions", []))
            final_trade = st.selectbox("Trade Type", sug.get("trades", []))

        col_b = st.columns(3)
        with col_b[0]: final_town = st.selectbox("Town", sug.get("towns", []))
        with col_b[1]: final_vlg = st.selectbox("Village", sug.get("villages", []))
        with col_b[2]: final_pin = st.selectbox("Pincode", sug.get("pins", []))

        st.markdown("#### Items Grid Input")
        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            final_make = st.selectbox("Make", sug.get("makes", []))
            final_max = st.selectbox("Max Cap", sug.get("max_caps", []))
        with col_i2:
            final_model = st.selectbox("Model", sug.get("models", []))
            final_min = st.selectbox("Min Cap", sug.get("min_caps", []))
        with col_i3:
            final_class = st.selectbox("Class", sug.get("classes", []))
            final_acc = st.selectbox("Accuracy", sug.get("accuracies", []))

        col_fee1, col_fee2, col_fee3 = st.columns(3)
        with col_fee1: item_stamping = st.number_input("Stamping Fee", min_value=0, value=400)
        with col_fee2: item_cc = st.number_input("CC Fee", min_value=0, value=50)
        with col_fee3: item_new = st.number_input("New Fee", min_value=0, value=0)
        item_mc = st.text_area("M/C Numbers", value="12345")

        if st.button("ADD ITEM TO LIST", use_container_width=True):
            st.session_state.bill_items.append({
                "no": str(len(st.session_state.bill_items) + 1), "make": final_make, "model": final_model, "max": final_max,
                "min": final_min, "acc": final_acc, "class": final_class, "mc_no": item_mc,
                "stamping": str(item_stamping), "cc": str(item_cc), "new": str(item_new), "total": (item_stamping + item_cc + item_new)
            })
            st.rerun()

        if st.session_state.bill_items:
            for idx, item in enumerate(st.session_state.bill_items):
                col_row1, col_row2 = st.columns([6, 1])
                col_row1.info(f"Item {idx+1}: {item['make']} | Fee: ₹{item['total']}/-")
                if col_row2.button("Delete", key=f"del_{idx}"):
                    st.session_state.bill_items.pop(idx)
                    st.rerun()

        st.divider()
        if st.button("GENERATE & SAVE CHALLANA", type="primary", use_container_width=True):
            if not st.session_state.cust_name: st.error("Provide Customer Name!")
            elif not st.session_state.bill_items: st.error("Add at least one item.")
            else:
                grand_total = sum(float(item['total']) for item in st.session_state.bill_items)
                history = load_json(HISTORY_FILE, [])
                new_record = {
                    "username": current_user.get('Username'), "bill_no": st.session_state.bill_no, "date": st.session_state.manual_date,
                    "name": st.session_state.cust_name, "phone": st.session_state.cust_phone, "pro": st.session_state.cust_pro, "area": st.session_state.cust_area,
                    "jurisdiction": final_jurisdiction, "trade": final_trade, "town": final_town, "vlg": final_vlg, "pin": final_pin,
                    "total": grand_total, "items": st.session_state.bill_items
                }
                history.append(new_record)
                save_json(HISTORY_FILE, history)
                
                if not manual_mode:
                    st.session_state.latest_pdf_path = generate_challana_pdf(st.session_state.bill_no, st.session_state.manual_date, final_jurisdiction, st.session_state.cust_name, final_trade, st.session_state.cust_pro, st.session_state.cust_area, final_town, final_vlg, final_pin, grand_total, current_user)
                
                st.session_state.bill_no = str(int(st.session_state.bill_no) + 1) if st.session_state.bill_no.isdigit() else "101"
                st.session_state.cust_name, st.session_state.cust_phone, st.session_state.cust_pro, st.session_state.cust_area = "", "", "", ""
                st.session_state.bill_items = []
                st.rerun()

    # ---- ట్యాబ్ 2: హిస్టరీ రికార్డ్స్ ----
    with tab_history:
        show_history_log_section()

    # ---- 🌟 ట్యాబ్ 3: లోకల్ లోగో & సంతకం సెట్టింగ్స్ ----
    with tab_settings:
        st.markdown("### 🏪 Upload / Change Your Shop Logo & Signature")
        st.info("💡 ఇక్కడ మీరు ఎప్పుడైనా లోగో/సంతకం అప్‌లోడ్ చేయవచ్చు లేదా మార్చవచ్చు. ఇది ఫోల్డర్ లో సేవ్ అవుతుంది. ఏమీ అప్‌లోడ్ చేయకపోతే PDF లో ఆ స్థలం Blank గా ఉంటుంది.")
        
        username = current_user.get('Username', '').strip()
        col_logo, col_sign = st.columns(2)
        
        with col_logo:
            st.markdown("#### 🖼️ Shop Logo")
            logo_filename = f"{username}_logo.png"
            logo_save_path = os.path.join(BASE_DIR, logo_filename)
            if os.path.exists(logo_save_path): st.image(logo_save_path, caption="Saved Logo", width=100)
                
            logo_file = st.file_uploader("Upload New Logo (.png)", type=["png"], key="dashboard_logo")
            if logo_file is not None:
                with open(logo_save_path, "wb") as f: f.write(logo_file.getbuffer())
                st.success("🎉 Logo Saved!")
                st.rerun()

        with col_sign:
            st.markdown("#### ✍️ Authorized Signature")
            sign_filename = f"{username}_sign.png"
            sign_save_path = os.path.join(BASE_DIR, sign_filename)
            if os.path.exists(sign_save_path): st.image(sign_save_path, caption="Saved Signature", width=150)
                
            sign_file = st.file_uploader("Upload New Signature (.png)", type=["png"], key="dashboard_sign")
            if sign_file is not None:
                with open(sign_save_path, "wb") as f: f.write(sign_file.getbuffer())
                st.success("🎉 Signature Saved!")
                st.rerun()