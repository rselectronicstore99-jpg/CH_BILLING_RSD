import streamlit as st
import os
import json
from datetime import datetime
from pdf_history import generate_challana_pdf, show_history_log_section
from database import load_json, save_json, HISTORY_FILE, BASE_DIR, LOGO_PATH, SIGN_PATH

AUTOSUGGEST_FILE = os.path.join(BASE_DIR, "autosuggest.json")

def render_smart_input(label, options_list, key_prefix):
    clean_opts = sorted(list(set([str(x).strip().upper() for x in options_list if x])))
    txt_key = f"txt_{key_prefix}"
    sel_key = f"sel_{key_prefix}"
    
    if txt_key not in st.session_state: st.session_state[txt_key] = ""
    if sel_key not in st.session_state: st.session_state[sel_key] = "▼"
        
    def sync_drop_to_text():
        selected = st.session_state[sel_key]
        if selected and selected != "▼":
            st.session_state[txt_key] = selected

    st.markdown(f"<p style='margin-bottom: -5px; font-weight: bold; font-size: 14px;'>{label}</p>", unsafe_allow_html=True)
    col_txt, col_sel = st.columns([3.4, 1.6])
    
    with col_txt:
        final_val = st.text_input("Input", key=txt_key, label_visibility="collapsed").strip().upper()
    with col_sel:
        st.selectbox("Dropdown", ["▼"] + clean_opts, key=sel_key, on_change=sync_drop_to_text, label_visibility="collapsed")
        
    return final_val

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
        "bill_no": "",
        "clear_all_fields": False,
        "item_added_success": False,
        "challana_saved_success": False
    }
    for key, value in dashboard_defaults.items():
        if key not in st.session_state: 
            st.session_state[key] = value

    if st.session_state.clear_all_fields:
        # [🎯 FIX]: పాత బిల్లు ఎడిట్ చేసినప్పుడు సీరియల్ నెంబర్ పాడవకుండా ఉండటానికి ఖాళీ చేసి ఆటో-రీకాలిక్యులేట్ చేస్తున్నాము
        st.session_state.bill_no = ""
        st.session_state.cust_name = ""
        st.session_state.cust_phone = ""
        st.session_state.cust_pro = ""
        st.session_state.cust_area = ""
        st.session_state.bill_items = []
        
        all_prefixes = ["jur", "trd", "twn", "vlg", "pin", "mk", "md", "mx", "mn", "cls", "ac", "mc"]
        for kp in all_prefixes:
            st.session_state[f"txt_{kp}"] = ""
            st.session_state[f"sel_{kp}"] = "▼"
            
        st.session_state.clear_all_fields = False
        st.session_state.challana_saved_success = True

    tab_create, tab_history, tab_settings = st.tabs([
        "🧾 CREATE CHALLANA", 
        "📅 BILLING HISTORY", 
        "⚙️ SHOP SETTINGS"
    ])

    sug = load_json(AUTOSUGGEST_FILE, {
        "jurisdictions": ["GUNTUR", "TENALI"], "trades": ["KIRANA STORE", "GOLD SHOP"],
        "towns": ["TENALI", "GUNTUR"], "villages": ["PERAVALI"], "pins": ["522201"],
        "makes": ["E-SCALE"], "models": ["STANDARD"], "max_caps": ["30KG"],
        "min_caps": ["100G"], "accuracies": ["1G"], "classes": ["CLASS-III"], "mc_nos": []
    })

    with tab_create:
        st.subheader("Challana Generator")
        
        if st.session_state.item_added_success:
            st.success("🎯 Item Added to List!")
            st.session_state.item_added_success = False
            
        if st.session_state.challana_saved_success:
            st.success("🎉 Challana Saved Successfully!")
            st.session_state.challana_saved_success = False
        
        if st.session_state.latest_pdf_path and os.path.exists(st.session_state.latest_pdf_path):
            with open(st.session_state.latest_pdf_path, "rb") as f:
                st.download_button(
                    label="📥 DOWNLOAD GENERATED CHALLANA PDF", 
                    data=f, 
                    file_name=os.path.basename(st.session_state.latest_pdf_path), 
                    mime="application/pdf", use_container_width=True, type="primary"
                )
            st.divider()

        history_records = load_json(HISTORY_FILE, [])
        user_bill_numbers = [int(r.get('bill_no', 0)) for r in history_records if r.get('username') == current_user.get('Username') if str(r.get('bill_no', '')).isdigit()]
        
        next_regular_bill = str(max(user_bill_numbers) + 1) if user_bill_numbers else "100"
        if not st.session_state.bill_no: 
            st.session_state.bill_no = next_regular_bill

        col_t1, col_t2, col_t3 = st.columns(3)
        # [🎯 KEY ADDED]: Manual Mode చెక్‌బాక్స్‌కు కీ ని అసైన్ చేసాము
        with col_t3: manual_mode = st.checkbox("Manual Mode (Skip PDF)", key="manual_mode_checkbox")
        with col_t1: st.session_state.bill_no = st.text_input("Bill No *", value=st.session_state.bill_no)
        with col_t2: st.session_state.manual_date = st.text_input("Date *", value=st.session_state.manual_date)

        st.markdown("#### 👤 Customer Information")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.session_state.cust_name = st.text_input("Customer Name (M/S) *", value=st.session_state.cust_name).upper()
            st.session_state.cust_phone = st.text_input("Phone Number", value=st.session_state.cust_phone)
            st.session_state.cust_pro = st.text_input("Proprietor Name", value=st.session_state.cust_pro).upper()
        with col_c2:
            st.session_state.cust_area = st.text_input("Area / Landmark", value=st.session_state.cust_area).upper()
            final_jurisdiction = render_smart_input("Jurisdiction", sug.get("jurisdictions", []), "jur")
            final_trade = render_smart_input("Trade Type", sug.get("trades", []), "trd")

        col_b = st.columns(3)
        with col_b[0]: final_town = render_smart_input("Town", sug.get("towns", []), "twn")
        with col_b[1]: final_vlg = render_smart_input("Village", sug.get("villages", []), "vlg")
        with col_b[2]: final_pin = render_smart_input("Pincode", sug.get("pins", []), "pin")

        st.markdown("#### ⚖️ Weighing Scale Specifications")
        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            final_make = render_smart_input("Make", sug.get("makes", []), "mk")
            final_max = render_smart_input("Max Cap", sug.get("max_caps", []), "mx")
        with col_i2:
            final_model = render_smart_input("Model", sug.get("models", []), "md")
            final_min = render_smart_input("Min Cap", sug.get("min_caps", []), "mn")
        with col_i3:
            final_class = render_smart_input("Class", sug.get("classes", []), "cls")
            final_acc = render_smart_input("Accuracy", sug.get("accuracies", []), "ac")

        col_fee1, col_fee2, col_fee3 = st.columns(3)
        with col_fee1: item_stamping = st.number_input("Stamping Fee", min_value=0, value=400)
        with col_fee2: item_cc = st.number_input("CC Fee", min_value=0, value=50)
        with col_fee3: item_new = st.number_input("New Fee (Sistu)", min_value=0, value=0)
        
        final_mc = render_smart_input("Machine Serial No (M/C NO)", sug.get("mc_nos", []), "mc")

        if st.button("➕ ADD ITEM TO CHALLANA LIST", use_container_width=True, type="secondary"):
            if not final_make or not final_model:
                st.error("❌ దయచేసి కనీసం Make మరియు Model వివరాలను ఎంటర్ చేయండి!")
            else:
                for k, v in [("makes", final_make), ("models", final_model), ("max_caps", final_max), 
                             ("min_caps", final_min), ("classes", final_class), ("accuracies", final_acc), ("mc_nos", final_mc)]:
                    if v and v not in sug[k]: sug[k].append(v)
                for k, v in [("jurisdictions", final_jurisdiction), ("trades", final_trade), 
                             ("towns", final_town), ("villages", final_vlg), ("pins", final_pin)]:
                    if v and v not in sug[k]: sug[k].append(v)
                save_json(AUTOSUGGEST_FILE, sug)

                st.session_state.bill_items.append({
                    "no": str(len(st.session_state.bill_items) + 1), 
                    "make": final_make, "model": final_model, "max": final_max, "min": final_min, 
                    "acc": final_acc, "class": final_class, "mc_no": final_mc,
                    "stamping": str(item_stamping), "cc": str(item_cc), "new": str(item_new), "total": (item_stamping + item_cc + item_new)
                })
                st.session_state.item_added_success = True
                st.rerun()

        if st.session_state.bill_items:
            st.markdown("##### 📋 Current Added Items:")
            for idx, item in enumerate(st.session_state.bill_items):
                col_row1, col_row2 = st.columns([6, 1])
                col_row1.info(f"Item {idx+1}: {item['make']} | Max: {item['max']} | M/C No: {item['mc_no']} | Total: ₹{item['total']}/-")
                if col_row2.button("🗑️ Delete", key=f"del_{idx}"):
                    st.session_state.bill_items.pop(idx)
                    st.rerun()

        st.divider()
        
        # [🎯 FIX]: MANUAL MODE ఆన్ / ఆఫ్ ఆధారంగా బటన్స్ మరియు యాక్షన్స్ మారే లాజిక్
        if manual_mode:
            st.info("⚙️ Manual Mode Features Active")
            # ఇక్కడ యూజర్ కేవలం సేవ్ చేయాలా లేక సేవ్ చేసి పీడీఎఫ్ కూడా కావాలో సెలెక్ట్ చేసుకోవచ్చు
            manual_action = st.radio(
                "Select Action for Manual Bill:",
                ["Save to History Only (No PDF)", "Save & Generate PDF Bill"],
                horizontal=True,
                key="manual_action_radio"
            )
            
            if st.button("💾 PROCESS & SAVE MANUAL CHALLANA", type="primary", use_container_width=True):
                if not st.session_state.cust_name or not st.session_state.bill_items:
                    st.error("❌ Please enter Customer Name and Add at least one item!")
                else:
                    grand_total = sum(float(item['total']) for item in st.session_state.bill_items)
                    history = load_json(HISTORY_FILE, [])
                    
                    new_record = {
                        "username": current_user.get('Username'), "bill_no": st.session_state.bill_no, "date": st.session_state.manual_date,
                        "name": st.session_state.cust_name, "phone": st.session_state.cust_phone, "pro": st.session_state.cust_pro, "area": st.session_state.cust_area,
                        "jurisdiction": final_jurisdiction, "trade": final_trade, "town": final_town, "vlg": final_vlg, "pin": final_pin,
                        "total": grand_total, "items": st.session_state.bill_items
                    }
                    
                    existing_idx = None
                    for i, record in enumerate(history):
                        if record.get('username') == current_user.get('Username') and str(record.get('bill_no')) == str(st.session_state.bill_no):
                            existing_idx = i
                            break
                    if existing_idx is not None:
                        history[existing_idx] = new_record  
                    else:
                        history.append(new_record)         
                    save_json(HISTORY_FILE, history)
                    
                    if manual_action == "Save & Generate PDF Bill":
                        st.session_state.latest_pdf_path = generate_challana_pdf(
                            st.session_state.bill_no, st.session_state.manual_date, final_jurisdiction, 
                            st.session_state.cust_name, final_trade, st.session_state.cust_pro, 
                            st.session_state.cust_area, final_town, final_vlg, final_pin, grand_total, current_user
                        )
                    st.session_state.clear_all_fields = True
                    st.rerun()
        else:
            # Regular Mode (Manual Mode OFF ఉన్నప్పుడు పాత లాగానే డైరెక్ట్ గా పీడీఎఫ్ క్రియేట్ అవుతుంది)
            if st.button("💾 GENERATE & SAVE CHALLANA", type="primary", use_container_width=True):
                if not st.session_state.cust_name or not st.session_state.bill_items: 
                    st.error("❌ Please enter Customer Name and Add at least one item!")
                else:
                    grand_total = sum(float(item['total']) for item in st.session_state.bill_items)
                    history = load_json(HISTORY_FILE, [])
                    
                    new_record = {
                        "username": current_user.get('Username'), "bill_no": st.session_state.bill_no, "date": st.session_state.manual_date,
                        "name": st.session_state.cust_name, "phone": st.session_state.cust_phone, "pro": st.session_state.cust_pro, "area": st.session_state.cust_area,
                        "jurisdiction": final_jurisdiction, "trade": final_trade, "town": final_town, "vlg": final_vlg, "pin": final_pin,
                        "total": grand_total, "items": st.session_state.bill_items
                    }
                    
                    existing_idx = None
                    for i, record in enumerate(history):
                        if record.get('username') == current_user.get('Username') and str(record.get('bill_no')) == str(st.session_state.bill_no):
                            existing_idx = i
                            break
                    if existing_idx is not None:
                        history[existing_idx] = new_record  
                    else:
                        history.append(new_record)         
                    save_json(HISTORY_FILE, history)
                    
                    st.session_state.latest_pdf_path = generate_challana_pdf(
                        st.session_state.bill_no, st.session_state.manual_date, final_jurisdiction, 
                        st.session_state.cust_name, final_trade, st.session_state.cust_pro, 
                        st.session_state.cust_area, final_town, final_vlg, final_pin, grand_total, current_user
                    )
                    st.session_state.clear_all_fields = True
                    st.rerun()

    with tab_history:
        show_history_log_section()

    with tab_settings:
        st.markdown("### 🏪 Shop Settings")
        col_logo, col_sign = st.columns(2)
        with col_logo:
            st.markdown("#### 🖼️ Shop Logo Management")
            if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=150)
            uploaded_logo = st.file_uploader("Upload Logo", type=["png", "jpg", "jpeg"], key="logo_upload_key")
            if uploaded_logo is not None and st.button("💾 SAVE LOGO", use_container_width=True):
                with open(LOGO_PATH, "wb") as f: f.write(uploaded_logo.getbuffer())
                st.success("Logo Saved!")
                st.rerun()
        with col_sign:
            st.markdown("#### ✍️ Signature Management")
            if os.path.exists(SIGN_PATH): st.image(SIGN_PATH, width=150)
            uploaded_sign = st.file_uploader("Upload Signature", type=["png", "jpg", "jpeg"], key="sign_upload_key")
            if uploaded_sign is not None and st.button("💾 SAVE SIGNATURE", use_container_width=True):
                with open(SIGN_PATH, "wb") as f: f.write(uploaded_sign.getbuffer())
                st.success("Signature Saved!")
                st.rerun()