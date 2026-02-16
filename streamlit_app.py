import time 
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

# Set page config
st.set_page_config(page_title="Plant Garden", page_icon="🪴")

if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

conn = st.connection("gsheets", type=GSheetsConnection)

# --- START PRIME LOGIC ---
if 'df' not in st.session_state:
    try:
        raw_df = conn.read(ttl=0)
        # Standardize Dates and Types immediately on load
        raw_df['Last Watered Date'] = pd.to_datetime(raw_df['Last Watered Date'], errors='coerce')
        raw_df['Frequency'] = pd.to_numeric(raw_df['Frequency'], errors='coerce').fillna(7).astype(int)
        raw_df['Dismissed Count'] = pd.to_numeric(raw_df['Dismissed Count'], errors='coerce').fillna(0).astype(int)
        
        st.session_state.df = raw_df
    except Exception:
        st.error("🚦 API Limit reached. Please refresh in 1 minute.")
        st.stop()

# Always refer to session_state
df = st.session_state.df

# Ensure columns exist and create Unique Label
required_cols = ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 
                 'Dismissed Gap', 'Dismissed Count', 'Acquisition Date']

for col in required_cols:
    if col not in df.columns:
        df[col] = 0 if "Dismissed" in col or col == "Frequency" else ""

# The Unique Label is our "ID" to prevent IndexErrors
df['Unique Label'] = df['Plant Name'] + " (" + df['Acquisition Date'].astype(str) + ")"
# --- END PRIME LOGIC ---

total_plants = len(df) if not df.empty else 0
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# Header
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{total_plants}**")

def needs_water(row):
    try:
        # 1. Check Snooze Date
        snooze_val = row.get('Snooze Date')
        if pd.notna(snooze_val) and snooze_val != "":
            snooze_dt = pd.to_datetime(snooze_val, errors='coerce').date()
            if pd.notna(snooze_dt) and snooze_dt > today:
                return False 
        
        # 2. Check Frequency
        last_dt = row['Last Watered Date']
        if pd.isna(last_dt):
            return True
            
        days_since = (today - last_dt.date()).days
        return days_since >= int(row['Frequency'])
    except:
        return True

# Filtering
needs_action_df = df[df.apply(needs_water, axis=1)].sort_values(by='Plant Name')                        
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

# 1. WATERING SECTION
with st.expander(f"🚿 Plants to Water {count_label}", expanded=st.session_state.water_expanded):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                with cols[0]:
                    last_water_display = row['Last Watered Date'].strftime("%m/%d/%Y") if pd.notna(row['Last Watered Date']) else "Never"
                    st.markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                    st.markdown(f"Last Watered on {last_water_display}")
                
                with cols[1]:
                    if st.button("💧", key=f"w_{index}"):
                        st.session_state.water_expanded = True
                        # Update using Timestamp to maintain data types
                        st.session_state.df.at[index, 'Last Watered Date'] = pd.Timestamp(today)
                        st.session_state.df.at[index, 'Snooze Date'] = "" 
                        conn.update(data=st.session_state.df)
                        st.toast(f"Success! {row['Plant Name']} watered. 🌊")
                        time.sleep(0.5)
                        st.rerun()
                
                with cols[2]:
                    if st.button("😴", key=f"s_{index}"):
                        st.session_state.water_expanded = True
                        days_to_add = st.session_state.get(f"days_{index}", 2)
                        reappear_date = (today + timedelta(days=days_to_add)).strftime("%m/%d/%Y")
                        st.session_state.df.at[index, 'Snooze Date'] = reappear_date
                        conn.update(data=st.session_state.df)
                        st.rerun()

                    st.number_input("Days", 1, 14, 2, key=f"days_{index}", label_visibility="collapsed")
    else:
        st.success("All plants are watered! ✨")

# 2. ADD NEW PLANT
with st.expander("
