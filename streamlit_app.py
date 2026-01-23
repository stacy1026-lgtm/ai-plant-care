import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

st.set_page_config(page_title="Plant Tracker", page_icon="🌱")
st.title("🌱 My Plant Garden")

# 1. Connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 2. Form to Add a New Plant
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_acq = st.date_input("Acquisition Date", format="MM/DD/YYYY")
        new_water = st.date_input("Last Watered Date", format="MM/DD/YYYY")
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                new_row = pd.DataFrame([{
                    "Plant Name": new_name, 
                    "Acquisition Date": new_acq.strftime("%m/%d/%Y"), 
                    "Last Watered Date": new_water.strftime("%m/%d/%Y")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Added {new_name}!")
                st.rerun()
            else:
                st.error("Please enter a name.")

st.divider()

st.subheader("🚿 Action Required")

today_str = date.today().strftime("%m/%d/%Y")

# 1. READ the full data
df = conn.read(ttl=0) 

# 2. FILTER for display, but KEEP the original index
today_str = date.today().strftime("%d/%m/%Y")
mask = (df['Last Watered Date'] != today_str) & (df.get('Snooze Date') != today_str)

# Filtered view for the loop
needs_action_df = df[mask]

if not needs_action_df.empty:
    for index, row in needs_action_df.iterrows():
        # 'index' here is the ORIGINAL row number from the Google Sheet
        cols = st.columns([2, 1, 1])
        with cols[0]:
            st.write(f"🪴 **{row['Plant Name']}**")
        with cols[1]:
            # Using the original index for the button key and the update
            if st.button("Watered", key=f"w_{index}"):
                # Update the ORIGINAL dataframe at the CORRECT row
                df.at[index, 'Last Watered Date'] = today_str
                conn.update(data=df)
                st.cache_data.clear()
                st.rerun()
