import streamlit as st
import database as db

def shop_registration_screen(system_id):
    st.markdown("<h2 style='text-align: center;'>🏪 RS Electronic Ultimate</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>కొత్త రిజిస్ట్రేషన్ (7 Days Free Trial)</p>", unsafe_allow_html=True)
    
    st.info(f"🤖 మీ సిస్టమ్ నంబర్: `{system_id}`\n\n(భవిష్యత్తులో యాప్ ఓపెన్ చేయడానికి ఈ నంబర్ అవసరం, దీన్ని నోట్ చేసుకోండి!)")
    
    with st.form("registration_form"):
        shop_name = st.text_input("మీ షాప్ పేరు (Shop Name) *").upper().strip()
        phone = st.text_input("మొబైల్ నంబర్ (Phone Number) *").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            lic_1 = st.text_input("లైసెన్స్ నంబర్ 1 *").upper().strip()
        with col2:
            lic_2 = st.text_input("లైసెన్స్ నంబర్ 2 (Optional)").upper().strip()
            
        addr_1 = st.text_input("అడ్రస్ లైన్ 1 *").upper().strip()
        addr_2 = st.text_input("అడ్రస్ లైన్ 2 *").upper().strip()
        
        submit_btn = st.form_submit_button("💾 Save Profile Details & Open App", type="primary", use_container_width=True)
        
        if submit_btn:
            if not shop_name or not phone or not lic_1 or not addr_1 or not addr_2:
                st.error("⚠️ దయచేసి స్టార్ (*) గుర్తు ఉన్న వివరాలన్నీ తప్పకుండా నింపండి!")
            else:
                with st.spinner("🔄 గూగుల్ షీట్ లో రికార్డ్ సేవ్ అవుతోంది..."):
                    success = db.register_system_customer(system_id, shop_name, phone, lic_1, lic_2, addr_1, addr_2)
                    if success:
                        st.success("🎉 ప్రొఫైల్ సేవ్ అయింది! 7 రోజుల ట్రయల్ యాక్టివేట్ చేయబడింది.")
                        st.rerun()

def trial_expired_screen(system_id):
    st.error("⏳ మీ 7 రోజుల ఉచిత ట్రయల్ గడువు ముగిసింది!")
    st.warning(f"యాప్‌ను లైఫ్‌టైమ్ యాక్టివేట్ చేయడానికి దయచేసి RS Electronic డెవలపర్‌ను సంప్రదించండి.\n\n🤖 మీ సిస్టమ్ నంబర్: `{system_id}`")
    
    input_key = st.text_input("లైసెన్స్ కీ ఇక్కడ ఎంటర్ చేయండి (Enter Activation Key):").strip()
    if st.button("యాక్టివేట్ చేయి (Activate App)", type="primary", use_container_width=True):
        if db.activate_lifetime_license(system_id, input_key):
            st.success("🎉 అభినందనలు! మీ యాప్ లైఫ్‌టైమ్ యాక్టివేట్ చేయబడింది.")
            st.rerun()
        else:
            st.error("❌ తప్పుడు లైసెన్స్ కీ! దయచేసి సరైన కీ ని ఇవ్వండి.")