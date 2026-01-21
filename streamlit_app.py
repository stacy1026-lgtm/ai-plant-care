import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import date

# 1. Setup AI (Using st.secrets for safety)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Fail-safe model selection
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="AI Plant Parent", page_icon="🌱")
st.title("🌱 AI Plant Parent")

# 2. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# --- AI ASSISTANT SEARCH BAR ---
st.subheader("Ask about your garden")
user_query = st.text_input("Example: 'Which plants need water today?'")

if user_query:
    # Convert the spreadsheet into a text summary for the AI
    plant_data_summary = df.to_string(index=False)
    
    full_prompt = (
        f"Today's date is {date.today()}. Here is my plant collection data:\n"
        f"{plant_data_summary}\n\n"
        f"User Question: {user_query}\n"
        "Please provide a concise, helpful answer based ONLY on this data."
    )
    
    with st.spinner("AI is thinking..."):
        try:
            response = model.generate_content(full_prompt)
            st.success(response.text)
        except Exception as e:
            st.error(f"AI Query Failed: {e}")

st.divider()

# 3. Individual Plant View
st.subheader("Your Plant Collection")
for index, row in df.iterrows():
    # Matches your specific column names exactly
    with st.expander(f"🪴 {row['Plant Name']}"):
        st.write(f"**Acquisition Date:** {row['Acquisition Date']}")
        st.write(f"**Last Watered Date:** {row['Last Watered Date']}")
        
        if st.button(f"Ask about {row['Plant Name']}", key=f"btn_{index}"):
            individual_prompt = (
                f"I have a {row['Plant Name']}. It was last watered on {row['Last Watered Date']}. "
                f"Identify its likely species and tell me if I should water it today ({date.today()})."
            )
            with st.spinner("Checking..."):
                res = model.generate_content(individual_prompt)
                st.info(res.text)
