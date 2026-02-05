import time
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

# --- CONFIG & CONNECTION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. DATA LOADING ---
@st.cache_data(ttl=60)
def fetch_data():
    try:
        data = conn.read(ttl=0)
        data['Last Watered Date'] = data['Last Watered Date'].astype(str)
        data['Frequency'] = pd.to_numeric(data['Frequency'], errors='coerce').fillna(7)
        for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Acquisition Date']:
            if col not in data.columns: data[col] = ""
        return data
    except: return None

# Initialize Session State
if 'df' not in st.session_state or st.session_state.df is None:
    st.session_state.df = fetch_data()

if st.session_state.df is None:
    st.error("🏎️ Google is busy! Please refresh.")
    st.stop()

# Helper Variables
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# --- 2. SAVE FUNCTION ---
def save_to_google(updated_df, worksheet=None, success_msg=None):
    try:
        if worksheet:
            conn.update(worksheet=worksheet, data=updated_df)
        else:
            conn.update(data=updated_df)
            st.session_state.df = updated_df 
        if success_msg:
            st.toast(success_msg, icon="🪴")
        return True
    except:
        st.error("🚦 Google busy. Saved locally.")
        return False

# --- 3. WATERING LOGIC ---
def needs_water(row):
    try:
        t_dt = datetime.now().date()
        s_val = row.get('Snooze Date')
        if pd.notna(s_val) and s_val != "":
            s_dt = pd.to_datetime(s_val, errors='coerce').date()
            if s_dt > t_dt: return False
        l_dt = pd.to_datetime(row.get('Last Watered Date'), errors='coerce').date()
        if pd.isna(l_dt): return True
        return (t_dt - l_dt).days >= int(row['Frequency'])
    except: return True

# --- 4. DISPLAY ---
st.title("🪴 My Plant Garden")

# Filter needs_action_df using the state
needs_action_df = st.session_state.df[st.session_state.df.apply(needs_water, axis=1)].sort_values(by='Plant Name')
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

with st.expander(f"🚿 Plants to Water {count_label}", expanded=True):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                cols[0].markdown(f"**{row['Plant Name']}**")
                cols[0].caption(f"Last: {row['Last Watered Date']} | Every {row['Frequency']} days")
                
                # WATER BUTTON
                if cols[1].button("💧", key=f"w_{index}"):
                    st.session_state.df.at[index, 'Last Watered Date'] = today_str
                    st.session_state.df.at[index, 'Snooze Date'] = ""
                    if save_to_google(st.session_state.df, success_msg="Watered!"):
                        st.rerun()

                # SNOOZE BUTTON
                if cols[2].button("😴", key=f"s_{index}"):
                    new_snooze = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                    st.session_state.df.at[index, 'Snooze Date'] = new_snooze
                    if save_to_google(st.session_state.df, success_msg="Snoozed!"):
                        st.rerun()
    else:
        st.success("All plants are watered! ✨")
