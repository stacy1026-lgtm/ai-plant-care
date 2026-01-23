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
st.subheader("🤖 AI Watering Decisions")

if not df.empty:
    # 1. Prepare data for the AI
    plants_list = df[['Plant Name', 'Last Watered Date']].to_string(index=False)
    
    # 2. Craft the prompt
    ai_prompt = (
        f"Today is {date.today()}. Based on these plants and their last watering dates:\n"
        f"{plants_list}\n\n"
        "Identify which specific plants likely need water today. "
        "Consider typical houseplant needs (e.g., succulents need weeks, ferns need days). "
        "Return ONLY the names of plants that need water, separated by commas. "
        "If none, say 'None'."
    )

    # 3. Get AI Decision
    with st.spinner("AI is analyzing your garden..."):
        response = model.generate_content(ai_prompt)
        decision = response.text.strip()

    # 4. Filter and Display
    if "None" in decision:
        st.success("The AI thinks everyone is hydrated! ✨")
    else:
        # Convert AI string into a list of names
        needs_water_names = [name.strip() for name in decision.split(',')]
        
        # Display only those plants
        for name in needs_water_names:
            plant_row = df[df['Plant Name'] == name]
            if not plant_row.empty:
                with st.expander(f"💧 {name} "):
                    st.write(f"Last Watered: {plant_row.iloc[0]['Last Watered Date']}")
                    st.info(f"The AI suggests watering {name} based on its typical species requirements.")
