import time
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

# --- CONFIG & CONNECTION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
st.warning("⚠️ YOU ARE IN THE DEVELOPMENT ENVIRONMENT")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. DATA LOADING ---
@st.cache_data(ttl=60) # Reduced to 1 min since Sync button is gone
def fetch_data():
    try:
        data = conn.read(ttl=0)
        data['Last Watered Date'] = data['Last Watered Date'].astype(str)
        data['Frequency'] = pd.to_numeric(data['Frequency'], errors='coerce').fillna(7)
        for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Dismissed Gap', 'Acquisition Date']:
            if col not in data.columns: data[col] = ""
        return data
    except Exception:
        return None

if 'df' not in st.session_state:
    st.session_state.df = fetch_data()

if st.session_state.df is None:
    st.error("🏎️ Google is moving too fast! Please refresh.")
    st.stop()

df = st.session_state.df
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# --- 2. THE SAVE FUNCTION ---
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
    except Exception:
        st.error("🚦 Google busy. Saved locally.")
        return False

# --- 3. LOGIC ---
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

# --- 4. HEADER ---
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{len(df)}**")

# --- 5. WATERING SECTION ---
# We re-filter every run so plants disappear naturally when state updates
needs_action_df = st.session_state.df[st.session_state.df.apply(needs_water, axis=1)].sort_values(by='Plant Name')
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

with st.expander(f"🚿 Plants to Water {count_label}", expanded=True):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                cols[0].markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                cols[0].caption(f"Last: {row['Last Watered Date']} | Every {row['Frequency']} days")
                
                if cols[1].button("💧", key=f"w_{index}"):
                    st.session_state.df.at[index, 'Last Watered Date'] = today_str
                    st.session_state.df.at[index, 'Snooze Date'] = ""
                    if save_to_google(st.session_state.df, success_msg=f"{row['Plant Name']} Watered!"):
                        # Log history in background
                        h_df = conn.read(worksheet="History", ttl="5m")
                        new_log = pd.DataFrame([{"Plant Name": row['Plant Name'], "Date Watered": today_str, "Acquisition Date": row['Acquisition Date']}])
                        conn.update(worksheet="History", data=pd.concat([h_df, new_log], ignore_index=True))

                if cols[2].button("😴", key=f"s_{index}"):
                    st.session_state.df.at[index, 'Snooze Date'] = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                    save_to_google(st.session_state.df, success_msg="Snoozed 2 days")
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
            new_r = pd.DataFrame([{"Plant Name": n_name, "Frequency": int(n_freq), "Acquisition Date": n_acq.strftime("%m/%d/%Y"), "Last Watered Date": n_wat.strftime("%m/%d/%Y"), "Snooze Date": "", "Dismissed Gap": 0}])
            st.session_state.df = pd.concat([st.session_state.df, new_r], ignore_index=True)
            save_to_google(st.session_state.df, success_msg="Added!")

# --- 7. CEMETERY ---
with st.expander("💀 Plant Cemetery"):
    if not st.session_state.df.empty:
        st.session_state.df['Display'] = st.session_state.df['Plant Name'] + " (" + st.session_state.df['Acquisition Date'].astype(str) + ")"
        choice = st.selectbox("Select plant:", options=st.session_state.df['Display'].tolist(), index=None)
        if choice and st.button("Confirm Removal", type="primary"):
            idx_rem = st.session_state.df[st.session_state.df['Display'] == choice].index[0]
            st.session_state.df = st.session_state.df.drop(idx_rem)
            save_to_google(st.session_state.df, success_msg="Removed")

# --- 8. FULL COLLECTION ---
st.divider()
with st.expander("📋 View Full Collection"):
    if not st.session_state.df.empty:
        st.write("### ⚡ Quick Update")
        c1, c2 = st.columns([0.7, 0.3])
        sel = c1.selectbox("Water immediately:", options=st.session_state.df.sort_values('Plant Name').apply(lambda r: f"{r['Plant Name']} ({r['Acquisition Date']})", axis=1))
        if c2.button("💧 Water Now"):
            p_n = sel.split(" (")[0]
            p_a = sel.split(" (")[1].replace(")", "")
            idx = st.session_state.df[(st.session_state.df['Plant Name'] == p_n) & (st.session_state.df['Acquisition Date'] == p_a)].index[0]
            st.session_state.df.at[idx, 'Last Watered Date'] = today_str
            st.session_state.df.at[idx, 'Snooze Date'] = ""
            save_to_google(st.session_state.df, success_msg=f"Updated {p_n}")
        
        st.write("---")
        df_v = st.session_state.df.copy().sort_values('Plant Name')
        df_v['Next Water'] = df_v.apply(lambda r: pd.to_datetime(r['Last Watered Date']).date() + timedelta(days=int(r['Frequency'])) if pd.notna(r['Last Watered Date']) else "Needs Date", axis=1)
        st.dataframe(df_v[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], use_container_width=True, hide_index=True)

# --- 9. SMART ANALYSIS ---
with st.expander("📊 Smart Frequency Analysis"):
    try:
        hist = conn.read(worksheet="History", ttl="10m")
        if not hist.empty:
            hist['Date Watered'] = pd.to_datetime(hist['Date Watered']).dt.date
            for (p_n, p_a), p_h in hist.groupby(['Plant Name', 'Acquisition Date']):
                p_d = p_h['Date Watered'].sort_values()
                if len(p_d) >= 3:
                    avg = int((p_d.diff().mean()).days)
                    match = st.session_state.df[(st.session_state.df['Plant Name'] == p_n) & (st.session_state.df['Acquisition Date'] == p_a)]
                    if not match.empty:
                        idx = match.index[0]
                        if avg != int(match['Frequency'].values[0]):
                            st.write(f"**{p_n}**: Avg {avg}d")
                            if st.button("✔️ Update", key=f"up_{idx}"):
                                st.session_state.df.at[idx, 'Frequency'] = avg
                                save_to_google(st.session_state.df)
    except: st.write("History busy.")
