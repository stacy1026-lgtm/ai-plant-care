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
        
st.subheader("🚿 Plants to Water")

today_str = date.today().strftime("%m/%d/%Y")

# 1. READ (ttl=0 ensures we don't see old data)
df = conn.read(ttl=0)

if not df.empty:
    # 2. SANITIZE (Prevents format mismatches)
    df['Last Watered Date'] = df['Last Watered Date'].astype(str).str.strip()
    df['Snooze Date'] = df.get('Snooze Date', pd.Series([""] * len(df))).astype(str).str.strip()

    # 3. FILTER
    mask = (df['Last Watered Date'] != today_str) & (df['Snooze Date'] != today_str)
    needs_action_df = df[mask]

    # 4. LOOP
if not needs_action_df.empty:
    for index, row in needs_action_df.iterrows():
        # Using st.container with border=True for a card look
        with st.container(border=True):
            # Higher ratio (12:1:1) forces buttons closer together
            cols = st.columns([10, .2,.2], gap="small")
            
            with cols[0]:
                st.write(f"🪴 **{row['Plant Name']}**")
            
            with cols[1]:
                if st.button("💧", key=f"w_{index}", help="Mark as Watered"):
                    df.at[index, 'Last Watered Date'] = today_str
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
                    
            with cols[2]:
                if st.button("😴", key=f"s_{index}", help="Snooze for Today"):
                    df.at[index, 'Snooze Date'] = today_str
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
else:
    st.success("All plants are watered or snoozed! ✨")
