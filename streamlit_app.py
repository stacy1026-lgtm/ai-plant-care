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

# 3. Display Plants Needing Water Today
st.subheader("🚿 Plants to Water")

today_str = date.today().strftime("%d/%m/%Y")

# Filter: Only show plants that were NOT watered today
if not df.empty:
    needs_water_df = df[df['Last Watered Date'] != today_str]

    if needs_water_df.empty:
        st.success("All plants are watered for today! ✨")
    else:
        for index, row in needs_water_df.iterrows():
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(f"🪴 **{row['Plant Name']}** (Last: {row['Last Watered Date']})")
            with cols[1]:
                # Unique key prevents button conflicts
                if st.button("Watered", key=f"water_{index}"):
                    df.at[index, 'Last Watered Date'] = today_str
                    conn.update(data=df)
                    st.toast(f"Updated {row['Plant Name']}!")
                    st.rerun()
else:
    st.info("Your garden is empty. Add a plant above!")
