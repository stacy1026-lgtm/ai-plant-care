import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import date

# 1. Setup AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# AUTOMATIC MODEL DISCOVERY: This finds which model your key actually supports
@st.cache_resource
def get_best_model():
    # Recommended models for 2026
    preferred_models = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
    for m_name in preferred_models:
        try:
            model = genai.GenerativeModel(m_name)
            model.generate_content("test") # quick check
            return model, m_name
        except:
            continue
    return genai.GenerativeModel('gemini-pro'), "gemini-pro"

model, active_model_name = get_best_model()

st.set_page_config(page_title="AI Plant Parent", page_icon="🌱")
st.title("🌱 AI Plant Parent")
st.caption(f"Connected via: {active_model_name}")

# 2. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# --- AI ASSISTANT SEARCH BAR ---
st.subheader("Ask about your garden")
user_query = st.text_input("Example: 'Which plants need water today?'")

if user_query:
    plant_data_summary = df.to_string(index=False)
    full_prompt = (
        f"Today's date is {date.today()}. My plants:\n{plant_data_summary}\n\n"
        f"User Question: {user_query}\n"
        "Provide a concise, helpful answer."
    )
    
    with st.spinner("AI is thinking..."):
        try:
            response = model.generate_content(full_prompt)
            st.success(response.text)
        except Exception as e:
            st.error(f"AI Error: {e}")

st.divider()

# 3. Individual Plant View
st.subheader("Your Plant Collection")
for index, row in df.iterrows():
    with st.expander(f"🪴 {row['Plant Name']}"):
        st.write(f"**Acquired:** {row['Acquisition Date']}")
        st.write(f"**Last Watered:** {row['Last Watered Date']}")
        
        if st.button(f"Analyze {row['Plant Name']}", key=f"btn_{index}"):
            with st.spinner("Checking..."):
                res = model.generate_content(f"I have a {row['Plant Name']} last watered {row['Last Watered Date']}. Advice?")
                st.info(res.text)
