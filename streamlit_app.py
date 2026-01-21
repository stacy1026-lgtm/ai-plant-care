import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from datetime import date

# 1. Setup AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# Try the most common stable name
try:
    model = genai.GenerativeModel('gemini-1.5-pro')
except:
    model = genai.GenerativeModel('gemini-pro')

# Add this temporarily to check if the AI is alive
try:
    test_response = model.generate_content("Hi")
    st.write("AI Connection: Success ✅")
except Exception as e:
    st.error(f"AI Connection Failed: {e}")

st.set_page_config(page_title="AI Plant Parent", page_icon="🌱")
st.title("🌱 AI Plant Parent")

# 2. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# --- NEW: AI ASSISTANT SEARCH BAR ---
st.subheader("Ask about your garden")
user_query = st.text_input("Example: 'Which plants need water today?' or 'Summarize my collection'")

if user_query:
    # Convert the spreadsheet into a text format the AI can read
    plant_data_summary = df.to_string(index=False)
    
    full_prompt = (
        f"Today's date is {date.today()}. Here is a list of my plants:\n"
        f"{plant_data_summary}\n\n"
        f"User Question: {user_query}\n"
        "Please provide a concise, helpful answer based ONLY on the data provided."
    )
    
    with st.spinner("AI is thinking..."):
        response = model.generate_content(full_prompt)
        st.success(response.text)

st.divider()

# 3. Individual Plant View (Existing feature)
st.subheader("Your Plant Collection")
for index, row in df.iterrows():
    with st.expander(f"🪴 {row['Plant Name']}"):
        st.write(f"**Acquisition Date:** {row['Acquisition Date']}")
        st.write(f"**Last Watered:** {row['Last Watered Date']}")
        
        if st.button(f"Ask about {row['Plant Name']}", key=f"btn_{index}"):
            prompt = (f"I have a plant named {row['Plant Name']}. "
                      f"Last watered: {row['Last Watered Date']}. Should I water it?")
            response = model.generate_content(prompt)
            st.info(response.text)
