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

if not df.empty:
    # 1. THE FILTER: Only keep rows where:
    #    - Last Watered is NOT today AND
    #    - Snooze Date is NOT today
    mask = (df['Last Watered Date'] != today_str) & (df.get('Snooze Date') != today_str)
    needs_action_df = df[mask]

    if needs_action_df.empty:
        st.success("Your work here is done! ✨")
    else:
        for index, row in needs_action_df.iterrows():
            cols = st.columns([2, 1, 1])
            with cols[0]:
                st.write(f"🪴 **{row['Plant Name']}**")
            with cols[1]:
                if st.button("Watered", key=f"w_{index}"):
                    df.at[index, 'Last Watered Date'] = today_str
                    conn.update(data=df)
                    st.rerun()
            with cols[2]:
                if st.button("Snooze", key=f"s_{index}"):
                    df.at[index, 'Snooze Date'] = today_str
                    conn.update(data=df)
                    st.rerun()
