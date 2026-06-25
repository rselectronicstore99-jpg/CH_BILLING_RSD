import streamlit as st
import os
import json
from datetime import datetime
from pdf_history import generate_challana_pdf, show_history_log_section
from database import load_json, HISTORY_FILE, BASE_DIR

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
    స్మార్ట్ ఆటో-ఫిల్ ఇన్‌పుట్ సిస్టమ్:
    పాత డేటాను సెలెక్ట్ చేయగానే కింద ఉన్న టెక్స్ట్ బాక్స్ ఆటోమేటిక్‌గా నిండుతుంది.
    కొత్త డేటా అయితే నేరుగా అదే బాక్స్ లో టైప్ చేయవచ్చు.
    """
    clean_opts = sorted(list(set([str(x).strip().upper() for x in options_list if x])))
    
    txt_key = f"txt_{key_prefix}"
    sel_key = f"sel_{key_prefix}"
    
    if txt_key not in st.session_state:
        st.session_state[txt_key] = ""
        
    # డ్రాప్‌డౌన్ లో పాత వాల్యూ సెలెక్ట్ చేసినప్పుడు టెక్స్ట్ బాక్స్ ని అప్‌డేట్ చేసే లాజిక్
    def sync_sel_to_txt():
        picked = st.session_state[sel_key]
        if picked and picked != "-- Select Past --":
            st.session_state[txt_key] = picked

    # 1. పాత డేటా సెలెక్ట్ చేసుకునే చిన్న డ్రాప్‌డౌన్
    st.selectbox(
        f"📋 Past {label}", 
        ["-- Select Past --"] + clean_opts, 
        key=sel_key, 
        on_change=sync_sel_to_txt
    )
    
    # 2. మెయిన్ ఇన్‌పుట్ బాక్స్ (ఇందులోనే డేటా కనిపిస్తుంది లేదా కొత్తది టైప్ చేయవచ్చు)
    final_val = st.text_input(f"✍️ {label} *", key=txt_key).strip().upper()
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

    # 🌟 3 ట్యాబ్స్ సిస్టమ్
    tab_create, tab_history, tab_settings = st.tabs([
        "🧾 CREATE CHALLANA", 
        "📅 BILLING HISTORY", 
        "⚙️ SHOP SETTINGS"
    ])

    # ---- ఆటోసజెషన్ మెమరీ డేటా లోడ్ చేయడం ----
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

    # ---- 🧾 ట్యాబ్ 1: బిల్ జనరేటర్ ----
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
            
            # 1 & 2. Jurisdiction, Trade Type ఆటో-ఫిల్స్
            final_jurisdiction = render_smart_input("Jurisdiction", sug.get("jurisdictions", []), "jur")
            final_trade = render_smart_input("Trade Type", sug.get("trades", []), "trd")

        # 3, 4 & 5. Town, Village, Pincode ఆటో-ఫిల్స్
        col_b = st.columns(3)
        with col_b[0]: final_town = render_smart_input("Town", sug.get("towns", []), "twn")
        with col_b[1]: final_vlg = render_smart_input("Village", sug.get("villages", []), "vlg")
        with col_b[2]: final_pin = render_smart_input("Pincode", sug.get("pins", []), "pin")

        st.markdown("#### ⚖️ Weighing Scale Specifications")
        
        # 6 నుండి 11. కాటా స్పెసిఫికేషన్స్ ఆటో-ఫిల్స్
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
        
        # 12. M/C No ఆటో-ఫిల్
        final_mc = render_smart_input("Machine Serial No (M/C NO)", sug.get("mc_nos", []), "mc")

        # ---- ఐటెమ్ యాడ్ చేయడం ----
        if st.button("➕ ADD ITEM TO CHALLANA LIST", use_container_width=True, type="secondary"):
            if not final_make or not final_model:
                st.error("❌ దయచేసి కనీసం Make మరియు Model వివరాలను ఎంటర్ చేయండి!")
            else:
                # కొత్త వాల్యూస్ ని మెమరీ లోకి సేవ్ చేయడం
                for k, v, target in [("makes", final_make, "makes"), ("models", final_model, "models"), 
                                     ("max_caps", final_max, "max_caps"), ("min_caps", final_min, "min_caps"), 
                                     ("classes", final_class, "classes"), ("accuracies", final_acc, "accuracies"), 
                                     ("mc_nos", final_mc, "mc_nos")]:
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
                
                # ఐటెమ్ యాడ్ అయ్యాక కాటా బాక్సులను క్లియర్ చేయడం
                for key in ["txt_mk", "txt_md", "txt_mx", "txt_mn", "txt_cls", "txt_ac", "txt_mc"]:
                    st.session_state[key] = ""
                st.success("🎯 Item Added to List!")
                st.rerun()

        # యాడ్ అయిన ఐటెమ్స్ లిస్ట్
        if st.session_state.bill_items:
            st.markdown("##### 📋 Current Added Items:")
            for idx, item in enumerate(st.session_state.bill_items):
                col_row1, col_row2 = st.columns([6, 1])
                col_row1.info(f"Item {idx+1}: {item['make']} | Max: {item['max']} | M/C No: {item['mc_no']} | Fee: ₹{item['total']}/-")
                if col_row2.button("🗑️ Delete", key=f"del_{idx}"):
                    st.session_state.bill_items.pop(idx)
                    st.rerun()

        st.divider()
        
        # ---- చల్లానా ఫైనల్ సేవ్ చేయడం ----
        if st.button("💾 GENERATE & SAVE CHALLANA", type="primary", use_container_width=True):
            if not st.session_state.cust_name: 
                st.error("❌ Please enter Customer Name!")
            elif not st.session_state.bill_items: 
                st.error("❌ Please add at least one item to the list!")
            elif not final_jurisdiction or not final_town:
                st.error("❌ Please enter Jurisdiction and Town details!")
            else:
                # కస్టమర్ లొకేషన్ వివరాలను మెమరీ లోకి సేవ్ చేయడం
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
                
                # రికార్డ్ సేవ్ అయ్యాక కస్టమర్ బాక్సులను క్లియర్ చేయడం
                st.session_state.bill_no = str(int(st.session_state.bill_no) + 1) if st.session_state.bill_no.isdigit() else "101"
                st.session_state.cust_name, st.session_state.cust_phone, st.session_state.cust_pro, st.session_state.cust_area = "", "", "", ""
                st.session_state.bill_items = []
                for key in ["txt_jur", "txt_trd", "txt_twn", "txt_vlg", "txt_pin"]:
                    st.session_state[key] = ""
                    
                st.success("🎉 Challana Saved Successfully!")
                st.rerun()

    # ---- 📅 ట్యాబ్ 2: హిస్టరీ ----
    with tab_history:
        show_history_log_section()

    # ---- ⚙️ ట్యాబ్ 3: సెట్టింగ్స్ ----
    with tab_settings:
        st.markdown("### 🏪 Shop Settings")
        st.info("💡 ఇక్కడ లోగో మరియు సంతకం అప్‌లోడ్ చేసుకోవచ్చు.")