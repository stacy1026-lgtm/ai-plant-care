import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime  # Added datetime here
import pandas as pd

st.warning("⚠️ YOU ARE IN THE DEVELEPMENT ENVIRONMENT")
# 1. Initialize Session State (at the very top)
if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

st.set_page_config(page_title="Plant Garden", page_icon="🪴")
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# Ensure columns exist
for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name']:
    if col not in df.columns:
        df[col] = ""

total_plants = len(df) if not df.empty else 0
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# 2. Header
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{total_plants}**")

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
                st.rerun()

# 4. Processing & Display
if not df.empty:
    # Safely convert dates
    df['Last Watered Date'] = pd.to_datetime(df['Last Watered Date'], errors='coerce').dt.date
    df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce').fillna(7).astype(int)
    
    def needs_water(row):
        if pd.isna(row['Last Watered Date']): return True
        days_since = (today - row['Last Watered Date']).days
        snooze_val = str(row.get('Snooze Date', ""))
        is_snoozed = False
        if snooze_val and snooze_val.strip():
            try:
                reappear_dt = datetime.strptime(snooze_val, "%m/%d/%Y").date()
                is_snoozed = today < reappear_dt
            except:
                is_snoozed = False
        return days_since >= row['Frequency'] and not is_snoozed

    needs_action_df = df[df.apply(needs_water, axis=1)]
    count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""
    
    with st.expander(f"🚿 Plants to Water {count_label}", expanded=st.session_state.water_expanded):
        if not needs_action_df.empty:
            for index, row in needs_action_df.iterrows():
                with st.container(border=True):
                    cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                    with cols[0]:
                        st.markdown(f"**{row['Plant Name']}**")
                        st.caption(f"Due every {row['Frequency']} days")
                    with cols[1]:
                        if st.button("💧", key=f"w_{index}"):
                            st.session_state.water_expanded = True
                            
                            # 1. Update main table
                            df.at[index, 'Last Watered Date'] = today_str
                            conn.update(data=df)
                            
                            # 2. Append to History Safely
                            try:
                                # Read existing history
                                history_df = conn.read(worksheet="History", ttl=0)
                                # Create new row
                                new_log = pd.DataFrame([{"Plant Name": row['Plant Name'], "Date Watered": today_str}])
                                # Combine and update
                                updated_history = pd.concat([history_df, new_log], ignore_index=True)
                                conn.update(worksheet="History", data=updated_history)
                            except Exception as e:
                                st.error(f"Could not log history: {e}")
                            
                            st.rerun()
                    with cols[2]:
                        if st.button("😴", key=f"s_{index}"):
                            st.session_state.water_expanded = True
                            reappear_date = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                            df.at[index, 'Snooze Date'] = reappear_date
                            conn.update(data=df)
                            st.rerun()
        else:
            st.success("All plants are watered! ✨")

    # 5. Full Collection
    with st.expander("📋 View Full Collection"):
        df_view = df.copy()
        df_view['Next Water'] = df_view.apply(
            lambda r: r['Last Watered Date'] + timedelta(days=r['Frequency']) 
            if pd.notna(r['Last Watered Date']) else "Needs Date", axis=1
        )
        st.dataframe(df_view[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], 
                     use_container_width=True, hide_index=True)
else:
    st.info("Your garden is empty.")
