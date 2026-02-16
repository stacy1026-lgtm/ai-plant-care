import time 
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
import pandas as pd

# Set page config

st.warning("⚠️ YOU ARE IN THE STAGING ENVIRONMENT")
# 1. Initialize Session State (at the very top)
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
                    "Last Watered Date": pd.Timestamp(new_water),
                    "Snooze Date": "",
                    "Dismissed Gap": 0,
                    "Dismissed Count": 0
                }])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                conn.update(data=st.session_state.df)
                st.rerun()

# 3. PLANT CEMETERY (Safe Delete)
with st.expander("💀 Plant Cemetery"):
    if not df.empty:
        selected_label = st.selectbox(
            "Select the plant that didn't make it:",
            options=df['Unique Label'].tolist(),
            index=None,
            placeholder="Type plant name..."
        )
        
        if selected_label:
            matches = df[df['Unique Label'] == selected_label]
            if not matches.empty:
                idx_to_remove = matches.index[0]
                plant_name = df.at[idx_to_remove, 'Plant Name']
                reason = st.text_input("Reason", placeholder="Optional")
                
                if st.button("Confirm Removal", type="primary"):
                    # Remove immediately from state and update sheet
                    st.session_state.df = st.session_state.df.drop(idx_to_remove)
                    conn.update(data=st.session_state.df)
                    st.success(f"{plant_name} moved to the cemetery.")
                    st.rerun()

# 4. FULL COLLECTION DISPLAY
st.divider()
with st.expander("📋 View Full Collection"):
    if not df.empty:
        # Quick Update Logic
        st.write("### ⚡ Quick Update")
        col1, col2 = st.columns([0.7, 0.3])
        
        # Safety match using Unique Label
        all_options = df.sort_values(by='Plant Name')['Unique Label'].tolist()
        selected_target = col1.selectbox("Mark as watered:", options=all_options, key="manual_water")
        
        if col2.button("💧 Water Now", use_container_width=True):
            match = df[df['Unique Label'] == selected_target]
            if not match.empty:
                target_idx = match.index[0]
                st.session_state.df.at[target_idx, 'Last Watered Date'] = pd.Timestamp(today)
                conn.update(data=st.session_state.df)
                st.rerun()

        # Final UI Table
        df_view = df.copy().sort_values(by='Plant Name')
        
        # Calculate Next Water
        df_view['Next Water'] = df_view.apply(
            lambda r: (r['Last Watered Date'] + timedelta(days=r['Frequency'])).strftime("%m/%d/%Y") 
            if pd.notna(r['Last Watered Date']) else "Needs Date", axis=1
        )
        
        # Format display dates
        df_view['Last Watered Date'] = df_view['Last Watered Date'].dt.strftime("%m/%d/%Y").fillna("Never")

        st.dataframe(df_view[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Your garden is empty.")
