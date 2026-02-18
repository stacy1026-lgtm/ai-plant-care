import time 
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

st.set_page_config(page_title="Plant Garden", page_icon="🪴")

if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

conn = st.connection("gsheets", type=GSheetsConnection)

# --- START PRIME LOGIC ---
try:
    # Read once, and do NOT convert to string yet
    df = conn.read(ttl="10s")
    
    # Standardize data types for math
    df['Last Watered Date'] = pd.to_datetime(df['Last Watered Date'], errors='coerce')
    df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce').fillna(7).astype(int)
    
    # Ensure all needed columns exist
    for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Dismissed Gap', 'Acquisition Date']:
        if col not in df.columns:
            df[col] = 0 if col in ['Frequency', 'Dismissed Gap'] else ""
except Exception as e:
    st.error("🚦 Connection error. Please refresh.")
    st.stop()

today = date.today()
today_str = today.strftime("%m/%d/%Y")

# Header
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{len(df)}**")

# --- WATERING LOGIC ---
def needs_water(row):
    try:
        # Check Snooze
        snooze_val = row.get('Snooze Date')
        if pd.notna(snooze_val) and snooze_val != "":
            snooze_dt = pd.to_datetime(snooze_val, errors='coerce').date()
            if pd.notna(snooze_dt) and snooze_dt > today:
                return False
        
        # Check Date Math
        if pd.isna(row['Last Watered Date']):
            return True
            
        days_since = (today - row['Last Watered Date'].date()).days
        return days_since >= int(row['Frequency'])
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
                    last_w = row['Last Watered Date'].strftime("%m/%d/%Y") if pd.notna(row['Last Watered Date']) else "Never"
                    st.markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                    st.markdown(f"Last Watered on {last_w}")
                with cols[1]:
                    if st.button("💧", key=f"w_{index}"):
                        st.session_state.water_expanded = True
                        df.at[index, 'Last Watered Date'] = pd.Timestamp(today)
                        df.at[index, 'Snooze Date'] = ""
                        conn.update(data=df)
                        
                        # Log to History
                        hist = conn.read(worksheet="History", ttl=0)
                        new_log = pd.DataFrame([{"Plant Name": row['Plant Name'], "Date Watered": today_str, "Acquisition Date": row['Acquisition Date']}])
                        conn.update(worksheet="History", data=pd.concat([hist, new_log], ignore_index=True))
                        st.rerun()
                with cols[2]:
                    if st.button("😴", key=f"s_{index}"):
                        st.session_state.water_expanded = True
                        df.at[index, 'Snooze Date'] = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                        conn.update(data=df)
                        st.rerun()
    else:
        st.success("All plants are watered! ✨")

# --- ADD / DELETE SECTION ---
with st.expander("➕ Add / 💀 Remove"):
    # (Add your Add/Delete logic here if needed)
    pass

# --- FULL COLLECTION & ANALYSIS ---
if not df.empty:
    st.divider()
    # Unique Label for lookup
    df['Unique Label'] = df['Plant Name'] + " (" + df['Acquisition Date'].astype(str) + ")"

    with st.expander("📋 View Full Collection"):
        df_view = df.copy().sort_values(by='Plant Name')
        df_view['Next Water'] = df_view.apply(lambda r: (r['Last Watered Date'] + timedelta(days=r['Frequency'])).strftime("%m/%d/%Y") if pd.notna(r['Last Watered Date']) else "Needs Date", axis=1)
        # Final Format for Table View
        df_view['Last Watered Date'] = df_view['Last Watered Date'].dt.strftime("%m/%d/%Y").fillna("Never")
        st.dataframe(df_view[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], use_container_width=True, hide_index=True)

    # --- THE SMART ANALYSIS (Line 115 approx) ---
    with st.expander("📊 Smart Frequency Analysis", expanded=False):
        try:
            hist = conn.read(worksheet="History", ttl=0)
            if not hist.empty:
                hist['Date Watered'] = pd.to_datetime(hist['Date Watered']).dt.date
                suggestions_found = False
                
                for (p_name, p_acq), p_history in hist.groupby(['Plant Name', 'Acquisition Date']):
                    p_dates = p_history['Date Watered'].sort_values()
                    
                    if len(p_dates) >= 3:
                        avg_gap = int((p_dates.diff().mean()).days)
                        match = df[(df['Plant Name'] == p_name) & (df['Acquisition Date'] == p_acq)]
                        
                        if not match.empty:
                            idx = match.index[0]
                            current_f = int(match['Frequency'].values[0])
                            
                            if avg_gap != current_f:
                                suggestions_found = True
                                with st.container(border=True):
                                    st.write(f"### {p_name}")
                                    st.write(f"Recommended: **{avg_gap} days** (Current: {current_f}d)")
                                    if st.button("Update Frequency", key=f"up_{idx}"):
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
