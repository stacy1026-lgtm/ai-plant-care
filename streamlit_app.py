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
# Note: These names must match your Google Sheet headers exactly (case-sensitive)
for index, row in df.iterrows():
    # Using 'Plant Name' as the header for the expander
    with st.expander(f"🪴 {row['Plant Name']}"):
        st.write(f"**Acquired on:** {row['Acquisition Date']}")
        st.write(f"**Last Watered:** {row['Last Watered Date']}")
        
        if st.button(f"Should I water {row['Plant Name']}?", key=index):
            # We tell the AI the name and date to help it decide
            prompt = (f"I have a plant named {row['Plant Name']}. "
                      f"It was last watered on {row['Last Watered Date']}. "
                      f"Based on its name, identify the species if possible and "
                      f"tell me if it needs water today. Give a short, friendly answer.")
            
            with st.spinner("Asking the AI..."):
                response = model.generate_content(prompt)
                st.info(response.text)
