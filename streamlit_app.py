import time 
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

st.warning("⚠️ YOU ARE IN THE STAGING ENVIRONMENT")

# 1. Initialize Session State
if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

st.set_page_config(page_title="Plant Garden", page_icon="🪴")
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl="10s")
except Exception as e:
    st.error("🚦 Whoa, slow down lady! Please refresh in 1 minute.")
    st.stop()

# Ensure columns exist immediately
for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Dismissed Gap', 'Acquisition Date']:
    if col not in df.columns:
        df[col] = 0 if col in ['Frequency', 'Dismissed Gap'] else ""

total_plants = len(df) if not df.empty else 0
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# 2. Header
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{total_plants}**")

def needs_water(row):
    try:
        today_dt = datetime.now().date()
        snooze_val = row.get('Snooze Date')
        if pd.notna(snooze_val) and snooze_val != "":
            snooze_dt = pd.to_datetime(snooze_val, errors='coerce').date()
            if pd.notna(snooze_dt) and snooze_dt > today_dt:
                return False 
        
        last_val = row.get('Last Watered Date')
        last_dt = pd.to_datetime(last_val, errors='coerce').date()
        if pd.isna(last_dt):
            return True
            
        frequency = int(row['Frequency'])
        days_since = (today_dt - last_dt).days
        return days_since >= frequency
    except:
        return True

needs_action_df = df[df.apply(needs_water, axis=1)].sort_values(by='Plant Name')                            
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

with st.expander(f"🚿 Plants to Water {count_label}", expanded=st.session_state.water_expanded):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                with cols[0]:
                    st.markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                    st.markdown(f"Last Watered on {row['Last Watered Date']}")
                with cols[1]:
                    if st.button("💧", key=f"w_{index}"):
                        st.session_state.water_expanded = True
                        df.at[index, 'Last Watered Date'] = today_str
                        df.at[index, 'Snooze Date'] = "" 
                        conn.update(data=df)
                        
                        # Log to History
                        try:
                            history_df = conn.read(worksheet="History", ttl="1m")
                            new_log = pd.DataFrame([{"Plant Name": row['Plant Name'], "Date Watered": today_str, "Acquisition Date": row['Acquisition Date']}])
                            conn.update(worksheet="History", data=pd.concat([history_df, new_log], ignore_index=True))
                        except: pass
                        st.rerun()
                with cols[2]:
                    if st.button("😴", key=f"s_{index}"):
                        st.session_state.water_expanded = True
                        df.at[index, 'Snooze Date'] = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                        conn.update(data=df)
                        st.rerun()
    else:
        st.success("All plants are watered! ✨")

# 3. Add / Delete Sections
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_freq = st.number_input("Watering Frequency (Days)", min_value=1, value=7)
        new_acq = st.date_input("Acquisition Date", format="MM/DD/YYYY")
        new_water = st.date_input("Last Watered Date", format="MM/DD/YYYY")
        if st.form_submit_button("Add to Collection"):
            if new_name:
                new_row = pd.DataFrame([{"Plant Name": new_name, "Frequency": int(new_freq), "Acquisition Date": new_acq.strftime("%m/%d/%Y"), "Last Watered Date": new_water.strftime("%m/%d/%Y"), "Snooze Date": "", "Dismissed Gap": 0}])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.rerun()

# 4. Full Collection Display
if not df.empty:
    st.divider()
    with st.expander("📋 View Full Collection"):
        df_view = df.copy().sort_values(by='Plant Name')
        # Convert for calculation
        df_view['LW_Date'] = pd.to_datetime(df_view['Last Watered Date'], errors='coerce')
        df_view['Next Water'] = df_view.apply(lambda r: (r['LW_Date'] + timedelta(days=int(r['Frequency']))).strftime("%m/%d/%Y") if pd.notna(r['LW_Date']) else "Needs Date", axis=1)
        st.dataframe(df_view[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], use_container_width=True, hide_index=True)

    # 5. Smart Frequency Analysis (MOVED OUTSIDE PREVIOUS BLOCKS)
    with st.expander("📊 Smart Frequency Analysis", expanded=False):
        try:
            hist = conn.read(worksheet="History", ttl=0)
            if not hist.empty:
                hist['Date Watered'] = pd.to_datetime(hist['Date Watered'], errors='coerce').dt.date
                suggestions_found = False
                
                for (p_name, p_acq), p_history in hist.groupby(['Plant Name', 'Acquisition Date']):
                    p_dates = p_history['Date Watered'].dropna().sort_values()
                    if len(p_dates) >= 3:
                        gaps = p_dates.diff().dt.days.dropna()
                        avg_gap = int(gaps.mean())
                        
                        match = df[(df['Plant Name'] == p_name) & (df['Acquisition Date'] == p_acq)]
                        if not match.empty:
                            idx = match.index[0]
                            current_f = int(match.iloc[0]['Frequency'])
                            if avg_gap != current_f:
                                suggestions_found = True
                                with st.container(border=True):
                                    st.write(f"### {p_name}")
                                    st.write(f"Average gap is **{avg_gap} days** (Current: {current_f}d)")
                                    if st.button("Update", key=f"smart_{idx}"):
                                        df.at[idx, 'Frequency'] = avg_gap
                                        conn.update(data=df)
                                        st.rerun()
                if not suggestions_found:
                    st.write("Frequencies match your habits!")
            else:
                st.info("Log 3+ waterings for insights.")
        except Exception as e:
            st.error(f"Analysis Error: {e}")
else:
    st.info("Your garden is empty.")
