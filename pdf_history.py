import os
import urllib.parse
from datetime import datetime
import streamlit as st
from num2words import num2words
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from database import load_json, save_json, upload_to_drive, HISTORY_FILE, BASE_DIR

def draw_cell_text(canvas_obj, text, x, y, max_width, font_name="Helvetica-Bold", font_size=9.5):
    text = str(text).strip()
    canvas_obj.setFont(font_name, font_size)
    current_size = font_size
    while canvas_obj.stringWidth(text, font_name, current_size) > max_width and current_size > 7.0:
        current_size -= 0.5
    canvas_obj.setFont(font_name, current_size)
    while canvas_obj.stringWidth(text, font_name, current_size) > max_width and len(text) > 0:
        text = text[:-1]
    canvas_obj.drawString(x, y, text)

def import_history_to_session_callback(record):
    is_manual_mode_on = st.session_state.get("manual_mode_checkbox", False)
    
    if is_manual_mode_on:
        st.session_state.bill_no = record.get('bill_no', '')
        st.session_state.manual_date = record.get('date', '')
    else:
        st.session_state.bill_no = "" 
        st.session_state.manual_date = datetime.now().strftime('%d-%m-%Y')
    
    # కస్టమర్ వివరాల ఇంపోర్ట్
    st.session_state.cust_name = record.get('name', '')
    st.session_state.cust_phone = record.get('phone', '')
    st.session_state.cust_pro = record.get('pro', '')
    st.session_state.cust_area = record.get('area', '')
    st.session_state.bill_items = record.get('items', [])
    
    # లొకేషన్ బాక్సుల వివరాలు
    st.session_state.txt_jur = record.get('jurisdiction', '')
    st.session_state.txt_trd = record.get('trade', '')
    st.session_state.txt_twn = record.get('town', '')
    st.session_state.txt_vlg = record.get('vlg', '')
    st.session_state.txt_pin = record.get('pin', '')
    
    # ✨ [NEW FEATURE IMPORT]: సబ్ క్లయింట్ పేరు కూడా ఆటో లోడ్ అవుతుంది
    st.session_state.txt_sub = record.get('sub_client', '')
    
    # మొదటి ఐటెమ్ యొక్క స్పెసిఫికేషన్ వివరాలు
    items_list = record.get('items', [])
    if items_list:
        first_item = items_list[0]
        st.session_state.txt_mk = first_item.get('make', '')
        st.session_state.txt_md = first_item.get('model', '')
        st.session_state.txt_mx = first_item.get('max', '')
        st.session_state.txt_mn = first_item.get('min', '')
        st.session_state.txt_cls = first_item.get('class', '')
        st.session_state.txt_ac = first_item.get('acc', '')
        st.session_state.txt_mc = first_item.get('mc_no', '')
    
    for kp in ["jur", "trd", "twn", "vlg", "pin", "mk", "md", "mx", "mn", "cls", "ac", "mc", "sub"]:
        st.session_state[f"sel_{kp}"] = "▼"
        
    st.session_state.import_success_trigger = True


