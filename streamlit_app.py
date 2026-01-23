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
# --- NEW PLANT FORM ---
st.divider()
st.subheader("➕ Add a New Plant")

with st.form("new_plant_form", clear_on_submit=True):
    new_name = st.text_input("Plant Name")
    
    # Add format="DD/MM/YYYY" to both date inputs
    new_acq_date = st.date_input("Acquisition Date", value=date.today(), format="MM/DD/YYYY")
    new_water_date = st.date_input("Last Watered Date", value=date.today(), format="MM/DD/YYYY")
    
    submit_new_plant = st.form_submit_button("Add to Collection")

if submit_new_plant:
    if new_name:
        # 1. Create a single-row DataFrame for the new plant
        import pandas as pd
        new_row = pd.DataFrame([{
            "Plant Name": new_name,
            "Acquisition Date": str(new_acq_date),
            "Last Watered Date": str(new_water_date)
        }])
        
        # 2. Combine with existing data
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # 3. Push back to Google Sheets
        conn.update(data=updated_df)
        
        st.success(f"Added {new_name} to your garden! 🌱")
        st.rerun()
    else:
        st.warning("Please enter a plant name.")            

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
