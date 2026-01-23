import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

import streamlit as st
import google.generativeai as genai
from datetime import date

# 1. Setup AI with Error Logging
try:
    # Ensure this matches exactly in Streamlit Secrets
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Secret Key Missing: {e}")

@st.cache_resource
def get_best_model():
    # 2026 Compatible Model List
    test_models = [
        'gemini-2.0-flash',        # Try the newest first
        'gemini-1.5-flash-latest', # Try the stable latest
        'gemini-pro'               # Legacy fallback
    ]
    
    for m_name in test_models:
        try:
            m = genai.GenerativeModel(m_name)
            # A tiny test call to verify connection
            m.generate_content("test", generation_config={"max_output_tokens": 1})
            return m, m_name
        except Exception as e:
            # We skip and try the next model
            continue
            
    return None, "All Models Failed"

# Define variables clearly to avoid NameError
model, active_model_name = get_best_model()

# 2. Main App
st.title("🌱 AI Plant Parent")
st.caption(f"Status: {active_model_name}")

if active_model_name == "All Models Failed":
    st.error("Google AI is not responding. Please check your API Key in Google AI Studio.")

# 2. Assign the results
model, active_model_name = get_best_model()

# Now line 48 will never fail
st.caption(f"AI Model: {active_model_name}")

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

# ... (Keep your AI setup and data loading code above)

if not df.empty:
    st.subheader("🤖 Needs Water Today")
    
    plants_summary = df[['Plant Name', 'Last Watered Date']].to_string(index=False)
    decision = get_ai_decision(plants_summary)

    # DEBUG: See what the AI actually said (Remove this line once it works)
    st.write(f"DEBUG: AI says these need water: `{decision}`")

    if "None" in decision or not decision:
        st.success("All plants are hydrated! ✨")
    else:
        # 1. Clean the list from the AI (lowercase and strip spaces)
        needs_water_list = [n.strip().lower() for n in decision.split(',')]
        today_str = date.today().strftime("%d/%m/%Y")

        found_any = False
        for index, row in df.iterrows():
            # 2. Match using lowercase to avoid "Aloe" vs "aloe" errors
            if row['Plant Name'].strip().lower() in needs_water_list:
                found_any = True
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
                            st.toast(f"Snoozed {row['Plant Name']}")
        
        if not found_any:
            st.warning("AI suggested plants, but I couldn't find those names in your list. Check for typos!")

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
