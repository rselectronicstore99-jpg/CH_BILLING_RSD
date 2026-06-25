import streamlit as st
import json
from datetime import datetime

# బిల్ నంబర్ ఆటో-క్యాలిక్యులేట్ చేసే ఫంక్షన్
def update_next_bill_number():
    if st.session_state.user_history:
        bill_nos = []
        for b in st.session_state.user_history:
            try: bill_nos.append(int(b.get('bill_no', 0)))
            except: pass
        if bill_nos:
            st.session_state.bill_no = str(max(bill_nos) + 1)
            return
    st.session_state.bill_no = "100"

def show_billing_dashboard(current_user):
    username = current_user.get('Username', 'user')
    shop_name = current_user.get('Shop_Name', 'RS ELECTRONIC')
    
    st.title(f"🏪 {shop_name} Dashboard")
    st.markdown("---")
    
    # 📱 సైడ్‌బార్ - మొబైల్ డేటాబేస్ మేనేజ్‌మెంట్
    st.sidebar.markdown("## 📱 Mobile Database")
    
    if "user_history" not in st.session_state:
        st.session_state.user_history = []
        
    # 1. మొబైల్ నుండి పాత ఫైల్ అప్‌లోడ్
    uploaded_db = st.sidebar.file_uploader(
        "Upload backup file (.json) from Mobile", 
        type=["json"], 
        key="mobile_db_sync"
    )
    
    if uploaded_db is not None:
        try:
            st.session_state.user_history = json.load(uploaded_db)
            st.sidebar.success("🔋 Database Synced successfully!")
            update_next_bill_number()
        except:
            st.sidebar.error("Invalid JSON Database File!")
    else:
        if not st.session_state.user_history:
            st.sidebar.info("No Backup File loaded.")
            if st.sidebar.button("🆕 Start New fresh History Log", use_container_width=True):
                st.session_state.user_history = []
                st.session_state.bill_no = "100"
                st.sidebar.success("Fresh Log Started!")

    # 2. మొబైల్‌లోకి సేవ్ చేసుకునే బటన్
    if st.session_state.user_history:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📥 Backup & Sync")
        js_data = json.dumps(st.session_state.user_history, indent=4)
        st.sidebar.download_button(
            label="💾 Download & Save to Mobile",
            data=js_data,
            file_name=f"rs_history_{username}.json",
            mime="application/json",
            use_container_width=True,
            type="primary"
        )
        st.sidebar.caption(f"Total Saved Bills: {len(st.session_state.user_history)}")

    # --- బిల్లింగ్ GUI స్క్రీన్ ---
    screen = st.radio("Navigate Screen", ["Create Challana", "View History Log"], horizontal=True)
    
    if screen == "Create Challana":
        st.subheader(f"Generate New Challana (Bill No: {st.session_state.bill_no})")
        
        # కస్టమర్ వివరాలు
        c_name = st.text_input("Customer Name *", value=st.session_state.cust_name).upper()
        c_phone = st.text_input("Customer Phone", value=st.session_state.cust_phone)
        c_area = st.text_input("Customer Area/Town", value=st.session_state.cust_area).upper()
        
        st.markdown("---")
        st.markdown("#### Add Items to Bill")
        
        # తాత్కాలికంగా ఐటమ్స్ యాడ్ చేయడానికి ఇన్‌పుట్స్
        item_desc = st.text_input("Item Description (e.g., 32 Inch LED TV Display)").upper()
        item_qty = st.number_input("Quantity", min_value=1, step=1, value=1)
        item_price = st.number_input("Rate Per Item (₹)", min_value=0.0, step=100.0, value=0.0)
        
        if st.button("➕ Add Item to List", use_container_width=True):
            if not item_desc or item_price <= 0:
                st.error("Please enter Item Description and Rate!")
            else:
                st.session_state.bill_items.append({
                    "description": item_desc,
                    "qty": item_qty,
                    "rate": item_price,
                    "total": item_qty * item_price
                })
                st.success(f"Added {item_desc}!")
                st.rerun()
                
        # యాడ్ చేసిన ఐటమ్స్ టేబుల్ రూపంలో చూపించడం
        if st.session_state.bill_items:
            st.markdown("##### Current Items List:")
            grand_total = 0
            for idx, item in enumerate(st.session_state.bill_items):
                grand_total += item["total"]
                col_i1, col_i2, col_i3 = st.columns([5, 2, 1])
                col_i1.write(f"**{item['description']}** (Qty: {item['qty']} × ₹{item['rate']})")
                col_i2.write(f"₹{item['total']}")
                if col_i3.button("❌", key=f"del_item_{idx}"):
                    st.session_state.bill_items.pop(idx)
                    st.rerun()
            st.markdown(f"### 🧾 Grand Total: ₹{grand_total}")
            
            # ఫైనల్ బిల్ సేవ్ అండ్ జనరేట్
            if st.button("🚀 SAVE & DOWNLOAD PDF BILL", type="primary", use_container_width=True):
                if not c_name:
                    st.error("Customer Name is required to save bill!")
                else:
                    new_bill = {
                        "bill_no": st.session_state.bill_no,
                        "date": st.session_state.manual_date,
                        "customer_name": c_name,
                        "phone": c_phone,
                        "area": c_area,
                        "items": st.session_state.bill_items,
                        "grand_total": grand_total
                    }
                    
                    # 1. మొబైల్ మెమరీ లోకి రికార్డ్ యాడ్ అవుతుంది
                    st.session_state.user_history.append(new_bill)
                    
                    # 2. ఇక్కడ మీ పాత `pdf_history` లోని PDF క్రియేషన్ లాజిక్ ని రన్ చేయండి
                    # (గమనిక: పిడిఎఫ్ ని లోకల్ గా జనరేట్ చేసి st.download_button ద్వారా ఇక్కడ చూపించవచ్చు)
                    
                    st.success("✅ Bill Added Successfully to Memory!")
                    st.balloons()
                    
                    # ఇన్పుట్స్ రీసెట్
                    st.session_state.bill_items = []
                    update_next_bill_number()
                    st.warning("⚠️ దయచేసి సైడ్‌బార్‌లో ఉన్న 'Download & Save to Mobile' బటన్ నొక్కి మీ ఫైల్‌ను అప్‌డేట్ చేసుకోండి!")
                    st.utility_code = True
                    
    elif screen == "View History Log":
        st.subheader("📋 Past Challana History Records")
        if st.session_state.user_history:
            for idx, b in enumerate(reversed(st.session_state.user_history)):
                with st.expander(f"Bill No: {b.get('bill_no')} | {b.get('customer_name')} ({b.get('date')}) - ₹{b.get('grand_total', 0)}"):
                    st.write(f"**Phone:** {b.get('phone')} | **Area:** {b.get('area')}")
                    st.markdown("**Items Included:**")
                    for it in b.get('items', []):
                        st.write(f"- {it['description']} (Qty: {it['qty']} × ₹{it['rate']}) = ₹{it['total']}")
                    
                    if st.button("🗑️ Delete this Bill Record", key=f"delete_bill_{idx}"):
                        st.session_state.user_history.remove(b)
                        update_next_bill_number()
                        st.experimental_rerun()
        else:
            st.info("No data available. Please upload your mobile backup file (.json) to see past history log.")