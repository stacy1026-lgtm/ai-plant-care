import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

# 1. Setup AI (Automatic Discovery)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_best_model():
    for m_name in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(m_name)
            model.generate_content("test")
            return model, m_name
        except: continue
    return None, None

model, active_model_name = get_best_model()

st.set_page_config(page_title="AI Plant Parent", page_icon="🌱")
st.title("🌱 AI Plant Parent")

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# --- NEW PLANT FORM ---
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_acq = st.date_input("Acquisition Date", format="DD/MM/YYYY")
        new_water = st.date_input("Last Watered Date", format="DD/MM/YYYY")
        if st.form_submit_button("Add to Collection"):
            new_row = pd.DataFrame([{"Plant Name": new_name, "Acquisition Date": new_acq.strftime("%d/%m/%Y"), "Last Watered Date": new_water.strftime("%d/%m/%Y")}])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.rerun()

st.divider()

# --- AI FILTERING LOGIC ---
st.subheader("🤖 Needs Water Today (AI Choice)")
if not df.empty:
    plants_summary = df[['Plant Name', 'Last Watered Date']].to_string(index=False)
    ai_prompt = f"Today is {date.today()}. Plants:\n{plants_summary}\nIdentify which need water today based on species needs. Return ONLY names separated by commas or 'None'."
    
    response = model.generate_content(ai_prompt)
    decision = response.text.strip()

    if "None" in decision:
        st.success("All plants are hydrated! ✨")
    else:
        # Display Loop
        needs_water_names = [n.strip() for n in decision.split(',')]
        for index, row in df.iterrows():
            if row['Plant Name'] in needs_water_names:
                cols = st.columns([3, 1])
