import streamlit as st
import os
from datetime import datetime
from pdf_history import generate_challana_pdf, show_history_log_section
import json
from database import load_json, HISTORY_FILE

AUTOSUGGEST_FILE = "autosuggest.json"

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except:
        pass

def show_billing_dashboard(current_user):
    # 🔥 [రక్షణ 4] - డ్యాష్‌బోర్డ్ రన్ అవ్వగానే అన్ని సెషన్ కీస్ ఉన్నాయో లేదో సరిచూసుకుంటుంది (Fixes Line 21 AttributeError)
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
        if key not in st.session_state:
            st.session_state[key] = value

    # Top navigation tabs
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("CREATE NEW CHALLANA", use_container_width=True, type="primary" if st.session_state.current_screen == "Create Challana" else "secondary"):
            st.session_state.current_screen = "Create Challana"
            st.rerun()
    with nav_col2:
        if st.button("VIEW CHALLANA HISTORY LOG", use_container_width=True, type="primary" if st.session_state.current_screen == "View History Log" else "secondary"):
            st.session_state.current_screen = "View History Log"
            st.rerun()

    st.divider()

    # 1. History Log Screen
    if st.session_state.current_screen == "View History Log":
        show_history_log_section()
        return

    # 2. Main Billing Screen
    st.subheader("Challana Generator")
    
    if st.session_state.latest_pdf_path and os.path.exists(st.session_state.latest_pdf_path):
        st.success("PDF generated successfully!")
        with open(st.session_state.latest_pdf_path, "rb") as f:
            st.download_button(
                label="DOWNLOAD GENERATED CHALLANA PDF",
                data=f,
                file_name=os.path.basename(st.session_state.latest_pdf_path),
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        st.divider()

    sug = load_json(AUTOSUGGEST_FILE, {
        "jurisdictions": ["GUNTUR", "TENALI", "BAPATLA"], "towns": ["TENALI", "GUNTUR"], 
        "villages": ["PERAVALI"], "pins": ["522201"], "trades": ["KIRANA STORE"],
        "makes": ["E-SCALE", "RS BRAND"], "models": ["STANDARD"],
        "max_caps": ["30KG"], "min_caps": ["100G"], "accuracies": ["1G"], "classes": ["CLASS-III"]
    })

    # ఈ నిర్దిష్ట యూజర్ యొక్క పాత బిల్లుల లిస్ట్ సేకరించడం
    history_records = load_json(HISTORY_FILE, [])
    user_bill_numbers = []
    
    for r in history_records:
        if r.get('username') == current_user.get('Username'):
            try:
                user_bill_numbers.append(int(r.get('bill_no', '')))
            except: pass
    
    if user_bill_numbers:
        max_val = max(user_bill_numbers)
        max_bill_no = str(max_val)
        next_regular_bill = str(max_val + 1)
    else:
        max_bill_no = "No Bills"
        next_regular_bill = "100"

    # సెషన్ స్టేట్‌లో బిల్ నంబర్ లేకపోతే డీఫాల్ట్ సెట్ చేయడం
    if not st.session_state.bill_no:
        st.session_state.bill_no = next_regular_bill

    # స్మార్ట్ చెక్: ప్రస్తుతం ఉన్న బిల్ నంబర్ ఆల్రెడీ హిస్టరీలో ఉందో లేదో చూస్తుంది (Edit Mode)
    try:
        is_editing_past_bill = int(st.session_state.bill_no) in user_bill_numbers
    except:
        is_editing_past_bill = False

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t3: 
        manual_mode = st.checkbox("Manual Mode (Skip PDF)")
        st.text_input("Last Regular Bill", value=max_bill_no, disabled=True)

    if not manual_mode and not is_editing_past_bill:
        try:
            if int(st.session_state.bill_no) < int(next_regular_bill):
                st.session_state.bill_no = next_regular_bill
        except:
            st.session_state.bill_no = next_regular_bill

    with col_t1: st.session_state.bill_no = st.text_input("Bill No *", value=st.session_state.bill_no)
    with col_t2: st.session_state.manual_date = st.text_input("Date *", value=st.session_state.manual_date)

    if is_editing_past_bill:
        st.warning(f"📝 **Edit Mode Active:** బిల్ నంబర్ {st.session_state.bill_no} ఆల్రెడీ హిస్టరీలో ఉంది. 'GENERATE' నొッキーతే పాత రికార్డు అప్‌డేట్ అవుతుంది.")

    st.markdown("#### Customer Information")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state.cust_name = st.text_input("Customer Name *", value=st.session_state.cust_name).upper()
        st.session_state.cust_phone = st.text_input("Phone Number", value=st.session_state.cust_phone)
        st.session_state.cust_pro = st.text_input("Proprietor Name (Pro/CO)", value=st.session_state.cust_pro).upper()
    with col_c2:
        st.session_state.cust_area = st.text_input("Area / Landmark", value=st.session_state.cust_area).upper()
        
        sel_j = st.selectbox("Jurisdiction", sug.get("jurisdictions", []) + ["TYPE NEW JURISDICTION"])
        final_jurisdiction = st.text_input("Enter Jurisdiction").upper() if sel_j == "TYPE NEW JURISDICTION" else sel_j
        
        sel_tr = st.selectbox("Trade Type", sug.get("trades", []) + ["TYPE NEW TRADE TYPE"])
        final_trade = st.text_input("Enter Trade").upper() if sel_tr == "TYPE NEW TRADE TYPE" else sel_tr

    col_b = st.columns(3)
    with col_b[0]:
        sel_t = st.selectbox("Town", sug.get("towns", []) + ["TYPE NEW TOWN"])
        final_town = st.text_input("Enter Town").upper() if sel_t == "TYPE NEW TOWN" else sel_t
    with col_b[1]:
        sel_v = st.selectbox("Village", sug.get("villages", []) + ["TYPE NEW VILLAGE"])
        final_vlg = st.text_input("Enter Village").upper() if sel_v == "TYPE NEW VILLAGE" else sel_v
    with col_b[2]:
        sel_p = st.selectbox("Pincode", sug.get("pins", []) + ["TYPE NEW PINCODE"])
        final_pin = st.text_input("Enter Pincode") if sel_p == "TYPE NEW PINCODE" else sel_p

    st.markdown("#### Items Grid Input")
    
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        sel_mk = st.selectbox("Make", sug.get("makes", []) + ["TYPE NEW MAKE"])
        final_make = st.text_input("New Make").upper() if sel_mk == "TYPE NEW MAKE" else sel_mk
        
        sel_mx = st.selectbox("Max Cap", sug.get("max_caps", []) + ["TYPE NEW MAX"])
        final_max = st.text_input("New Max").upper() if sel_mx == "TYPE NEW MAX" else sel_mx
    with col_i2:
        sel_md = st.selectbox("Model", sug.get("models", []) + ["TYPE NEW MODEL"])
        final_model = st.text_input("New Model").upper() if sel_md == "TYPE NEW MODEL" else sel_md
        
        sel_mn = st.selectbox("Min Cap", sug.get("min_caps", []) + ["TYPE NEW MIN"])
        final_min = st.text_input("New Min").upper() if sel_mn == "TYPE NEW MIN" else sel_mn
    with col_i3:
        sel_cl = st.selectbox("Class", sug.get("classes", []) + ["TYPE NEW CLASS"])
        final_class = st.text_input("New Class").upper() if sel_cl == "TYPE NEW CLASS" else sel_cl
        
        sel_ac = st.selectbox("Accuracy", sug.get("accuracies", []) + ["TYPE NEW ACCURACY"])
        final_acc = st.text_input("New Accuracy").upper() if sel_ac == "TYPE NEW ACCURACY" else sel_ac

    col_fee1, col_fee2, col_fee3 = st.columns(3)
    with col_fee1: item_stamping = st.number_input("Stamping Fee", min_value=0, value=400)
    with col_fee2: item_cc = st.number_input("CC Fee", min_value=0, value=50)
    with col_fee3: item_new = st.number_input("New Fee", min_value=0, value=0)
    
    item_mc = st.text_area("M/C Numbers (Comma separated)", value="12345")

    if st.button("ADD ITEM TO LIST", use_container_width=True):
        db_changed = False
        pairs = [("makes", final_make), ("models", final_model), ("max_caps", final_max), ("min_caps", final_min), ("classes", final_class), ("accuracies", final_acc)]
        for k, v in pairs:
            if v and v not in sug[k]:
                sug[k].append(v)
                db_changed = True
        if db_changed: save_json(AUTOSUGGEST_FILE, sug)

        st.session_state.bill_items.append({
            "no": str(len(st.session_state.bill_items) + 1), "make": final_make, "model": final_model, "max": final_max,
            "min": final_min, "acc": final_acc, "class": final_class, "mc_no": item_mc,
            "stamping": str(item_stamping), "cc": str(item_cc), "new": str(item_new), "total": (item_stamping + item_cc + item_new)
        })
        st.success("Item added to list.")
        st.rerun()

    if st.session_state.bill_items:
        st.markdown("##### Current Items Loaded:")
        for idx, item in enumerate(st.session_state.bill_items):
            col_row1, col_row2 = st.columns([6, 1])
            with col_row1:
                st.info(f"Item {idx+1}: {item['make']} - {item['model']} | M/C: {item['mc_no']} | Fee: ₹{item['total']}/-")
            with col_row2:
                if st.button("Delete", key=f"del_{idx}"):
                    st.session_state.bill_items.pop(idx)
                    for i, itm in enumerate(st.session_state.bill_items):
                        itm["no"] = str(i + 1)
                    st.rerun()

    st.divider()
    
    if st.button("GENERATE & SAVE CHALLANA", type="primary", use_container_width=True):
        if not st.session_state.cust_name or not final_trade or not final_town:
            st.error("Please provide Customer Name, Trade Type, and Town details.")
        elif not st.session_state.bill_items:
            st.error("Please add at least one item.")
        else:
            grand_total = sum(float(item['total']) for item in st.session_state.bill_items)
            
            db_updated = False
            for field, value in [("jurisdictions", final_jurisdiction), ("trades", final_trade), ("towns", final_town), ("villages", final_vlg), ("pins", final_pin)]:
                if value and value not in sug[field]:
                    sug[field].append(value)
                    db_updated = True
            if db_updated: save_json(AUTOSUGGEST_FILE, sug)
                
            history = load_json(HISTORY_FILE, [])
            
            new_record = {
                "username": current_user.get('Username'),
                "bill_no": st.session_state.bill_no, "date": st.session_state.manual_date, "name": st.session_state.cust_name, "phone": st.session_state.cust_phone,
                "pro": st.session_state.cust_pro, "area": st.session_state.cust_area, "jurisdiction": final_jurisdiction,
                "trade": final_trade, "town": final_town, "vlg": final_vlg, "pin": final_pin,
                "total": grand_total, "items": st.session_state.bill_items
            }

            updated = False
            for i, r in enumerate(history):
                if str(r.get('bill_no')) == str(st.session_state.bill_no) and r.get('username') == current_user.get('Username'):
                    history[i] = new_record
                    updated = True
                    break
                    
            if not updated:
                history.append(new_record)
                
            save_json(HISTORY_FILE, history)
            
            if not manual_mode:
                pdf_path = generate_challana_pdf(
                    st.session_state.bill_no, st.session_state.manual_date, final_jurisdiction, 
                    st.session_state.cust_name, final_trade, st.session_state.cust_pro, 
                    st.session_state.cust_area, final_town, final_vlg, final_pin, grand_total, current_user
                )
                st.session_state.latest_pdf_path = pdf_path
            
            if is_editing_past_bill:
                st.session_state.bill_no = next_regular_bill
            else:
                try: st.session_state.bill_no = str(int(st.session_state.bill_no) + 1)
                except: pass
                
            st.session_state.manual_date = datetime.now().strftime('%d-%m-%Y')
            st.session_state.cust_name, st.session_state.cust_phone, st.session_state.cust_pro, st.session_state.cust_area = "", "", "", ""
            st.session_state.bill_items = []
            st.rerun()