import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

# 1. Setup AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_best_model():
    # Attempting to find the best available model
    for m_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(m_name)
            model.generate_content("test")
            return model, m_name
        except:
            continue
    return None, "None"

model, active_model_name = get_best_model()
# 2. Connection & Data Loading (MUST come before the title)
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="5m")
st.set_page_config(page_title="AI Plant Parent", page_icon="🌱")
st.title(f"🌱 AI Plant Parent ({len(df)})")

# Refresh button at the top
if st.button("🔄 Refresh AI Advice"):
    st.cache_data.clear()
    st.rerun()

# This displays the last time the AI actually ran
st.caption(f"AI Model: {active_model_name}")

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="5m")

# 3. AI Watering Decisions (Cached for 24 Hours)
@st.cache_data(ttl=86400)
def get_ai_decision(data_str):
    prompt = (
        f"Today is {date.today()}. Plants:\n{data_str}\n"
        "Identify which need water today. Return ONLY names separated by commas or 'None'."
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "None"

if not df.empty:
    st.subheader("🤖 Needs Water Today")
    
    # Generate decision based on current data
    plants_summary = df[['Plant Name', 'Last Watered Date']].to_string(index=False)
    decision = get_ai_decision(plants_summary)

    if "None" in decision or not decision:
        st.success("All plants are hydrated! ✨")
    else:
        needs_water_names = [n.strip() for n in decision.split(',')]
        today_str = date.today().strftime("%d/%m/%Y")

        for index, row in df.iterrows():
            if row['Plant Name'] in needs_water_names:
                with st.container(border=True):
                    # One-line mobile layout
                    cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                    with cols[0]:
                        st.markdown(f"**{row['Plant Name']}**")
                    with cols[1]:
                        if st.button("💧", key=f"w_{index}"):
                            df.at[index, 'Last Watered Date'] = today_str
                            conn.update(data=df)
                            st.cache_data.clear()
                            st.rerun()
                    with cols[2]:
                        if st.button("😴", key=f"s_{index}"):
                            st.toast(f"Snoozed {row['Plant Name']}")

# 4. Add New Plant (Inside Expander)
st.divider()
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_acq = st.date_input("Acquisition Date", format="DD/MM/YYYY")
        new_water = st.date_input("Last Watered Date", format="DD/MM/YYYY")
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                new_row = pd.DataFrame([{
                    "Plant Name": new_name, 
                    "Acquisition Date": new_acq.strftime("%d/%m/%Y"), 
                    "Last Watered Date": new_water.strftime("%d/%m/%Y")
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.cache_data.clear()
                st.rerun()
