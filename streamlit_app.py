import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

st.set_page_config(page_title="Plant Tracker", page_icon="🌱")
st.title("🌱 Mitzy's House Plant Garden")

# 1. Connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 2. Form to Add a New Plant
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
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Added {new_name}!")
                st.rerun()
            else:
                st.error("Please enter a name.")

st.divider()

st.subheader("🚿 Plants to Water")

today_str = date.today().strftime("%d/%m/%Y")

if not df.empty:
    # Filter out plants watered today OR snoozed today
    # (Checking if 'Snooze Date' matches today)
    mask = (df['Last Watered Date'] != today_str) & (df.get('Snooze Date') != today_str)
    needs_water_df = df[mask]

    if needs_water_df.empty:
        st.success("All plants are watered or snoozed! ✨")
    else:
        for index, row in needs_water_df.iterrows():
            cols = st.columns([2, 1, 1]) # Three columns now
            with cols[0]:
                st.write(f"🪴 **{row['Plant Name']}**")
            with cols[1]:
                if st.button("Watered", key=f"water_{index}"):
                    df.at[index, 'Last Watered Date'] = today_str
                    conn.update(data=df)
                    st.rerun()
            with cols[2]:
                if st.button("Snooze", key=f"snooze_{index}"):
                    df.at[index, 'Snooze Date'] = today_str
                    conn.update(data=df)
                    st.toast(f"Snoozed {row['Plant Name']} until tomorrow.")
                    st.rerun()
