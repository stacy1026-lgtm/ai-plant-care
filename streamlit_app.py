import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import google.generativeai as genai

# 1. Setup
st.set_page_config(page_title="Plant Care", layout="centered")

# Configure Gemini API (Add 'GOOGLE_API_KEY' to your secrets)
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('models/gemini-1.5-flash')

st.title("🪴 Plant Care Tracker")

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="10m") # Cached for 10m to prevent API errors

# 3. Counts & Filtering
today_str = date.today().strftime("%d/%m/%Y")
total_plants = len(df) if not df.empty else 0

if not df.empty:
    df['Last Watered Date'] = df['Last Watered Date'].astype(str).str.strip()
    df['Snooze Date'] = df.get('Snooze Date', pd.Series([""] * len(df))).astype(str).str.strip()
    
    mask = (df['Last Watered Date'] != today_str) & (df['Snooze Date'] != today_str)
    needs_action_df = df[mask]

# 4. Header & AI Advice
st.markdown(f"### You have **{total_plants}** total plants")

@st.cache_data(ttl=86400) # Only runs once every 24 hours
def get_ai_advice(plants):
    if not plants:
        return "All plants are happy! No watering needed today."
    prompt = f"I have these plants that need watering today: {plants}. Give me one very brief, witty tip for caring for them."
    response = model.generate_content(prompt)
    return response.text

if not needs_action_df.empty:
    plant_list = ", ".join(needs_action_df['Plant Name'].tolist())
    advice = get_ai_advice(plant_list)
    st.info(advice) # Displays the AI advice in a blue box

    # 5. The Display Loop
    for index, row in needs_action_df.iterrows():
        with st.container(border=True):
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
                    df.at[index, 'Snooze Date'] = today_str
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
else:
    st.success("All plants are watered or snoozed! ✨")
