import streamlit as st
import os
import json
from datetime import datetime
from pdf_history import generate_challana_pdf, show_history_log_section
from database import load_json, save_json, HISTORY_FILE, BASE_DIR

AUTOSUGGEST_FILE = os.path.join(BASE_DIR, "autosuggest.json")

def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

def render_smart_input(label, options_list, key_prefix):
    """
    మీరు స్కెచ్ లో చూపించిన విధంగా పక్కపక్కనే (Side-by-Side) ఉండేలా డిజైన్ చేసిన సిస్టమ్:
    - ఎడమవైపు: మెయిన్ డేటా ఎంట్రీ బాక్స్ 
    - కుడివైపు: చిన్న సెలెక్షన్ డౌన్ ఆరో బటన్ (▼)
    """
    clean_opts = sorted(list(set([str(x).strip().upper() for x in options_list if x])))
    txt_key = f"txt_{key_prefix}"
    sel_key = f"sel_{key_prefix}"
    
    if txt_key not in st.session_state: st.session_state[txt_key] = ""
    if sel_key not in st.session_state: st.session_state[sel_key] = "▼"
        
    # డ్రాప్‌డౌన్ లో పాత రికార్డు ఎంచుకున్నప్పుడు ఎడమపక్క బాక్స్ ని అప్‌డేట్ చేసే ఫంక్షన్
    def sync_drop_to_text():
        selected = st.session_state[sel_key]
        if selected and selected != "▼":
            st.session_state[txt_key] = selected

    # పైభాగంలో లేబుల్
    st.markdown(f"<p style='margin-bottom: -5px; font-weight: bold; font-size: 14px;'>{label}</p>", unsafe_allow_html=True)
    
    # ఎడమపక్క బాక్స్ మరియు కుడిపక్క ఆరో బటన్ కోసం రేషియో
    col_txt, col_sel = st.columns([3.8, 1.2])
    
    with col_sel:
        st.selectbox("Dropdown", ["▼"] + clean_opts, key=sel_key, on_change=sync_drop_to_text, label_visibility="collapsed")
    with col_txt:
        final_val = st.text_input("Input", key=txt_key, label_visibility="collapsed").strip().upper()
        
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
        "bill_no": "100"
    }
    for key, value in dashboard_defaults.items():
        if key not in st.session_state: 
            st.session_state[key] = value

    # 🌟 3 ట్యాబ్స్ లేఅవుట్
    tab_create, tab_history, tab_settings = st.tabs([
        "🧾 CREATE CHALLANA", 
        "📅 BILLING HISTORY", 
        "⚙️ SHOP SETTINGS"
    ])

    # ---- ఆటోసజెషన్ డేటాబేస్ లోడ్ చేయడం ----
    sug = load_json(AUTOSUGGEST_FILE, {
        "jurisdictions": ["GUNTUR", "TENALI"],
        "trades": ["KIRANA STORE", "GOLD SHOP", "FERTILIZER"],
        "towns": ["TENALI", "GUNTUR", "REPALLE"],
        "villages": ["PERAVALI", "CHREBROLU"],
        "pins": ["522201", "522202"],
        "makes": ["E-SCALE", "CONTECH", "AVERY"],
        "models": ["STANDARD", "TABLETOP", "COUNTER"],
        "max_caps": ["30KG", "50KG", "100KG"],
        "min_caps": ["100G", "200G"],
        "accuracies": ["1G", "2G", "5G"],
        "classes": ["CLASS-III", "CLASS-II"],
        "mc_nos": []
    })

    # ---- 🧾 ట్యాబ్ 1: చల్లానా జనరేటర్ ----
    with tab_create:
        st.subheader("Challana Generator")
        
        if st.session_state.latest_pdf_path and os.path.exists(st.session_state.latest_pdf_path):
            st.success("🎉 PDF విజయవంతంగా క్రియేట్ అయింది!")
            with open(st.session_state.latest_pdf_path, "rb") as f:
                st.download_button(
                    label="📥 DOWNLOAD GENERATED CHALLANA PDF", 
                    data=f, 
                    file_name=os.path.basename(st.session_state.latest_pdf_path), 
                    mime="application/pdf", 
                    use_container_width=True, 
                    type="primary"
                )
            st.divider()

        history_records = load_json(HISTORY_FILE, [])
        user_bill_numbers = [int(r.get('bill_no', 0)) for r in history_records if r.get('username') == current_user.get('Username')]
        
        next_regular_bill = str(max(user_bill_numbers) + 1) if user_bill_numbers else "100"
        if not st.session_state.bill_no: 
            st.session_state.bill_no = next_regular_bill

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t3: manual_mode = st.checkbox("Manual Mode (Skip PDF)")
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
            
            # 1 & 2. Jurisdiction, Trade Type (Side-by-Side)
            final_jurisdiction = render_smart_input("Jurisdiction", sug.get("jurisdictions", []), "jur")
            final_trade = render_smart_input("Trade Type", sug.get("trades", []), "trd")

        # 3, 4 & 5. Town, Village, Pincode (Side-by-Side)
        col_b = st.columns(3)
        with col_b[0]: final_town = render_smart_input("Town", sug.get("towns", []), "twn")
        with col_b[1]: final_vlg = render_smart_input("Village", sug.get("villages", []), "vlg")
        with col_b[2]: final_pin = render_smart_input("Pincode", sug.get("pins", []), "pin")

        st.markdown("#### ⚖️ Weighing Scale Specifications")
        
        # 6 నుండి 11. కాటా స్పెసిఫికేషన్స్ (Side-by-Side)
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
        
        # 12. M/C No (Side-by-Side)
        final_mc = render_smart_input("Machine Serial No (M/C NO)", sug.get("mc_nos", []), "mc")

        # ---- ఐటెమ్ యాడ్ బటన్ రన్ లాజిక్ ----
        if st.button("➕ ADD ITEM TO CHALLANA LIST", use_container_width=True, type="secondary"):
            if not final_make or not final_model:
                st.error("❌ దయచేసి కనీసం Make మరియు Model వివరాలను టైప్ లేదా సెలెక్ట్ చేయండి!")
            else:
                # కొత్త వాల్యూస్ ని ఆటోసజెషన్ ఫైల్ లో అప్‌డేట్ చేయడం
                for k, v in [("makes", final_make), ("models", final_model), ("max_caps", final_max), 
                             ("min_caps", final_min), ("classes", final_class), ("accuracies", final_acc), ("mc_nos", final_mc)]:
                    if v and v not in sug[k]: sug[k].append(v)
                save_json(AUTOSUGGEST_FILE, sug)

                st.session_state.bill_items.append({
                    "no": str(len(st.session_state.bill_items) + 1), 
                    "make": final_make, "model": final_model, 
                    "max": final_max, "min": final_min, 
                    "acc": final_acc, "class": final_class, "mc_no": final_mc,
                    "stamping": str(item_stamping), "cc": str(item_cc), "new": str(item_new), 
                    "total": (item_stamping + item_cc + item_new)
                })
                
                # ఐటెమ్ యాడ్ అయ్యాక కాటా స్పెసిఫికేషన్ బాక్సులను మరియు ఆరోలని క్లియర్/రీసెట్ చేయడం
                for kp in ["mk", "md", "mx", "mn", "cls", "ac", "mc"]:
                    st.session_state[f"txt_{kp}"] = ""
                    st.session_state[f"sel_{kp}"] = "▼"
                st.success("🎯 Item Added to List!")
                st.rerun()

        # యాడ్ చేసిన ఐటెమ్స్ టేబుల్ ప్రదర్శన
        if st.session_state.bill_items:
            st.markdown("##### 📋 Current Added Items:")
            for idx, item in enumerate(st.session_state.bill_items):
                col_row1, col_row2 = st.columns([6, 1])
                col_row1.info(f"Item {idx+1}: {item['make']} | Max: {item['max']} | M/C No: {item['mc_no']} | Total: ₹{item['total']}/-")
                if col_row2.button("🗑️ Delete", key=f"del_{idx}"):
                    st.session_state.bill_items.pop(idx)
                    st.rerun()

        st.divider()
        
        # ---- చల్లానా సేవ్ చేసి బిల్ క్రియేట్ చేయడం ----
        if st.button("💾 GENERATE & SAVE CHALLANA", type="primary", use_container_width=True):
            if not st.session_state.cust_name: 
                st.error("❌ Please enter Customer Name!")
            elif not st.session_state.bill_items: 
                st.error("❌ Please add at least one item to the list!")
            elif not final_jurisdiction or not final_town:
                st.error("❌ Please enter Jurisdiction and Town details!")
            else:
                # లొకేషన్ రికార్డులను ఫ్యూచర్ లో వాడటానికి సేవ్ చేయడం
                for k, v in [("jurisdictions", final_jurisdiction), ("trades", final_trade), 
                             ("towns", final_town), ("villages", final_vlg), ("pins", final_pin)]:
                    if v and v not in sug[k]: sug[k].append(v)
                save_json(AUTOSUGGEST_FILE, sug)

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
                    st.session_state.latest_pdf_path = generate_challana_pdf(
                        st.session_state.bill_no, st.session_state.manual_date, final_jurisdiction, 
                        st.session_state.cust_name, final_trade, st.session_state.cust_pro, 
                        st.session_state.cust_area, final_town, final_vlg, final_pin, grand_total, current_user
                    )
                
                # రికార్డ్ సక్సెస్ అయ్యాక కస్టమర్ డేటా బాక్సులను క్లియర్/రీసెట్ చేయడం
                st.session_state.bill_no = str(int(st.session_state.bill_no) + 1) if st.session_state.bill_no.isdigit() else "101"
                st.session_state.cust_name, st.session_state.cust_phone, st.session_state.cust_pro, st.session_state.cust_area = "", "", "", ""
                st.session_state.bill_items = []
                for kp in ["jur", "trd", "twn", "vlg", "pin"]:
                    st.session_state[f"txt_{kp}"] = ""
                    st.session_state[f"sel_{kp}"] = "▼"
                    
                st.success("🎉 Challana Saved Successfully!")
                st.rerun()

    # ---- 📅 ట్యాబ్ 2: హిస్టరీ ----
    with tab_history:
        show_history_log_section()

    # ---- ⚙️ ట్యాబ్ 3: సెట్టింగ్స్ ----
    with tab_settings:
        st.markdown("### 🏪 Shop Settings")
        st.info("💡 ఇక్కడ మీ లోగో మరియు సంతకం మేనేజ్ చేసుకోవచ్చు.")