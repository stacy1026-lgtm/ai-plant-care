import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime, timedelta
import pandas as pd

# 1. Setup & Data Loading
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# Ensure 'Frequency' column exists (defaulting to 7 days if missing)
if not df.empty and 'Frequency' not in df.columns:
    df['Frequency'] = 7

total_plants = len(df) if not df.empty else 0
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# 2. Header
st.title("🪴 My Plant Garden")
st.markdown(f"### You have **{total_plants}** total plants")

# 3. Add New Plant
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_freq = st.number_input("Watering Frequency (Days)", min_value=1, value=7)
        new_acq = st.date_input("Acquisition Date", format="MM/DD/YYYY")
        new_water = st.date_input("Last Watered Date", format="MM/DD/YYYY")
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                new_row = pd.DataFrame([{
                    "Plant Name": new_name, 
                    "Frequency": int(new_freq),
                    "Acquisition Date": new_acq.strftime("%m/%d/%Y"), 
                    "Last Watered Date": new_water.strftime("%m/%d/%Y"),
                    "Snooze Date": ""
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Added {new_name}!")
                st.rerun()

# 4. Plants to Water (Logic Upgrade)
if not df.empty:
    # Convert dates to actual date objects for math
    df['Last Watered Date'] = pd.to_datetime(df['Last Watered Date'], format="%m/%d/%Y").dt.date
    df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce').fillna(7).astype(int)
    
    # Logic: Today - Last Watered >= Frequency
    def needs_water(row):
        days_since = (today - row['Last Watered Date']).days
        is_snoozed = str(row.get('Snooze Date', "")) == today_str
        return days_since >= row['Frequency'] and not is_snoozed

    needs_action_df = df[df.apply(needs_water, axis=1)]
    count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""
    
    with st.expander(f"🚿 Plants to Water {count_label}", expanded=False):
        if not needs_action_df.empty:
            for index, row in needs_action_df.iterrows():
                with st.container(border=True):
                    cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                    with cols[0]:
                        st.markdown(f"**{row['Plant Name']}**")
                        st.caption(f"Every {row['Frequency']} days")
                    with cols[1]:
                        if st.button("💧", key=f"w_{index}"):
                            df.at[index, 'Last Watered Date'] = today_str
                            conn.update(data=df)
                            st.rerun()
                    with cols[2]:
                        if st.button("😴", key=f"s_{index}"):
                            df.at[index, 'Snooze Date'] = today_str
                            conn.update(data=df)
                            st.rerun()
        else:
            st.success("All plants are watered! ✨")

    # 5. Full Collection
    with st.expander("📋 View Full Collection"):
        st.dataframe(df[['Plant Name', 'Frequency', 'Last Watered Date']], 
                     use_container_width=True, hide_index=True)
