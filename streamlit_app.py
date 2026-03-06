import time
import streamlit as st
import pytz
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

# 1. Config & Setup
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
local_tz = pytz.timezone('US/Eastern') # Adjust if needed
today_local = datetime.now(local_tz).date()
today_str = today_local.strftime("%m/%d/%Y")

# 2. Load and Prime Data
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df = conn.read(ttl="10s")
    # Clean and Prime
    df['Plant Name'] = df['Plant Name'].fillna('Unknown')
    df['Acquisition Date'] = df['Acquisition Date'].fillna('No Date')
    df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce').fillna(7).astype(int)
    # The "Unique Label" is created once here for the whole app
    df['Unique Label'] = df['Plant Name'] + " (" + df['Acquisition Date'].astype(str) + ")"
except Exception as e:
    st.error("🚦 Whoa, slow down lady! Not even Google works that fast. Please refresh in 1 minute.")
    st.stop()

# 3. Session State
if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{len(df)}**")

# 4. Helper: Needs Water
def needs_water(row):
    try:
        snooze_val = row.get('Snooze Date')
        if pd.notna(snooze_val) and snooze_val != "":
            snooze_dt = pd.to_datetime(snooze_val, errors='coerce').date()
            if snooze_dt > today_local: return False
        
        last_val = row.get('Last Watered Date')
        last_dt = pd.to_datetime(last_val, errors='coerce').date()
        if pd.isna(last_dt): return True
        
        return (today_local - last_dt).days >= int(row['Frequency'])
    except: return True

# 5. UI Sections
needs_action_df = df[df.apply(needs_water, axis=1)].sort_values(by='Plant Name')
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

with st.expander(f"🚿 Plants to Water {count_label}", expanded=st.session_state.water_expanded):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                if st.button("💧 Watered Today", key=f"w_{index}"):
                    df.at[index, 'Last Watered Date'] = today_str
                    df.at[index, 'Snooze Date'] = ""
                    conn.update(data=df)
                    st.rerun()
    else:
        st.success("All plants are watered! ✨")

# Add New Plant Form... (use today_str for default dates)
# Cemetery Section... (use df['Unique Label'])
# Smart Analysis...
