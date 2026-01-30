import time
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

# --- CONFIG & CONNECTION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
st.warning("⚠️ YOU ARE IN THE STAGING ENVIRONMENT")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. DATA LOADING (CACHED) ---
@st.cache_data(ttl=300) # Only hits Google once every 5 mins
def fetch_data():
    try:
        data = conn.read(ttl=0)
        # Force types and ensure columns
        data['Last Watered Date'] = data['Last Watered Date'].astype(str)
        data['Frequency'] = pd.to_numeric(data['Frequency'], errors='coerce').fillna(7)
        for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Dismissed Gap']:
            if col not in data.columns:
                data[col] = ""
        return data
    except Exception:
        return None

# Initialize Session State
if 'df' not in st.session_state:
    st.session_state.df = fetch_data()

if st.session_state.df is None:
    st.error("🏎️ Google is moving too fast! Please refresh in 1 minute.")
    st.stop()

if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

# Use state-based dataframe for the entire app
df = st.session_state.df
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# --- 2. THE SAVE FUNCTION (ONE PLACE FOR ALL WRITES) ---
def save_to_google(updated_df, worksheet=None, success_msg=None):
    try:
        if worksheet:
            conn.update(worksheet=worksheet, data=updated_df)
        else:
            conn.update(data=updated_df)
            st.session_state.df = updated_df # Keep local memory in sync
        
        if success_msg:
            st.toast(success_msg, icon="🪴")
        time.sleep(1) # API breather
        return True
    except Exception:
        st.error("🚦 Google is busy. Change saved locally, but might not be in the Sheet yet.")
        return False

# --- 3. LOGIC FUNCTIONS ---
def needs_water(row):
    try:
        t_dt = datetime.now().date()
        snooze_val = row.get('Snooze Date')
        if pd.notna(snooze_val) and snooze_val != "":
            s_dt = pd.to_datetime(snooze_val, errors='coerce').date()
            if pd.notna(s_dt) and s_dt > t_dt: return False
        
        l_val = row.get('Last Watered Date')
        l_dt = pd.to_datetime(l_val, errors='coerce').date()
        if pd.isna(l_dt): return True
        
        return (t_dt - l_dt).days >= int(row['Frequency'])
    except:
        return True

# --- 4. HEADER & SYNC ---
st.title("🪴 My Plant Garden")
if st.button("🔄 Sync with Google Sheets"):
    st.cache_data.clear()
    st.session_state.df = fetch_data()
    st.rerun()

st.markdown(f"### Total Plants: **{len(df)}**")

# --- 5. WATERING SECTION ---
needs_action_df = df[df.apply(needs_water, axis=1)].sort_values(by='Plant Name')
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

with st.expander(f"🚿 Plants to Water {count_label}", expanded=st.session_state.water_expanded):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                cols[0].markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                cols[0].caption(f"Last: {row['Last Watered Date']} | Every {row['Frequency']} days")
                
                # WATER BUTTON
                if cols[1].button("💧", key=f"w_{index}"):
                    df.at[index, 'Last Watered Date'] = today_str
                    df.at[index, 'Snooze Date'] = ""
                    if save_to_google(df, success_msg=f"{row['Plant Name']} Watered!"):
                        # Log History
                        hist = conn.read(worksheet="History", ttl="5m")
                        new_log = pd.DataFrame([{"Plant Name": row['Plant Name'], "Date Watered": today_str, "Acquisition Date": row['Acquisition Date']}])
                        save_to_google(pd.concat([hist, new_log], ignore_index=True), worksheet="History")
                        st.rerun()

                # SNOOZE BUTTON
                if cols[2].button("😴", key=f"s_{index}"):
                    df.at[index, 'Snooze Date'] = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                    if save_to_google(df, success_msg="Snoozed for 2 days"):
                        st.rerun()
    else:
        st.success("All plants are watered! ✨")

# --- 6. ADD NEW PLANT ---
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant", clear_on_submit=True):
        n_name = st.text_input("Plant Name")
        n_freq = st.number_input("Frequency (Days)", min_value=1, value=7)
        n_acq = st.date_input("Acquisition Date", format="MM/DD/YYYY")
        n_wat = st.date_input("Last Watered", format="MM/DD/YYYY")
        if st.form_submit_button("Add to Collection") and n_name:
            new_row = pd.DataFrame([{"Plant Name": n_name, "Frequency": int(n_freq), "Acquisition Date": n_acq.strftime("%m/%d/%Y"), "Last Watered Date": n_wat.strftime("%m/%d/%Y"), "Snooze Date": "", "Dismissed Gap": 0}])
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_google(df, success_msg="New plant added!"):
                st.rerun()

# --- 7. CEMETERY ---
with st.expander("💀 Plant Cemetery"):
    if not df.empty:
        df['Display'] = df['Plant Name'] + " (" + df['Acquisition Date'].astype(str) + ")"
        choice = st.selectbox("Select plant:", options=df['Display'].tolist(), index=None)
        if choice:
            idx_rem = df[df['Display'] == choice].index[0]
            reason = st.text_input("Reason?")
            if st.button("Confirm Removal", type="primary"):
                # Optional: Log to Graveyard here using save_to_google(worksheet="Graveyard")
                df = df.drop(idx_rem)
                if save_to_google(df, success_msg="Moved to cemetery"):
                    st.rerun()

# --- 8. FULL COLLECTION TABLE ---
st.divider()
with st.expander("📋 View Full Collection"):
    df_view = df.copy().sort_values(by='Plant Name')
    df_view['Next Water'] = df_view.apply(lambda r: pd.to_datetime(r['Last Watered Date']).date() + timedelta(days=int(r['Frequency'])) if pd.notna(r['Last Watered Date']) else "Needs Date", axis=1)
    st.dataframe(df_view[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], use_container_width=True, hide_index=True)

# --- 9. SMART ANALYSIS ---
with st.expander("📊 Smart Frequency Analysis"):
    try:
        hist = conn.read(worksheet="History", ttl="10m")
        if not hist.empty:
            hist['Date Watered'] = pd.to_datetime(hist['Date Watered']).dt.date
            for (p_name, p_acq), p_hist in hist.groupby(['Plant Name', 'Acquisition Date']):
                p_dates = p_hist['Date Watered'].sort_values()
                if len(p_dates) >= 3:
                    avg_gap = int((p_dates.diff().mean()).days)
                    match = df[(df['Plant Name'] == p_name) & (df['Acquisition Date'] == p_acq)]
                    if not match.empty:
                        idx = match.index[0]
                        curr_f = int(match['Frequency'].values[0])
                        if avg_gap != curr_f:
                            st.write(f"**{p_name}**: Avg {avg_gap} days (Current: {curr_f}d)")
                            if st.button("✔️ Update", key=f"up_{idx}"):
                                df.at[idx, 'Frequency'] = avg_gap
                                if save_to_google(df): st.rerun()
        else:
            st.info("Need more history for analysis.")
    except:
        st.write("History tab busy.")
