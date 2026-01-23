import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

# 1. Setup & AI Config
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_best_model():
    for m_name in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(m_name)
            model.generate_content("test")
            return model, m_name
        except: continue
    return None, "None"

model, active_model_name = get_best_model()

# 2. Connection & Data
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="5m")
today_str = date.today().strftime("%d/%m/%Y")

# 3. 24-Hour Cached AI Decision
@st.cache_data(ttl=86400) # Only runs once every 24 hours
def get_daily_watering_list(plants_summary):
    prompt = (
        f"Today is {date.today()}. Based on these plants and last watered dates:\n{plants_summary}\n"
        "Identify which need water today. Return ONLY names separated by commas or 'None'."
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "None"

# --- UI Layout ---
st.title(f"🌱 AI Plant Parent ({len(df)})")
st.caption(f"AI Model: {active_model_name}")

if not df.empty:
    plants_summary = df[['Plant Name', 'Last Watered Date']].to_string(index=False)
    decision = get_daily_watering_list(plants_summary)
    
    st.subheader("🤖 Needs Water Today")
    
    if "None" in decision or not decision:
        st.success("The AI thinks everyone is hydrated! ✨")
    else:
        needs_water_names = [n.strip() for n in decision.split(',')]
        
        for index, row in df.iterrows():
            if row['Plant Name'] in needs_water_names:
                # Optimized Mobile Row
                with st.container(border=True):
                    cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                    
                    with cols[0]:
                        st.markdown(f"**{row['Plant Name']}**")
                    
                    with cols[1]:
                        if st.button("💧", key=f"w_{index}"):
                            df.at[index, 'Last Watered Date'] = today_str
                            conn.update(data=df)
                            st.cache_data.clear() # Clear cache to refresh list
                            st.rerun()
                            
                    with cols[2]:
                        # Assuming you have/want a snooze or info button
                        if st.button("😴", key=f"s_{index}"):
                            st.toast(f"Snoozed {row['Plant Name']}")

# ... (Keep your 'Add New Plant' form below this) ...