# 📄 pdf_history.py లో ఈ ఫంక్షన్‌ను అప్‌డేట్ చేయండి
def show_history_log_section():
    st.markdown("### 📅 Filter & Search History Logs")
    all_records = load_json(HISTORY_FILE, [])
    
    # 🔒 ఇంకొక పద్ధతి: డైరెక్ట్‌గా స్ట్రీమ్‌లిట్ గ్లోబల్ మెమొరీ నుండి యూజర్‌ను పట్టుకోవడం
    logged_in_user = ""
    
    # మీ యాప్‌లో లాగిన్ ఐడి ఏ పేరుతో సేవ్ అయిందో అన్నింటినీ ఇక్కడ చెక్ చేస్తుంది
    if "user_profile" in st.session_state and st.session_state.user_profile:
        logged_in_user = str(st.session_state.user_profile.get('Username', '')).strip().upper()
    elif "username" in st.session_state:
        logged_in_user = str(st.session_state.username).strip().upper()
    elif "user_id" in st.session_state:
        logged_in_user = str(st.session_state.user_id).strip().upper()

    # 🛠️ టెంపరరీ డిబగ్గర్ (యాప్ కరెక్ట్‌గా పనిచేసాక ఈ కింద లైన్ తీసేయవచ్చు)
    # st.sidebar.write(f"Logged in as: `{logged_in_user}`")

    # 🛡️ సెక్యూరిటీ ఫిల్టర్: ఒకవేళ అడ్మిన్ కాకపోతే, కేవలం ఆ క్లయింట్ బిల్లులు మాత్రమే చూపిస్తుంది
    if logged_in_user and logged_in_user != "ADMIN":
        history_records = [
            r for r in all_records 
            if str(r.get('username') or r.get('Username') or r.get('user_id') or '').strip().upper() == logged_in_user
        ]
    else:
        # ఒకవేళ ADMIN లాగిన్ అయితే అందరి డేటా కనిపిస్తుంది
        history_records = all_records
    
    # --- ఇక్కడి నుండి మిగతా కోడ్ అంతా మామూలే ---
    if st.session_state.get("import_success_trigger"):
        st.success("🎉 డేటా విజయవంతంగా ఇంపోర్ట్ చేయబడింది! దయచేసి 'CREATE CHALLANA' ట్యాబ్ ఓపెン చేసి చూడండి.")
        st.session_state.import_success_trigger = False
    
    if not history_records:
        st.info("ఈ ఆర్థిక సంవత్సరానికి ఎటువంటి హిస్టరీ డేటా రికార్డ్ అవ్వలేదు.")
        return

    alert_templates = [
        "Dear Customer, your weighing scale stamping renewal is due. Please contact immediately.",
        "నమస్కారం, మీ షాప్ కాటా ముద్ర గడువు ముగియనుంది. త్వరగా రిన్యూవల్ చేసుకోగలరు."
    ]

    default_start_date = datetime.now().date()
    if history_records:
        parsed_dates = []
        for record in history_records:
            try:
                d = datetime.strptime(record.get('date', ''), '%d-%m-%Y').date()
                parsed_dates.append(d)
            except: pass
        if parsed_dates: default_start_date = min(parsed_dates)

    col_d1, col_d2 = st.columns(2)
    with col_d1: start_date = st.date_input("From Date", value=default_start_date)
    with col_d2: end_date = st.date_input("To Date", value=datetime.now().date())
        
    user_subs = sorted(list(set([
        str(r.get('sub_client', '')).strip().upper() 
        for r in history_records if r.get('sub_client')
    ])))
    filter_sub = st.selectbox("🗂️ Filter by SUB Account (Salesman)", ["ALL SUB CUSTOMERS"] + user_subs)

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: search_name = st.text_input("👤 Search Customer Name").strip().upper()
    with col_s2: search_phone = st.text_input("📞 Search Phone Number").strip()
    with col_s3: search_bill = st.text_input("🧾 Search Bill Number").strip()
        
    filtered_records = []
    is_searching = bool(search_name or search_phone or search_bill)

    for record in history_records:
        if filter_sub != "ALL SUB CUSTOMERS":
            if str(record.get('sub_client', '')).strip().upper() != filter_sub: continue
            
        if not is_searching:
            try:
                rec_date = datetime.strptime(record.get('date', ''), '%d-%m-%Y').date()
                if not (start_date <= rec_date <= end_date): continue
            except: pass
            
        if search_name and search_name not in record.get('name', '').upper(): continue
        if search_phone and search_phone not in record.get('phone', ''): continue
        if search_bill and search_bill not in record.get('bill_no', ''): continue
        filtered_records.append(record)
            
    st.markdown(f"🔍 లభించిన రికార్డులు: **{len(filtered_records)}**")
    tab1, tab2 = st.tabs(["📋 DETAILED HISTORY LOGS", "📲 QUICK WHATSAPP LIST"])
    
    with tab1:
        for idx, record in enumerate(reversed(filtered_records)):
            sub_label = f" | SUB: {record.get('sub_client')}" if record.get('sub_client') else ""
            with st.expander(f"🧾 Bill: {record.get('bill_no')} | {record.get('date')} | {record.get('name')} | ₹{record.get('total')}/-{sub_label}"):
                st.write(f"📍 **Address:** {record.get('town')}, {record.get('vlg')} ({record.get('pin')}) | 📞 **Phone:** {record.get('phone')}")
                st.table(record.get('items', []))
                
                chosen_template = st.selectbox("Select Alert Message", alert_templates, key=f"tpl_{idx}")
                wa_url = f"https://wa.me/91{record.get('phone')}?text={urllib.parse.quote(chosen_template)}"
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.button(
                        "📥 IMPORT THIS DATA TO MAIN GUI", 
                        key=f"imp_{idx}", 
                        type="primary", 
                        use_container_width=True,
                        on_click=import_history_to_session_callback,
                        args=(record,)
                    )
                with col_b2:
                    st.link_button("📲 SEND WHATSAPP REMINDER", wa_url, use_container_width=True)

    with tab2:
        st.markdown("#### ⚡ Fast WhatsApp Reminder Panel")
        global_template = st.selectbox("Select Message Template for List", alert_templates, key="global_wa_tpl")
        for idx, record in enumerate(reversed(filtered_records)):
            col1, col2, col3, col4, col5 = st.columns([1.2, 2.5, 1.5, 1.5, 1.5])
            col1.write(record.get('date', ''))
            col2.write(record.get('name', ''))
            col3.write(record.get('phone', ''))
            col4.write(record.get('town', ''))
            quick_wa_url = f"https://wa.me/91{record.get('phone')}?text={urllib.parse.quote(global_template)}"
            col5.link_button("📲 SEND WA", quick_wa_url, use_container_width=True, key=f"qwa_{idx}")

