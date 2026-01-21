import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai

# 1. Setup AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🌱 AI Plant Parent")

# 2. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 3. Display Plants
for index, row in df.iterrows():
    with st.expander(f"{row['Plant Name']} ({row['Species']})"):
        st.write(f"Last Watered: {row['Last Watered']}")
        
        if st.button(f"Ask AI for {row['Plant Name']}"):
            prompt = f"I have a {row['Species']} in {row['Location']}. It was last watered on {row['Last Watered']}. Is it time to water it? Give a short answer."
            response = model.generate_content(prompt)
            st.info(response.text)