def generate_challana_pdf(bill_no, bill_date, final_jurisdiction, cust_name, final_trade, cust_pro, cust_area, final_town, final_vlg, final_pin, grand_total, current_user):
    pdf_filename = os.path.join(BASE_DIR, f"CH_{bill_no}.pdf")
    canvas_obj = canvas.Canvas(pdf_filename, pagesize=landscape(A4))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.setStrokeColorRGB(0.6, 0.6, 0.6)
    canvas_obj.line(421, 15, 421, 580)
    
    username = current_user.get('Username', '').strip()
    user_logo_path = None
    if username:
        for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
            p = os.path.join(BASE_DIR, f"{username}_logo{ext}")
            if os.path.exists(p):
                user_logo_path = p
                break

    user_sign_path = None
    if username:
        for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
            p = os.path.join(BASE_DIR, f"{username}_sign{ext}")
            if os.path.exists(p):
                user_sign_path = p
                break
    
    for offset in [0, 421]:
        canvas_obj.setLineWidth(1.2)
        canvas_obj.rect(15 + offset, 15, 390, 565)
        canvas_obj.setLineWidth(1)
        
        if user_logo_path and os.path.exists(user_logo_path):
            try: canvas_obj.drawImage(user_logo_path, 22 + offset, 515, width=50, height=45, mask='auto')
            except: pass
        
        canvas_obj.setFont("Helvetica-Bold", 14)
        canvas_obj.drawCentredString(210 + offset, 562, "CHALLANA")
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawRightString(395 + offset, 552, f"LIC NO: {current_user.get('Lic_1', '')}")
        canvas_obj.drawRightString(395 + offset, 541, f"CELL NO: {current_user.get('Phone_No', '')}")
        
        canvas_obj.setFont("Helvetica-Bold", 12)
        canvas_obj.drawCentredString(210 + offset, 515, current_user.get('Shop_Name', 'RS ELECTRONIC STORE'))
        canvas_obj.setFont("Helvetica-Bold", 7.5)
        canvas_obj.drawCentredString(210 + offset, 503, "GOVT. LICENCE TO REPAIRER OF ELECTRONIC WEIGHING INSTRUMENTS")
        
        canvas_obj.setFont("Helvetica", 7.5)
        shop_addr1 = str(current_user.get('Address_Line1', '')).upper().strip()
        shop_addr2 = str(current_user.get('Address_Line2', '')).upper().strip()
        if shop_addr1 and shop_addr2:
            canvas_obj.drawCentredString(210 + offset, 492, shop_addr1)
            canvas_obj.drawCentredString(210 + offset, 483, shop_addr2)
        elif shop_addr1:
            canvas_obj.drawCentredString(210 + offset, 488, shop_addr1)
            
        canvas_obj.line(15 + offset, 474, 405 + offset, 474)
        canvas_obj.setFont("Helvetica-Bold", 9.5)
        canvas_obj.drawString(25 + offset, 459, f"NO: {bill_no}")
        canvas_obj.drawCentredString(210 + offset, 459, f"DATE: {bill_date}")
        canvas_obj.drawRightString(395 + offset, 459, "CUSTOMER COPY" if offset == 0 else "OFFICE COPY")
        
        canvas_obj.rect(25 + offset, 424, 370, 22)
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(30 + offset, 431, f"To: THE ASSISTANT CONTROLLER, LEGAL METROLOGY, {final_jurisdiction}.")
        
        canvas_obj.rect(25 + offset, 364, 370, 52)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(30 + offset, 404, f"M/S: {cust_name} ({final_trade})")
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(30 + offset, 391, f"PRO/C/O: {cust_pro} | AREA: {cust_area}")
        canvas_obj.drawString(30 + offset, 378, f"TOWN: {final_town} | VILLAGE: {final_vlg} | PIN: {final_pin}")
        
        canvas_obj.setFont("Helvetica-Oblique", 8)
        canvas_obj.drawCentredString(210 + offset, 352, "Sir, please verify, and STAMP the following Electronic Weighing Instruments:")
        
        table_top, col_widths = 342, [20, 45, 45, 30, 25, 25, 35, 75, 70]
        cols_x = [25 + offset]
        for w in col_widths: cols_x.append(cols_x[-1] + w)
            
        canvas_obj.setStrokeColorRGB(0, 0, 0)
        canvas_obj.setLineWidth(0.8)
        
        header_height = 18
        header_bottom = table_top - header_height
        canvas_obj.line(25 + offset, table_top, 395 + offset, table_top)
        canvas_obj.line(25 + offset, header_bottom, 395 + offset, header_bottom)
        for cx in cols_x: canvas_obj.line(cx, table_top, cx, header_bottom)
            
        canvas_obj.setFont("Helvetica-Bold", 8)
        headers = ["NO", "MAKE", "MODEL", "MAX", "MIN", "ACC", "CLASS", "M/C NO", "FEE DETAILS"]
        for h_idx, text in enumerate(headers): canvas_obj.drawString(cols_x[h_idx] + 3, header_bottom + 5, text)
            
        row_height = 35
        fixed_rows_count = 6
        
        for idx in range(fixed_rows_count):
            current_row_top = header_bottom - (idx * row_height)
            current_row_bottom = current_row_top - row_height
            canvas_obj.line(25 + offset, current_row_bottom, 395 + offset, current_row_bottom)
            for cx in cols_x: canvas_obj.line(cx, current_row_top, cx, current_row_bottom)
                
            fee_col_start = cols_x[8]
            fee_col_end = 395 + offset
            canvas_obj.line(fee_col_start, current_row_top - 8.5, fee_col_end, current_row_top - 8.5)
            canvas_obj.line(fee_col_start, current_row_top - 17, fee_col_end, current_row_top - 17)
            canvas_obj.line(fee_col_start, current_row_top - 25.5, fee_col_end, current_row_top - 25.5)
            
            if idx < len(st.session_state.bill_items):
                item = st.session_state.bill_items[idx]
                text_y = current_row_top - 21
                draw_cell_text(canvas_obj, item.get('no', ''), cols_x[0]+3, text_y, col_widths[0]-4, font_size=7.5)
                draw_cell_text(canvas_obj, item.get('make', ''), cols_x[1]+3, text_y, col_widths[1]-4, font_size=7.5)
                draw_cell_text(canvas_obj, item.get('model', ''), cols_x[2]+3, text_y, col_widths[2]-4, font_size=7.5)
                draw_cell_text(canvas_obj, item.get('max', ''), cols_x[3]+3, text_y, col_widths[3]-4, font_size=7.5)
                draw_cell_text(canvas_obj, item.get('min', ''), cols_x[4]+3, text_y, col_widths[4]-4, font_size=7.5)
                draw_cell_text(canvas_obj, item.get('acc', ''), cols_x[5]+3, text_y, col_widths[5]-4, font_size=7.5)
                draw_cell_text(canvas_obj, item.get('class', ''), cols_x[6]+3, text_y, col_widths[6]-4, font_size=7.5)
                
                mc_text = str(item.get('mc_no', ''))
                if ',' in mc_text: mc_lines = [line.strip() for line in mc_text.split(',')]
                else: mc_lines = [mc_text[i:i+12].strip() for i in range(0, len(mc_text), 12)]
                mc_lines = [l for l in mc_lines if l][:3]
                for m_idx, line_text in enumerate(mc_lines):
                    draw_cell_text(canvas_obj, line_text, cols_x[7]+3, current_row_top - 6.5 - (m_idx * 8.5), col_widths[7]-4, font_size=7)
                    
                try: stamping_val = f"{float(item.get('stamping', 0)):.2f}"
                except: stamping_val = "0.00"
                try: sistu_val = f"{float(item.get('new', 0)):.2f}"
                except: sistu_val = "0.00"
                try: cc_val = f"{float(item.get('cc', 0)):.2f}"
                except: cc_val = "0.00"
                try: total_val = f"{float(item.get('total', 0)):.2f}"
                except: total_val = "0.00"
                
                draw_cell_text(canvas_obj, f"STAMPING: {stamping_val}", fee_col_start+3, current_row_top - 6.5, col_widths[8]-4, font_size=6.5)
                draw_cell_text(canvas_obj, f"SISTU: {sistu_val}", fee_col_start+3, current_row_top - 15, col_widths[8]-4, font_size=6.5)
                draw_cell_text(canvas_obj, f"C. C: {cc_val}", fee_col_start+3, current_row_top - 23.5, col_widths[8]-4, font_size=6.5)
                draw_cell_text(canvas_obj, f"TOTAL: {total_val}", fee_col_start+3, current_row_top - 32, col_widths[8]-4, font_size=6.5)
                
        y_total = header_bottom - (fixed_rows_count * row_height) - 15
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(25 + offset, y_total, f"GRAND TOTAL: Rs. {grand_total:.2f}/-")
        try:
            words = num2words(int(grand_total)).upper() + " ONLY"
            canvas_obj.setFont("Helvetica-Oblique", 6.5)
            canvas_obj.drawString(25 + offset, y_total - 10, f"In Words: {words}")
        except: pass
        
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawRightString(395 + offset, y_total - 25, f"For {current_user.get('Shop_Name', 'RS ELECTRONIC STORE')}")
        if user_sign_path and os.path.exists(user_sign_path):
            try: canvas_obj.drawImage(user_sign_path, 310 + offset, y_total - 52, width=70, height=25, mask='auto')
            except: pass
        canvas_obj.drawRightString(395 + offset, y_total - 60, "Authorized Signatory")
        
    canvas_obj.save()
    upload_to_drive(pdf_filename)
    return pdf_filename